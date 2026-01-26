from app.normalization.extractors import (
    classify_seniority_detailed,
    extract_education_detailed,
    extract_experience_years_detailed,
    extract_task_statements,
)


def test_extract_education_detailed():
    text = "Requires a Bachelor's degree or higher in Computer Science."
    result = extract_education_detailed(text)
    assert result is not None
    assert result["value"] == "Bachelor"
    assert result["confidence"] >= 0.6
    assert result["evidence"]
    assert result["start"] is not None


def test_extract_experience_years_detailed():
    text = "Minimum 3 years of experience with data pipelines."
    result = extract_experience_years_detailed(text)
    assert result is not None
    assert result["value"] == 3
    assert result["confidence"] >= 0.7
    assert "years" in result["evidence"].lower()


def test_classify_seniority_detailed():
    result = classify_seniority_detailed("Senior Data Engineer", 5)
    assert result["value"] == "Senior"
    assert result["confidence"] >= 0.6
    assert result["source"] in {"title_keyword", "experience"}


def test_extract_task_statements_evidence():
    text = "Responsibilities:\n- Build data pipelines\n- Maintain ETL jobs"
    results = extract_task_statements(text)
    assert results
    assert results[0]["evidence"]
    assert results[0]["start"] is not None
