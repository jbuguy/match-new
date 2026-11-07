from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organisation, OrganisationType, Role, User
from app.security import create_access_token, hash_password


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def course_payload(**overrides: object) -> dict[str, object]:
    return {
        "title": "Formation Excel avancé",
        "summary": "Apprendre à analyser des données avec Excel.",
        "skills": ["Excel", "Analyse"],
        "delivery_mode": "hybrid",
        "location": "Tunis",
        "starts_on": "2026-12-01",
        "ends_on": "2026-12-15",
        "duration_hours": 24,
        "capacity": 2,
        "price_tnd": "150.00",
        "status": "published",
        **overrides,
    }


def offer_payload(**overrides: object) -> dict[str, object]:
    return {
        "title": "Analyste de données",
        "description": "Analyser et partager les indicateurs métier.",
        "location": "Tunis",
        "required_skills": ["Python", "SQL"],
        **overrides,
    }


def test_training_courses_are_owned_and_candidate_enrollment_is_scoped(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    provider_headers = auth_headers(users[Role.TRAINING_PROVIDER])
    created = client.post(
        "/training/courses",
        headers=provider_headers,
        json=course_payload(capacity=1),
    )
    assert created.status_code == 201
    course = created.json()
    assert course["price_tnd"] == "150.00"
    assert course["enrollment_count"] == 0

    candidate_headers = auth_headers(users[Role.CANDIDATE])
    assert [item["id"] for item in client.get(
        "/candidate/courses", headers=candidate_headers
    ).json()] == [course["id"]]
    enrolled = client.post(
        f"/candidate/courses/{course['id']}/enroll",
        headers=candidate_headers,
    )
    assert enrolled.status_code == 201
    assert enrolled.json()["status"] == "enrolled"
    assert client.post(
        f"/candidate/courses/{course['id']}/enroll",
        headers=candidate_headers,
    ).status_code == 409
    assert client.get(
        "/candidate/enrollments", headers=candidate_headers
    ).json()[0]["course_title"] == course["title"]

    second_candidate = User(
        email="second-candidate@example.test",
        password_hash=hash_password("LocalDemoPassword2026!"),
        role=Role.CANDIDATE,
    )
    session.add(second_candidate)
    session.flush()
    full_course = client.post(
        f"/candidate/courses/{course['id']}/enroll",
        headers=auth_headers(second_candidate),
    )
    assert full_course.status_code == 409

    updated = client.put(
        f"/training/enrollments/{enrolled.json()['id']}/status",
        headers=provider_headers,
        json={"status": "completed"},
    )
    assert updated.status_code == 200
    assert updated.json()["candidate_name"] is None
    assert updated.json()["candidate_skills"] == []

    provider_courses = client.get("/training/courses", headers=provider_headers).json()
    assert provider_courses[0]["completed_count"] == 1
    assert provider_courses[0]["enrollment_count"] == 0
    assert client.get(
        f"/training/courses/{course['id']}/enrollments",
        headers=provider_headers,
    ).json()[0]["status"] == "completed"
    assert client.get(
        "/training/courses", headers=auth_headers(users[Role.EMPLOYER])
    ).status_code == 403


def test_provider_course_validation_and_capacity_updates(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    provider_headers = auth_headers(users[Role.TRAINING_PROVIDER])
    assert client.post(
        "/training/courses",
        headers=provider_headers,
        json=course_payload(location=None),
    ).status_code == 422
    assert client.post(
        "/training/courses",
        headers=provider_headers,
        json=course_payload(starts_on="2026-12-20", ends_on="2026-12-01"),
    ).status_code == 422
    course = client.post(
        "/training/courses",
        headers=provider_headers,
        json=course_payload(delivery_mode="online", location=None),
    )
    assert course.status_code == 201
    assert client.post(
        "/training/courses",
        headers=auth_headers(users[Role.CANDIDATE]),
        json=course_payload(),
    ).status_code == 403
    other_provider = User(
        email="other-provider@example.test",
        password_hash=hash_password("LocalDemoPassword2026!"),
        role=Role.TRAINING_PROVIDER,
    )
    session.add(other_provider)
    session.flush()
    other_headers = auth_headers(other_provider)
    assert client.get("/training/courses", headers=other_headers).json() == []
    assert client.get(
        f"/training/courses/{course.json()['id']}/enrollments",
        headers=other_headers,
    ).status_code == 404
    assert client.put(
        f"/training/courses/{course.json()['id']}",
        headers=other_headers,
        json=course_payload(),
    ).status_code == 404


def test_job_applications_are_owned_and_admin_indicators_are_aggregate_only(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    employer_headers = auth_headers(users[Role.EMPLOYER])
    admin_headers = auth_headers(users[Role.MINISTRY_ADMIN])

    client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"full_name": "Candidate Private Name", "skills": ["Python", "Excel"]},
    )
    session.add(
        Organisation(name="Centre de formation de test", organisation_type=OrganisationType.TRAINING_PROVIDER)
    )
    first_offer = client.post(
        "/employer/offers", headers=employer_headers, json=offer_payload()
    ).json()
    second_offer = client.post(
        "/employer/offers",
        headers=employer_headers,
        json=offer_payload(
            title="Développeur Python",
            required_skills=["Python", "Docker"],
        ),
    ).json()
    first_application = client.post(
        f"/candidate/applications/{first_offer['id']}",
        headers=candidate_headers,
    )
    second_application = client.post(
        f"/candidate/applications/{second_offer['id']}",
        headers=candidate_headers,
    )
    assert first_application.status_code == 201
    assert second_application.status_code == 201
    assert client.post(
        f"/candidate/applications/{first_offer['id']}",
        headers=candidate_headers,
    ).status_code == 409

    assert client.get(
        "/employer/applications", headers=employer_headers
    ).json()[0]["candidate_skills"] == ["Python", "Excel"]
    hired = client.put(
        f"/employer/applications/{first_application.json()['id']}/status",
        headers=employer_headers,
        json={"status": "hired"},
    )
    rejected = client.put(
        f"/employer/applications/{second_application.json()['id']}/status",
        headers=employer_headers,
        json={"status": "rejected"},
    )
    assert hired.json()["status"] == "hired"
    assert rejected.json()["status"] == "rejected"
    assert client.put(
        f"/employer/applications/{first_application.json()['id']}/status",
        headers=employer_headers,
        json={"status": "rejected"},
    ).status_code == 409
    assert client.get(
        "/candidate/applications", headers=candidate_headers
    ).json()[0]["job_title"] in {"Analyste de données", "Développeur Python"}

    course = client.post(
        "/training/courses",
        headers=auth_headers(users[Role.TRAINING_PROVIDER]),
        json=course_payload(),
    ).json()
    enrolled = client.post(
        f"/candidate/courses/{course['id']}/enroll",
        headers=candidate_headers,
    )
    assert enrolled.status_code == 201
    client.put(
        f"/training/enrollments/{enrolled.json()['id']}/status",
        headers=auth_headers(users[Role.TRAINING_PROVIDER]),
        json={"status": "completed"},
    )

    indicators = client.get("/admin/indicators", headers=admin_headers)
    assert indicators.status_code == 200
    payload = indicators.json()
    assert payload["candidate_registrations"] == 1
    assert payload["organisations"] == 1
    assert payload["published_job_offers"] == 2
    assert payload["applications_total"] == 2
    assert payload["closed_applications"] == 2
    assert payload["hired_applications"] == 1
    assert payload["hire_rate_percent"] == 50.0
    assert payload["top_skills"][0] == {"skill": "Python", "offer_count": 2}
    assert payload["published_courses"] == 1
    assert payload["active_enrollments"] == 0
    assert payload["course_completions"] == 1
    assert "Candidate Private Name" not in indicators.text
    assert users[Role.CANDIDATE].email not in indicators.text
    assert client.get(
        "/admin/indicators", headers=candidate_headers
    ).status_code == 403
    assert client.get(
        "/employer/applications", headers=auth_headers(users[Role.TRAINING_PROVIDER])
    ).status_code == 403

    other_employer = User(
        email="other-employer@example.test",
        password_hash=hash_password("LocalDemoPassword2026!"),
        role=Role.EMPLOYER,
    )
    session.add(other_employer)
    session.flush()
    assert client.get(
        "/employer/applications", headers=auth_headers(other_employer)
    ).json() == []
    assert client.put(
        f"/employer/applications/{first_application.json()['id']}/status",
        headers=auth_headers(other_employer),
        json={"status": "reviewing"},
    ).status_code == 404


def test_admin_indicator_date_range_validation_and_empty_outcome_rate(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    admin_headers = auth_headers(users[Role.MINISTRY_ADMIN])
    invalid = client.get(
        "/admin/indicators?start_date=2026-12-02&end_date=2026-12-01",
        headers=admin_headers,
    )
    assert invalid.status_code == 422
    empty = client.get("/admin/indicators", headers=admin_headers).json()
    assert empty["hire_rate_percent"] is None
    assert empty["applications_total"] == 0
