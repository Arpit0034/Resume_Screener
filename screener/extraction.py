"""LLM calls: parse a job description, parse a resume, write a short verdict."""
from .llm import LLM
from .models import JobD, Resume

MAX_RESUME_CHARS = 20_000

JOB_SYSTEM = """You are an expert HR assistant. Extract structured information from a job description.

Return ONLY a JSON object with exactly these keys:
{
  "role": "job title, or null",
  "required_skills": ["Java", "Spring Boot"],
  "preferred_skills": ["Docker"],
  "minimum_experience": 0,
  "education_requirements": ["Bachelor's degree in Computer Science"],
  "responsibilities": ["Design and maintain backend services"]
}

Rules:
- Do not invent information.
- minimum_experience is a number of years. For a range such as "0-2 years", use the lower bound. If no experience is mentioned, use null.
- If a list has no information, use an empty list.
- required_skills and preferred_skills hold atomic skill or technology names only, such as "Java", "MySQL", "Git".
- Never return a sentence or descriptive phrase as a skill. If one phrase names several technologies (for example "MySQL or PostgreSQL"), split it into separate entries.
- Put skills the job calls "required", "must have" or similar in required_skills, and "preferred", "nice to have" or "bonus" skills in preferred_skills."""

RESUME_SYSTEM = """You are an expert resume parser. Extract information based on meaning, not only on exact section headings (Experience, Work History, Employment and Internships can all hold work experience).

Return ONLY a JSON object with exactly these keys:
{
  "name": "full name, or null",
  "email": "or null",
  "phone": "or null",
  "total_experience_years": 0,
  "skills": ["Java", "SQL"],
  "experiences": [
    {"company": "", "role": "", "duration": "", "description": "", "skills_used": []}
  ],
  "education": [],
  "projects": [],
  "certifications": []
}

Rules:
- Do not invent information.
- Use null for a missing value and [] for a list with no information.
- Include internships inside experiences.
- total_experience_years is a number of years of professional experience (internships count); use 0 for none and null if you cannot tell.
- skills holds atomic skill and technology names mentioned anywhere in the resume, including projects and experience."""


def analyze_job(llm: LLM, job_text: str) -> JobD:
    data = llm.json(
        [
            {"role": "system", "content": JOB_SYSTEM},
            {"role": "user", "content": f"Analyze this job description:\n\n{job_text}"},
        ]
    )
    job = JobD(**data)
    job.required_skills = _dedupe(job.required_skills)
    required = {s.lower() for s in job.required_skills}
    job.preferred_skills = [s for s in _dedupe(job.preferred_skills) if s.lower() not in required]
    return job


def parse_resume(llm: LLM, resume_text: str) -> Resume:
    data = llm.json(
        [
            {"role": "system", "content": RESUME_SYSTEM},
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text[:MAX_RESUME_CHARS]}"},
        ]
    )
    return Resume(**data)


def write_verdict(llm: LLM, name: str, matching: list[str], missing: list[str], score: float, exp_met: bool | None) -> str:
    experience = {True: "meets", False: "does not meet", None: "has no clear comparison with"}[exp_met]
    prompt = f"""You are an HR recruiter. Write a verdict of 1-2 sentences using only these facts.

Candidate: {name}
Matching required skills: {matching or "none"}
Missing required skills: {missing or "none"}
Match score: {score}%
The candidate {experience} the minimum experience requirement.

Do not invent a different score and do not claim skills that are not listed above."""
    return llm.chat([{"role": "user", "content": prompt}])


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
