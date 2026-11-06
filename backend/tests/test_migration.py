from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def test_sqlite_migration_enforces_append_only_audit_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "migrations.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO audit_log
                    (id, actor_user_id, actor_role, action, resource_type,
                     resource_id, details, created_at)
                VALUES
                    ('event-1', NULL, NULL, 'test.action', NULL, NULL, '{}',
                     '2026-01-01T00:00:00')
                """
            )
        )

    with pytest.raises(IntegrityError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE audit_log SET action = 'changed' WHERE id = 'event-1'")
            )

    with pytest.raises(IntegrityError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM audit_log WHERE id = 'event-1'"))

    command.downgrade(alembic_config, "base")
    engine.dispose()
