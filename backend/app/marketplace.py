from collections import Counter
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.audit import record_audit_event, record_sensitive_read
from app.database import get_session
from app.dependencies import require_permission
from app.models import (
    CandidateProfile,
    CourseEnrollment,
    CourseEnrollmentStatus,
    CourseStatus,
    JobApplication,
    JobApplicationStatus,
    JobOffer,
    Organisation,
    Role,
    TrainingCourse,
    User,
)
from app.permissions import Permission
from app.schemas import (
    AdminIndicatorsResponse,
    ApplicationStatusIndicator,
    CourseEnrollmentResponse,
    CourseEnrollmentStatusUpdate,
    EmployerApplicationResponse,
    JobApplicationResponse,
    JobApplicationStatusUpdate,
    ProviderCourseEnrollmentResponse,
    SkillDemandIndicator,
    TrainingCourseCreate,
    TrainingCourseResponse,
)

router = APIRouter()

_CLOSED_APPLICATION_STATUSES = {
    JobApplicationStatus.HIRED,
    JobApplicationStatus.REJECTED,
}


def _date_window(
    column: ColumnElement[datetime] | ColumnElement[datetime | None],
    start_date: date | None,
    end_date: date | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if start_date is not None:
        conditions.append(
            column >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        )
    if end_date is not None:
        conditions.append(
            column <= datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        )
    return conditions


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The start date must be on or before the end date.",
        )


def _enrollment_counts(
    session: Session,
    course_ids: list[str],
) -> dict[str, tuple[int, int]]:
    if not course_ids:
        return {}
    rows = session.execute(
        select(CourseEnrollment.course_id, CourseEnrollment.status, func.count())
        .where(CourseEnrollment.course_id.in_(course_ids))
        .group_by(CourseEnrollment.course_id, CourseEnrollment.status)
    )
    counts: dict[str, tuple[int, int]] = {}
    for course_id, enrollment_status, count in rows:
        enrolled, completed = counts.get(course_id, (0, 0))
        if enrollment_status == CourseEnrollmentStatus.ENROLLED:
            enrolled = count
        elif enrollment_status == CourseEnrollmentStatus.COMPLETED:
            completed = count
        counts[course_id] = (enrolled, completed)
    return counts


def _course_response(
    course: TrainingCourse,
    counts: tuple[int, int] = (0, 0),
) -> TrainingCourseResponse:
    return TrainingCourseResponse.model_validate(course).model_copy(
        update={"enrollment_count": counts[0], "completed_count": counts[1]}
    )


def _candidate_application_response(
    application: JobApplication,
    offer: JobOffer,
) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=application.id,
        job_offer_id=offer.id,
        job_title=offer.title,
        location=offer.location,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.post(
    "/candidate/applications/{offer_id}",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["candidate applications"],
)
def apply_to_job(
    offer_id: str,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> JobApplicationResponse:
    offer = session.get(JobOffer, offer_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job offer not found.")
    application = JobApplication(
        candidate_id=user.id,
        job_offer_id=offer.id,
        status=JobApplicationStatus.SUBMITTED,
    )
    session.add(application)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        existing_application = session.scalar(
            select(JobApplication.id).where(
                JobApplication.candidate_id == user.id,
                JobApplication.job_offer_id == offer.id,
            )
        )
        if existing_application is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this offer.",
        ) from error
    record_audit_event(
        session,
        action="candidate.job_application.created",
        actor=user,
        resource_type="job_application",
        resource_id=application.id,
    )
    session.commit()
    session.refresh(application)
    return _candidate_application_response(application, offer)


@router.get(
    "/candidate/applications",
    response_model=list[JobApplicationResponse],
    tags=["candidate applications"],
)
def candidate_applications(
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> list[JobApplicationResponse]:
    rows = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.candidate_id == user.id)
        .order_by(JobApplication.created_at.desc())
    )
    return [
        _candidate_application_response(application, offer)
        for application, offer in rows
    ]


@router.get(
    "/employer/applications",
    response_model=list[EmployerApplicationResponse],
    tags=["employer applications"],
)
def employer_applications(
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> list[EmployerApplicationResponse]:
    rows = session.execute(
        select(JobApplication, JobOffer, User, CandidateProfile)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .join(User, User.id == JobApplication.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(JobOffer.employer_id == user.id)
        .order_by(JobApplication.created_at.desc())
    )
    response: list[EmployerApplicationResponse] = []
    for application, offer, candidate, profile in rows:
        record_sensitive_read(
            session,
            actor=user,
            resource_type="job_applicant",
            resource_id=candidate.id,
        )
        response.append(
            EmployerApplicationResponse(
                id=application.id,
                job_offer_id=offer.id,
                job_title=offer.title,
                location=offer.location,
                status=application.status,
                created_at=application.created_at,
                updated_at=application.updated_at,
                candidate_name=profile.full_name if profile else None,
                candidate_location=profile.location if profile else None,
                candidate_skills=profile.skills if profile else [],
            )
        )
    if response:
        session.commit()
    return response


@router.put(
    "/employer/applications/{application_id}/status",
    response_model=JobApplicationResponse,
    tags=["employer applications"],
)
def update_application_status(
    application_id: str,
    request: JobApplicationStatusUpdate,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> JobApplicationResponse:
    row = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(
            JobApplication.id == application_id,
            JobOffer.employer_id == user.id,
        )
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    application, offer = row
    if application.status in _CLOSED_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A closed application outcome cannot be changed.",
        )
    if request.status == JobApplicationStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An employer cannot reset an application to submitted.",
        )
    previous_status = application.status
    application.status = request.status
    record_audit_event(
        session,
        action="employer.job_application.status_updated",
        actor=user,
        resource_type="job_application",
        resource_id=application.id,
        details={"from": previous_status.value, "to": request.status.value},
    )
    session.commit()
    session.refresh(application)
    return _candidate_application_response(application, offer)


@router.get(
    "/training/courses",
    response_model=list[TrainingCourseResponse],
    tags=["training provider"],
)
def provider_courses(
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[TrainingCourseResponse]:
    courses = list(
        session.scalars(
            select(TrainingCourse)
            .where(TrainingCourse.provider_id == user.id)
            .order_by(TrainingCourse.updated_at.desc())
        )
    )
    counts = _enrollment_counts(session, [course.id for course in courses])
    return [_course_response(course, counts.get(course.id, (0, 0))) for course in courses]


@router.post(
    "/training/courses",
    response_model=TrainingCourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["training provider"],
)
def create_course(
    request: TrainingCourseCreate,
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> TrainingCourseResponse:
    course = TrainingCourse(provider_id=user.id, **request.model_dump())
    if course.status == CourseStatus.PUBLISHED:
        course.published_at = datetime.now(timezone.utc)
    session.add(course)
    session.flush()
    record_audit_event(
        session,
        action="training.course.created",
        actor=user,
        resource_type="training_course",
        resource_id=course.id,
        details={"status": course.status.value, "skill_count": len(course.skills)},
    )
    session.commit()
    session.refresh(course)
    return _course_response(course)


@router.put(
    "/training/courses/{course_id}",
    response_model=TrainingCourseResponse,
    tags=["training provider"],
)
def update_course(
    course_id: str,
    request: TrainingCourseCreate,
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> TrainingCourseResponse:
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.provider_id == user.id,
        ).with_for_update()
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    active_enrollments = session.scalar(
        select(func.count())
        .select_from(CourseEnrollment)
        .where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
        )
    ) or 0
    if request.capacity < active_enrollments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capacity cannot be lower than the current active enrollment count.",
        )
    previous_status = course.status
    for field, value in request.model_dump().items():
        setattr(course, field, value)
    if request.status == CourseStatus.PUBLISHED and previous_status != CourseStatus.PUBLISHED:
        course.published_at = datetime.now(timezone.utc)
    elif request.status != CourseStatus.PUBLISHED:
        course.published_at = None
    record_audit_event(
        session,
        action="training.course.updated",
        actor=user,
        resource_type="training_course",
        resource_id=course.id,
        details={"from_status": previous_status.value, "to_status": course.status.value},
    )
    session.commit()
    session.refresh(course)
    counts = _enrollment_counts(session, [course.id])
    return _course_response(course, counts.get(course.id, (0, 0)))


@router.get(
    "/training/courses/{course_id}/enrollments",
    response_model=list[ProviderCourseEnrollmentResponse],
    tags=["training provider"],
)
def provider_course_enrollments(
    course_id: str,
    user: User = Depends(
        require_permission(Permission.COURSE_ENROLLMENT_READ_ORGANISATION)
    ),
    session: Session = Depends(get_session),
) -> list[ProviderCourseEnrollmentResponse]:
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.provider_id == user.id,
        )
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    rows = session.execute(
        select(CourseEnrollment, User, CandidateProfile)
        .join(User, User.id == CourseEnrollment.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(CourseEnrollment.course_id == course.id)
        .order_by(CourseEnrollment.created_at.desc())
    )
    enrollments: list[ProviderCourseEnrollmentResponse] = []
    for enrollment, candidate, profile in rows:
        record_sensitive_read(
            session,
            actor=user,
            resource_type="course_enrollee",
            resource_id=candidate.id,
        )
        enrollments.append(
            ProviderCourseEnrollmentResponse(
                id=enrollment.id,
                course_id=course.id,
                course_title=course.title,
                status=enrollment.status,
                created_at=enrollment.created_at,
                updated_at=enrollment.updated_at,
                candidate_name=profile.full_name if profile else None,
                candidate_location=profile.location if profile else None,
                candidate_skills=profile.skills if profile else [],
            )
        )
    if enrollments:
        session.commit()
    return enrollments


@router.put(
    "/training/enrollments/{enrollment_id}/status",
    response_model=ProviderCourseEnrollmentResponse,
    tags=["training provider"],
)
def update_course_enrollment(
    enrollment_id: str,
    request: CourseEnrollmentStatusUpdate,
    user: User = Depends(
        require_permission(Permission.COURSE_ENROLLMENT_MANAGE_ORGANISATION)
    ),
    session: Session = Depends(get_session),
) -> ProviderCourseEnrollmentResponse:
    row = session.execute(
        select(CourseEnrollment, TrainingCourse, User, CandidateProfile)
        .join(TrainingCourse, TrainingCourse.id == CourseEnrollment.course_id)
        .join(User, User.id == CourseEnrollment.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(
            CourseEnrollment.id == enrollment_id,
            TrainingCourse.provider_id == user.id,
        )
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found.")
    enrollment, course, candidate, profile = row
    if (
        enrollment.status != CourseEnrollmentStatus.ENROLLED
        and enrollment.status != request.status
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A completed or withdrawn enrollment cannot be changed.",
        )
    record_sensitive_read(
        session,
        actor=user,
        resource_type="course_enrollee",
        resource_id=candidate.id,
    )
    previous_status = enrollment.status
    enrollment.status = request.status
    record_audit_event(
        session,
        action="training.enrollment.status_updated",
        actor=user,
        resource_type="course_enrollment",
        resource_id=enrollment.id,
        details={"from": previous_status.value, "to": request.status.value},
    )
    session.commit()
    session.refresh(enrollment)
    return ProviderCourseEnrollmentResponse(
        id=enrollment.id,
        course_id=course.id,
        course_title=course.title,
        status=enrollment.status,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
        candidate_name=profile.full_name if profile else None,
        candidate_location=profile.location if profile else None,
        candidate_skills=profile.skills if profile else [],
    )


@router.get(
    "/candidate/courses",
    response_model=list[TrainingCourseResponse],
    tags=["candidate courses"],
)
def published_courses(
    user: User = Depends(require_permission(Permission.COURSE_READ_PUBLISHED)),
    session: Session = Depends(get_session),
) -> list[TrainingCourseResponse]:
    courses = list(
        session.scalars(
            select(TrainingCourse)
            .where(TrainingCourse.status == CourseStatus.PUBLISHED)
            .order_by(TrainingCourse.starts_on, TrainingCourse.created_at.desc())
        )
    )
    counts = _enrollment_counts(session, [course.id for course in courses])
    return [_course_response(course, counts.get(course.id, (0, 0))) for course in courses]


@router.post(
    "/candidate/courses/{course_id}/enroll",
    response_model=CourseEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["candidate courses"],
)
def enroll_in_course(
    course_id: str,
    user: User = Depends(require_permission(Permission.COURSE_ENROLL)),
    session: Session = Depends(get_session),
) -> CourseEnrollmentResponse:
    course = session.scalar(
        select(TrainingCourse)
        .where(
            TrainingCourse.id == course_id,
            TrainingCourse.status == CourseStatus.PUBLISHED,
        )
        .with_for_update()
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    active_count = session.scalar(
        select(func.count())
        .select_from(CourseEnrollment)
        .where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
        )
    ) or 0
    if active_count >= course.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course is full.")
    enrollment = CourseEnrollment(
        candidate_id=user.id,
        course_id=course.id,
        status=CourseEnrollmentStatus.ENROLLED,
    )
    session.add(enrollment)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        existing_enrollment = session.scalar(
            select(CourseEnrollment.id).where(
                CourseEnrollment.candidate_id == user.id,
                CourseEnrollment.course_id == course.id,
            )
        )
        if existing_enrollment is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        ) from error
    record_audit_event(
        session,
        action="candidate.course.enrolled",
        actor=user,
        resource_type="course_enrollment",
        resource_id=enrollment.id,
    )
    session.commit()
    session.refresh(enrollment)
    return CourseEnrollmentResponse(
        id=enrollment.id,
        course_id=course.id,
        course_title=course.title,
        status=enrollment.status,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
    )


@router.get(
    "/candidate/enrollments",
    response_model=list[CourseEnrollmentResponse],
    tags=["candidate courses"],
)
def candidate_enrollments(
    user: User = Depends(require_permission(Permission.COURSE_READ_PUBLISHED)),
    session: Session = Depends(get_session),
) -> list[CourseEnrollmentResponse]:
    rows = session.execute(
        select(CourseEnrollment, TrainingCourse)
        .join(TrainingCourse, TrainingCourse.id == CourseEnrollment.course_id)
        .where(CourseEnrollment.candidate_id == user.id)
        .order_by(CourseEnrollment.created_at.desc())
    )
    return [
        CourseEnrollmentResponse(
            id=enrollment.id,
            course_id=course.id,
            course_title=course.title,
            status=enrollment.status,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
        )
        for enrollment, course in rows
    ]


@router.get(
    "/admin/indicators",
    response_model=AdminIndicatorsResponse,
    tags=["administration"],
)
def admin_indicators(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> AdminIndicatorsResponse:
    _validate_date_range(start_date, end_date)
    candidate_registrations = session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role == Role.CANDIDATE,
            *_date_window(User.created_at, start_date, end_date),
        )
    ) or 0
    organisations = session.scalar(
        select(func.count(Organisation.id)).where(
            *_date_window(Organisation.created_at, start_date, end_date)
        )
    ) or 0
    offers = list(
        session.scalars(
            select(JobOffer).where(*_date_window(JobOffer.created_at, start_date, end_date))
        )
    )
    application_rows = session.execute(
        select(JobApplication.status, func.count())
        .where(*_date_window(JobApplication.created_at, start_date, end_date))
        .group_by(JobApplication.status)
    )
    counts_by_status = {app_status: count for app_status, count in application_rows}
    applications_total = sum(counts_by_status.values())
    hired = counts_by_status.get(JobApplicationStatus.HIRED, 0)
    closed = hired + counts_by_status.get(JobApplicationStatus.REJECTED, 0)
    skills_by_key: dict[str, str] = {}
    skill_counts: Counter[str] = Counter()
    for offer in offers:
        skills_in_offer = {skill.strip().casefold(): skill.strip() for skill in offer.required_skills}
        for key, display in skills_in_offer.items():
            if key:
                skills_by_key.setdefault(key, display)
                skill_counts[key] += 1
    top_skills = [
        SkillDemandIndicator(skill=skills_by_key[key], offer_count=count)
        for key, count in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    published_courses = session.scalar(
        select(func.count(TrainingCourse.id)).where(
            TrainingCourse.status == CourseStatus.PUBLISHED,
            *_date_window(TrainingCourse.published_at, start_date, end_date),
        )
    ) or 0
    active_enrollments = session.scalar(
        select(func.count(CourseEnrollment.id)).where(
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
            *_date_window(CourseEnrollment.created_at, start_date, end_date),
        )
    ) or 0
    course_completions = session.scalar(
        select(func.count(CourseEnrollment.id)).where(
            CourseEnrollment.status == CourseEnrollmentStatus.COMPLETED,
            *_date_window(CourseEnrollment.updated_at, start_date, end_date),
        )
    ) or 0
    return AdminIndicatorsResponse(
        start_date=start_date,
        end_date=end_date,
        candidate_registrations=candidate_registrations,
        organisations=organisations,
        published_job_offers=len(offers),
        applications_total=applications_total,
        applications_by_status=[
            ApplicationStatusIndicator(status=app_status, count=count)
            for app_status, count in sorted(counts_by_status.items(), key=lambda item: item[0].value)
        ],
        closed_applications=closed,
        hired_applications=hired,
        hire_rate_percent=round(100 * hired / closed, 1) if closed else None,
        top_skills=top_skills,
        published_courses=published_courses,
        active_enrollments=active_enrollments,
        course_completions=course_completions,
    )
