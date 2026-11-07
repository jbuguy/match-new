from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.competencies import build_role_preparation_profile
from app.models import Role, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_role_preparation_profile_uses_offer_skills_and_marks_suggestions() -> None:
    offer = SimpleNamespace(
        id="offer-1",
        title="Développeuse Python",
        description="Construire des services.",
        location="Tunis",
        required_skills=["Python", "SQL", "python"],
    )

    profile = build_role_preparation_profile(offer, [" python "])

    assert [item["name"] for item in profile["required_competencies"]] == [
        "Python",
        "SQL",
    ]
    python_requirement = profile["required_competencies"][0]
    assert python_requirement["candidate_evidence"] == "self_reported"
    assert python_requirement["source"] == "job_offer"
    assert python_requirement["mandatory"] is True
    assert python_requirement["required_proficiency_level"] is None
    assert python_requirement["importance_weight"] is None
    sql_requirement = profile["required_competencies"][1]
    assert sql_requirement["candidate_evidence"] == "gap"
    assert all(
        item["source"] == "platform_guidance"
        and item["mandatory"] is False
        and item["candidate_evidence"] == "not_assessed"
        for item in profile["suggested_competencies"]
    )
    assert [item["level"] for item in profile["proficiency_levels"]] == [1, 2, 3, 4, 5]


def test_candidate_can_read_offer_based_interview_profile(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    offer_response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": "Technicienne support",
            "description": "Assurer le support applicatif.",
            "location": "Sfax",
            "required_skills": ["Support informatique", "Réseaux"],
        },
    )
    assert offer_response.status_code == 201
    offer_id = offer_response.json()["id"]
    candidate_headers = auth_headers(users[Role.CANDIDATE])

    roles_response = client.get(
        "/candidate/interview-prep/roles",
        headers=candidate_headers,
    )
    assert roles_response.status_code == 200
    assert [role["id"] for role in roles_response.json()] == [offer_id]

    profile_response = client.get(
        f"/candidate/interview-prep/profiles/{offer_id}",
        headers=candidate_headers,
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["role"]["title"] == "Technicienne support"
    assert [item["name"] for item in profile["required_competencies"]] == [
        "Support informatique",
        "Réseaux",
    ]
    assert "communication" in [item["id"] for item in profile["suggested_competencies"]]
    assert client.get(
        "/candidate/interview-prep/profiles/unknown-offer",
        headers=candidate_headers,
    ).status_code == 404


def test_interview_preparation_endpoints_are_candidate_only(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    for role, user in users.items():
        if role == Role.CANDIDATE:
            continue
        headers = auth_headers(user)
        assert client.get(
            "/candidate/interview-prep/roles",
            headers=headers,
        ).status_code == 403
        assert client.get(
            "/candidate/interview-prep/profiles/any-offer",
            headers=headers,
        ).status_code == 403
