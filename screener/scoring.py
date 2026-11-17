"""Deterministic skill matching and scoring (no LLM involved, so scores are reproducible)."""
import re

from .models import JobD, Resume

REQUIRED_WEIGHT = 0.8        # share of the score from required skills when preferred skills exist
EXPERIENCE_PENALTY = 0.7     # multiplier when the experience requirement is clearly not met

# Extra spellings that count as the same skill. Extend as needed.
ALIASES: dict[str, list[str]] = {
    "sql": ["mysql", "postgresql", "postgres", "sqlite", "sql server", "mssql", "mariadb", "pl/sql"],
    "postgresql": ["postgres"],
    "rest api": ["rest", "restful", "rest apis", "restful api", "restful apis"],
    "rest apis": ["rest", "restful", "rest api", "restful api", "restful apis"],
    "kubernetes": ["k8s"],
    "ci/cd": ["cicd", "ci cd", "jenkins", "github actions", "gitlab ci"],
    "machine learning": ["ml"],
    "node.js": ["nodejs", "node js"],
    "react": ["reactjs", "react.js"],
    "git": ["github", "gitlab", "bitbucket"],
    "aws": ["amazon web services"],
    "oop": ["object oriented", "object oriented programming"],
    "multithreading": ["multi threading", "multi threaded", "multithreaded", "concurrency", "concurrent programming"],
    "data structures": ["dsa", "data structures and algorithms"],
    "algorithms": ["dsa", "data structures and algorithms"],
}


def normalize(text: str) -> str:
    text = text.lower().replace("-", " ")
    text = re.sub(r"[^a-z0-9+#./\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _found(needle: str, haystack: str) -> bool:
    # Boundaries stop "java" matching "javascript" and "c" matching "c++".
    pattern = rf"(?<![a-z0-9+#]){re.escape(needle)}(?![a-z0-9+#])"
    return re.search(pattern, haystack) is not None


def skill_in_text(skill: str, corpus: str) -> bool:
    base = normalize(skill)
    if not base:
        return False
    return any(_found(v, corpus) for v in [base, *ALIASES.get(base, [])])


def match_skills(skills: list[str], corpus: str) -> tuple[list[str], list[str]]:
    corpus = normalize(corpus)
    matching, missing = [], []
    for skill in skills:
        (matching if skill_in_text(skill, corpus) else missing).append(skill)
    return matching, missing


def build_corpus(resume: Resume, raw_text: str) -> str:
    parts = [raw_text, *resume.skills]
    for exp in resume.experiences:
        parts += exp.skills_used
    return "\n".join(parts)


def experience_status(job: JobD, resume: Resume) -> bool | None:
    """True/False when comparable, None when the job states no requirement or the resume is unclear."""
    if job.minimum_experience is None:
        return None
    if job.minimum_experience <= 0:
        return True
    if resume.total_experience_years is None:
        return None
    return resume.total_experience_years >= job.minimum_experience


def compute_score(job: JobD, matched_required: list[str], matched_preferred: list[str], exp_met: bool | None) -> float:
    n_req, n_pref = len(job.required_skills), len(job.preferred_skills)
    if n_req and n_pref:
        base = 100 * (
            REQUIRED_WEIGHT * len(matched_required) / n_req
            + (1 - REQUIRED_WEIGHT) * len(matched_preferred) / n_pref
        )
    elif n_req:
        base = 100 * len(matched_required) / n_req
    elif n_pref:
        base = 100 * len(matched_preferred) / n_pref
    else:
        return 0.0
    if exp_met is False:
        base *= EXPERIENCE_PENALTY
    return round(base, 1)
