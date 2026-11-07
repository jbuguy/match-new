from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.career_roadmap import build_career_roadmap
from app.models import Role, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_roadmap_is_deterministic_and_prioritizes_common_skill_gaps() -> None:
    offers = [
        SimpleNamespace(
            id="offer-b",
            title="Analyste",
            required_skills=["SQL", "Excel", "Python"],
        ),
        SimpleNamespace(
            id="offer-a",
            title="Développeuse",
            required_skills=["Python", "sql"],
        ),
    ]

    steps = build_career_roadmap(offers, [" Python "], {"sql": True})

    assert [(step.skill, step.offer_count, step.completed) for step in steps] == [
        ("SQL", 2, True),
        ("Excel", 1, False),
    ]
    assert steps[0].required_by == ["Analyste", "Développeuse"]
    assert [
        step.skill_key
        for step in build_career_roadmap(reversed(offers), ["Python"], {"sql": True})
    ] == ["sql", "excel"]


def test_candidate_can_update_only_their_current_roadmap_steps(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    employer_headers = auth_headers(users[Role.EMPLOYER])
    offer_response = client.post(
        "/employer/offers",
        headers=employer_headers,
        json={
            "title": "Analyste de données",
            "description": "Analyser des données pour éclairer les décisions.",
            "location": "Tunis",
            "required_skills": ["SQL", "Excel"],
        },
    )
    assert offer_response.status_code == 201

    candidate_headers = auth_headers(users[Role.CANDIDATE])
    roadmap_response = client.get("/candidate/roadmap", headers=candidate_headers)
    assert roadmap_response.status_code == 200
    assert [step["skill"] for step in roadmap_response.json()["steps"]] == ["Excel", "SQL"]
    assert roadmap_response.json()["progress_percent"] == 0

    updated_response = client.put(
        "/candidate/roadmap/steps",
        headers=candidate_headers,
        json={"skill": "sql", "completed": True},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["completed_steps"] == 1
    assert updated_response.json()["total_steps"] == 2
    assert updated_response.json()["progress_percent"] == 50
    assert next(
        step for step in updated_response.json()["steps"] if step["skill_key"] == "sql"
    )["completed"]

    other_candidate = User(
        id="other-candidate",
        email="other-candidate@example.test",
        password_hash="unused",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    other_headers = auth_headers(other_candidate)
    other_roadmap = client.get("/candidate/roadmap", headers=other_headers)
    assert other_roadmap.status_code == 200
    assert other_roadmap.json()["completed_steps"] == 0


def test_roadmap_rejects_non_candidate_roles_and_unknown_skills(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    for role, user in users.items():
        if role != Role.CANDIDATE:
            assert client.get(
                "/candidate/roadmap",
                headers=auth_headers(user),
            ).status_code == 403
    assert client.put(
        "/candidate/roadmap/steps",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={"skill": "Nonexistent", "completed": True},
    ).status_code == 404
