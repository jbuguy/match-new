import os

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.dependencies import get_current_user, require_role
from app.models import AuditEvent, Role, User
from app.schemas import AuditEventResponse, LoginRequest, LoginResponse, UserResponse
from app.security import DUMMY_PASSWORD_HASH, create_access_token, verify_password


app = FastAPI(
    title="Mahara Match API",
    description="API for the Mahara Match employment support platform.",
    version="0.1.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    """Report that the API process is responsive; does not imply database readiness."""
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse, tags=["authentication"])
def login(
    request: LoginRequest,
    session: Session = Depends(get_session),
) -> LoginResponse:
    user = session.scalar(select(User).where(User.email == request.email))
    password_matches = verify_password(
        request.password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )
    if user is None or not user.is_active or not password_matches:
        record_audit_event(
            session,
            action="auth.login.failed",
            actor=user,
            resource_type="authentication",
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        access_token, expires_in = create_access_token(user)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured correctly.",
        ) from error

    record_audit_event(
        session,
        action="auth.login.succeeded",
        actor=user,
        resource_type="authentication",
    )
    session.commit()
    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@app.get("/auth/me", response_model=UserResponse, tags=["authentication"])
def current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@app.get(
    "/operator/audit-log",
    response_model=list[AuditEventResponse],
    tags=["operator"],
)
def read_audit_log(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    _operator: User = Depends(require_role(Role.OPERATOR)),
) -> list[AuditEventResponse]:
    events = session.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id).limit(limit)
    )
    return [
        AuditEventResponse(
            id=audit_event.id,
            action=audit_event.action,
            resource_type=audit_event.resource_type,
            actor_role=audit_event.actor_role,
            created_at=audit_event.created_at,
        )
        for audit_event in events
    ]
