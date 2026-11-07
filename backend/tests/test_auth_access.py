import pytest
import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit import record_admin_action, record_sensitive_read
from app.dependencies import assert_organisation_member, assert_resource_owner
from app.models import (
    AuditEvent,
    Organisation,
    OrganisationMembership,
    OrganisationType,
    Role,
    User,
)
from app.permissions import Permission, has_permission
from app.security import create_access_token


@pytest.mark.parametrize("role", list(Role))
def test_each_role_can_read_its_authenticated_identity(
    client: TestClient,
    users: dict[Role, User],
    role: Role,
) -> None:
    token, _ = create_access_token(users[role])

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == role.value
    assert response.json()["email"] == users[role].email


@pytest.mark.parametrize("role", list(Role))
def test_each_role_can_log_in(
    client: TestClient,
    users: dict[Role, User],
    role: Role,
) -> None:
    response = client.post(
        "/auth/login",
        json={"email": users[role].email, "password": "LocalDemoPassword2026!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == role.value


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (Role.CANDIDATE, 403),
        (Role.EMPLOYER, 403),
        (Role.MINISTRY_ADMIN, 403),
        (Role.TRAINING_PROVIDER, 403),
        (Role.OPERATOR, 200),
    ],
)
def test_operator_audit_route_is_role_restricted(
    client: TestClient,
    users: dict[Role, User],
    role: Role,
    expected_status: int,
) -> None:
    token, _ = create_access_token(users[role])

    response = client.get("/operator/audit-log", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == expected_status


def test_protected_routes_reject_missing_or_invalid_tokens(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    assert client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-token"}
    ).status_code == 401


def test_public_liveness_remains_available_without_authentication(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_issues_role_claim_and_audits_without_email(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    candidate = users[Role.CANDIDATE]

    response = client.post(
        "/auth/login",
        json={"email": candidate.email.upper(), "password": "LocalDemoPassword2026!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == Role.CANDIDATE.value
    assert response.json()["token_type"] == "bearer"
    claims = jwt.decode(
        response.json()["access_token"],
        "test-only-signing-key-that-is-at-least-32-chars",
        algorithms=["HS256"],
        issuer="mahara-match",
    )
    assert claims["sub"] == candidate.id
    assert claims["role"] == Role.CANDIDATE.value

    operator_token, _ = create_access_token(users[Role.OPERATOR])
    audit_response = client.get(
        "/operator/audit-log",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    audit_json = audit_response.json()
    assert audit_response.status_code == 200
    assert audit_json[0]["action"] == "auth.login.succeeded"
    assert audit_json[0]["actor_role"] == Role.CANDIDATE.value
    assert candidate.email not in audit_response.text
    assert candidate.id not in audit_response.text


def test_login_failure_has_generic_message_and_is_audited(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "not-a-real-user@example.test", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect."

    operator_token, _ = create_access_token(users[Role.OPERATOR])
    audit_response = client.get(
        "/operator/audit-log",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert audit_response.json()[0]["action"] == "auth.login.failed"
    assert "not-a-real-user@example.test" not in audit_response.text


def test_token_is_invalidated_when_a_users_role_changes(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    candidate = users[Role.CANDIDATE]
    token, _ = create_access_token(candidate)
    candidate.role = Role.EMPLOYER
    session.flush()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_permission_matrix_prevents_cross_role_reads() -> None:
    assert has_permission(Role.CANDIDATE, Permission.PROFILE_READ_OWN)
    assert not has_permission(Role.EMPLOYER, Permission.PROFILE_READ_OWN)
    assert has_permission(Role.EMPLOYER, Permission.APPLICANT_READ_BY_APPLICATION)
    assert not has_permission(Role.MINISTRY_ADMIN, Permission.PROFILE_READ_OWN)
    assert has_permission(Role.MINISTRY_ADMIN, Permission.INDICATOR_READ_AGGREGATE)
    assert not has_permission(Role.TRAINING_PROVIDER, Permission.APPLICATION_MANAGE_OWN)
    assert has_permission(Role.TRAINING_PROVIDER, Permission.COURSE_MANAGE_ORGANISATION)
    assert has_permission(Role.OPERATOR, Permission.AUDIT_READ)
    assert not has_permission(Role.OPERATOR, Permission.PROFILE_READ_OWN)


def test_resource_access_is_limited_to_candidate_or_organisation_member(
    session: Session,
    users: dict[Role, User],
) -> None:
    candidate = users[Role.CANDIDATE]
    employer = users[Role.EMPLOYER]
    other_employer = users[Role.TRAINING_PROVIDER]
    organisation = Organisation(
        name="Employer Org", organisation_type=OrganisationType.EMPLOYER
    )
    session.add(organisation)
    session.flush()
    session.add(
        OrganisationMembership(user_id=employer.id, organisation_id=organisation.id)
    )
    session.flush()

    assert_resource_owner(
        candidate,
        resource_owner_id=candidate.id,
    )
    assert_organisation_member(
        employer,
        organisation_id=organisation.id,
        session=session,
    )
    with pytest.raises(HTTPException) as candidate_error:
        assert_resource_owner(
            candidate,
            resource_owner_id="another-candidate",
        )
    assert getattr(candidate_error.value, "status_code", None) == 403
    with pytest.raises(HTTPException) as other_org_error:
        assert_organisation_member(
            other_employer,
            organisation_id=organisation.id,
            session=session,
        )
    assert getattr(other_org_error.value, "status_code", None) == 403
    with pytest.raises(HTTPException) as operator_error:
        assert_resource_owner(
            users[Role.OPERATOR],
            resource_owner_id=users[Role.OPERATOR].id,
        )
    assert getattr(operator_error.value, "status_code", None) == 403


def test_password_hashes_are_not_plain_text(users: dict[Role, User]) -> None:
    candidate = users[Role.CANDIDATE]
    assert candidate.password_hash != "LocalDemoPassword2026!"
    assert candidate.password_hash.startswith("$argon2")


def test_login_audit_events_are_append_only(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    client.post(
        "/auth/login",
        json={"email": users[Role.CANDIDATE].email, "password": "LocalDemoPassword2026!"},
    )
    event = session.query(AuditEvent).one()

    with pytest.raises(RuntimeError, match="append-only"):
        session.delete(event)
        session.flush()


def test_admin_actions_and_sensitive_reads_are_audited(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    record_admin_action(
        session,
        actor=users[Role.MINISTRY_ADMIN],
        action="referential.updated",
        resource_type="skill",
        resource_id="skill-code-1",
    )
    record_sensitive_read(
        session,
        actor=users[Role.EMPLOYER],
        resource_type="candidate_contact",
        resource_id="candidate-123",
    )
    session.commit()

    operator_token, _ = create_access_token(users[Role.OPERATOR])
    response = client.get(
        "/operator/audit-log",
        headers={"Authorization": f"Bearer {operator_token}"},
    )

    assert response.status_code == 200
    assert {event["action"] for event in response.json()} == {
        "sensitive.read",
        "admin.referential.updated",
    }
    assert "candidate-123" not in response.text
    assert all(
        not {"actor_user_id", "resource_id", "details"}.intersection(event)
        for event in response.json()
    )
