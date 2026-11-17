"""Pydantic models. Validators are lenient because LLM JSON is rarely perfect."""
import re
from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def _stringify(item) -> str:
    if isinstance(item, dict):
        return ", ".join(str(v) for v in item.values() if v)
    return str(item)


def _clean_strs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    out = [_stringify(x).strip() for x in value if x is not None]
    return [x for x in out if x]


def _to_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _opt_str(value) -> str | None:
    if value is None:
        return None
    text = _stringify(value).strip()
    return text or None


def _dict_items(value) -> list[dict]:
    return [x for x in (value or []) if isinstance(x, dict)]


StrList = Annotated[list[str], BeforeValidator(_clean_strs)]
OptFloat = Annotated[float | None, BeforeValidator(_to_float)]
OptStr = Annotated[str | None, BeforeValidator(_opt_str)]


class JobD(BaseModel):
    role: OptStr = None
    required_skills: StrList = []
    preferred_skills: StrList = []
    minimum_experience: OptFloat = None
    education_requirements: StrList = []
    responsibilities: StrList = []


class Experience(BaseModel):
    company: OptStr = None
    role: OptStr = None
    duration: OptStr = None
    description: OptStr = None
    skills_used: StrList = []


class Resume(BaseModel):
    name: OptStr = None
    email: OptStr = None
    phone: OptStr = None
    total_experience_years: OptFloat = None
    skills: StrList = []
    experiences: Annotated[list[Experience], BeforeValidator(_dict_items)] = []
    education: StrList = []
    projects: StrList = []
    certifications: StrList = []


class MatchResult(BaseModel):
    candidate_name: str
    file_name: str
    score: float
    matching_skills: list[str]
    missing_skills: list[str]
    matching_preferred: list[str] = []
    missing_preferred: list[str] = []
    experience_met: bool | None = None  # None = no requirement or unknown
    candidate_experience_years: float | None = None
    verdict: str = ""
    resume: Resume
