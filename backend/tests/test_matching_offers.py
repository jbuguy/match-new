from fastapi.testclient import TestClient

from app.models import Role, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_candidate_skills_are_normalized_and_used_for_matching(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    employer_headers = auth_headers(users[Role.EMPLOYER])
    offer_response = client.post(
        "/employer/offers",
        headers=employer_headers,
        json={
            "title": "Développeur Python",
            "description": "Concevoir et maintenir des outils internes.",
            "location": "Tunis",
            "required_skills": ["Python", "SQL", "python"],
        },
    )
    assert offer_response.status_code == 201
    assert offer_response.json()["required_skills"] == ["Python", "SQL"]

    candidate_headers = auth_headers(users[Role.CANDIDATE])
    profile_response = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"skills": [" Python ", "PYTHON", "  Excel"]},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["skills"] == ["Python", "Excel"]

    matches_response = client.get("/candidate/matches", headers=candidate_headers)
    assert matches_response.status_code == 200
    assert matches_response.json()[0]["match_score"] == 50
    assert matches_response.json()[0]["matched_skills"] == ["Python"]
    assert matches_response.json()[0]["missing_skills"] == ["SQL"]


def test_employers_can_only_read_their_offers(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": "Chargé de projet",
            "description": "Coordonner les projets de transformation.",
            "location": "Sfax",
            "required_skills": ["Organisation"],
        },
    )
    assert response.status_code == 201

    own_offers = client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
    )
    other_offers = client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.TRAINING_PROVIDER]),
    )
    assert len(own_offers.json()) == 1
    assert other_offers.status_code == 403


def test_candidate_and_employer_routes_reject_other_roles(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    assert client.get(
        "/candidate/matches",
        headers=auth_headers(users[Role.EMPLOYER]),
    ).status_code == 403
    assert client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={
            "title": "Chargé de projet",
            "description": "Coordonner les projets de transformation.",
            "location": "Sfax",
            "required_skills": ["Organisation"],
        },
    ).status_code == 403


def test_invalid_job_offer_is_not_published(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": " ",
            "description": "Too short",
            "location": "Tunis",
            "required_skills": [],
        },
    )
    assert response.status_code == 422
    assert client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
    ).json() == []
