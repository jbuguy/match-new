from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import interview_transcription, main
from app.assistant_services import AssistantServiceError
from app.models import Role, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def create_offer(client: TestClient, employer: User) -> str:
    response = client.post(
        "/employer/offers",
        headers=auth_headers(employer),
        json={
            "title": "Technicienne",
            "description": "Résoudre des problèmes.",
            "location": "Tunis",
            "required_skills": ["Python"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def start_assessment(
    client: TestClient,
    candidate: User,
    offer_id: str,
    assessment_type: str,
) -> str:
    if assessment_type == "technical":
        response = client.post(
            "/candidate/interview-prep/assessments",
            headers=auth_headers(candidate),
            json={"offer_id": offer_id, "skill": "Python"},
        )
    else:
        response = client.post(
            "/candidate/interview-prep/behavioral-assessments",
            headers=auth_headers(candidate),
            json={"offer_id": offer_id, "skill": "teamwork"},
        )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize("assessment_type,question_id", [("technical", "q2"), ("behavioral", "q1")])
def test_candidate_can_upload_and_poll_interview_audio_transcription(
    client: TestClient,
    users: dict[Role, User],
    assessment_type: str,
    question_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    assessment_id = start_assessment(
        client,
        users[Role.CANDIDATE],
        offer_id,
        assessment_type,
    )
    transcribe_mock = AsyncMock(return_value="J'ai résolu le problème en vérifiant les données.")
    monkeypatch.setattr(interview_transcription, "transcribe_audio", transcribe_mock)
    headers = auth_headers(users[Role.CANDIDATE])

    upload = client.post(
        f"/candidate/interview-prep/{assessment_type}-assessments/{assessment_id}"
        f"/questions/{question_id}/transcription",
        headers=headers,
        files={"audio": ("voice.webm", b"audio-content", "audio/webm;codecs=opus")},
    )
    assert upload.status_code == 202
    queued = upload.json()
    assert queued["status"] == "queued"
    assert queued["transcript"] is None
    assert queued["assessment_type"] == assessment_type
    transcribe_mock.assert_awaited_once_with(
        b"audio-content",
        "interview-answer",
        "audio/webm",
    )

    result = client.get(
        f"/candidate/interview-prep/transcriptions/{queued['id']}",
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["transcript"] == "J'ai résolu le problème en vérifiant les données."


def test_transcription_failures_are_persisted_and_visible(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    assessment_id = start_assessment(
        client,
        users[Role.CANDIDATE],
        offer_id,
        "behavioral",
    )
    monkeypatch.setattr(
        interview_transcription,
        "transcribe_audio",
        AsyncMock(side_effect=AssistantServiceError("No speech was recognized.", status_code=422)),
    )
    headers = auth_headers(users[Role.CANDIDATE])

    upload = client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}"
        "/questions/q1/transcription",
        headers=headers,
        files={"audio": ("voice.webm", b"audio-content", "audio/webm")},
    )
    assert upload.status_code == 202
    result = client.get(
        f"/candidate/interview-prep/transcriptions/{upload.json()['id']}",
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    assert result.json()["error_message"] == "No speech was recognized."
    assert result.json()["transcript"] is None


def test_interview_audio_rejects_invalid_upload_or_question(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    assessment_id = start_assessment(
        client,
        users[Role.CANDIDATE],
        offer_id,
        "technical",
    )
    url = (
        f"/candidate/interview-prep/technical-assessments/{assessment_id}"
        "/questions/q1/transcription"
    )
    headers = auth_headers(users[Role.CANDIDATE])

    not_audio = client.post(
        url,
        headers=headers,
        files={"audio": ("answer.txt", b"not audio", "text/plain")},
    )
    assert not_audio.status_code == 415
    empty = client.post(
        url,
        headers=headers,
        files={"audio": ("answer.webm", b"", "audio/webm")},
    )
    assert empty.status_code == 422
    unknown_question = client.post(
        url.replace("/q1/", "/unknown/"),
        headers=headers,
        files={"audio": ("answer.webm", b"audio", "audio/webm")},
    )
    assert unknown_question.status_code == 404


def test_transcription_status_is_candidate_owned_and_role_restricted(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    assessment_id = start_assessment(
        client,
        users[Role.CANDIDATE],
        offer_id,
        "technical",
    )
    monkeypatch.setattr(
        interview_transcription,
        "transcribe_audio",
        AsyncMock(return_value="Transcript."),
    )
    upload = client.post(
        f"/candidate/interview-prep/technical-assessments/{assessment_id}"
        "/questions/q1/transcription",
        headers=auth_headers(users[Role.CANDIDATE]),
        files={"audio": ("answer.webm", b"audio", "audio/webm")},
    )
    transcription_id = upload.json()["id"]

    for role, user in users.items():
        if role == Role.CANDIDATE:
            continue
        assert client.get(
            f"/candidate/interview-prep/transcriptions/{transcription_id}",
            headers=auth_headers(user),
        ).status_code == 403
    other_candidate = User(
        id="transcription-other-candidate",
        email="transcription-other@example.test",
        password_hash="unused",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    assert client.get(
        f"/candidate/interview-prep/transcriptions/{transcription_id}",
        headers=auth_headers(other_candidate),
    ).status_code == 404
