import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrganisationMembership, Role, User
from app.seed_demo_users import DEMO_ACCOUNTS, main, seed_demo_users


def test_demo_seed_creates_all_roles_and_organisation_memberships(session: Session) -> None:
    seed_demo_users(session, "LocalDemoPassword2026!")

    users = session.scalars(select(User)).all()
    memberships = session.scalars(select(OrganisationMembership)).all()
    assert {user.role for user in users} == set(Role)
    assert len(users) == len(DEMO_ACCOUNTS)
    assert len(memberships) == 2
    assert all(user.email.endswith("@demo.maharamatch.test") for user in users)


def test_demo_seed_is_idempotent_and_does_not_reset_passwords(session: Session) -> None:
    seed_demo_users(session, "LocalDemoPassword2026!")
    candidate = session.scalar(
        select(User).where(User.role == Role.CANDIDATE)
    )
    assert candidate is not None
    original_hash = candidate.password_hash

    seed_demo_users(session, "DifferentDemoPassword2026!")

    assert session.query(User).count() == len(DEMO_ACCOUNTS)
    assert session.query(OrganisationMembership).count() == 2
    assert candidate.password_hash == original_hash


def test_demo_seed_refuses_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MAHARA_ENABLE_DEMO_USERS", "true")
    monkeypatch.setenv("MAHARA_DEMO_PASSWORD", "LocalDemoPassword2026!")

    with pytest.raises(SystemExit, match="cannot be seeded in a production"):
        main()
