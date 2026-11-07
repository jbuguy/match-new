"""Download selected public labour-market data and store raw and normalized snapshots."""

import argparse
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
from io import BytesIO
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


def _normalize(source: DataSource, payload: dict[str, Any]) -> Iterable[dict[str, object]]:
    if source.id == "eurostat-fr-unemployment":
        return _eurostat_records(payload)
    if source.id == "francetravail-bmo-catalog":
        return _bmo_catalog_records(payload)
    raise CollectionError(f"No normalizer is configured for source {source.id}.")


def _write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


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
            raw_bytes = _request_bytes(source.url, {source.host})
            raw_path = raw_dir / f"{source.id}.json"
            raw_path.write_bytes(raw_bytes)
            payload = json.loads(raw_bytes)
            if not isinstance(payload, dict):
                raise CollectionError("Source response must be a JSON object.")
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
