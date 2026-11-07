import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from app.data_pipeline import (
    CollectionError,
    SOURCES,
    _agridata_job_creation_records,
    _bmo_xlsx_records,
    _ckan_result,
    _eurostat_records,
    _vocational_specialty_records,
    _world_bank_records,
    collect_sources,
)
from app.synthetic_data import generate_synthetic_offers, write_synthetic_offers


def test_synthetic_offers_are_reproducible_and_marked_as_fake() -> None:
    first = list(generate_synthetic_offers(seed=8, count=12))
    second = list(generate_synthetic_offers(seed=8, count=12))

    assert first == second
    assert len(first) == 12
    assert all(record["is_synthetic"] is True for record in first)
    assert all(record["source"] == "synthetic" for record in first)
    assert len({record["id"] for record in first}) == 12


def test_synthetic_writer_is_byte_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    write_synthetic_offers(first, seed=3, count=5)
    write_synthetic_offers(second, seed=3, count=5)

    assert first.read_bytes() == second.read_bytes()


def test_synthetic_generator_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="count"):
        list(generate_synthetic_offers(seed=1, count=-1))


def test_eurostat_normalizer_extracts_periods_and_values() -> None:
    response: dict[str, Any] = {
        "id": ["freq", "age", "unit", "sex", "geo", "time"],
        "size": [1, 1, 1, 1, 1, 3],
        "dimension": {
            "time": {"category": {"index": {"2022": 0, "2023": 1, "2024": 2}}}
        },
        "value": {"0": 7.3, "1": 7.4, "2": 7.2},
        "status": {"0": "d", "1": "d", "2": "p"},
    }

    assert _eurostat_records(response) == [
        {
            "period": "2022",
            "value": 7.3,
            "unit": "percent of labour force",
            "country": "FR",
            "measure": "unemployment_rate",
            "status": "d",
        },
        {
            "period": "2023",
            "value": 7.4,
            "unit": "percent of labour force",
            "country": "FR",
            "measure": "unemployment_rate",
            "status": "d",
        },
        {
            "period": "2024",
            "value": 7.2,
            "unit": "percent of labour force",
            "country": "FR",
            "measure": "unemployment_rate",
            "status": "p",
        },
    ]


def test_eurostat_normalizer_rejects_unexpected_dimensions() -> None:
    response: dict[str, Any] = {
        "id": ["geo", "time"],
        "size": [2, 1],
        "dimension": {"time": {"category": {"index": {"2024": 0}}}},
        "value": {"0": 7.2},
    }
    with pytest.raises(CollectionError, match="unexpected"):
        _eurostat_records(response)


def test_world_bank_normalizer_preserves_tunisia_indicator_provenance() -> None:
    source = SOURCES["worldbank-tn-unemployment"]
    response: list[Any] = [
        {"page": 1, "pages": 1, "total": 2, "lastupdated": "2026-10-08"},
        [
            {
                "indicator": {
                    "id": "SL.UEM.TOTL.ZS",
                    "value": "Unemployment, total (% of total labor force) (modeled ILO estimate)",
                },
                "countryiso3code": "TUN",
                "date": "2025",
                "value": 15.108,
            },
            {
                "indicator": {"id": "SL.UEM.TOTL.ZS", "value": "Unemployment"},
                "countryiso3code": "TUN",
                "date": "2024",
                "value": None,
            },
        ],
    ]

    assert _world_bank_records(response, source) == [
        {
            "country": "TN",
            "country_name": "Tunisia",
            "indicator_id": "SL.UEM.TOTL.ZS",
            "indicator": (
                "Unemployment, total (% of total labor force) "
                "(modeled ILO estimate)"
            ),
            "period": "2025",
            "value": 15.108,
            "unit": "percent",
            "methodology": "World Bank indicator based on modelled ILO estimates.",
            "source_id": "worldbank-tn-unemployment",
            "provider": "World Bank, World Development Indicators",
            "source_url": (
                "https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=TN"
            ),
            "updated_at": "2026-10-08",
            "record_type": "labour_market_observation",
        }
    ]


def test_world_bank_normalizer_rejects_wrong_indicator_and_invalid_values() -> None:
    source = SOURCES["worldbank-tn-unemployment"]
    with pytest.raises(CollectionError, match="unexpected indicator"):
        _world_bank_records(
            [
                {},
                [{"indicator": {"id": "OTHER"}, "date": "2025", "value": 15.1}],
            ],
            source,
        )
    with pytest.raises(CollectionError, match="non-numeric"):
        _world_bank_records(
            [
                {},
                [
                    {
                        "indicator": {"id": source.indicator_id},
                        "countryiso3code": "TUN",
                        "date": "2025",
                        "value": "15.1",
                    }
                ],
            ],
            source,
        )
    with pytest.raises(CollectionError, match="unexpected country"):
        _world_bank_records(
            [
                {},
                [
                    {
                        "indicator": {"id": source.indicator_id},
                        "countryiso3code": "FRA",
                        "date": "2025",
                        "value": 15.1,
                    }
                ],
            ],
            source,
        )


def test_collector_writes_world_bank_tunisia_indicator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SOURCES["worldbank-tn-unemployment"]
    response = [
        {"page": 1, "pages": 1, "total": 1, "lastupdated": "2026-10-08"},
        [
            {
                "indicator": {"id": source.indicator_id, "value": source.title},
                "countryiso3code": "TUN",
                "date": "2025",
                "value": 15.108,
            }
        ],
    ]
    monkeypatch.setattr(
        "app.data_pipeline._request_bytes",
        lambda url, host: json.dumps(response).encode(),
    )

    manifest, failed = collect_sources(tmp_path, [source.id])

    assert not failed
    assert manifest[0]["status"] == "ok"
    assert manifest[0]["provider"] == "World Bank, World Development Indicators"
    assert manifest[0]["data_last_updated"] == "2026-10-08"
    assert manifest[0]["record_count"] == 1
    record = json.loads(
        (tmp_path / "normalized" / f"{source.id}.jsonl").read_text(encoding="utf-8")
    )
    assert record["country"] == "TN"
    assert record["period"] == "2025"
    assert record["value"] == 15.108


def test_vocational_specialty_normalizer_keeps_historical_bilingual_fields() -> None:
    content = (
        "القطاع;القطــاع الفرعي;رمز الاختصاص;تسمية الإختصاص;رمز;الشهادة;"
        "مدة التكوين بالسنة\n"
        "BTP;Building;301204;Ferrailleur;حدائدي;ش ك م;1\n"
        "; ;301205;Poseur de revêtements;مركب;ش ك م;2\n"
    ).encode("utf-8")

    records = _vocational_specialty_records(content)

    assert len(records) == 2
    assert records[0]["specialty_fr"] == "Ferrailleur"
    assert records[0]["specialty_ar"] == "حدائدي"
    assert records[1]["sector"] == "BTP"
    assert records[1]["subsector"] == "Building"
    assert records[0]["source_year"] == 2017
    assert records[0]["availability_status"] == (
        "historical_specialty_list_not_current_course_catalogue"
    )
    assert not any("phone" in key or "email" in key for key in records[0])


def test_agridata_normalizer_maps_job_creation_series_with_methodology() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([None, 2017, 2018, 2019, 2020, 2021, 2022])
    sheet.append(["Nombre d'emploi crées", 5719, 6654, 5464, 3965, 4288, 3541])
    content = BytesIO()
    workbook.save(content)
    workbook.close()

    records = _agridata_job_creation_records(content.getvalue())

    assert len(records) == 6
    assert records[0]["country"] == "TN"
    assert records[0]["period"] == "2017"
    assert records[0]["value"] == 5719
    assert records[-1]["period"] == "2022"
    assert records[-1]["value"] == 3541
    assert "not total employment or vacancies" in str(records[0]["methodology"])


def test_ckan_collector_checks_license_and_keeps_raw_resource_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SOURCES["tunisia-vocational-specialties"]
    resource_url = (
        "https://catalog.data.gov.tn/dataset/specialties.csv"
    )
    catalogue = {
        "success": True,
        "result": {
            "id": source.ckan_dataset_id,
            "title": source.title,
            "url": source.landing_page,
            "license_title": "cc-by",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "metadata_modified": "2023-03-14T18:04:03.369347",
            "organization": {"title": source.provider},
            "resources": [
                {
                    "name": "Liste des spécialités",
                    "format": "CSV",
                    "url": resource_url,
                    "last_modified": "2023-03-14T18:00:00",
                }
            ],
        },
    }
    csv_content = (
        "القطاع;القطــاع الفرعي;رمز الاختصاص;تسمية الإختصاص;رمز;الشهادة;"
        "مدة التكوين بالسنة\n"
        "BTP;Building;301204;Ferrailleur;حدائدي;ش ك م;1\n"
    ).encode("utf-8")

    def fake_request(url: str, hosts: set[str]) -> bytes:
        if url == source.url:
            assert hosts == {source.host}
            return json.dumps(catalogue, ensure_ascii=False).encode("utf-8")
        assert url == resource_url
        assert hosts == {source.host}
        return csv_content

    monkeypatch.setattr("app.data_pipeline._request_bytes", fake_request)

    manifest, failed = collect_sources(tmp_path, [source.id])

    assert not failed
    entry = manifest[0]
    assert entry["status"] == "ok"
    assert entry["license"] == "cc-by"
    assert entry["resource_title"] == "Liste des spécialités"
    assert entry["record_count"] == 1
    normalized = json.loads(
        (tmp_path / "normalized" / f"{source.id}.jsonl").read_text(encoding="utf-8")
    )
    assert normalized["specialty_fr"] == "Ferrailleur"


def test_ckan_normalizer_rejects_unreviewed_license() -> None:
    source = SOURCES["tunisia-vocational-specialties"]
    with pytest.raises(CollectionError, match="licence changed"):
        _ckan_result(
            {"result": {"id": source.ckan_dataset_id, "license_title": "other"}},
            source,
        )


def test_bmo_normalizer_maps_occupation_and_region_fields() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BMO_2026_open_data"
    sheet.append(
        [
            "annee",
            "Code métier BMO",
            "Nom métier BMO",
            "Famille_met",
            "Lbl_fam_met",
            "REG",
            "NOM_REG",
            "Dept",
            "NomDept",
            "BE26",
            "NOMBE26",
            "clpe",
            "met",
            "xmet",
            "smet",
        ]
    )
    sheet.append(
        [2026, "A0X40", "Agriculteurs", "Z", "Autres métiers", "01", "Guadeloupe",
         "971", "Guadeloupe", 101, "BASSIN BASSE-TERRE", "CLPE97101", "69", "30", "23"]
    )
    content = BytesIO()
    workbook.save(content)
    workbook.close()

    record = next(iter(_bmo_xlsx_records(content.getvalue())))

    assert record["occupation_code"] == "A0X40"
    assert record["region_code"] == "01"
    assert record["employment_area_code"] == "101"
    assert record["planned_recruitments"] == 69
    assert record["difficult_recruitments"] == 30
    assert record["seasonal_recruitments"] == 23
    assert record["country"] == "FR"


def test_collector_writes_raw_normalized_and_licence_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "id": ["freq", "age", "unit", "sex", "geo", "time"],
        "size": [1, 1, 1, 1, 1, 1],
        "dimension": {"time": {"category": {"index": {"2024": 0}}}},
        "value": {"0": 7.2},
        "status": {"0": "p"},
    }
    monkeypatch.setattr(
        "app.data_pipeline._request_bytes",
        lambda url, host: json.dumps(payload).encode(),
    )

    manifest, failed = collect_sources(tmp_path, ["eurostat-fr-unemployment"])

    assert not failed
    assert manifest[0]["status"] == "ok"
    assert manifest[0]["license"] == SOURCES["eurostat-fr-unemployment"].license
    assert (tmp_path / "raw" / "eurostat-fr-unemployment.json").exists()
    normalized = (tmp_path / "normalized" / "eurostat-fr-unemployment.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"period": "2024"' in normalized
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))[0]["status"] == "ok"


def test_collector_downloads_and_normalizes_latest_bmo_resource(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_url = "https://www.data.gouv.fr/api/1/datasets/561fa564c751df4f2acdbb48/"
    resource_url = (
        "https://www.francetravail.org/files/live/sites/peorg/files/documents/"
        "Statistiques-et-analyses/Open-data/BMO/Base-open-data-BMO-2026.xlsx"
    )
    metadata = {
        "id": "561fa564c751df4f2acdbb48",
        "title": "BMO",
        "page": "https://www.data.gouv.fr/datasets/example",
        "organization": {"name": "France Travail"},
        "license": "fr-lo",
        "resources": [
            {"id": "bmo-2026", "title": "Enquête BMO 2026", "format": "xlsx", "url": resource_url},
            {"id": "bmo-2025", "title": "Enquête BMO 2025", "format": "xlsx", "url": resource_url},
        ],
    }
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "annee",
            "Code métier BMO",
            "Nom métier BMO",
            "Famille_met",
            "Lbl_fam_met",
            "REG",
            "NOM_REG",
            "Dept",
            "NomDept",
            "BE26",
            "NOMBE26",
            "clpe",
            "met",
            "xmet",
            "smet",
        ]
    )
    sheet.append([2026, "A0X40", "Agriculteurs", "Z", "Autres métiers", "01", "Guadeloupe",
                  "971", "Guadeloupe", 101, "BASSIN BASSE-TERRE", "CLPE97101", "69", "30", "23"])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    workbook_bytes = content.getvalue()

    def fake_request(url: str, hosts: set[str]) -> bytes:
        if url == source_url:
            return json.dumps(metadata).encode()
        assert url == resource_url
        assert hosts == {"www.francetravail.org", "www.pole-emploi.org"}
        return workbook_bytes

    monkeypatch.setattr("app.data_pipeline._request_bytes", fake_request)

    manifest, failed = collect_sources(tmp_path, ["francetravail-bmo-catalog"])

    assert not failed
    assert manifest[0]["resource_year"] == 2026
    assert manifest[0]["record_count"] == 1
    assert (tmp_path / "raw" / "francetravail-bmo-2026.xlsx").read_bytes() == workbook_bytes
    bmo_record = json.loads(
        (tmp_path / "normalized" / "francetravail-bmo-2026.jsonl").read_text(encoding="utf-8")
    )
    assert bmo_record["occupation"] == "Agriculteurs"


def test_collector_records_source_failure_and_returns_failure_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(url: str, host: str) -> bytes:
        raise CollectionError("source unavailable")

    monkeypatch.setattr("app.data_pipeline._request_bytes", fail_request)

    manifest, failed = collect_sources(tmp_path, ["eurostat-fr-unemployment"])

    assert failed
    assert manifest[0]["status"] == "error"
    assert manifest[0]["error"] == "source unavailable"
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))[0]["status"] == "error"
