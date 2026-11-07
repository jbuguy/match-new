"""Reproducible, clearly labelled synthetic job offers for development and tests."""

import argparse
import json
import random
from collections.abc import Iterator
from pathlib import Path


LOCATIONS = ("Tunis", "Sfax", "Sousse", "Kairouan", "Gabes", "Bizerte")
SECTORS = (
    ("information_technology", ("Python", "SQL", "JavaScript", "Linux", "Git")),
    ("healthcare", ("Communication", "Care planning", "First aid", "Teamwork")),
    ("renewable_energy", ("Electrical systems", "Safety", "Solar PV", "Maintenance")),
    ("tourism", ("Customer service", "French", "English", "Event planning")),
    ("logistics", ("Inventory", "Excel", "Route planning", "Communication")),
    ("agriculture", ("Irrigation", "Quality control", "Equipment", "Safety")),
)
TITLES = {
    "information_technology": ("Développeur logiciel junior", "Technicien support informatique"),
    "healthcare": ("Assistant de soins", "Technicien de laboratoire"),
    "renewable_energy": ("Technicien solaire", "Assistant maintenance énergétique"),
    "tourism": ("Agent d'accueil", "Coordinateur touristique"),
    "logistics": ("Assistant logistique", "Gestionnaire de stock"),
    "agriculture": ("Technicien agricole", "Assistant qualité agricole"),
}


def generate_synthetic_offers(seed: int, count: int) -> Iterator[dict[str, object]]:
    """Yield fake offers; the same seed and count always produce the same records."""
    if count < 0:
        raise ValueError("count must not be negative")

    rng = random.Random(seed)
    for index in range(count):
        sector, skills = rng.choice(SECTORS)
        yield {
            "id": f"SYN-TN-{index + 1:06d}",
            "record_type": "synthetic_job_offer",
            "is_synthetic": True,
            "country": "TN",
            "title": rng.choice(TITLES[sector]),
            "sector": sector,
            "location": rng.choice(LOCATIONS),
            "description": "Synthetic development data; not a real vacancy.",
            "required_skills": sorted(rng.sample(skills, k=min(3, len(skills)))),
            "source": "synthetic",
        }


def write_synthetic_offers(output: Path, seed: int, count: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as file:
        for record in generate_synthetic_offers(seed, count):
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/data/generated/synthetic_job_offers.jsonl"),
    )
    args = parser.parse_args()
    write_synthetic_offers(args.output, args.seed, args.count)
    print(f"Wrote {args.count} synthetic offers to {args.output}")


if __name__ == "__main__":
    main()
