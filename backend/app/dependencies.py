from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
    Organisation,
    OrganisationMembership,
    OrganisationType,
    Role,
    User,
)
from app.permissions import Permission, has_permission
from app.security import decode_access_token, role_from_claim


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured correctly.",
        ) from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user_id = claims.get("sub")
    token_role = role_from_claim(claims.get("role"))
    if not isinstance(user_id, str) or token_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, user_id)
    if user is None or not user.is_active or user.role != token_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: Role) -> Callable[..., User]:
    if not roles:
        raise ValueError("require_role needs at least one role.")

    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have access to this resource.",
            )
        return user

    return role_dependency


def require_permission(permission: Permission) -> Callable[..., User]:
    def permission_dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have permission for this action.",
            )
        return user

    return permission_dependency


def assert_resource_owner(
    user: User,
    *,
    resource_owner_id: str,
) -> None:
    if user.role == Role.CANDIDATE and user.id == resource_owner_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not own this resource.",
    )


def require_resource_owner(
    resource_owner_id: str,
    user: User = Depends(get_current_user),
) -> User:
    assert_resource_owner(user, resource_owner_id=resource_owner_id)
    return user


def assert_organisation_member(
    user: User,
    *,
    organisation_id: str,
    session: Session,
) -> None:
    allowed_organisation_type = {
        Role.EMPLOYER: OrganisationType.EMPLOYER,
        Role.TRAINING_PROVIDER: OrganisationType.TRAINING_PROVIDER,
    }.get(user.role)
    if allowed_organisation_type is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role cannot access organisation resources.",
        )
    membership = session.scalar(
        select(OrganisationMembership.id)
        .join(Organisation, Organisation.id == OrganisationMembership.organisation_id)
        .where(
            OrganisationMembership.user_id == user.id,
            OrganisationMembership.organisation_id == organisation_id,
            Organisation.organisation_type == allowed_organisation_type,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not belong to this organisation.",
        )


def require_organisation_member(
    organisation_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> User:
    assert_organisation_member(user, organisation_id=organisation_id, session=session)
    return user
