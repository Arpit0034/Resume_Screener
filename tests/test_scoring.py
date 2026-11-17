from screener.models import JobD, Resume
from screener.scoring import compute_score, experience_status, match_skills


def test_java_does_not_match_javascript():
    matching, missing = match_skills(["Java"], "Built UIs with JavaScript and React")
    assert matching == [] and missing == ["Java"]


def test_c_does_not_match_cpp():
    assert match_skills(["C"], "Wrote C++ services")[0] == []
    assert match_skills(["C++"], "Wrote C++ services")[0] == ["C++"]


def test_alias_and_hyphen_handling():
    corpus = "Used MySQL daily. Wrote multi-threaded code and RESTful services on GitHub."
    matching, _ = match_skills(["SQL", "Multithreading", "REST API", "Git"], corpus)
    assert matching == ["SQL", "Multithreading", "REST API", "Git"]


def test_score_weights_required_and_preferred():
    job = JobD(required_skills=["a", "b"], preferred_skills=["c", "d"])
    assert compute_score(job, ["a", "b"], [], None) == 80.0
    assert compute_score(job, ["a", "b"], ["c", "d"], None) == 100.0


def test_score_without_preferred_uses_required_only():
    job = JobD(required_skills=["a", "b", "c", "d"])
    assert compute_score(job, ["a", "b"], [], None) == 50.0


def test_experience_penalty_only_when_clearly_not_met():
    job = JobD(required_skills=["a"], minimum_experience=3)
    assert compute_score(job, ["a"], [], False) == 70.0
    assert compute_score(job, ["a"], [], None) == 100.0


def test_experience_status():
    assert experience_status(JobD(), Resume()) is None
    assert experience_status(JobD(minimum_experience=0), Resume()) is True
    assert experience_status(JobD(minimum_experience=2), Resume()) is None
    assert experience_status(JobD(minimum_experience=2), Resume(total_experience_years=1)) is False
    assert experience_status(JobD(minimum_experience=2), Resume(total_experience_years=2)) is True


def test_empty_job_scores_zero():
    assert compute_score(JobD(), [], [], None) == 0.0
