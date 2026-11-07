import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import main
from app.assistant_services import AssistantServiceError
from app.behavioral_assessment import (
    evaluate_behavioral_answer,
    generate_behavioral_questions,
    get_behavioral_competency,
)
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
            "title": "Assistante de projet",
            "description": "Contribuer à des projets d'équipe.",
            "location": "Sousse",
            "required_skills": ["Organisation"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def fake_behavioral_evaluation(
    question: dict[str, Any],
    answer: str,
) -> dict[str, object]:
    criteria = question["criteria"]
    criteria_scores = [
        {
            "criterion_id": criterion["id"],
            "label": criterion["label"],
            "score": 4,
            "max_score": 5,
        }
        for criterion in criteria
    ]
    is_star = question["type"] == "behavioral"
    star_scores = (
        {
            component: {"score": 3, "max_score": 5, "evidence": f"Élément {component}."}
            for component in ("situation", "task", "action", "result")
        }
        if is_star
        else {}
    )
    return {
        "score": sum(item["score"] for item in criteria_scores)
        + sum(item["score"] for item in star_scores.values()),
        "max_score": len(criteria_scores) * 5 + len(star_scores) * 5,
        "criteria_scores": criteria_scores,
        "star_scores": star_scores,
        "explanation": "Retour fondé sur les éléments décrits.",
        "strengths": ["La contribution est clairement présentée."],
        "weaknesses": ["Le résultat pourrait être plus précis."],
        "suggested_improvements": ["Précisez l'effet de votre action."],
        "method": "llm",
    }


def test_behavioral_competencies_offer_star_and_situational_prompts() -> None:
    competency = get_behavioral_competency("teamwork")
    assert competency is not None
    assert get_behavioral_competency("unknown") is None

    questions = generate_behavioral_questions("teamwork")

    assert [question["type"] for question in questions] == [
        "behavioral",
        "situational",
    ]
    assert questions[0]["format"] == "star_text"
    assert [item["id"] for item in questions[0]["star_components"]] == [
        "situation",
        "task",
        "action",
        "result",
    ]
    assert questions[1]["format"] == "text_answer"
    assert questions[1]["star_components"] == []


def test_behavioral_evaluator_validates_star_scores_and_normalizes_criteria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = generate_behavioral_questions("teamwork")[0]
    monkeypatch.setattr(
        "app.behavioral_assessment.generate_career_assistant_reply",
        AsyncMock(
            return_value=json.dumps(
                {
                    "criteria_scores": [
                        {"criterion_id": criterion["id"], "score": 4}
                        for criterion in reversed(question["criteria"])
                    ],
                    "star_scores": {
                        component: {
                            "score": 3,
                            "evidence": f"Exemple de {component}.",
                        }
                        for component in ("situation", "task", "action", "result")
                    },
                    "explanation": "Réponse analysée avec prudence.",
                    "strengths": ["Action personnelle visible."],
                    "weaknesses": ["Résultat peu détaillé."],
                    "suggested_improvements": ["Précisez l'effet de votre action."],
                }
            )
        ),
    )

    evaluation = asyncio.run(evaluate_behavioral_answer(question, "Projet scolaire en équipe."))

    assert evaluation["score"] == 36
    assert evaluation["max_score"] == 50
    assert [item["criterion_id"] for item in evaluation["criteria_scores"]] == [
        criterion["id"] for criterion in question["criteria"]
    ]
    assert set(evaluation["star_scores"]) == {"situation", "task", "action", "result"}


def test_situational_question_does_not_claim_star_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = generate_behavioral_questions("decision-making")[1]
    monkeypatch.setattr(
        "app.behavioral_assessment.generate_career_assistant_reply",
        AsyncMock(
            return_value=json.dumps(
                {
                    "criteria_scores": [
                        {"criterion_id": criterion["id"], "score": 3}
                        for criterion in question["criteria"]
                    ],
                    "star_scores": {},
                    "explanation": "Évaluation de la démarche proposée.",
                    "strengths": [],
                    "weaknesses": [],
                    "suggested_improvements": [],
                }
            )
        ),
    )

    evaluation = asyncio.run(evaluate_behavioral_answer(question, "Je clarifie les priorités."))

    assert evaluation["star_scores"] == {}
    assert evaluation["max_score"] == 30


def test_behavioral_evaluation_rejects_mismatched_star_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = generate_behavioral_questions("teamwork")[0]
    monkeypatch.setattr(
        "app.behavioral_assessment.generate_career_assistant_reply",
        AsyncMock(
            return_value=json.dumps(
                {
                    "criteria_scores": [
                        {"criterion_id": criterion["id"], "score": 3}
                        for criterion in question["criteria"]
                    ],
                    "star_scores": {"action": {"score": 3, "evidence": "Action."}},
                    "explanation": "Incomplete.",
                    "strengths": [],
                    "weaknesses": [],
                    "suggested_improvements": [],
                }
            )
        ),
    )

    with pytest.raises(AssistantServiceError) as error:
        asyncio.run(evaluate_behavioral_answer(question, "Mon exemple."))
    assert error.value.status_code == 502


def test_behavioral_assessment_persists_star_and_situational_feedback(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    session.autoflush = False
    monkeypatch.setattr(
        main,
        "evaluate_behavioral_answer",
        AsyncMock(side_effect=fake_behavioral_evaluation),
    )

    started = client.post(
        "/candidate/interview-prep/behavioral-assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "teamwork"},
    )
    assert started.status_code == 201
    assessment = started.json()
    assert assessment["competency_name"] == "Travail en équipe"
    assert assessment["status"] == "in_progress"
    assert [question["type"] for question in assessment["questions"]] == [
        "behavioral",
        "situational",
    ]
    assessment_id = assessment["id"]

    first_answer = client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "answer": "Dans un projet scolaire, notre équipe devait..."},
    )
    assert first_answer.status_code == 200
    first_result = first_answer.json()["answers"][0]["evaluation"]
    assert first_result["max_score"] == 50
    assert set(first_result["star_scores"]) == {"situation", "task", "action", "result"}
    assert first_answer.json()["status"] == "in_progress"

    second_answer = client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q2", "answer": "Je clarifierais le besoin avec l'équipe."},
    )
    assert second_answer.status_code == 200
    second_result = second_answer.json()["answers"][1]["evaluation"]
    assert second_result["star_scores"] == {}
    assert second_answer.json()["status"] == "completed"

    persisted = client.get(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}",
        headers=candidate_headers,
    )
    assert persisted.status_code == 200
    assert len(persisted.json()["answers"]) == 2
    assert persisted.json()["answers"][0]["evaluation"]["suggested_improvements"]
    assert client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "answer": "Second attempt"},
    ).status_code == 409


def test_behavioral_assessment_rejects_unknown_competency_and_question(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    assert client.post(
        "/candidate/interview-prep/behavioral-assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "unsupported"},
    ).status_code == 404
    started = client.post(
        "/candidate/interview-prep/behavioral-assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "communication"},
    )
    assert started.status_code == 201
    assessment_id = started.json()["id"]
    monkeypatch.setattr(
        main,
        "evaluate_behavioral_answer",
        AsyncMock(side_effect=fake_behavioral_evaluation),
    )
    assert client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "unknown", "answer": "A response."},
    ).status_code == 404
    assert client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "selected_option_id": "a"},
    ).status_code == 422


def test_behavioral_assessments_are_candidate_owned_and_fail_without_model_feedback(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    started = client.post(
        "/candidate/interview-prep/behavioral-assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "communication"},
    )
    assessment_id = started.json()["id"]
    for role, user in users.items():
        if role == Role.CANDIDATE:
            continue
        headers = auth_headers(user)
        assert client.get(
            f"/candidate/interview-prep/behavioral-assessments/{assessment_id}",
            headers=headers,
        ).status_code == 403
        assert client.post(
            "/candidate/interview-prep/behavioral-assessments",
            headers=headers,
            json={"offer_id": offer_id, "skill": "communication"},
        ).status_code == 403

    other_candidate = User(
        id="behavioral-other-candidate",
        email="behavioral-other@example.test",
        password_hash="unused",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    assert client.get(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}",
        headers=auth_headers(other_candidate),
    ).status_code == 404

    monkeypatch.setattr(
        main,
        "evaluate_behavioral_answer",
        AsyncMock(
            side_effect=AssistantServiceError("Behavioral model unavailable.")
        ),
    )
    failed_response = client.post(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "answer": "An example."},
    )
    assert failed_response.status_code == 503
    persisted = client.get(
        f"/candidate/interview-prep/behavioral-assessments/{assessment_id}",
        headers=candidate_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["answers"] == []
