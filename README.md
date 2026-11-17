# Resume screener

Paste a job description, upload resumes (PDF, DOCX or TXT), and get a ranked list of candidates showing which required skills each one has and lacks. Built with Streamlit and the Groq API.

## How it works

1. **Read the job description.** An LLM extracts the role, required skills, preferred skills and minimum experience.
2. **Parse each resume.** The text is extracted from the file and an LLM turns it into structured data (skills, experience, education, projects).
3. **Score deterministically.** Skill matching and scoring are plain Python, not an LLM, so the same inputs always give the same score.
4. **Write a verdict.** The LLM writes a one or two sentence summary from the computed facts only. You can turn this off.

### Scoring

- With preferred skills in the job description: 80% of the score comes from required skills and 20% from preferred skills. Without them, the score is the share of required skills found.
- If the job states a minimum experience and the candidate is clearly below it, the score is multiplied by 0.7.
- Matching respects word boundaries (`Java` does not match `JavaScript`) and knows common aliases (`SQL` matches `MySQL`, `REST API` matches `RESTful`). Add your own in `ALIASES` in `screener/scoring.py`.

Tune the weights at the top of `screener/scoring.py`.

## Run it locally

Requires Python 3.10 or newer and a free [Groq API key](https://console.groq.com/keys).

```bash
git clone <your-repo-url>
cd resume-screener
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # then put your key in .env
streamlit run app.py
```

You can also skip `.env` and paste the key into the app's sidebar.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a fake LLM, so they need no API key or network.

## Project layout

```
app.py                  Streamlit interface
screener/
  llm.py                Groq client with retries and tolerant JSON parsing
  readers.py            PDF / DOCX / TXT to text
  extraction.py         Prompts for the job, resume and verdict
  scoring.py            Skill matching and score
  pipeline.py           Screens one resume end to end
  models.py             Pydantic models
tests/
```

## Privacy

Resume text is sent to the Groq API for analysis. Only upload files you have the right to share. `.gitignore` excludes `.env`, `resumes/`, and PDF and DOCX files so real resumes and keys don't end up in the repository.

## Limitations

- Scanned or image-only PDFs have no text to read and are skipped with a message.
- Skill extraction depends on the model. The app shows what it found in the job description so you can check it.
- Scores rank candidates against a job; they are a screening aid, not a hiring decision.
