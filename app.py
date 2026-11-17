import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import APIConnectionError, AuthenticationError, RateLimitError

from screener import MODELS, SUPPORTED_EXTENSIONS, LLM, analyze_job, screen_resume
from screener.samples import SAMPLE_JD

load_dotenv()
st.set_page_config(page_title="Resume screener", page_icon="📄", layout="wide")


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "The Groq API key was rejected. Check the key in the sidebar."
    if isinstance(exc, RateLimitError):
        return "Groq's rate limit was hit. Wait a minute, or choose a smaller model."
    if isinstance(exc, APIConnectionError):
        return "Couldn't reach the Groq API. Check your internet connection."
    return str(exc) or exc.__class__.__name__


def tier(score: float) -> str:
    if score >= 70:
        return "🟢 Strong"
    if score >= 40:
        return "🟡 Moderate"
    return "🔴 Weak"


def experience_label(result) -> str:
    years = result.candidate_experience_years
    shown = f"{years:g} yrs" if years is not None else "unclear"
    if result.experience_met is True:
        return f"{shown} · meets"
    if result.experience_met is False:
        return f"{shown} · below"
    return shown


def chips(items: list[str]) -> str:
    return "  ".join(f"`{i}`" for i in items) if items else "none"


def run_screening(api_key: str, model: str, jd: str, files, ai_verdicts: bool) -> None:
    llm = LLM(api_key, model)
    progress = st.progress(0.0, text="Reading the job description…")
    try:
        job = analyze_job(llm, jd)
    except Exception as exc:
        progress.empty()
        st.error(f"Couldn't analyze the job description. {friendly_error(exc)}")
        return

    results, errors = [], []
    for i, f in enumerate(files, start=1):
        progress.progress((i - 1) / len(files), text=f"Screening {f.name} ({i} of {len(files)})")
        try:
            results.append(screen_resume(llm, job, f.name, f.getvalue(), ai_verdict=ai_verdicts))
        except Exception as exc:
            errors.append((f.name, friendly_error(exc)))
    progress.empty()

    results.sort(key=lambda r: r.score, reverse=True)
    st.session_state.update(job=job, results=results, errors=errors)


def render_results() -> None:
    job, results, errors = st.session_state["job"], st.session_state["results"], st.session_state["errors"]

    for name, message in errors:
        st.warning(f"**{name}** was skipped. {message}")
    if not results:
        return

    with st.expander("What the model found in the job description"):
        st.markdown(f"**Role:** {job.role or 'not stated'}")
        st.markdown(
            "**Minimum experience:** "
            + (f"{job.minimum_experience:g} years" if job.minimum_experience is not None else "not stated")
        )
        st.markdown(f"**Required skills:** {chips(job.required_skills)}")
        st.markdown(f"**Preferred skills:** {chips(job.preferred_skills)}")
        st.caption("If a skill looks wrong, rewrite that line of the job description and screen again.")

    scores = [r.score for r in results]
    m1, m2, m3 = st.columns(3)
    m1.metric("Candidates screened", len(results))
    m2.metric("Top score", f"{max(scores):.1f}%")
    m3.metric("Average score", f"{sum(scores) / len(scores):.1f}%")

    n_req = len(job.required_skills)
    table = pd.DataFrame(
        [
            {
                "Rank": i,
                "Candidate": r.candidate_name,
                "Score": r.score,
                "Fit": tier(r.score),
                "Required skills": f"{len(r.matching_skills)} of {n_req}",
                "Experience": experience_label(r),
                "File": r.file_name,
            }
            for i, r in enumerate(results, start=1)
        ]
    )
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")},
    )
    st.download_button("Download results as CSV", table.to_csv(index=False).encode(), "screening_results.csv", "text/csv")

    st.subheader("Candidate details")
    for i, r in enumerate(results, start=1):
        with st.expander(f"{i}. {r.candidate_name} · {r.score:.1f}%", expanded=(i == 1)):
            st.write(r.verdict)
            left, right = st.columns(2)
            left.markdown("**Required skills found**")
            left.markdown(chips(r.matching_skills))
            right.markdown("**Required skills missing**")
            right.markdown(chips(r.missing_skills))
            if job.preferred_skills:
                left.markdown("**Preferred skills found**")
                left.markdown(chips(r.matching_preferred))
                right.markdown("**Preferred skills missing**")
                right.markdown(chips(r.missing_preferred))
            st.caption("Parsed resume")
            st.json(r.resume.model_dump(), expanded=False)


# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    env_key = os.getenv("GROQ_API_KEY", "")
    typed_key = st.text_input("Groq API key", type="password", placeholder="gsk_…")
    api_key = typed_key or env_key
    if env_key and not typed_key:
        st.caption("Using GROQ_API_KEY from the environment.")
    model = st.selectbox("Model", MODELS)
    ai_verdicts = st.toggle("Write a verdict for each candidate", value=True, help="Turn off to halve the number of API calls.")
    st.divider()
    st.caption("Resume text is sent to the Groq API for analysis. Only upload files you're allowed to share.")

# ---------- main ----------
st.title("Resume screener")
st.write("Paste a job description, upload resumes, and get a ranked list showing which required skills each candidate has and lacks.")

col_jd, col_files = st.columns(2, gap="large")
with col_jd:
    st.subheader("Job description")
    st.text_area(
        "Job description",
        key="jd",
        height=360,
        label_visibility="collapsed",
        placeholder="Paste the full job posting, including required and preferred skills.",
    )
    st.button("Fill in a sample", on_click=lambda: st.session_state.update(jd=SAMPLE_JD))
with col_files:
    st.subheader("Resumes")
    files = st.file_uploader(
        "Resumes",
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="PDF, DOCX or TXT. Scanned, image-only PDFs can't be read.",
    )
    if files:
        st.caption(f"{len(files)} file(s) ready: " + ", ".join(Path(f.name).name for f in files[:5]) + (" …" if len(files) > 5 else ""))

jd_text = st.session_state.get("jd", "").strip()
missing_inputs = [label for label, ok in [("a Groq API key", api_key), ("a job description", jd_text), ("at least one resume", files)] if not ok]

if st.button("Screen candidates", type="primary", disabled=bool(missing_inputs)):
    run_screening(api_key, model, jd_text, files, ai_verdicts)
if missing_inputs:
    st.caption("To start, add " + ", ".join(missing_inputs) + ".")

if st.session_state.get("results") is not None:
    st.divider()
    render_results()
