from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import main
from app.models import CandidateAssistantSession, Role, User
from app.security import create_access_token, hash_password


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_candidate_can_create_chat_and_retrieve_persisted_history(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "generate_career_assistant_reply",
        AsyncMock(return_value="Aslema! نحكيو على المهارات اللي تحب تطورها."),
    )
    headers = auth_headers(users[Role.CANDIDATE])
    created = client.post("/candidate/assistant/sessions", headers=headers)
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert created.json()["messages"] == []

    sent = client.post(
        f"/candidate/assistant/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "Nheb nkawwer fi skills mte3i"},
    )
    assert sent.status_code == 200
    assert sent.json()["title"] == "Nheb nkawwer fi skills mte3i"
    assert [message["role"] for message in sent.json()["messages"]] == ["user", "assistant"]

    listed = client.get("/candidate/assistant/sessions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == session_id
    assert listed.json()[0]["title"] == "Nheb nkawwer fi skills mte3i"
    stored = session.get(CandidateAssistantSession, session_id)
    assert stored is not None
    assert stored.messages[0]["content"] == "Nheb nkawwer fi skills mte3i"

    retrieved = client.get(f"/candidate/assistant/sessions/{session_id}", headers=headers)
    assert retrieved.json()["messages"] == sent.json()["messages"]


def test_chat_sessions_are_candidate_owned_and_deletable(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    owner = users[Role.CANDIDATE]
    other_candidate = User(
        email="other-candidate@example.test",
        password_hash=hash_password("LocalDemoPassword2026!"),
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    chat_session = CandidateAssistantSession(
        user_id=owner.id,
        title="Private conversation",
        messages=[{"role": "user", "content": "Private text"}],
    )
    session.add(chat_session)
    session.commit()

    other_headers = auth_headers(other_candidate)
    assert (
        client.get(
            f"/candidate/assistant/sessions/{chat_session.id}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/candidate/assistant/sessions/{chat_session.id}",
            headers=other_headers,
        ).status_code
        == 404
    )

    owner_headers = auth_headers(owner)
    assert (
        client.delete(
            f"/candidate/assistant/sessions/{chat_session.id}",
            headers=owner_headers,
        ).status_code
        == 204
    )
    assert session.scalar(
        select(CandidateAssistantSession).where(CandidateAssistantSession.id == chat_session.id)
    ) is None


def test_chat_sessions_are_candidate_only(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.get(
        "/candidate/assistant/sessions",
        headers=auth_headers(users[Role.EMPLOYER]),
    )
    assert response.status_code == 403
