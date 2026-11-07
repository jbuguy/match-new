from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    CandidateProfile,
    CourseEnrollment,
    CourseEnrollmentStatus,
    CourseStatus,
    JobApplication,
    JobApplicationStatus,
    JobOffer,
    Organisation,
    OrganisationMembership,
    OrganisationType,
    Role,
    TrainingCourse,
    User,
)
from app.security import hash_password

DEMO_BASE_PASSWORD = "LocalDemoPassword2026!"

DEMO_CANDIDATES = (
    {
        "email": "ahmed.ben.ali@demo.maharamatch.test",
        "full_name": "Ahmed Ben Ali",
        "location": "Tunis",
        "skills": ["Python", "SQL", "FastAPI", "Docker", "Git"],
        "education": "Master en ingénierie logicielle, Université de Tunis El Manar",
        "experience": "Ingénieur Python backend avec 3 ans d'expérience dans des services APIs et des pipelines de données.",
        "phone": "+216 22 111 111",
    },
    {
        "email": "mariem.trabelsi@demo.maharamatch.test",
        "full_name": "Mariem Trabelsi",
        "location": "Sfax",
        "skills": ["Figma", "UX Research", "Design System", "Prototypage", "HTML"],
        "education": "Licence design graphique, Institut Supérieur des Arts",
        "experience": "UX/UI designer avec 2 ans d'expérience sur des parcours web et mobile orientés conversion.",
        "phone": "+216 22 222 222",
    },
    {
        "email": "youssef.gharbi@demo.maharamatch.test",
        "full_name": "Youssef Gharbi",
        "location": "Sousse",
        "skills": ["Power BI", "SQL", "Excel", "Data Analysis", "Tableau"],
        "education": "Master en statistiques appliquées, Université de Sousse",
        "experience": "Analyste de données junior avec 1 an d'expérience en reporting et automatisation.",
        "phone": "+216 22 333 333",
    },
    {
        "email": "nour.ben-salem@demo.maharamatch.test",
        "full_name": "Nour Ben Salem",
        "location": "Tunis",
        "skills": ["JavaScript", "React", "TypeScript", "CSS", "Accessibility"],
        "education": "Diplôme d'ingénieur en informatique, ENSI",
        "experience": "Frontend developer de 4 ans sur des applications SaaS B2B et interfaces d'administration.",
        "phone": "+216 22 444 444",
    },
    {
        "email": "amira.mansouri@demo.maharamatch.test",
        "full_name": "Amira Mansouri",
        "location": "Bizerte",
        "skills": ["Marketing Digital", "SEO", "Google Ads", "Analytics", "Content Strategy"],
        "education": "Master marketing digital, ISG Tunis",
        "experience": "Growth marketer de 2 ans, orientée acquisition, CRM et performance de campagnes.",
        "phone": "+216 22 555 555",
    },
    {
        "email": "sami.jlassi@demo.maharamatch.test",
        "full_name": "Sami Jlassi",
        "location": "Ariana",
        "skills": ["Python", "Machine Learning", "Scikit-learn", "Pandas", "MLOps"],
        "education": "Master IA et apprentissage automatique, Sup'Com Tunis",
        "experience": "Machine learning engineer de 3 ans sur des modèles prédictifs et des workflows de production.",
        "phone": "+216 22 666 666",
    },
    {
        "email": "ines.chaabane@demo.maharamatch.test",
        "full_name": "Ines Chaabane",
        "location": "Monastir",
        "skills": ["Product Design", "User Flows", "Research", "Figma", "Stakeholder Management"],
        "education": "Master innovation produit, IHEC Carthage",
        "experience": "Product designer avec 1 an d'expérience en conception de parcours et validation utilisateur.",
        "phone": "+216 22 777 777",
    },
    {
        "email": "mohamed.khelifi@demo.maharamatch.test",
        "full_name": "Mohamed Khelifi",
        "location": "Tunis",
        "skills": ["DevOps", "Kubernetes", "Terraform", "CI/CD", "Linux"],
        "education": "Ingénierie système et réseaux, ISIMM",
        "experience": "DevOps engineer de 5 ans avec expertise sur plateformes cloud et automatisation infra.",
        "phone": "+216 22 888 888",
    },
    {
        "email": "salma.bouazizi@demo.maharamatch.test",
        "full_name": "Salma Bouazizi",
        "location": "Sousse",
        "skills": ["Business Analysis", "SQL", "Process Mapping", "Stakeholder Management", "Documentation"],
        "education": "Master gestion de projet et analyse métier, ISET Sousse",
        "experience": "Business analyst de 2 ans en transformation digitale et optimisation des processus.",
        "phone": "+216 22 999 999",
    },
    {
        "email": "karim.ayari@demo.maharamatch.test",
        "full_name": "Karim Ayari",
        "location": "Nabeul",
        "skills": ["Swift", "Kotlin", "Flutter", "Mobile UI", "API Integration"],
        "education": "Master développement mobile, Institut Polytechnique",
        "experience": "Mobile developer de 3 ans sur des apps iOS et Android en environnement startup.",
        "phone": "+216 21 111 222",
    },
    {
        "email": "yasmine.zouari@demo.maharamatch.test",
        "full_name": "Yasmine Zouari",
        "location": "Kairouan",
        "skills": ["Cybersecurity", "Network Security", "Python", "Threat Analysis", "ISO 27001"],
        "education": "Master cybersécurité, Université de la Manouba",
        "experience": "Analyste sécurité de 2 ans, forte expérience sur détection et hardening d'infrastructures.",
        "phone": "+216 21 222 333",
    },
    {
        "email": "walid.masmoudi@demo.maharamatch.test",
        "full_name": "Walid Masmoudi",
        "location": "Gabès",
        "skills": ["Node.js", "React", "GraphQL", "PostgreSQL", "Microservices"],
        "education": "Licence informatique, Université de Sfax",
        "experience": "Full-stack developer de 3 ans sur des plateformes B2B et outils internes SaaS.",
        "phone": "+216 21 333 444",
    },
)

DEMO_EMPLOYERS = (
    {
        "email": "careers@carthage-digital.tn",
        "company_name": "Carthage Digital",
        "industry": "Technologie",
        "location": "Tunis",
        "website": "https://www.carthage-digital.tn",
    },
    {
        "email": "jobs@techbridge.tn",
        "company_name": "TechBridge Tunisia",
        "industry": "Services IT",
        "location": "Sfax",
        "website": "https://www.techbridge.tn",
    },
    {
        "email": "talent@novasoft.tn",
        "company_name": "NovaSoft",
        "industry": "Logiciels",
        "location": "Ariana",
        "website": "https://www.novasoft.tn",
    },
    {
        "email": "hiring@medina-analytics.tn",
        "company_name": "Medina Analytics",
        "industry": "Data & Analytics",
        "location": "Tunis",
        "website": "https://www.medina-analytics.tn",
    },
    {
        "email": "recruiting@bluewave.tn",
        "company_name": "BlueWave Solutions",
        "industry": "Consulting",
        "location": "Sousse",
        "website": "https://www.bluewave.tn",
    },
    {
        "email": "careers@atlas-consulting.tn",
        "company_name": "Atlas Consulting",
        "industry": "Conseil",
        "location": "Monastir",
        "website": "https://www.atlas-consulting.tn",
    },
    {
        "email": "jobs@futurestack.tn",
        "company_name": "FutureStack",
        "industry": "Produit digital",
        "location": "Nabeul",
        "website": "https://www.futurestack.tn",
    },
)

DEMO_JOB_OFFERS = (
    ("Carthage Digital", "Développeur Python Backend", "Concevoir et maintenir des API REST et des services de traitement de données pour des clients fintech et SaaS.", "Tunis", ["Python", "FastAPI", "SQL", "Docker"]),
    ("Carthage Digital", "Data Analyst Senior", "Analyser les indicateurs de performance business et proposer des recommandations actionnables.", "Tunis", ["SQL", "Power BI", "Python", "Excel"]),
    ("TechBridge Tunisia", "Ingénieur DevOps", "Automatiser les déploiements, la sécurité et la supervision des environnements cloud.", "Sfax", ["DevOps", "Docker", "Kubernetes", "CI/CD"]),
    ("TechBridge Tunisia", "Développeur Frontend React", "Construire des interfaces de gestion et des dashboards internes pour des équipes opérationnelles.", "Sfax", ["React", "TypeScript", "CSS", "JavaScript"]),
    ("NovaSoft", "Product Designer", "Concevoir des parcours utilisateurs simples et accessibles pour des produits B2B.", "Ariana", ["Figma", "UX Research", "Design System", "Prototypage"]),
    ("NovaSoft", "Data Scientist", "Mettre en place des modèles prédictifs et des pipelines de scoring sur des données clients.", "Ariana", ["Python", "Machine Learning", "SQL", "Pandas"]),
    ("Medina Analytics", "Analyste Business", "Cartographier les besoins métiers et piloter la mise en place de solutions de reporting.", "Tunis", ["Business Analysis", "SQL", "Documentation", "Stakeholder Management"]),
    ("Medina Analytics", "Développeur SQL / BI", "Créer des tableaux de bord et des modèles analytiques fiables pour l'équipe direction.", "Tunis", ["SQL", "Power BI", "Excel", "Data Analysis"]),
    ("BlueWave Solutions", "Cybersecurity Analyst", "Surveiller les risques de sécurité, documenter les vulnérabilités et renforcer la posture SI.", "Sousse", ["Cybersecurity", "Threat Analysis", "Python", "Network Security"]),
    ("BlueWave Solutions", "Consultant Marketing Digital", "Piloter la stratégie acquisition et améliorer les performances de campagnes digitales.", "Sousse", ["Marketing Digital", "SEO", "Analytics", "Google Ads"]),
    ("Atlas Consulting", "Consultant Fonctionnel SAP", "Accompagner la transformation digitale des clients et formaliser les besoins métiers.", "Monastir", ["Business Analysis", "Documentation", "Stakeholder Management", "SQL"]),
    ("Atlas Consulting", "Développeur Mobile Flutter", "Concevoir des applications mobile performantes et cohérentes avec le design system.", "Monastir", ["Flutter", "Kotlin", "Swift", "Mobile UI"]),
    ("FutureStack", "Full-Stack Developer", "Développer des fonctionnalités complètes sur les applications web et leur API associée.", "Nabeul", ["Node.js", "React", "PostgreSQL", "GraphQL"]),
    ("FutureStack", "QA Automation Engineer", "Développer des tests automatisés et des scénarios de validation sur les chemins critiques.", "Nabeul", ["Python", "Testing", "CI/CD", "Automation"]),
    ("Carthage Digital", "AI Engineer", "Construire des pipelines IA et optimiser des modèles d'augmentation de performance produit.", "Tunis", ["Python", "Machine Learning", "MLOps", "SQL"]),
    ("TechBridge Tunisia", "Frontend Engineer Junior", "Contribuer à la qualité d'interface et à la maintenance des composants UI.", "Sfax", ["JavaScript", "React", "HTML", "CSS"]),
    ("NovaSoft", "Security Engineer", "Renforcer les mécanismes de protection des services et auditer les configurations cloud.", "Ariana", ["Cybersecurity", "Docker", "Linux", "Python"]),
    ("Medina Analytics", "BI Consultant", "Mettre en place des tableaux de bord et des analyses de performance pour les équipes clients.", "Tunis", ["Power BI", "SQL", "Excel", "Data Analysis"]),
    ("BlueWave Solutions", "Growth Manager", "Optimiser les campagnes de acquisition et la conversion sur les canaux digitaux.", "Sousse", ["Marketing Digital", "Analytics", "SEO", "Content Strategy"]),
    ("Atlas Consulting", "Project Manager Digital", "Piloter la mise en œuvre de projets digitaux avec des équipes transverses.", "Monastir", ["Project Management", "Stakeholder Management", "Documentation", "Business Analysis"]),
    ("FutureStack", "Backend Engineer Go", "Développer des services backend à forte disponibilité et faible latence.", "Nabeul", ["Go", "PostgreSQL", "Microservices", "API Design"]),
    ("Carthage Digital", "Scrum Master", "Faciliter les routines d'équipe et améliorer le débit de livraisons autour de produits numériques.", "Tunis", ["Project Management", "Stakeholder Management", "Documentation", "Agile"]),
    ("TechBridge Tunisia", "System Administrator", "Gérer les serveurs, la supervision et les procédures de déploiement de l'infrastructure.", "Sfax", ["Linux", "DevOps", "Network Security", "Docker"]),
    ("NovaSoft", "Mobile Developer", "Développer des applications mobile sur Android et iOS avec une expérience fluide.", "Ariana", ["Kotlin", "Swift", "Flutter", "Mobile UI"]),
    ("Medina Analytics", "Data Engineer", "Construire des pipelines de données, automatismes et modèles pour le reporting opérationnel.", "Tunis", ["Python", "SQL", "ETL", "PostgreSQL"]),
)

DEMO_TRAINING_COURSES = (
    {
        "title": "Python pour le backend et les APIs",
        "summary": "Formation pratique sur FastAPI, tests, bases de données et déploiement de services backend robustes.",
        "skills": ["Python", "FastAPI", "SQL", "Testing"],
        "delivery_mode": "hybrid",
        "location": "Tunis",
        "starts_on": date.today() + timedelta(days=16),
        "ends_on": date.today() + timedelta(days=31),
        "duration_hours": 24,
        "capacity": 20,
        "price_tnd": "550.00",
    },
    {
        "title": "Data analyst: SQL et dashboards",
        "summary": "Approche pratique du reporting, des modèles de données et des tableaux de bord décisionnels.",
        "skills": ["SQL", "Power BI", "Excel", "Data Analysis"],
        "delivery_mode": "in_person",
        "location": "Sfax",
        "starts_on": date.today() + timedelta(days=20),
        "ends_on": date.today() + timedelta(days=35),
        "duration_hours": 18,
        "capacity": 15,
        "price_tnd": "420.00",
    },
    {
        "title": "UX/UI design et parcours utilisateurs",
        "summary": "Créer des parcours cohérents, tester des hypothèses et documenter les composants interface.",
        "skills": ["Figma", "UX Research", "Design System", "Prototypage"],
        "delivery_mode": "online",
        "location": "Remote",
        "starts_on": date.today() + timedelta(days=12),
        "ends_on": date.today() + timedelta(days=27),
        "duration_hours": 16,
        "capacity": 18,
        "price_tnd": "390.00",
    },
)


DEMO_EMAIL_ROLES = {
    "candidate@demo.maharamatch.test": Role.CANDIDATE,
    "employer@demo.maharamatch.test": Role.EMPLOYER,
    "ministry@demo.maharamatch.test": Role.MINISTRY_ADMIN,
    "provider@demo.maharamatch.test": Role.TRAINING_PROVIDER,
    "operator@demo.maharamatch.test": Role.OPERATOR,
}


def _get_or_create_user(session: Session, email: str, role: Role, password: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(password), role=role)
        session.add(user)
        session.flush()
    elif user.role != role:
        if DEMO_EMAIL_ROLES.get(email) == role:
            user.role = role
        else:
            raise ValueError(f"User {email} exists with unexpected role {user.role.value!r}.")
    return user


def _ensure_organisation(session: Session, name: str, organisation_type: OrganisationType) -> Organisation:
    organisation = session.scalar(
        select(Organisation).where(
            Organisation.name == name,
            Organisation.organisation_type == organisation_type,
        )
    )
    if organisation is None:
        organisation = Organisation(name=name, organisation_type=organisation_type)
        session.add(organisation)
        session.flush()
    return organisation


def _ensure_membership(session: Session, user_id: str, organisation_id: str) -> None:
    membership = session.scalar(
        select(OrganisationMembership.id).where(
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.organisation_id == organisation_id,
        )
    )
    if membership is None:
        session.add(OrganisationMembership(user_id=user_id, organisation_id=organisation_id))


def _ensure_profile(session: Session, user_id: str, payload: dict[str, Any]) -> None:
    profile = session.get(CandidateProfile, user_id)
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        session.add(profile)
    profile.full_name = payload["full_name"]
    profile.location = payload["location"]
    profile.phone = payload["phone"]
    profile.skills = payload["skills"]
    profile.education = payload["education"]
    profile.experience = payload["experience"]


def _ensure_job_offer(session: Session, employer_id: str, title: str, description: str, location: str, required_skills: list[str]) -> JobOffer:
    offer = session.scalar(
        select(JobOffer).where(JobOffer.employer_id == employer_id, JobOffer.title == title)
    )
    if offer is None:
        offer = JobOffer(
            employer_id=employer_id,
            title=title,
            description=description,
            location=location,
            required_skills=required_skills,
        )
        session.add(offer)
        session.flush()
    else:
        offer.description = description
        offer.location = location
        offer.required_skills = required_skills
    return offer


def _ensure_application(
    session: Session,
    candidate_id: str,
    job_offer_id: str,
    status: JobApplicationStatus,
) -> JobApplication:
    application = session.scalar(
        select(JobApplication).where(
            JobApplication.candidate_id == candidate_id,
            JobApplication.job_offer_id == job_offer_id,
        )
    )
    if application is None:
        application = JobApplication(
            candidate_id=candidate_id,
            job_offer_id=job_offer_id,
            status=status,
        )
        session.add(application)
        session.flush()
    else:
        application.status = status
    return application


def _ensure_course(session: Session, provider_id: str, payload: dict[str, Any]) -> TrainingCourse:
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.provider_id == provider_id,
            TrainingCourse.title == payload["title"],
        )
    )
    if course is None:
        course = TrainingCourse(provider_id=provider_id, **payload)
        session.add(course)
        session.flush()
    else:
        for key, value in payload.items():
            setattr(course, key, value)
        course.status = CourseStatus.PUBLISHED
    return course


def _ensure_course_enrollment(session: Session, candidate_id: str, course_id: str) -> None:
    enrollment = session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.candidate_id == candidate_id,
            CourseEnrollment.course_id == course_id,
        )
    )
    if enrollment is None:
        session.add(
            CourseEnrollment(
                candidate_id=candidate_id,
                course_id=course_id,
                status=CourseEnrollmentStatus.ENROLLED,
            )
        )


def seed_demo_data(session: Session, password: str | None = None) -> dict[str, int]:
    configured_password = password or os.getenv("MAHARA_DEMO_PASSWORD") or DEMO_BASE_PASSWORD
    if len(configured_password) < 12:
        raise ValueError("The demo password must be at least 12 characters.")

    if os.getenv("APP_ENV", "development").casefold() in {"prod", "production"}:
        raise RuntimeError("Demo data cannot be seeded in a production environment.")

    base_users = (
        ("candidate@demo.maharamatch.test", Role.CANDIDATE),
        ("employer@demo.maharamatch.test", Role.EMPLOYER),
        ("ministry@demo.maharamatch.test", Role.MINISTRY_ADMIN),
        ("provider@demo.maharamatch.test", Role.TRAINING_PROVIDER),
        ("operator@demo.maharamatch.test", Role.OPERATOR),
    )
    for email, role in base_users:
        _get_or_create_user(session, email, role, configured_password)

    user_by_email: dict[str, User] = {}
    for candidate in DEMO_CANDIDATES:
        user = _get_or_create_user(session, candidate["email"], Role.CANDIDATE, configured_password)
        user_by_email[candidate["email"]] = user
        _ensure_profile(session, user.id, candidate)

    for employer in DEMO_EMPLOYERS:
        user = _get_or_create_user(session, employer["email"], Role.EMPLOYER, configured_password)
        organisation = _ensure_organisation(
            session,
            employer["company_name"],
            OrganisationType.EMPLOYER,
        )
        _ensure_membership(session, user.id, organisation.id)
        user_by_email[employer["email"]] = user

    provider_user = _get_or_create_user(
        session,
        "provider@demo.maharamatch.test",
        Role.TRAINING_PROVIDER,
        configured_password,
    )
    provider_organisation = _ensure_organisation(
        session,
        "Demo Training Provider",
        OrganisationType.TRAINING_PROVIDER,
    )
    _ensure_membership(session, provider_user.id, provider_organisation.id)

    for company_name, title, description, location, required_skills in DEMO_JOB_OFFERS:
        employer = session.scalar(
            select(User).join(OrganisationMembership, OrganisationMembership.user_id == User.id)
            .join(Organisation, Organisation.id == OrganisationMembership.organisation_id)
            .where(
                Organisation.name == company_name,
                Organisation.organisation_type == OrganisationType.EMPLOYER,
            )
            .where(User.role == Role.EMPLOYER)
        )
        if employer is None:
            continue
        _ensure_job_offer(session, employer.id, title, description, location, required_skills)

    jobs = session.scalars(select(JobOffer)).all()
    candidate_users = session.scalars(select(User).where(User.role == Role.CANDIDATE)).all()
    for index, candidate in enumerate(candidate_users):
        if candidate.email.endswith("@demo.maharamatch.test") and candidate.email not in user_by_email:
            continue
        offer_index = index % max(1, len(jobs))
        offer = jobs[offer_index]
        status = JobApplicationStatus.SUBMITTED if index % 3 else JobApplicationStatus.INTERVIEW
        _ensure_application(session, candidate.id, offer.id, status)

    for index, course in enumerate(DEMO_TRAINING_COURSES):
        course_payload = {
            "title": course["title"],
            "summary": course["summary"],
            "skills": course["skills"],
            "delivery_mode": course["delivery_mode"],
            "location": course["location"],
            "starts_on": course["starts_on"],
            "ends_on": course["ends_on"],
            "duration_hours": course["duration_hours"],
            "capacity": course["capacity"],
            "price_tnd": course["price_tnd"],
            "status": "published",
            "published_at": course["starts_on"] - timedelta(days=5),
        }
        created_course = _ensure_course(session, provider_user.id, course_payload)
        for candidate in candidate_users[: min(4, len(candidate_users))]:
            if index == 0 and candidate.email.startswith("ahmed"):
                _ensure_course_enrollment(session, candidate.id, created_course.id)
            elif index == 1 and candidate.email.startswith("youssef"):
                _ensure_course_enrollment(session, candidate.id, created_course.id)
            elif index == 2 and candidate.email.startswith("mariem"):
                _ensure_course_enrollment(session, candidate.id, created_course.id)

    session.commit()
    return {
        "candidates": len(DEMO_CANDIDATES),
        "employers": len(DEMO_EMPLOYERS),
        "job_offers": len(DEMO_JOB_OFFERS),
        "applications": session.query(JobApplication).count(),
        "training_courses": len(DEMO_TRAINING_COURSES),
    }


def main() -> None:
    if os.getenv("APP_ENV", "development").casefold() in {"prod", "production"}:
        raise SystemExit("Demo data cannot be seeded in a production environment.")

    with SessionLocal() as session:
        result = seed_demo_data(session)
    print(
        "Seeded demo dataset: "
        f"{result['candidates']} candidates, {result['employers']} employers, "
        f"{result['job_offers']} offers, {result['applications']} applications, "
        f"{result['training_courses']} training courses."
    )


if __name__ == "__main__":
    main()
