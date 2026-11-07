from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.assistant_rag import (
    AssistantIntent,
    build_evidence_context,
    classify_assistant_intent,
    load_application_context,
)
from app.knowledge_base import KnowledgeHit
from app import main
from app.models import CandidateProfile, JobOffer, Role, User
from app.security import create_access_token
from fastapi.testclient import TestClient


def _auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_assistant_intent_keeps_general_questions_out_of_retrieval() -> None:
    assert classify_assistant_intent("What is Python?") == AssistantIntent.GENERAL
    assert (
        classify_assistant_intent("Which technical skills are growing in Tunisia?")
        == AssistantIntent.SKILL
    )
    assert (
        classify_assistant_intent("What is the Tunisian job market like?")
        == AssistantIntent.MARKET
    )
    assert (
        classify_assistant_intent("How can I become a data analyst?")
        == AssistantIntent.CAREER
    )
    assert (
        classify_assistant_intent("Which formations teach Python?")
        == AssistantIntent.FORMATION
    )
    assert (
        classify_assistant_intent("Find jobs matching my skills")
        == AssistantIntent.PERSONALIZED
    )
    assert (
        classify_assistant_intent("Show me current job offers")
        == AssistantIntent.JOB_SEARCH
    )


def test_evidence_context_cites_source_and_separates_general_and_verified_data() -> None:
    hit = KnowledgeHit(
        document_id="wdi-tn-unemployment-2025",
        chunk_id="chunk-id",
        title="Tunisia unemployment",
        content="Unemployment was 15.1 percent in 2025.",
        source="World Bank WDI",
        source_url="https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=TN",
        category="labor_market",
        country="TN",
        region=None,
        published_at=None,
        source_updated_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        metadata={"period": "2025"},
        score=0.8,
    )

    context = build_evidence_context(
        intent=AssistantIntent.MARKET,
        hits=[hit],
        application_context="Verified application data: two actual job offers.",
    )

    assert "[S1]" in context
    assert "Country: TN" in context
    assert "World Bank WDI" in context
    assert "general model knowledge" in context
    assert "two actual job offers" in context
    assert "do not substitute French observations" in context


def test_no_evidence_context_does_not_block_answering_from_general_knowledge() -> None:
    context = build_evidence_context(
        intent=AssistantIntent.CAREER,
        hits=[],
        application_context="",
    )

    assert "No relevant local reference evidence" in context
    assert "You may still answer from general knowledge" in context


def test_old_source_is_explicitly_marked_as_potentially_stale() -> None:
    hit = KnowledgeHit(
        document_id="old-report",
        chunk_id="old-chunk",
        title="Older labour report",
        content="Historical market observation.",
        source="Test source",
        source_url=None,
        category="labor_market",
        country="Tunisia",
        region=None,
        published_at=None,
        source_updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        metadata={},
        score=0.5,
    )
    context = build_evidence_context(
        intent=AssistantIntent.MARKET,
        hits=[hit],
        application_context="",
    )

    assert "potentially stale" in context


def test_formation_request_never_invents_catalogue_records(
    session,
    users: dict[Role, User],
) -> None:
    context = load_application_context(
        session,
        user=users[Role.CANDIDATE],
        intent=AssistantIntent.FORMATION,
    )

    assert "does not yet have a current, verified formation catalogue" in context.content
    assert context.profile_read is False


def test_general_assistant_question_skips_retrieval(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch,
) -> None:
    generator = AsyncMock(return_value="Python is a programming language.")
    retrieval = AsyncMock(return_value=[])
    monkeypatch.setattr(main, "generate_career_assistant_reply", generator)
    monkeypatch.setattr(main, "retrieve_assistant_evidence", retrieval)

    created = client.post(
        "/candidate/assistant/sessions",
        headers=_auth_headers(users[Role.CANDIDATE]),
    )
    response = client.post(
        f"/candidate/assistant/sessions/{created.json()['id']}/messages",
        headers=_auth_headers(users[Role.CANDIDATE]),
        json={"content": "What is Python?"},
    )

    assert response.status_code == 200
    retrieval.assert_not_awaited()
    assert generator.await_args is not None
    model_messages = generator.await_args.args[0]
    assert "Retrieved reference evidence" not in model_messages[0]["content"]
    assert [message["role"] for message in model_messages] == ["system", "user"]


def test_personalized_chat_uses_verified_profile_and_job_records(
    client: TestClient,
    users: dict[Role, User],
    session,
    monkeypatch,
) -> None:
    candidate = users[Role.CANDIDATE]
    session.add(CandidateProfile(user_id=candidate.id, skills=["Python"]))
    offer = JobOffer(
        employer_id=users[Role.EMPLOYER].id,
        title="Junior Python Developer",
        description="Build Python services with a small engineering team.",
        location="Tunis",
        required_skills=["Python", "SQL"],
    )
    session.add(offer)
    session.flush()
    generator = AsyncMock(return_value="This role overlaps with Python.")
    monkeypatch.setattr(main, "generate_career_assistant_reply", generator)
    monkeypatch.setattr(
        main,
        "retrieve_assistant_evidence",
        AsyncMock(return_value=[]),
    )

    created = client.post(
        "/candidate/assistant/sessions",
        headers=_auth_headers(candidate),
    )
    response = client.post(
        f"/candidate/assistant/sessions/{created.json()['id']}/messages",
        headers=_auth_headers(candidate),
        json={"content": "Based on my skills, which jobs fit me?"},
    )

    assert response.status_code == 200
    assert generator.await_args is not None
    model_messages = generator.await_args.args[0]
    evidence_message = next(
        message["content"]
        for message in model_messages
        if message["role"] == "system" and "Verified application data" in message["content"]
    )
    assert "Candidate profile skills: Python." in evidence_message
    assert f"ID {offer.id}; Junior Python Developer; Tunis" in evidence_message
    assert "candidate skill overlap: 50%" in evidence_message
    assert "Python services" in evidence_message


def test_market_chat_includes_retrieved_citation(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch,
) -> None:
    hit = KnowledgeHit(
        document_id="wdi-tn-unemployment",
        chunk_id="chunk-id",
        title="Tunisia unemployment",
        content="Observed unemployment was reported for 2025.",
        source="World Bank WDI",
        source_url="https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=TN",
        category="labor_market",
        country="Tunisia",
        region=None,
        published_at=None,
        source_updated_at=None,
        metadata={"period": "2025"},
        score=0.8,
    )
    generator = AsyncMock(return_value="The 2025 estimate is [S1].")
    retrieval = AsyncMock(return_value=[hit])
    monkeypatch.setattr(main, "generate_career_assistant_reply", generator)
    monkeypatch.setattr(main, "retrieve_assistant_evidence", retrieval)

    candidate = users[Role.CANDIDATE]
    created = client.post(
        "/candidate/assistant/sessions",
        headers=_auth_headers(candidate),
    )
    response = client.post(
        f"/candidate/assistant/sessions/{created.json()['id']}/messages",
        headers=_auth_headers(candidate),
        json={"content": "What is the Tunisian job market like?"},
    )

    assert response.status_code == 200
    assert retrieval.await_args is not None
    assert generator.await_args is not None
    assert retrieval.await_args.kwargs["intent"] == AssistantIntent.MARKET
    assert "[S1] Tunisia unemployment" in generator.await_args.args[0][1]["content"]
    assert "World Bank WDI" in generator.await_args.args[0][1]["content"]
