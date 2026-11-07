"""Import approved annual labour-market series into the assistant knowledge base."""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.database import SessionLocal
from app.knowledge_base import ingest_document


LOGGER = logging.getLogger(__name__)
SUPPORTED_SOURCE_IDS = {
    "eurostat-fr-unemployment",
    "tunisia-agridata-jobs-created",
    "tunisia-vocational-specialties",
    "worldbank-tn-employment-to-population",
    "worldbank-tn-unemployment",
    "worldbank-tn-youth-unemployment",
}


class LabourDataIngestionError(Exception):
    """The local source snapshots could not be imported safely."""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as error:
                    raise LabourDataIngestionError(
                        f"Invalid JSON in {path.name} at line {line_number}."
                    ) from error
                if not isinstance(value, dict):
                    raise LabourDataIngestionError(
                        f"Expected a JSON object in {path.name} at line {line_number}."
                    )
                records.append(value)
    except OSError as error:
        raise LabourDataIngestionError(f"Could not read labour data {path}.") from error
    return records


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise LabourDataIngestionError(f"Invalid source update timestamp: {value}.") from error


def build_series_document(
    source: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    source_id = source.get("source_id")
    if source_id not in SUPPORTED_SOURCE_IDS:
        raise LabourDataIngestionError(f"Source {source_id!r} is not approved for ingestion.")
    if not records:
        raise LabourDataIngestionError(f"Source {source_id!r} has no normalized records.")

    country_codes = {record.get("country") for record in records}
    if country_codes == {"TN"}:
        country = "Tunisia"
    elif country_codes == {"FR"}:
        country = "France"
    else:
        raise LabourDataIngestionError(
            f"Source {source_id!r} contains unexpected or mixed country records."
        )

    indicator = str(records[0].get("indicator") or source.get("title") or source_id)
    sorted_records = sorted(records, key=lambda record: str(record.get("period", "")))
    observations: list[str] = []
    periods: list[str] = []
    for record in sorted_records:
        period = record.get("period")
        value = record.get("value")
        if not isinstance(period, str) or not period.isdigit():
            raise LabourDataIngestionError(
                f"Source {source_id!r} contains an invalid observation period."
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        periods.append(period)
        observations.append(
            f"{period}: {value} {record.get('unit') or 'reported units'}"
        )
    if not observations:
        raise LabourDataIngestionError(f"Source {source_id!r} has no numeric observations.")

    methodology = records[0].get("methodology")
    if not isinstance(methodology, str) or not methodology:
        methodology = (
            "The World Bank series is based on modelled ILO estimates."
            if source_id.startswith("worldbank-tn-")
            else "Eurostat annual unemployment rate; see the linked series definition."
        )
    title = f"{source.get('title', source_id)} — annual observations"
    content = (
        f"{title}\nCountry: {country} ({next(iter(country_codes))}).\n"
        f"Indicator: {indicator}.\nMethodology: {methodology}\n"
        f"Annual observations: {'; '.join(observations)}."
    )
    updated_at = source.get("data_last_updated") or source.get("retrieved_at")
    return {
        "external_id": source_id,
        "title": title,
        "content": content,
        "source": str(source.get("provider") or "Unknown provider"),
        "source_url": source.get("landing_page") or source.get("url"),
        "category": "labor_market",
        "subcategory": "employment_trends",
        "country": country,
        "language": "en",
        "source_updated_at": _parse_datetime(updated_at),
        "metadata": {
            "source_id": source_id,
            "methodology": methodology,
            "period_start": periods[0],
            "period_end": periods[-1],
            "observation_count": len(observations),
            "retrieved_at": source.get("retrieved_at"),
            "license": source.get("license"),
            "license_url": source.get("license_url"),
        },
    }


def build_specialties_document(
    source: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    source_id = source.get("source_id")
    if source_id != "tunisia-vocational-specialties":
        raise LabourDataIngestionError(
            f"Source {source_id!r} is not an approved specialty catalogue."
        )
    if not records or any(record.get("country") != "TN" for record in records):
        raise LabourDataIngestionError(
            "The historical specialty catalogue is empty or contains non-Tunisian records."
        )
    lines = []
    for record in records:
        specialty = str(record.get("specialty_fr") or record.get("specialty_ar") or "").strip()
        if not specialty:
            continue
        lines.append(
            "Specialty code: "
            f"{record.get('specialty_code')}; French: {specialty}; "
            f"Arabic: {record.get('specialty_ar') or 'not supplied'}; "
            f"sector: {record.get('sector') or 'not supplied'}; "
            f"subsector: {record.get('subsector') or 'not supplied'}; "
            f"certificate: {record.get('certificate') or 'not supplied'}; "
            f"training duration in years: "
            f"{record.get('training_duration_years') or 'not supplied'}."
        )
    if not lines:
        raise LabourDataIngestionError("The specialty catalogue has no usable entries.")

    title = str(source.get("title") or "Vocational specialties in Tunisia")
    content = (
        f"{title}\nHistorical source year: 2017.\n"
        "This is a list of vocational specialties, not a current course availability "
        "catalogue. Confirm directly with a provider before advising that a course "
        "is currently offered.\n"
        + "\n".join(lines)
    )
    return {
        "external_id": source_id,
        "title": title,
        "content": content,
        "source": str(source.get("provider") or "Unknown provider"),
        "source_url": source.get("landing_page") or source.get("url"),
        "category": "formation",
        "subcategory": "historical_vocational_specialties",
        "country": "Tunisia",
        "language": "ar+fr",
        "source_updated_at": _parse_datetime(
            source.get("resource_modified_at") or source.get("data_last_updated")
        ),
        "metadata": {
            "source_id": source_id,
            "source_year": 2017,
            "current_course_catalogue": False,
            "record_count": len(lines),
            "license": source.get("license"),
            "license_url": source.get("license_url"),
            "retrieved_at": source.get("retrieved_at"),
        },
    }


def load_manifest(data_dir: Path) -> list[dict[str, Any]]:
    manifest_path = data_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LabourDataIngestionError(
            f"Could not read source manifest at {manifest_path}."
        ) from error
    if not isinstance(manifest, list):
        raise LabourDataIngestionError("The source manifest must contain a JSON array.")
    return [
        item
        for item in manifest
        if isinstance(item, dict)
        and item.get("source_id") in SUPPORTED_SOURCE_IDS
        and item.get("status") == "ok"
    ]


def ingest_local_series(data_dir: Path) -> int:
    sources = load_manifest(data_dir)
    if not sources:
        raise LabourDataIngestionError(
            "No successfully collected approved labour-market sources were found."
        )
    imported = 0
    with SessionLocal() as session:
        for source in sources:
            normalized_path = source.get("normalized_path")
            if not isinstance(normalized_path, str):
                raise LabourDataIngestionError(
                    f"Source {source.get('source_id')} has no normalized path."
                )
            path = data_dir / normalized_path
            records = _read_jsonl(path)
            if source["source_id"] == "tunisia-vocational-specialties":
                document = build_specialties_document(source, records)
            else:
                document = build_series_document(source, records)
            asyncio.run(ingest_document(session, **document))
            LOGGER.info(
                "Ingested %s (%d source records).",
                source["source_id"],
                document["metadata"].get(
                    "observation_count",
                    document["metadata"].get("record_count", 0),
                ),
            )
            imported += 1
    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "open",
        help="Directory containing manifest.json and normalized JSONL source files.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        count = ingest_local_series(args.data_dir)
    except LabourDataIngestionError as error:
        LOGGER.error("%s", error)
        sys.exit(1)
    LOGGER.info("Imported %d labour-market series.", count)


if __name__ == "__main__":
    main()
