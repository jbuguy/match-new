import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from app.data_pipeline import (
    CollectionError,
    SOURCES,
    _bmo_xlsx_records,
    _eurostat_records,
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
