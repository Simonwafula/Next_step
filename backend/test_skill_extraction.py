from app.normalization.skills import extract_skills_detailed


def test_extract_skills_detailed_patterns(monkeypatch):
    monkeypatch.setenv("SKILL_EXTRACTOR_MODE", "patterns")
    text = "We need SQL and Python experience."
    results = extract_skills_detailed(text)

    assert "sql" in results
    assert "python" in results
    assert results["sql"]["confidence"] >= 0.6
    assert results["sql"]["evidence"]
    assert results["sql"]["start"] is not None
    assert results["sql"]["end"] is not None


def test_extract_skills_custom_mapping(monkeypatch):
    monkeypatch.setenv("SKILL_EXTRACTOR_MODE", "patterns")
    text = "Experience with FastAPI and Postgres is required."
    results = extract_skills_detailed(text)

    assert "fastapi" in results
    assert "postgresql" in results
