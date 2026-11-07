from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.models import JobOffer


@dataclass(frozen=True)
class RoadmapStep:
    skill: str
    skill_key: str
    required_by: list[str]
    offer_count: int
    completed: bool


@dataclass
class _SkillRequirement:
    skill: str
    offer_ids: set[str] = field(default_factory=set)
    titles: set[str] = field(default_factory=set)


def build_career_roadmap(
    offers: Iterable[JobOffer],
    candidate_skills: Iterable[str],
    completed_by_skill: Mapping[str, bool],
) -> list[RoadmapStep]:
    known_skills = {skill.strip().casefold() for skill in candidate_skills}
    requirements: dict[str, _SkillRequirement] = {}

    for offer in sorted(offers, key=lambda item: (item.title.casefold(), item.id)):
        seen_in_offer: set[str] = set()
        for skill in offer.required_skills:
            skill_key = skill.strip().casefold()
            if skill_key in known_skills or skill_key in seen_in_offer:
                continue
            seen_in_offer.add(skill_key)
            requirement = requirements.setdefault(skill_key, _SkillRequirement(skill=skill.strip()))
            requirement.offer_ids.add(offer.id)
            requirement.titles.add(offer.title)

    steps = [
        RoadmapStep(
            skill=requirement.skill,
            skill_key=skill_key,
            required_by=sorted(requirement.titles, key=str.casefold),
            offer_count=len(requirement.offer_ids),
            completed=completed_by_skill.get(skill_key, False),
        )
        for skill_key, requirement in requirements.items()
    ]
    return sorted(steps, key=lambda step: (-step.offer_count, step.skill_key))
