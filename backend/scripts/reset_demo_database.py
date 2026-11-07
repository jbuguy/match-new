from __future__ import annotations

import argparse
import os
from urllib.parse import urlparse

from sqlalchemy import delete, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal


def _database_name_from_url(database_url: str) -> str | None:
    if not database_url:
        return None
    try:
        return make_url(database_url).database
    except Exception:
        return None


def _require_mahara_match_database(database_url: str | None) -> str:
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    database_name = _database_name_from_url(database_url)
    if database_name != "mahara_match":
        raise RuntimeError(
            "Refusing to reset a database that is not the local development database "
            "named 'mahara_match'."
        )
    return database_name


def reset_demo_database(session: Session, *, confirm: bool = True) -> dict[str, int]:
    database_url = os.getenv("DATABASE_URL")
    if confirm:
       _require_mahara_match_database(database_url)

    if os.getenv("APP_ENV", "development").casefold() in {"prod", "production"}:
        raise RuntimeError("Demo database resets are prohibited in production environments.")

    tables = []
    for table in reversed(Base.metadata.sorted_tables):
        if not inspect(session.bind).has_table(table.name):
            continue
        tables.append(table)

    if not tables:
        return {"tables_cleared": 0, "rows_deleted": 0}

    rows_deleted = 0
    for table in tables:
        rows_deleted += int(session.execute(delete(table)).rowcount)
    session.commit()
    return {"tables_cleared": len(tables), "rows_deleted": rows_deleted}


def _prompt_for_confirmation(database_url: str) -> None:
    target = urlparse(database_url)
    db_name = target.path.lstrip("/") if target.path else ""
    prompt = (
        f"This will clear all application data in the PostgreSQL database '{db_name}'. "
        "This preserves the schema and migration history, but removes users, profiles, "
        "offers, applications and other demo records. Type 'RESET mahara_match' to continue: "
    )
    response = input(prompt)
    if response.strip() != "RESET mahara_match":
        raise SystemExit("Reset cancelled. No data was changed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the local development database while preserving schema and migration history.")
    parser.add_argument("--confirm", action="store_true", help="Skip the interactive confirmation prompt.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set before resetting the demo database.")

    _require_mahara_match_database(database_url)

    if not args.confirm:
        _prompt_for_confirmation(database_url)

    with SessionLocal() as session:
        result = reset_demo_database(session, confirm=False)
    print(
        "Reset completed: "
        f"cleared {result['tables_cleared']} tables and {result['rows_deleted']} rows "
        f"from {database_url}"
    )


if __name__ == "__main__":
    main()
