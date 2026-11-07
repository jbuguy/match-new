import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import main
from app import assistant_services
from app.assistant_services import AssistantServiceError, generate_assistant_reply
from app.models import CandidateProfile, Role, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_candidate_registration_creates_candidate_and_empty_profile(
    client: TestClient,
    session: Session,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "  New.Candidate@example.test ",
            "password": "A-Secure-Local-Passphrase-123",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "new.candidate@example.test"
    assert response.json()["user"]["role"] == Role.CANDIDATE.value
    user = session.scalar(select(User).where(User.email == "new.candidate@example.test"))
    assert user is not None
    assert user.password_hash != "A-Secure-Local-Passphrase-123"
    profile = session.get(CandidateProfile, user.id)
    assert profile is not None
    assert profile.skills == []


def test_registration_rejects_duplicate_email_and_short_password(client: TestClient) -> None:
    payload = {
        "email": "candidate@example.test",
        "password": "A-Secure-Local-Passphrase-123",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409
    assert (
        client.post(
            "/auth/register",
            json={"email": "other@example.test", "password": "short"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "A-Secure-Local-Passphrase-123"},
        ).status_code
        == 422
    )


def test_candidate_profile_updates_keep_legacy_skills_and_add_onboarding_fields(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    headers = auth_headers(users[Role.CANDIDATE])
    legacy_update = client.put(
        "/candidate/profile",
        headers=headers,
        json={"skills": [" Excel ", "excel", "Service client"]},
    )
    assert legacy_update.status_code == 200
    assert legacy_update.json()["skills"] == ["Excel", "Service client"]

    full_update = client.put(
        "/candidate/profile",
        headers=headers,
        json={
            "full_name": "  Amira Ben Salem ",
            "phone": "+216 20 000 000",
            "location": "Sfax",
            "education": "Licence en gestion",
            "experience": "Deux ans en service client",
            "skills": ["Excel", "Organisation"],
        },
    )
    assert full_update.status_code == 200
    assert full_update.json()["full_name"] == "Amira Ben Salem"
    assert full_update.json()["education"] == "Licence en gestion"
    assert full_update.json()["experience"] == "Deux ans en service client"
    assert full_update.json()["skills"] == ["Excel", "Organisation"]

    skills_only_update = client.put(
        "/candidate/profile",
        headers=headers,
        json={"skills": ["Python"]},
    )
    assert skills_only_update.status_code == 200
    assert skills_only_update.json()["full_name"] == "Amira Ben Salem"
    assert skills_only_update.json()["location"] == "Sfax"

    read_back = client.get("/candidate/profile", headers=headers)
    assert read_back.json()["phone"] == "+216 20 000 000"
    assert read_back.json()["location"] == "Sfax"


def test_candidate_can_upload_cv_and_extract_profile(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    cv_content = (
        "Amira Ben Salem\n+216 20 000 000\nTunis\n\n"
        "Formation: Master en gestion\n\n"
        "Expérience: 3 ans en support client\n\n"
        "Compétences: Python, SQL, Excel"
    )
    response = client.post(
        "/candidate/profile/cv",
        headers=auth_headers(users[Role.CANDIDATE]),
        files={"file": ("candidate_cv.txt", cv_content.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["full_name"] == "Amira Ben Salem"
    assert payload["phone"] == "+216 20 000 000"
    assert payload["location"] == "Tunis"
    assert "Master" in payload["education"] or "Management" in payload["education"]
    assert "support" in payload["experience"].lower() or "client" in payload["experience"].lower()
    assert "Python" in payload["skills"]
    assert "SQL" in payload["skills"]
    assert "Excel" in payload["skills"]


def test_candidate_assistant_returns_uncommitted_profile_suggestions(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "generate_assistant_reply",
        AsyncMock(
            return_value={
                "reply": "Merci ! Où habites-tu ?",
                "profile_updates": {"full_name": "Amira Ben Salem"},
            }
        ),
    )
    response = client.post(
        "/candidate/assistant/chat",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={"messages": [{"role": "user", "content": "Ismi Amira Ben Salem"}]},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Merci ! Où habites-tu ?"
    assert response.json()["profile_updates"]["full_name"] == "Amira Ben Salem"
    profile = session.get(CandidateProfile, users[Role.CANDIDATE].id)
    assert profile is None or profile.full_name is None


def test_assistant_endpoints_are_candidate_only(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/candidate/assistant/chat",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={"messages": [{"role": "user", "content": "Help me"}]},
    )
    assert response.status_code == 403


def test_assistant_chat_surfaces_missing_local_model_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAHARA_LLM_BASE_URL", raising=False)
    with pytest.raises(AssistantServiceError, match="MAHARA_LLM_BASE_URL"):
        asyncio.run(generate_assistant_reply([]))


def test_local_llm_uses_openai_chat_completions_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"reply":"Aslema","profile_updates":{"location":"Tunis"}}'
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url: str, *, json: dict[str, object], headers: dict[str, str]):
            captured.update({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setenv("MAHARA_LLM_BASE_URL", "http://localhost:1234")
    monkeypatch.setenv("MAHARA_LLM_MODEL", "qwen-local")
    monkeypatch.setattr(assistant_services.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    response = asyncio.run(
        generate_assistant_reply([{"role": "user", "content": "Aslema"}])
    )

    assert response["reply"] == "Aslema"
    assert captured["url"] == "http://localhost:1234/v1/chat/completions"
    assert captured["json"]["model"] == "qwen-local"
    assert captured["json"]["response_format"]["type"] == "json_schema"


def test_candidate_voice_endpoints_use_configured_services(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "transcribe_audio",
        AsyncMock(return_value="Nheb nkammel profil mte3i."),
    )
    monkeypatch.setattr(
        main,
        "synthesize_speech",
        AsyncMock(return_value=(b"fake-audio", "audio/mpeg")),
    )
    headers = auth_headers(users[Role.CANDIDATE])

    transcript = client.post(
        "/candidate/assistant/transcriptions",
        headers=headers,
        files={"audio": ("voice.webm", b"audio-content", "audio/webm")},
    )
    assert transcript.status_code == 200
    assert transcript.json() == {"text": "Nheb nkammel profil mte3i."}

    speech = client.post(
        "/candidate/assistant/speech",
        headers=headers,
        json={"text": "Aslema!"},
    )
    assert speech.status_code == 200
    assert speech.content == b"fake-audio"
    assert speech.headers["content-type"] == "audio/mpeg"


def test_transcription_rejects_non_audio_upload(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/candidate/assistant/transcriptions",
        headers=auth_headers(users[Role.CANDIDATE]),
        files={"audio": ("profile.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 415
