import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Organisation,
    OrganisationMembership,
    OrganisationType,
    Role,
    User,
)
from app.security import hash_password


DEMO_ACCOUNTS: tuple[tuple[str, Role, str | None, OrganisationType | None], ...] = (
    ("candidate@demo.maharamatch.test", Role.CANDIDATE, None, None),
    (
        "employer@demo.maharamatch.test",
        Role.EMPLOYER,
        "Demo Employer Organisation",
        OrganisationType.EMPLOYER,
    ),
    ("ministry@demo.maharamatch.test", Role.MINISTRY_ADMIN, None, None),
    (
        "provider@demo.maharamatch.test",
        Role.TRAINING_PROVIDER,
        "Demo Training Provider",
        OrganisationType.TRAINING_PROVIDER,
    ),
    ("operator@demo.maharamatch.test", Role.OPERATOR, None, None),
)


DEMO_ACCOUNT_ROLES = {email: role for email, role, _, _ in DEMO_ACCOUNTS}


def seed_demo_users(session: Session, password: str) -> None:
    if len(password) < 12:
        raise ValueError("The demo password must be at least 12 characters.")

    for email, role, organisation_name, organisation_type in DEMO_ACCOUNTS:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash=hash_password(password), role=role)
            session.add(user)
            session.flush()
        elif user.role != role:
            if DEMO_ACCOUNT_ROLES.get(email) == role:
                user.role = role
            else:
                raise ValueError(f"The existing demo account {email} has an unexpected role.")

        if organisation_name is None or organisation_type is None:
            continue

        organisation = session.scalar(
            select(Organisation).where(
                Organisation.name == organisation_name,
                Organisation.organisation_type == organisation_type,
            )
        )
        if organisation is None:
            organisation = Organisation(
                name=organisation_name,
                organisation_type=organisation_type,
            )
            session.add(organisation)
            session.flush()

        membership = session.scalar(
            select(OrganisationMembership.id).where(
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.organisation_id == organisation.id,
            )
        )
        if membership is None:
            session.add(
                OrganisationMembership(user_id=user.id, organisation_id=organisation.id)
            )

    session.commit()


def main() -> None:
    environment = os.getenv("APP_ENV", "development").casefold()
    if environment in {"prod", "production"}:
        raise SystemExit("Demo accounts cannot be seeded in a production environment.")
    if os.getenv("MAHARA_ENABLE_DEMO_USERS", "").casefold() != "true":
        raise SystemExit("Set MAHARA_ENABLE_DEMO_USERS=true to seed local demo accounts.")
    password = os.getenv("MAHARA_DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Set MAHARA_DEMO_PASSWORD to a value of at least 12 characters.")

    with SessionLocal() as session:
        seed_demo_users(session, password)
    print(f"Seeded {len(DEMO_ACCOUNTS)} demo accounts (existing passwords were not changed).")


if __name__ == "__main__":
    main()
