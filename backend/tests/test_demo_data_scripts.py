from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, CourseEnrollment, JobApplication, JobOffer, Role, User
from scripts.reset_demo_database import reset_demo_database
from scripts.seed_demo_data import seed_demo_data


def test_seed_demo_data_repair_demo_role_mismatch(session: Session) -> None:
    existing = User(email="employer@demo.maharamatch.test", password_hash="hash", role=Role.CANDIDATE)
    session.add(existing)
    session.flush()

    seed_demo_data(session, "LocalDemoPassword2026!")

    repaired = session.scalar(select(User).where(User.email == "employer@demo.maharamatch.test"))
    assert repaired is not None
    assert repaired.role == Role.EMPLOYER


def test_seed_demo_data_is_idempotent_and_populates_dataset(session: Session) -> None:
    first = seed_demo_data(session, "LocalDemoPassword2026!")
    second = seed_demo_data(session, "LocalDemoPassword2026!")

    assert first == second
    assert first["candidates"] >= 10
    assert first["employers"] >= 5
    assert first["job_offers"] >= 20
    assert first["applications"] >= 10
    assert first["training_courses"] == 3
    assert session.query(User).filter(User.role == "candidate").count() >= 10
    assert session.query(JobOffer).count() >= 20
    assert session.query(JobApplication).count() >= 10
    assert session.query(CandidateProfile).count() >= 10
    assert session.query(CourseEnrollment).count() >= 3


def test_reset_demo_database_clears_tables_without_dropping_schema(session: Session) -> None:
    seed_demo_data(session, "LocalDemoPassword2026!")

    result = reset_demo_database(session, confirm=False)
    assert result["tables_cleared"] >= 1
    assert result["rows_deleted"] >= 1
    assert session.query(User).count() == 0
    assert session.query(JobOffer).count() == 0
    assert session.query(JobApplication).count() == 0
