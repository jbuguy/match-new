from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
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
    tables = set(inspect(engine).get_table_names())
    assert {
        "candidate_profiles",
        "job_offers",
        "candidate_assistant_sessions",
        "candidate_roadmap_steps",
        "job_applications",
        "training_courses",
        "course_enrollments",
        "candidate_technical_assessments",
        "candidate_technical_assessment_answers",
        "candidate_behavioral_assessments",
        "candidate_behavioral_assessment_answers",
        "candidate_interview_transcriptions",
    } <= tables
    profile_columns = {column["name"] for column in inspect(engine).get_columns("candidate_profiles")}
    assert {
        "full_name",
        "phone",
        "location",
        "education",
        "experience",
    } <= profile_columns
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


def test_candidate_profile_migration_preserves_existing_skills(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "profile-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "0002_candidate_profiles_job_offers")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users
                    (id, email, password_hash, role, is_active, created_at)
                VALUES
                    ('candidate-1', 'candidate@example.test', 'hash', 'candidate',
                     1, '2026-01-01T00:00:00')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO candidate_profiles (user_id, skills, updated_at)
                VALUES ('candidate-1', '["Excel"]', '2026-01-01T00:00:00')
                """
            )
        )

    command.upgrade(alembic_config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT skills, full_name, education FROM candidate_profiles "
                "WHERE user_id = 'candidate-1'"
            )
        ).one()
    assert row.skills == '["Excel"]'
    assert row.full_name is None
    assert row.education is None
    engine.dispose()
    command.downgrade(alembic_config, "base")
