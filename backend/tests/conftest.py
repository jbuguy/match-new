import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import Role, User
from app.security import hash_password


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    engine.dispose()


@pytest.fixture
def users(session: Session, monkeypatch: pytest.MonkeyPatch) -> dict[Role, User]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-signing-key-that-is-at-least-32-chars")
    encoded_password = hash_password("LocalDemoPassword2026!")
    users_by_role: dict[Role, User] = {}
    for role in Role:
        user = User(
            email=f"{role.value}@example.test",
            password_hash=encoded_password,
            role=role,
        )
        session.add(user)
        users_by_role[role] = user
    session.flush()
    return users_by_role


@pytest.fixture
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-signing-key-that-is-at-least-32-chars")

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
