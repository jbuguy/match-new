from app.models import AuditEvent, User
from sqlalchemy.orm import Session


def record_audit_event(
    session: Session,
    *,
    action: str,
    actor: User | None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, object] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    session.add(event)
    return event


def record_sensitive_read(
    session: Session,
    *,
    actor: User,
    resource_type: str,
    resource_id: str,
) -> AuditEvent:
    return record_audit_event(
        session,
        action="sensitive.read",
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
    )


def record_admin_action(
    session: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
) -> AuditEvent:
    return record_audit_event(
        session,
        action=f"admin.{action}",
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
    )
