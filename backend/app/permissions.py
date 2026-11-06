from enum import Enum

from app.models import Role


class Permission(str, Enum):
    PROFILE_READ_OWN = "profile:read:own"
    PROFILE_WRITE_OWN = "profile:write:own"
    CONSENT_MANAGE_OWN = "consent:manage:own"
    MATCH_READ_OWN = "match:read:own"
    APPLICATION_MANAGE_OWN = "application:manage:own"
    ROADMAP_MANAGE_OWN = "roadmap:manage:own"
    CHAT_MANAGE_OWN = "chat:manage:own"
    OFFER_MANAGE_ORGANISATION = "offer:manage:organisation"
    APPLICATION_MANAGE_ORGANISATION = "application:manage:organisation"
    APPLICANT_READ_BY_APPLICATION = "applicant:read:by_application"
    REFERENTIAL_MANAGE = "referential:manage"
    SUGGESTION_REVIEW = "suggestion:review"
    DATASET_IMPORT = "dataset:import"
    INDICATOR_READ_AGGREGATE = "indicator:read:aggregate"
    EXPORT_CREATE_LOGGED = "export:create:logged"
    COURSE_MANAGE_ORGANISATION = "course:manage:organisation"
    VALIDATED_SKILL_READ = "skill:read:validated"
    SERVICE_CONFIGURE = "service:configure"
    JOB_STATUS_READ = "job_status:read"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.CANDIDATE: frozenset(
        {
            Permission.PROFILE_READ_OWN,
            Permission.PROFILE_WRITE_OWN,
            Permission.CONSENT_MANAGE_OWN,
            Permission.MATCH_READ_OWN,
            Permission.APPLICATION_MANAGE_OWN,
            Permission.ROADMAP_MANAGE_OWN,
            Permission.CHAT_MANAGE_OWN,
        }
    ),
    Role.EMPLOYER: frozenset(
        {
            Permission.OFFER_MANAGE_ORGANISATION,
            Permission.APPLICATION_MANAGE_ORGANISATION,
            Permission.APPLICANT_READ_BY_APPLICATION,
        }
    ),
    Role.MINISTRY_ADMIN: frozenset(
        {
            Permission.REFERENTIAL_MANAGE,
            Permission.SUGGESTION_REVIEW,
            Permission.DATASET_IMPORT,
            Permission.INDICATOR_READ_AGGREGATE,
            Permission.EXPORT_CREATE_LOGGED,
        }
    ),
    Role.TRAINING_PROVIDER: frozenset(
        {Permission.COURSE_MANAGE_ORGANISATION, Permission.VALIDATED_SKILL_READ}
    ),
    Role.OPERATOR: frozenset(
        {Permission.SERVICE_CONFIGURE, Permission.JOB_STATUS_READ, Permission.AUDIT_READ}
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
