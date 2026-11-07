"""Download selected public labour-market data and store raw and normalized snapshots."""

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


LOGGER = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 20
BMO_RESOURCE_HOSTS = {"www.francetravail.org", "www.pole-emploi.org"}


@dataclass(frozen=True)
class DataSource:
    id: str
    title: str
    url: str
    host: str
    provider: str
    license: str
    landing_page: str
    format: str
    indicator_id: str | None = None
    ckan_dataset_id: str | None = None
    resource_name_contains: str | None = None
    resource_format: str | None = None
    resource_hosts: tuple[str, ...] = ()


SOURCES = {
    "eurostat-fr-unemployment": DataSource(
        id="eurostat-fr-unemployment",
        title="Unemployment by sex and age — annual data (France, total, age 15–74)",
        url=(
            "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            "une_rt_a?geo=FR&unit=PC_ACT&sex=T&age=Y15-74"
            "&sinceTimePeriod=2010&lang=en"
        ),
        host="ec.europa.eu",
        provider="Eurostat",
        license="Eurostat data reuse policy; attribution required.",
        landing_page="https://ec.europa.eu/eurostat/databrowser/view/une_rt_a/default/table",
        format="JSON-stat 2.0",
    ),
    "francetravail-bmo-catalog": DataSource(
        id="francetravail-bmo-catalog",
        title="Enquête Besoins en main-d’œuvre (BMO) — France Travail",
        url="https://www.data.gouv.fr/api/1/datasets/561fa564c751df4f2acdbb48/",
        host="www.data.gouv.fr",
        provider="France Travail via data.gouv.fr",
        license="Licence Ouverte / Open Licence (Etalab)",
        landing_page="https://www.data.gouv.fr/datasets/enquete-besoins-en-main-doeuvre-bmo",
        format="JSON metadata and resource catalogue",
    ),
    "worldbank-tn-unemployment": DataSource(
        id="worldbank-tn-unemployment",
        title="Unemployment, total (% of total labour force) — Tunisia",
        url=(
            "https://api.worldbank.org/v2/country/TUN/indicator/"
            "SL.UEM.TOTL.ZS?format=json&per_page=100&date=2010:2025"
        ),
        host="api.worldbank.org",
        provider="World Bank, World Development Indicators",
        license=(
            "World Bank Terms of Use for Datasets; attribution required and "
            "indicator-specific restrictions may apply."
        ),
        landing_page="https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=TN",
        format="World Bank Indicators API JSON",
        indicator_id="SL.UEM.TOTL.ZS",
    ),
    "worldbank-tn-youth-unemployment": DataSource(
        id="worldbank-tn-youth-unemployment",
        title="Unemployment, youth ages 15–24 (% of youth labour force) — Tunisia",
        url=(
            "https://api.worldbank.org/v2/country/TUN/indicator/"
            "SL.UEM.1524.ZS?format=json&per_page=100&date=2010:2025"
        ),
        host="api.worldbank.org",
        provider="World Bank, World Development Indicators",
        license=(
            "World Bank Terms of Use for Datasets; attribution required and "
            "indicator-specific restrictions may apply."
        ),
        landing_page="https://data.worldbank.org/indicator/SL.UEM.1524.ZS?locations=TN",
        format="World Bank Indicators API JSON",
        indicator_id="SL.UEM.1524.ZS",
    ),
    "worldbank-tn-employment-to-population": DataSource(
        id="worldbank-tn-employment-to-population",
        title="Employment to population ratio, ages 15+ — Tunisia",
        url=(
            "https://api.worldbank.org/v2/country/TUN/indicator/"
            "SL.EMP.TOTL.SP.ZS?format=json&per_page=100&date=2010:2025"
        ),
        host="api.worldbank.org",
        provider="World Bank, World Development Indicators",
        license=(
            "World Bank Terms of Use for Datasets; attribution required and "
            "indicator-specific restrictions may apply."
        ),
        landing_page="https://data.worldbank.org/indicator/SL.EMP.TOTL.SP.ZS?locations=TN",
        format="World Bank Indicators API JSON",
        indicator_id="SL.EMP.TOTL.SP.ZS",
    ),
    "tunisia-vocational-specialties": DataSource(
        id="tunisia-vocational-specialties",
        title="Liste des spécialités de la formation professionnelle en Tunisie en 2017",
        url=(
            "https://catalog.data.gov.tn/api/3/action/package_show"
            "?id=86fa57e3-4c1e-43ad-8cbb-ab9678f55848"
        ),
        host="catalog.data.gov.tn",
        provider="Ministère de l'Emploi et de la Formation professionnelle",
        license="cc-by",
        landing_page=(
            "https://catalog.data.gov.tn/dataset/"
            "liste-des-specialites-de-la-formation-professionnelle-en-tunisie-en-2017"
        ),
        format="CKAN JSON metadata and semicolon-delimited UTF-8 CSV",
        ckan_dataset_id="86fa57e3-4c1e-43ad-8cbb-ab9678f55848",
        resource_name_contains="liste",
        resource_format="CSV",
    ),
    "tunisia-agridata-jobs-created": DataSource(
        id="tunisia-agridata-jobs-created",
        title=(
            "Nombre de postes d'emploi créés par les investissements agricoles "
            "en Tunisie"
        ),
        url=(
            "https://catalog.data.gov.tn/api/3/action/package_show"
            "?id=20dfc498-397d-49d4-b0ff-b23d221e868a"
        ),
        host="catalog.data.gov.tn",
        provider="APIA via Tunisia National Open Data Catalogue",
        license="Licence Nationale de Données Publiques Ouvertes",
        landing_page="https://catalog.data.gov.tn/dataset/recapitulatif-de-l-investissement-agricole",
        format="CKAN JSON metadata and XLSX resource",
        ckan_dataset_id="20dfc498-397d-49d4-b0ff-b23d221e868a",
        resource_name_contains="postes d'emploi",
        resource_format="XLS",
        resource_hosts=("catalog.agridata.tn",),
    ),
}


class CollectionError(Exception):
    """Expected source, network, or payload error during collection."""


class _AllowedHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(
        self,
        request: urllib.request.Request,
        response: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        parsed = urllib.parse.urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise CollectionError(f"Refusing redirect outside configured HTTPS hosts: {new_url}")
        return super().redirect_request(request, response, code, message, headers, new_url)


def _request_bytes(url: str, expected_hosts: set[str]) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in expected_hosts:
        raise CollectionError(f"Refusing URL outside the configured HTTPS host: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MaharaMatch-open-data-collector/1.0",
        },
    )
    opener = urllib.request.build_opener(_AllowedHostRedirectHandler(expected_hosts))
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise CollectionError(f"Source returned HTTP {response.status}: {url}")
            final_url = urllib.parse.urlparse(response.geturl())
            if final_url.scheme != "https" or final_url.hostname not in expected_hosts:
                raise CollectionError(f"Source redirected outside configured HTTPS hosts: {url}")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise CollectionError(f"Source returned HTTP {error.code}: {url}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise CollectionError(f"Could not retrieve source {url}: {error}") from error
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectionError(f"Source exceeds the {MAX_RESPONSE_BYTES}-byte limit: {url}")
    return payload


def _eurostat_records(payload: dict[str, Any]) -> list[dict[str, object]]:
    dimensions = payload.get("dimension")
    values = payload.get("value")
    if not isinstance(dimensions, dict) or not isinstance(values, dict):
        raise CollectionError("Eurostat response is missing dimension or value data.")
    time_dimension = dimensions.get("time")
    if not isinstance(time_dimension, dict):
        raise CollectionError("Eurostat response has no time dimension.")
    time_category = time_dimension.get("category", {})
    time_indices = time_category.get("index")
    if not isinstance(time_indices, dict):
        raise CollectionError("Eurostat response has no time-period index.")
    dimension_ids = payload.get("id")
    dimension_sizes = payload.get("size")
    if not isinstance(dimension_ids, list) or not isinstance(dimension_sizes, list):
        raise CollectionError("Eurostat response has invalid dimension metadata.")
    time_position = dimension_ids.index("time") if "time" in dimension_ids else -1
    if time_position < 0 or any(
        size != 1 for position, size in enumerate(dimension_sizes) if position != time_position
    ):
        raise CollectionError("Eurostat response contains unexpected non-time dimensions.")

    status_values = payload.get("status", {})
    records: list[dict[str, object]] = []
    for period, position in sorted(time_indices.items(), key=lambda item: item[1]):
        value = values.get(str(position))
        if value is None:
            continue
        record: dict[str, object] = {
            "period": period,
            "value": value,
            "unit": "percent of labour force",
            "country": "FR",
            "measure": "unemployment_rate",
            "status": status_values.get(str(position)) if isinstance(status_values, dict) else None,
        }
        records.append(record)
    if not records:
        raise CollectionError("Eurostat response contains no observations for the selected filters.")
    return records


def _bmo_catalog_records(payload: dict[str, Any]) -> list[dict[str, object]]:
    resources = payload.get("resources")
    if not isinstance(resources, list):
        raise CollectionError("France Travail BMO dataset response has no resource catalogue.")
    organization = payload.get("organization")
    provider = organization.get("name") if isinstance(organization, dict) else None
    return [
        {
            "dataset_id": payload.get("id"),
            "dataset_title": payload.get("title"),
            "dataset_url": payload.get("page"),
            "provider": provider,
            "license": payload.get("license"),
            "resource_id": resource.get("id"),
            "resource_title": resource.get("title"),
            "format": resource.get("format"),
            "url": resource.get("url"),
            "last_modified": resource.get("last_modified"),
        }
        for resource in resources
        if isinstance(resource, dict)
    ]


def _world_bank_records(payload: Any, source: DataSource) -> list[dict[str, object]]:
    if (
        source.indicator_id is None
        or not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[1], list)
    ):
        raise CollectionError("World Bank response has an invalid indicators API structure.")

    records: list[dict[str, object]] = []
    metadata = payload[0]
    if not isinstance(metadata, dict):
        raise CollectionError("World Bank response is missing pagination metadata.")
    data_last_updated = metadata.get("lastupdated")
    for observation in payload[1]:
        if not isinstance(observation, dict):
            raise CollectionError("World Bank response contains an invalid observation.")
        indicator = observation.get("indicator")
        date = observation.get("date")
        value = observation.get("value")
        if not isinstance(indicator, dict) or indicator.get("id") != source.indicator_id:
            raise CollectionError("World Bank response contains an unexpected indicator.")
        if observation.get("countryiso3code") != "TUN":
            raise CollectionError("World Bank response contains an unexpected country.")
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}", date):
            raise CollectionError("World Bank observation has an invalid year.")
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CollectionError("World Bank observation has a non-numeric value.")
        records.append(
            {
                "country": "TN",
                "country_name": "Tunisia",
                "indicator_id": source.indicator_id,
                "indicator": indicator.get("value") or source.title,
                "period": date,
                "value": value,
                "unit": "percent",
                "methodology": "World Bank indicator based on modelled ILO estimates.",
                "source_id": source.id,
                "provider": source.provider,
                "source_url": source.landing_page,
                "updated_at": data_last_updated,
                "record_type": "labour_market_observation",
            }
        )
    if not records:
        raise CollectionError("World Bank response contains no numeric observations.")
    return records


def _ckan_result(payload: Any, source: DataSource) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict) or result.get("id") != source.ckan_dataset_id:
        raise CollectionError("Tunisia open-data catalogue returned an unexpected dataset.")
    if result.get("license_title") != source.license:
        raise CollectionError(
            f"Dataset licence changed from the reviewed licence for {source.id}."
        )
    return result


def _ckan_resource(
    payload: dict[str, Any],
    source: DataSource,
) -> dict[str, Any]:
    resources = payload.get("resources")
    if not isinstance(resources, list) or source.resource_name_contains is None:
        raise CollectionError(f"Dataset {source.id} has no configured resource selector.")
    candidates = [
        resource
        for resource in resources
        if isinstance(resource, dict)
        and str(resource.get("name", "")).casefold().find(
            source.resource_name_contains.casefold()
        ) >= 0
        and str(resource.get("format", "")).upper() == source.resource_format
    ]
    if len(candidates) != 1:
        raise CollectionError(
            f"Expected exactly one reviewed resource for {source.id}; found {len(candidates)}."
        )
    resource = candidates[0]
    resource_url = resource.get("url")
    allowed_hosts = set(source.resource_hosts) or {source.host}
    parsed = urllib.parse.urlparse(resource_url if isinstance(resource_url, str) else "")
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise CollectionError(
            f"Refusing resource URL outside the reviewed HTTPS hosts for {source.id}."
        )
    return resource


def _vocational_specialty_records(payload: bytes) -> list[dict[str, object]]:
    try:
        csv_text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CollectionError("Vocational specialty CSV must be UTF-8 encoded.") from error
    reader = csv.DictReader(StringIO(csv_text), delimiter=";")
    required_headers = {"رمز الاختصاص", "تسمية الإختصاص", "القطاع"}
    if not reader.fieldnames or not required_headers.issubset(reader.fieldnames):
        raise CollectionError("Vocational specialty CSV has unexpected columns.")
    records: list[dict[str, object]] = []
    current_sector = ""
    current_subsector = ""
    for row in reader:
        current_sector = (row.get("القطاع") or "").strip() or current_sector
        current_subsector = (row.get("القطــاع الفرعي") or "").strip() or current_subsector
        specialty_code = (row.get("رمز الاختصاص") or "").strip()
        specialty_fr = (row.get("تسمية الإختصاص") or "").strip()
        specialty_ar = (row.get("رمز") or "").strip()
        if not specialty_code or not (specialty_fr or specialty_ar):
            continue
        duration_value = (row.get("مدة التكوين بالسنة") or "").strip()
        try:
            duration = float(duration_value) if duration_value else None
        except ValueError as error:
            raise CollectionError("Vocational specialty duration is not numeric.") from error
        records.append(
            {
                "country": "TN",
                "record_type": "training_specialty",
                "source_year": 2017,
                "specialty_code": specialty_code,
                "specialty_fr": specialty_fr,
                "specialty_ar": specialty_ar,
                "sector": current_sector,
                "subsector": current_subsector,
                "certificate": (row.get("الشهادة") or "").strip(),
                "training_duration_years": duration,
                "language": "ar+fr",
                "availability_status": "historical_specialty_list_not_current_course_catalogue",
            }
        )
    if not records:
        raise CollectionError("Vocational specialty CSV contains no specialty records.")
    return records


def _agridata_job_creation_records(payload: bytes) -> list[dict[str, object]]:
    try:
        workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
    except (OSError, ValueError, zipfile.BadZipFile, InvalidFileException) as error:
        raise CollectionError(f"Could not read the APIA jobs workbook: {error}") from error

    try:
        sheet = workbook.worksheets[0] if workbook.worksheets else None
        if sheet is None:
            raise CollectionError("APIA jobs workbook has no worksheets.")
        rows = sheet.iter_rows(min_row=1, max_row=5, values_only=True)
        header = next(rows, ())
        years: dict[int, int] = {}
        for column, value in enumerate(header[1:], start=1):
            if isinstance(value, int) and not isinstance(value, bool) and 1900 <= value <= 2100:
                years[value] = column
            elif isinstance(value, str) and re.fullmatch(r"20\d{2}", value.strip()):
                years[int(value)] = column
        if not years:
            raise CollectionError("APIA jobs workbook has no annual header values.")

        job_row = None
        for row in rows:
            label = str(row[0] or "").casefold()
            if "emploi" in label:
                job_row = row
                break
        if job_row is None:
            raise CollectionError("APIA jobs workbook has no job-creation measure row.")

        records: list[dict[str, object]] = []
        for year, column in sorted(years.items()):
            value = job_row[column] if column < len(job_row) else None
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CollectionError("APIA jobs workbook contains a non-numeric observation.")
            records.append(
                {
                    "country": "TN",
                    "country_name": "Tunisia",
                    "record_type": "labour_market_observation",
                    "indicator": "New jobs created through agricultural investments",
                    "period": str(year),
                    "value": value,
                    "unit": "jobs created through agricultural investment projects",
                    "methodology": (
                        "Administrative count of jobs created through agricultural "
                        "investment projects; not total employment or vacancies."
                    ),
                    "source_id": "tunisia-agridata-jobs-created",
                }
            )
        if not records:
            raise CollectionError("APIA jobs workbook has no numeric observations.")
        return records
    finally:
        workbook.close()


def _normalize_ckan_resource(source: DataSource, payload: bytes) -> Iterable[dict[str, object]]:
    if source.id == "tunisia-vocational-specialties":
        return _vocational_specialty_records(payload)
    if source.id == "tunisia-agridata-jobs-created":
        return _agridata_job_creation_records(payload)
    raise CollectionError(f"No Tunisia catalogue normalizer is configured for {source.id}.")


def _bmo_resource(payload: dict[str, Any]) -> tuple[int, str]:
    resources = payload.get("resources")
    if not isinstance(resources, list):
        raise CollectionError("France Travail BMO dataset response has no resource catalogue.")
    candidates: list[tuple[int, str]] = []
    for resource in resources:
        if not isinstance(resource, dict) or str(resource.get("format", "")).lower() != "xlsx":
            continue
        title = resource.get("title")
        url = resource.get("url")
        year_match = re.search(r"\b(20\d{2})\b", title if isinstance(title, str) else "")
        if year_match and isinstance(url, str):
            candidates.append((int(year_match.group(1)), url))
    if not candidates:
        raise CollectionError("France Travail BMO catalogue has no year-labelled XLSX resource.")
    return max(candidates, key=lambda item: item[0])


BMO_FIELDS = {
    "annee": "year",
    "Code métier BMO": "occupation_code",
    "Nom métier BMO": "occupation",
    "Famille_met": "occupation_family_code",
    "Lbl_fam_met": "occupation_family",
    "REG": "region_code",
    "NOM_REG": "region",
    "Dept": "department_code",
    "NomDept": "department",
    "clpe": "local_employment_committee",
    "met": "planned_recruitments",
    "xmet": "difficult_recruitments",
    "smet": "seasonal_recruitments",
}
BMO_REQUIRED_FIELDS = {
    "annee",
    "Code métier BMO",
    "Nom métier BMO",
    "REG",
    "NOM_REG",
    "Dept",
    "NomDept",
    "met",
    "xmet",
    "smet",
}
BMO_CODE_FIELDS = {
    "occupation_code",
    "occupation_family_code",
    "region_code",
    "department_code",
    "employment_area_code",
    "local_employment_committee",
}
BMO_MEASURE_FIELDS = {
    "planned_recruitments",
    "difficult_recruitments",
    "seasonal_recruitments",
}


def _bmo_xlsx_records(payload: bytes) -> Iterable[dict[str, object]]:
    try:
        workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
    except (OSError, ValueError, zipfile.BadZipFile, InvalidFileException) as error:
        raise CollectionError(f"Could not read the France Travail BMO workbook: {error}") from error

    selected_sheet = None
    header_row: tuple[object, ...] | None = None
    for sheet in workbook.worksheets:
        first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        if BMO_REQUIRED_FIELDS.issubset({value for value in first_row if isinstance(value, str)}):
            selected_sheet = sheet
            header_row = first_row
            break
    if selected_sheet is None or header_row is None:
        workbook.close()
        raise CollectionError("BMO workbook has no sheet with the expected public data columns.")

    headers: list[str | None] = []
    for value in header_row:
        if isinstance(value, str) and re.fullmatch(r"BE\d{2}", value):
            headers.append("employment_area_code")
        elif isinstance(value, str) and re.fullmatch(r"NOMBE\d{2}", value):
            headers.append("employment_area")
        else:
            headers.append(BMO_FIELDS.get(value) if isinstance(value, str) else None)

    def records() -> Iterable[dict[str, object]]:
        try:
            for row in selected_sheet.iter_rows(min_row=2, values_only=True):
                mapped = {
                    field: value
                    for field, value in zip(headers, row)
                    if field is not None
                }
                if not mapped.get("occupation_code") and not mapped.get("occupation"):
                    continue
                for field in BMO_CODE_FIELDS:
                    value = mapped.get(field)
                    if value is not None:
                        mapped[field] = str(value).strip()
                for field in BMO_MEASURE_FIELDS:
                    value = mapped.get(field)
                    if isinstance(value, str) and value.isdigit():
                        mapped[field] = int(value)
                mapped["country"] = "FR"
                mapped["record_type"] = "labour_market_observation"
                yield mapped
        finally:
            workbook.close()

    return records()


def _normalize(source: DataSource, payload: Any) -> Iterable[dict[str, object]]:
    if source.id == "eurostat-fr-unemployment":
        return _eurostat_records(payload)
    if source.id == "francetravail-bmo-catalog":
        return _bmo_catalog_records(payload)
    if source.indicator_id is not None:
        return _world_bank_records(payload, source)
    raise CollectionError(f"No normalizer is configured for source {source.id}.")


def _write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _collect_ckan_source(
    source: DataSource,
    output_dir: Path,
    raw_dir: Path,
    normalized_dir: Path,
) -> dict[str, object]:
    catalogue_bytes = _request_bytes(source.url, {source.host})
    try:
        catalogue_payload = json.loads(catalogue_bytes)
    except json.JSONDecodeError as error:
        raise CollectionError("Tunisia open-data catalogue returned invalid JSON.") from error
    dataset = _ckan_result(catalogue_payload, source)
    resource = _ckan_resource(dataset, source)
    resource_url = str(resource["url"])
    resource_hosts = set(source.resource_hosts) or {source.host}
    resource_bytes = _request_bytes(resource_url, resource_hosts)
    suffix = Path(urllib.parse.urlparse(resource_url).path).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise CollectionError(f"Unsupported Tunisia catalogue file extension: {suffix}.")

    raw_catalogue_path = raw_dir / f"{source.id}.json"
    raw_resource_path = raw_dir / f"{source.id}-resource{suffix}"
    normalized_path = normalized_dir / f"{source.id}.jsonl"
    raw_catalogue_path.write_bytes(catalogue_bytes)
    raw_resource_path.write_bytes(resource_bytes)
    record_count = _write_jsonl(
        normalized_path,
        _normalize_ckan_resource(source, resource_bytes),
    )
    organization = dataset.get("organization")
    provider = (
        organization.get("title")
        if isinstance(organization, dict) and isinstance(organization.get("title"), str)
        else source.provider
    )
    return {
        "title": source.title,
        "dataset_title": dataset.get("title"),
        "provider": provider,
        "license": dataset["license_title"],
        "license_url": dataset.get("license_url"),
        "dataset_id": dataset["id"],
        "data_last_updated": dataset.get("metadata_modified"),
        "resource_title": resource.get("name"),
        "resource_format": resource.get("format"),
        "resource_url": resource_url,
        "resource_modified_at": resource.get("last_modified"),
        "raw_path": raw_catalogue_path.relative_to(output_dir).as_posix(),
        "resource_path": raw_resource_path.relative_to(output_dir).as_posix(),
        "resource_sha256": hashlib.sha256(resource_bytes).hexdigest(),
        "resource_bytes": len(resource_bytes),
        "normalized_path": normalized_path.relative_to(output_dir).as_posix(),
        "sha256": hashlib.sha256(catalogue_bytes).hexdigest(),
        "record_count": record_count,
        "status": "ok",
    }


def collect_sources(output_dir: Path, source_ids: list[str]) -> tuple[list[dict[str, object]], bool]:
    raw_dir = output_dir / "raw"
    normalized_dir = output_dir / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    manifest: list[dict[str, object]] = []
    failed = False

    for source_id in source_ids:
        source = SOURCES[source_id]
        entry: dict[str, object] = {
            "source_id": source.id,
            "title": source.title,
            "url": source.url,
            "landing_page": source.landing_page,
            "provider": source.provider,
            "license": source.license,
            "format": source.format,
            "retrieved_at": retrieved_at,
        }
        try:
            if source.ckan_dataset_id is not None:
                entry.update(
                    _collect_ckan_source(
                        source,
                        output_dir,
                        raw_dir,
                        normalized_dir,
                    )
                )
                manifest.append(entry)
                continue

            raw_bytes = _request_bytes(source.url, {source.host})
            raw_path = raw_dir / f"{source.id}.json"
            raw_path.write_bytes(raw_bytes)
            payload = json.loads(raw_bytes)
            if source.indicator_id is None and not isinstance(payload, dict):
                raise CollectionError("Source response must be a JSON object.")
            if source.indicator_id is not None:
                metadata = payload[0] if isinstance(payload, list) and payload else None
                if isinstance(metadata, dict) and isinstance(metadata.get("lastupdated"), str):
                    entry["data_last_updated"] = metadata["lastupdated"]
            records = _normalize(source, payload)
            entry["raw_path"] = raw_path.relative_to(output_dir).as_posix()
            if source.id == "francetravail-bmo-catalog":
                catalog_path = normalized_dir / f"{source.id}.jsonl"
                catalog_count = _write_jsonl(catalog_path, records)
                year, resource_url = _bmo_resource(payload)
                resource_bytes = _request_bytes(resource_url, BMO_RESOURCE_HOSTS)
                resource_path = raw_dir / f"francetravail-bmo-{year}.xlsx"
                resource_path.write_bytes(resource_bytes)
                normalized_path = normalized_dir / f"francetravail-bmo-{year}.jsonl"
                record_count = _write_jsonl(normalized_path, _bmo_xlsx_records(resource_bytes))
                entry.update(
                    {
                        "catalog_normalized_path": catalog_path.relative_to(output_dir).as_posix(),
                        "catalog_record_count": catalog_count,
                        "resource_path": resource_path.relative_to(output_dir).as_posix(),
                        "resource_sha256": hashlib.sha256(resource_bytes).hexdigest(),
                        "resource_bytes": len(resource_bytes),
                        "resource_year": year,
                    }
                )
            else:
                normalized_path = normalized_dir / f"{source.id}.jsonl"
                record_count = _write_jsonl(normalized_path, records)
            entry.update(
                {
                    "status": "ok",
                    "normalized_path": normalized_path.relative_to(output_dir).as_posix(),
                    "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                    "record_count": record_count,
                }
            )
        except (CollectionError, json.JSONDecodeError, OSError) as error:
            failed = True
            entry.update({"status": "error", "error": str(error)})
            LOGGER.error("Failed to collect %s: %s", source.id, error)
        manifest.append(entry)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/data/open"),
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=sorted(SOURCES),
        default=sorted(SOURCES),
        help="Source ids to collect (default: all configured sources).",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _, failed = collect_sources(args.output_dir, args.sources)
    if failed:
        sys.exit(1)
    LOGGER.info("Collected %d source(s) into %s", len(args.sources), args.output_dir)


if __name__ == "__main__":
    main()
