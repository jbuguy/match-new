from dataclasses import dataclass
from enum import IntEnum, StrEnum

from app.models import JobOffer


class CompetencyCategory(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    COMMUNICATION = "communication"


class ProficiencyLevel(IntEnum):
    BEGINNER = 1
    BASIC = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


@dataclass(frozen=True)
class ProficiencyLevelDefinition:
    level: ProficiencyLevel
    name: str
    description: str


@dataclass(frozen=True)
class CompetencyDefinition:
    id: str
    name: str
    description: str
    category: CompetencyCategory
    assessment_criteria: tuple[str, ...]


PROFICIENCY_LEVELS = (
    ProficiencyLevelDefinition(
        ProficiencyLevel.BEGINNER,
        "Débutant",
        "Reconnaît les notions de base et a besoin d'un accompagnement régulier.",
    ),
    ProficiencyLevelDefinition(
        ProficiencyLevel.BASIC,
        "Élémentaire",
        "Réalise des tâches simples avec des consignes ou des exemples.",
    ),
    ProficiencyLevelDefinition(
        ProficiencyLevel.INTERMEDIATE,
        "Intermédiaire",
        "Travaille de façon autonome sur les situations courantes.",
    ),
    ProficiencyLevelDefinition(
        ProficiencyLevel.ADVANCED,
        "Avancé",
        "Traite des situations complexes et peut guider d'autres personnes.",
    ),
    ProficiencyLevelDefinition(
        ProficiencyLevel.EXPERT,
        "Expert",
        "Maîtrise les cas complexes et peut définir les pratiques de référence.",
    ),
)


SOFT_COMPETENCIES = (
    CompetencyDefinition(
        "communication",
        "Communication",
        "Présenter une idée et écouter les autres de manière compréhensible et adaptée.",
        CompetencyCategory.COMMUNICATION,
        (
            "Présentez votre réponse avec une structure facile à suivre.",
            "Adaptez votre explication à votre interlocuteur et donnez un exemple concret.",
            "Écoutez la question et répondez sans vous éloigner du sujet.",
        ),
    ),
    CompetencyDefinition(
        "teamwork",
        "Travail en équipe",
        "Contribuer à un objectif collectif et coopérer avec des collègues.",
        CompetencyCategory.SOFT,
        (
            "Décrivez votre contribution personnelle à un résultat collectif.",
            "Expliquez comment vous avez partagé les informations et coordonné le travail.",
        ),
    ),
    CompetencyDefinition(
        "problem-solving",
        "Résolution de problèmes",
        "Analyser une difficulté, comparer des options et agir pour la résoudre.",
        CompetencyCategory.SOFT,
        (
            "Expliquez comment vous avez identifié la cause d'un problème.",
            "Présentez les options envisagées, votre décision et son résultat.",
        ),
    ),
    CompetencyDefinition(
        "critical-thinking",
        "Esprit critique",
        "Évaluer les informations disponibles et justifier une conclusion.",
        CompetencyCategory.SOFT,
        (
            "Distinguez les faits des suppositions dans votre exemple.",
            "Expliquez les éléments qui ont justifié votre conclusion.",
        ),
    ),
    CompetencyDefinition(
        "adaptability",
        "Adaptabilité",
        "S'ajuster à un changement de contexte, de priorité ou de méthode.",
        CompetencyCategory.SOFT,
        (
            "Décrivez un changement auquel vous avez dû vous adapter.",
            "Expliquez ce que vous avez modifié et ce que vous en avez appris.",
        ),
    ),
    CompetencyDefinition(
        "leadership",
        "Leadership",
        "Aider un groupe à avancer vers un objectif commun, avec ou sans rôle hiérarchique.",
        CompetencyCategory.SOFT,
        (
            "Décrivez comment vous avez aidé un groupe à atteindre un objectif.",
            "Expliquez comment vous avez pris en compte les contributions des autres.",
        ),
    ),
    CompetencyDefinition(
        "conflict-resolution",
        "Gestion des désaccords",
        "Aborder un désaccord de façon constructive et rechercher une issue praticable.",
        CompetencyCategory.SOFT,
        (
            "Décrivez le désaccord sans attribuer d'intentions aux personnes.",
            "Expliquez les étapes suivies pour trouver une solution.",
        ),
    ),
    CompetencyDefinition(
        "decision-making",
        "Prise de décision",
        "Choisir une action en tenant compte des objectifs, contraintes et conséquences.",
        CompetencyCategory.SOFT,
        (
            "Présentez les critères et contraintes pris en compte.",
            "Expliquez la décision prise et comment vous en avez évalué les effets.",
        ),
    ),
    CompetencyDefinition(
        "time-management",
        "Gestion du temps",
        "Organiser le travail et ajuster les priorités pour respecter les engagements.",
        CompetencyCategory.SOFT,
        (
            "Expliquez comment vous avez organisé des tâches avec des échéances.",
            "Décrivez comment vous avez communiqué ou révisé vos priorités.",
        ),
    ),
    CompetencyDefinition(
        "accountability",
        "Responsabilisation",
        "Assumer ses engagements, communiquer sur les difficultés et tirer des leçons.",
        CompetencyCategory.SOFT,
        (
            "Précisez votre responsabilité dans la situation.",
            "Expliquez comment vous avez communiqué le résultat et les apprentissages.",
        ),
    ),
    CompetencyDefinition(
        "initiative",
        "Initiative",
        "Repérer une occasion d'amélioration et agir dans le cadre de ses responsabilités.",
        CompetencyCategory.SOFT,
        (
            "Décrivez une amélioration que vous avez proposée ou mise en œuvre.",
            "Expliquez comment vous avez vérifié son utilité et obtenu les retours nécessaires.",
        ),
    ),
)


def build_role_preparation_profile(
    offer: JobOffer,
    candidate_skills: list[str],
) -> dict[str, object]:
    reported_skills = {skill.strip().casefold() for skill in candidate_skills}
    requirements = []
    seen_skills: set[str] = set()

    for skill in offer.required_skills:
        clean_skill = skill.strip()
        skill_key = clean_skill.casefold()
        if not clean_skill or skill_key in seen_skills:
            continue
        seen_skills.add(skill_key)
        requirements.append(
            {
                "id": f"hard:{skill_key}",
                "name": clean_skill,
                "description": f"{clean_skill} est indiquée comme compétence requise dans cette offre.",
                "category": CompetencyCategory.HARD,
                "associated_skill": clean_skill,
                "assessment_criteria": [
                    f"Expliquez les notions essentielles liées à {clean_skill}.",
                    f"Décrivez un exemple concret où vous avez utilisé {clean_skill}.",
                    f"Présentez votre méthode pour vérifier votre travail avec {clean_skill}.",
                ],
                "required_proficiency_level": None,
                "importance_weight": None,
                "mandatory": True,
                "source": "job_offer",
                "candidate_evidence": (
                    "self_reported" if skill_key in reported_skills else "gap"
                ),
            }
        )

    suggestions = [
        {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
            "category": definition.category,
            "associated_skill": None,
            "assessment_criteria": list(definition.assessment_criteria),
            "required_proficiency_level": None,
            "importance_weight": None,
            "mandatory": False,
            "source": "platform_guidance",
            "candidate_evidence": "not_assessed",
        }
        for definition in SOFT_COMPETENCIES
    ]

    return {
        "role": {
            "id": offer.id,
            "title": offer.title,
            "description": offer.description,
            "location": offer.location,
            "required_skills": list(offer.required_skills),
        },
        "required_competencies": requirements,
        "suggested_competencies": suggestions,
        "proficiency_levels": [
            {
                "level": definition.level,
                "name": definition.name,
                "description": definition.description,
            }
            for definition in PROFICIENCY_LEVELS
        ],
    }
