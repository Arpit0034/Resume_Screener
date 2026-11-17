"""Screen one resume against an already-analyzed job."""
from pathlib import Path

from .extraction import parse_resume, write_verdict
from .llm import LLM
from .models import JobD, MatchResult
from .readers import extract_text
from .scoring import build_corpus, compute_score, experience_status, match_skills


def fallback_verdict(name: str, matching: list[str], missing: list[str], score: float) -> str:
    total = len(matching) + len(missing)
    return f"{name} matches {len(matching)} of {total} required skills (score {score}%)."


def screen_resume(llm: LLM, job: JobD, file_name: str, data: bytes, ai_verdict: bool = True) -> MatchResult:
    text = extract_text(file_name, data)
    if len(text.strip()) < 30:
        raise ValueError("No readable text found. The file may be a scan or image-only.")

    resume = parse_resume(llm, text)
    corpus = build_corpus(resume, text)
    matching, missing = match_skills(job.required_skills, corpus)
    matching_pref, missing_pref = match_skills(job.preferred_skills, corpus)
    exp_met = experience_status(job, resume)
    score = compute_score(job, matching, matching_pref, exp_met)
    name = resume.name or Path(file_name).stem

    verdict = fallback_verdict(name, matching, missing, score)
    if ai_verdict:
        try:
            verdict = write_verdict(llm, name, matching, missing, score, exp_met) or verdict
        except Exception:
            pass  # the score is already computed; keep the plain-text verdict

    return MatchResult(
        candidate_name=name,
        file_name=file_name,
        score=score,
        matching_skills=matching,
        missing_skills=missing,
        matching_preferred=matching_pref,
        missing_preferred=missing_pref,
        experience_met=exp_met,
        candidate_experience_years=resume.total_experience_years,
        verdict=verdict,
        resume=resume,
    )
