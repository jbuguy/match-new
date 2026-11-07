import io
import json
import os
import re
import zipfile
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from app.assistant_services import generate_assistant_reply
from app.schemas import CandidateProfileUpdate

COMMON_SKILLS = [
    "Python",
    "SQL",
    "FastAPI",
    "JavaScript",
    "TypeScript",
    "React",
    "Node.js",
    "PostgreSQL",
    "Excel",
    "Power BI",
    "Tableau",
    "Docker",
    "Git",
    "Agile",
    "Scrum",
    "Customer Service",
    "Sales",
    "Support Client",
    "Gestion de Projet",
    "Project Management",
    "Communication",
    "Data Analysis",
    "UX Design",
    "Product Management",
    "CRM",
    "Marketing Digital",
    "Service Client",
    "Réseau Social",
    "Microsoft Office",
    "Google Workspace",
]

CITY_HINTS = [
    "tunis",
    "sfax",
    "sousse",
    "monastir",
    "bizerte",
    "gabes",
    "nabeul",
    "kairouan",
    "tozeur",
    "kef",
    "beja",
    "ariana",
    "ben arous",
    "tataouine",
    "mahdia",
    "medenine",
    "jendouba",
    "siliana",
]

SECTION_HEADINGS = [
    "experience",
    "expérience",
    "formation",
    "education",
    "compétences",
    "competences",
    "skills",
    "technologies",
    "outils",
    "projets",
    "profil",
    "résumé",
    "resume",
]


async def normalize_candidate_profile_from_cv(filename: str, file_bytes: bytes) -> CandidateProfileUpdate:
    text = _extract_cv_text(filename, file_bytes)
    if os.getenv("MAHARA_LLM_BASE_URL", "").strip():
        try:
            result = await generate_assistant_reply(
                [
                    {
                        "role": "system",
                        "content": (
                            "You extract structured candidate profile data from a CV. "
                            "Return a JSON object with the fields full_name, phone, location, "
                            "education, experience, skills. Use short concrete values, no invented facts, "
                            "and keep skills as a list of high-signal professional skills."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Extract a candidate profile from this CV text. "
                            f"Return only valid JSON matching the requested schema. CV:\n{text[:20000]}"
                        ),
                    },
                ]
            )
            profile_updates = result.get("profile_updates")
            if isinstance(profile_updates, dict):
                cleaned = {
                    key: value
                    for key, value in profile_updates.items()
                    if key in {"full_name", "phone", "location", "education", "experience", "skills"}
                }
                if cleaned:
                    return CandidateProfileUpdate.model_validate(cleaned)
        except Exception:
            pass
    return extract_candidate_profile_from_cv(filename, file_bytes)


def extract_candidate_profile_from_cv(filename: str, file_bytes: bytes) -> CandidateProfileUpdate:
    text = _extract_cv_text(filename, file_bytes)
    profile: dict[str, object] = {}

    full_name = _extract_full_name(text)
    if full_name:
        profile["full_name"] = full_name

    email = _extract_email(text)
    if email:
        profile["email"] = email

    phone = _extract_phone(text)
    if phone:
        profile["phone"] = phone

    location = _extract_location(text)
    if location:
        profile["location"] = location

    education = _extract_section_block(text, ["formation", "education", "diplôme", "diplome", "études", "etudes"])
    if education:
        profile["education"] = education

    experience = _extract_section_block(text, ["experience", "expérience", "parcours", "professionnel", "career"])
    if experience:
        profile["experience"] = experience

    skills = _extract_skills(text)
    if skills:
        profile["skills"] = skills

    if not profile:
        raise ValueError("Unable to read a usable profile from the CV.")

    parsed = CandidateProfileUpdate.model_validate(profile)
    if "email" in profile:
        parsed = CandidateProfileUpdate.model_validate({
            key: value for key, value in profile.items() if key != "email"
        })
    return parsed


def _extract_cv_text(filename: str, file_bytes: bytes) -> str:
    lower_name = (filename or "").lower()
    if lower_name.endswith(".pdf"):
        return _read_pdf_text(file_bytes)
    if lower_name.endswith(".docx"):
        return _read_docx_text(file_bytes)
    if lower_name.endswith(".txt") or lower_name.endswith(".md"):
        return file_bytes.decode("utf-8-sig", errors="replace")
    text = file_bytes.decode("utf-8-sig", errors="replace")
    if text.strip():
        return text
    raise ValueError("Unsupported CV format. Upload a PDF, DOCX, or TXT file.")


def _read_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(extracted)
    text = "\n".join(pages)
    if not text.strip():
        raise ValueError("The PDF did not contain readable text.")
    return text


def _read_docx_text(file_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as error:
            raise ValueError("The DOCX file is invalid or missing its document content.") from error
        root = ET.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        fragments = [node.text or "" for node in root.iterfind(".//w:t", namespace)]
    text = "\n".join(fragments)
    if not text.strip():
        raise ValueError("The DOCX file did not contain readable text.")
    return text


def _extract_full_name(text: str) -> str | None:
    lines = _split_lines(text)
    for line in lines[:25]:
        candidate = _clean_heading(line)
        if not candidate or re.search(r"[@0-9]", candidate):
            continue
        words = candidate.split()
        if len(words) < 2:
            continue
        if any(token.lower() in {"cv", "resume", "profil", "profile"} for token in words[:2]):
            continue
        if sum(char.isalpha() for char in candidate) < 4:
            continue
        return candidate
    return None


def _extract_email(text: str) -> str | None:
    matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return matches[0] if matches else None


def _extract_phone(text: str) -> str | None:
    matches = re.findall(
        r"(?:\+?\d[\d .()\-]{7,}\d)",
        text,
    )
    for match in matches:
        digits = re.sub(r"\D", "", match)
        if len(digits) >= 8:
            return match.strip()
    return None


def _extract_location(text: str) -> str | None:
    normalized = text.lower()
    for city in CITY_HINTS:
        if city.lower() in normalized:
            return _title_case_city(city)
    for line in _split_lines(text):
        lower = line.lower()
        if any(city in lower for city in CITY_HINTS):
            return _title_case_city(next(city for city in CITY_HINTS if city in lower))
    return None


def _extract_section_block(text: str, keywords: list[str]) -> str | None:
    lines = _split_lines(text)
    lowercase_headings = [keyword.casefold() for keyword in keywords]
    for index, line in enumerate(lines):
        cleaned = _clean_heading(line)
        if not cleaned:
            continue
        lower = cleaned.casefold()
        if any(keyword in lower for keyword in lowercase_headings):
            block: list[str] = []
            suffix = _extract_heading_value(cleaned, lowercase_headings)
            if suffix:
                block.append(suffix)
            for next_line in lines[index + 1:]:
                next_clean = _clean_heading(next_line)
                if not next_clean:
                    continue
                next_lower = next_clean.casefold()
                if any(heading in next_lower for heading in SECTION_HEADINGS):
                    break
                block.append(next_clean)
            if block:
                return " ".join(block)
    return None


def _extract_heading_value(line: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        pattern = re.compile(rf"(?i).*?\b{re.escape(keyword)}\b\s*[:\-]?\s*(.*)$")
        match = pattern.match(line)
        if match:
            value = match.group(1).strip()
            if value and not value.casefold().startswith("http"):
                return value
    return None


def _extract_skills(text: str) -> list[str] | None:
    section = _extract_section_block(
        text,
        ["compétences", "competences", "skills", "technologies", "outils", "stack"],
    ) or ""
    candidates = []
    if section:
        for chunk in re.split(r"[\n,;|/]+", section):
            cleaned = chunk.strip()
            cleaned = cleaned.strip("•-*•\t ")
            if not cleaned:
                continue
            if len(cleaned.split()) > 6:
                continue
            if cleaned.lower() not in {"management", "project", "project management", "anglais", "français", "arabe", "langues"}:
                candidates.append(_safe_skill_name(cleaned))
    fallback = [
        skill for skill in COMMON_SKILLS if skill.casefold() in text.casefold()
    ]
    merged = []
    seen: set[str] = set()
    for skill in [*candidates, *fallback]:
        safe = _safe_skill_name(skill)
        if not safe:
            continue
        key = safe.casefold()
        if key not in seen:
            merged.append(safe)
            seen.add(key)
    if not merged:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+./#-]{2,}", text):
            if token.lower() in {"python", "sql", "excel", "react", "javascript", "typescript", "docker", "git", "tableau", "power", "bi"}:
                merged.append(token)
    return merged[:12] or None


def _safe_skill_name(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^[\-•*\d\)\.]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) < 2:
        return ""
    if cleaned.lower() in {"experience", "formation", "profile", "resume", "cv"}:
        return ""
    return cleaned


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def _clean_heading(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())
    cleaned = cleaned.strip("-•*#")
    return cleaned


def _title_case_city(value: str) -> str:
    parts = value.split()
    return " ".join(part.capitalize() if part.lower() not in {"de", "et", "du"} else part for part in parts)
