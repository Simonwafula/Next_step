from __future__ import annotations

from app.normalization.skills import extract_skills


def test_skill_denylist_filters_known_noise():
    text = (
        "We need a data analyst with Python and SQL. "
        "Avoid noise like Scholastic Read 180 and PD 5500 Standard, plus Z39.50 Standard."
    )
    skills = [s.lower() for s in extract_skills(text)]

    assert "python" in skills
    assert "sql" in skills

    assert "scholastic read 180" not in skills
    assert "pd 5500 standard" not in skills
    assert "z39.50 standard" not in skills


def test_skillner_ngram_min_confidence_env_var_does_not_break_patterns(monkeypatch):
    # Even if SkillNER is enabled with an aggressive threshold, our deterministic
    # pattern/custom extraction should still contribute.
    monkeypatch.setenv("SKILL_EXTRACTOR_MODE", "skillner")
    monkeypatch.setenv("SKILLNER_NGRAM_MIN_CONFIDENCE", "0.99")

    text = "Looking for a data analyst with SQL, Python, and Power BI."
    skills = [s.lower() for s in extract_skills(text)]

    # These are pattern hits; they should survive regardless of SkillNER settings.
    assert "python" in skills
    assert "sql" in skills
    assert "power bi" in skills
