import io

import pytest
from docx import Document

from screener import analyze_job, screen_resume
from screener.llm import parse_json_object
from screener.models import Resume


def test_resume_model_tolerates_messy_llm_output():
    r = Resume(
        skills=None,
        projects=[{"name": "Chat app", "description": "Spring Boot"}],
        total_experience_years="2 years",
        experiences=[{"company": "Acme", "skills_used": None}, "junk"],
    )
    assert r.skills == [] and r.total_experience_years == 2.0
    assert r.projects == ["Chat app, Spring Boot"] and len(r.experiences) == 1


def test_parse_json_object_handles_code_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! {"a": 1} Hope that helps') == {"a": 1}
    with pytest.raises(ValueError):
        parse_json_object("no json here")


class FakeLLM:
    def json(self, messages):
        if "job description" in messages[0]["content"].lower():
            return {
                "role": "Java Developer",
                "required_skills": ["Java", "Spring Boot", "SQL", "Java"],
                "preferred_skills": ["Docker"],
                "minimum_experience": 2,
            }
        return {"name": "Asha Rao", "skills": ["Java"], "total_experience_years": 1}

    def chat(self, messages, json_mode=False):
        return "Solid fit."


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_end_to_end_with_fake_llm():
    llm = FakeLLM()
    job = analyze_job(llm, "any job text")
    assert job.required_skills == ["Java", "Spring Boot", "SQL"]  # deduplicated

    resume_bytes = _docx_bytes("Asha Rao. Java developer who built apps with Spring Boot and MySQL for a year.")
    result = screen_resume(llm, job, "asha.docx", resume_bytes)
    assert result.candidate_name == "Asha Rao"
    assert result.matching_skills == ["Java", "Spring Boot", "SQL"]
    assert result.experience_met is False          # 1 year < 2 years
    assert result.score == pytest.approx(56.0)     # 3/3 required = 80, x0.7 experience penalty
    assert result.verdict == "Solid fit."


def test_unreadable_file_raises():
    with pytest.raises(ValueError):
        screen_resume(FakeLLM(), analyze_job(FakeLLM(), "x"), "empty.txt", b"hi")
