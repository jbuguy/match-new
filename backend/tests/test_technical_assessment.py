import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import main
from app.assistant_services import AssistantServiceError
from app.models import Role, User
from app.security import create_access_token
from app.technical_assessment import (
    evaluate_open_answer,
    generate_technical_questions,
)


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def create_offer(client: TestClient, employer: User, skills: list[str]) -> str:
    response = client.post(
        "/employer/offers",
        headers=auth_headers(employer),
        json={
            "title": "Développeuse Python",
            "description": "Concevoir des services et traiter des données.",
            "location": "Tunis",
            "required_skills": skills,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def fake_evaluation(question: dict[str, Any], answer: str) -> dict[str, object]:
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
    return {
        "score": 12,
        "max_score": 15,
        "criteria_scores": criteria_scores,
        "explanation": "Réponse évaluée selon les critères techniques.",
        "strengths": ["La démarche est structurée."],
        "weaknesses": ["Quelques détails restent à préciser."],
        "suggested_improvements": ["Précisez les vérifications effectuées."],
        "method": "llm",
    }


def test_question_generation_has_objective_and_text_only_formats() -> None:
    python_questions = generate_technical_questions("Python")
    assert len(python_questions) == 3
    assert [question["type"] for question in python_questions] == [
        "knowledge",
        "practical",
        "scenario",
    ]
    assert python_questions[0]["format"] == "multiple_choice"
    assert "correct_option_id" in python_questions[0]
    assert python_questions[1]["format"] == "text_exercise"

    custom_skill_questions = generate_technical_questions("Cybersécurité")
    assert custom_skill_questions[0]["format"] == "short_answer"
    assert all(
        question["format"] != "code_execution"
        for question in custom_skill_questions
    )


def test_open_answer_evaluation_validates_and_normalizes_structured_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = generate_technical_questions("Excel")[0]
    monkeypatch.setattr(
        "app.technical_assessment.generate_career_assistant_reply",
        AsyncMock(
            return_value=json.dumps(
                {
                    "criteria_scores": [
                        {"criterion_id": "reasoning", "score": 4},
                        {"criterion_id": "correctness", "score": 3},
                        {"criterion_id": "completeness", "score": 2},
                    ],
                    "explanation": "Réponse structurée.",
                    "strengths": ["Donne un exemple."],
                    "weaknesses": ["Manque de précision."],
                    "suggested_improvements": ["Précisez le résultat attendu."],
                }
            )
        ),
    )

    evaluation = asyncio.run(evaluate_open_answer(question, "Une réponse"))

    assert evaluation["score"] == 9
    assert evaluation["max_score"] == 15
    assert [item["criterion_id"] for item in evaluation["criteria_scores"]] == [
        "correctness",
        "completeness",
        "reasoning",
    ]
    assert evaluation["method"] == "llm"


def test_open_answer_evaluation_rejects_unexpected_criteria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = generate_technical_questions("Excel")[0]
    monkeypatch.setattr(
        "app.technical_assessment.generate_career_assistant_reply",
        AsyncMock(
            return_value=json.dumps(
                {
                    "criteria_scores": [
                        {"criterion_id": "unrequested", "score": 5},
                    ],
                    "explanation": "Invalid criteria.",
                    "strengths": [],
                    "weaknesses": [],
                    "suggested_improvements": [],
                }
            )
        ),
    )

    with pytest.raises(AssistantServiceError) as error:
        asyncio.run(evaluate_open_answer(question, "Une réponse"))
    assert error.value.status_code == 502


def test_assessment_persists_deterministic_and_open_answer_evaluations(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session.autoflush = False
    offer_id = create_offer(client, users[Role.EMPLOYER], ["Python"])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    monkeypatch.setattr(main, "evaluate_open_answer", AsyncMock(side_effect=fake_evaluation))

    started = client.post(
        "/candidate/interview-prep/assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": " python "},
    )
    assert started.status_code == 201
    assessment = started.json()
    assert assessment["skill"] == "Python"
    assert assessment["status"] == "in_progress"
    assert len(assessment["questions"]) == 3
    assert "correct_option_id" not in assessment["questions"][0]
    assessment_id = assessment["id"]

    objective_answer = client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "selected_option_id": "a"},
    )
    assert objective_answer.status_code == 200
    assert objective_answer.json()["answers"][0]["evaluation"]["method"] == "deterministic"
    assert objective_answer.json()["answers"][0]["evaluation"]["score"] == 5

    practical_answer = client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q2", "answer": "Je vérifie les entrées et les résultats."},
    )
    assert practical_answer.status_code == 200
    assert practical_answer.json()["answers"][1]["evaluation"]["score"] == 12
    assert practical_answer.json()["answers"][1]["evaluation"]["max_score"] == 15
    assert practical_answer.json()["status"] == "in_progress"

    scenario_answer = client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q3", "answer": "Je reproduis le problème puis je teste."},
    )
    assert scenario_answer.status_code == 200
    assert scenario_answer.json()["status"] == "completed"
    assert len(scenario_answer.json()["answers"]) == 3

    persisted = client.get(
        f"/candidate/interview-prep/assessments/{assessment_id}",
        headers=candidate_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["answers"][2]["answer"] == "Je reproduis le problème puis je teste."
    assert persisted.json()["answers"][2]["evaluation"]["suggested_improvements"]
    assert client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "selected_option_id": "a"},
    ).status_code == 409


def test_assessment_requires_offer_skill_and_supported_answer_format(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER], ["SQL"])
    candidate_headers = auth_headers(users[Role.CANDIDATE])

    assert client.post(
        "/candidate/interview-prep/assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "Python"},
    ).status_code == 404
    started = client.post(
        "/candidate/interview-prep/assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "SQL"},
    )
    assert started.status_code == 201
    assessment_id = started.json()["id"]

    assert client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "answer": "Free text is not accepted for a choice."},
    ).status_code == 422
    assert client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "selected_option_id": "invalid"},
    ).status_code == 422
    assert client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q2", "selected_option_id": "a"},
    ).status_code == 422


def test_open_answer_service_failure_does_not_save_unscored_response(
    client: TestClient,
    users: dict[Role, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER], ["Excel"])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    started = client.post(
        "/candidate/interview-prep/assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "Excel"},
    )
    assessment_id = started.json()["id"]
    monkeypatch.setattr(
        main,
        "evaluate_open_answer",
        AsyncMock(
            side_effect=AssistantServiceError("Assessment model unavailable.")
        ),
    )

    response = client.post(
        f"/candidate/interview-prep/assessments/{assessment_id}/answers",
        headers=candidate_headers,
        json={"question_id": "q1", "answer": "A spreadsheet skill."},
    )
    assert response.status_code == 503
    persisted = client.get(
        f"/candidate/interview-prep/assessments/{assessment_id}",
        headers=candidate_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["answers"] == []


def test_assessments_are_candidate_owned_and_candidate_only(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    offer_id = create_offer(client, users[Role.EMPLOYER], ["Python"])
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    started = client.post(
        "/candidate/interview-prep/assessments",
        headers=candidate_headers,
        json={"offer_id": offer_id, "skill": "Python"},
    )
    assessment_id = started.json()["id"]

    for role, user in users.items():
        if role == Role.CANDIDATE:
            continue
        headers = auth_headers(user)
        assert client.post(
            "/candidate/interview-prep/assessments",
            headers=headers,
            json={"offer_id": offer_id, "skill": "Python"},
        ).status_code == 403
        assert client.get(
            f"/candidate/interview-prep/assessments/{assessment_id}",
            headers=headers,
        ).status_code == 403

    other_candidate = User(
        id="different-candidate",
        email="different-candidate@example.test",
        password_hash="unused",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    other_candidate_headers = auth_headers(other_candidate)
    assert client.get(
        f"/candidate/interview-prep/assessments/{assessment_id}",
        headers=other_candidate_headers,
    ).status_code == 404
