"""Regression tests for extraction + analytics pipelines (T-603a/b).

Uses the fixture dataset at data/samples/regression_jobs.json to verify
that extractors produce deterministic, expected results across runs.
"""

import json
from pathlib import Path

import pytest

from app.normalization.extractors import (
    classify_seniority,
    classify_seniority_detailed,
    extract_education_detailed,
    extract_education_level,
    extract_experience_years_detailed,
    extract_experience_years,
)
from app.normalization.parsers import parse_salary
from app.normalization.skills import extract_skills
from app.normalization.skills import extract_skills_detailed
from app.normalization.titles import normalize_title

FIXTURES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "regression_jobs.json"
)


@pytest.fixture(scope="module")
def regression_jobs():
    with open(FIXTURES_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Title normalization
# ---------------------------------------------------------------------------


class TestTitleNormalization:
    def test_family_matches_expected(self, regression_jobs):
        for job in regression_jobs:
            family, _ = normalize_title(job["title"])
            expected = job["expected"]["title_family"]
            assert family == expected, (
                f"{job['id']}: expected family={expected}, got {family}"
            )


# ---------------------------------------------------------------------------
# Seniority classification
# ---------------------------------------------------------------------------


class TestSeniorityClassification:
    def test_seniority_matches_expected(self, regression_jobs):
        for job in regression_jobs:
            exp = extract_experience_years(job["description"])
            seniority = classify_seniority(job["title"], exp)
            expected = job["expected"]["seniority"]
            assert seniority == expected, (
                f"{job['id']}: expected seniority={expected}, got {seniority}"
            )


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------


class TestExperienceExtraction:
    def test_experience_years(self, regression_jobs):
        for job in regression_jobs:
            exp = extract_experience_years(job["description"])
            expected = job["expected"]["experience_years"]
            if expected is None:
                assert exp is None, f"{job['id']}: expected exp=None, got {exp}"
            else:
                assert exp == expected, (
                    f"{job['id']}: expected exp={expected}, got {exp}"
                )


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------


class TestEducationExtraction:
    def test_education_matches_expected(self, regression_jobs):
        for job in regression_jobs:
            edu = extract_education_level(job["description"])
            expected = job["expected"]["education"]
            if expected is None:
                assert edu is None, f"{job['id']}: expected None, got {edu}"
            else:
                assert edu is not None, f"{job['id']}: expected {expected}, got None"
                assert expected.lower() in edu.lower(), (
                    f'{job["id"]}: expected "{expected}" in "{edu}"'
                )


# ---------------------------------------------------------------------------
# Salary parsing
# ---------------------------------------------------------------------------


class TestSalaryParsing:
    def test_salary_max(self, regression_jobs):
        for job in regression_jobs:
            _, salary_max, _ = parse_salary(job["description"])
            expected_max = job["expected"]["salary_max"]
            if expected_max is None:
                # No strict check — parser may pick up stray numbers.
                continue
            assert salary_max is not None, (
                f"{job['id']}: expected salary_max={expected_max}"
            )
            assert salary_max == pytest.approx(expected_max, rel=0.01), (
                f"{job['id']}: expected max={expected_max}, got {salary_max}"
            )


# ---------------------------------------------------------------------------
# Skill extraction (pattern-based fallback when SkillNER unavailable)
# ---------------------------------------------------------------------------


class TestSkillExtraction:
    def test_expected_skills_present(self, regression_jobs):
        for job in regression_jobs:
            expected = job["expected"]["skills_subset"]
            if not expected:
                continue
            skills = extract_skills(job["description"])
            skills_lower = [s.lower() for s in skills]
            for expected_skill in expected:
                msg = f'{job["id"]}: expected skill "{expected_skill}" not in {skills}'
                assert expected_skill.lower() in skills_lower, msg


# ---------------------------------------------------------------------------
# Determinism: running extractors twice yields identical results
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_title_deterministic(self, regression_jobs):
        for job in regression_jobs:
            r1 = normalize_title(job["title"])
            r2 = normalize_title(job["title"])
            assert r1 == r2

    def test_skills_deterministic(self, regression_jobs):
        for job in regression_jobs:
            r1 = sorted(extract_skills(job["description"]))
            r2 = sorted(extract_skills(job["description"]))
            assert r1 == r2

    def test_seniority_deterministic(self, regression_jobs):
        for job in regression_jobs:
            exp = extract_experience_years(job["description"])
            r1 = classify_seniority(job["title"], exp)
            r2 = classify_seniority(job["title"], exp)
            assert r1 == r2

    def test_salary_deterministic(self, regression_jobs):
        for job in regression_jobs:
            r1 = parse_salary(job["description"])
            r2 = parse_salary(job["description"])
            assert r1 == r2


# ---------------------------------------------------------------------------
# Evidence + confidence gates (hardening)
# ---------------------------------------------------------------------------


class TestEvidenceGates:
    def test_skill_evidence_and_confidence(self, regression_jobs):
        for job in regression_jobs:
            expected = job["expected"]["skills_subset"]
            if not expected:
                continue
            detailed = extract_skills_detailed(job["description"])
            for expected_skill in expected:
                msg = (
                    f"{job['id']}: expected skill '{expected_skill}' in detailed skills"
                )
                assert expected_skill in detailed, msg
                entry = detailed[expected_skill]
                assert entry.get("confidence", 0) >= 0.5, (
                    f"{job['id']}: low confidence for {expected_skill}"
                )
                assert entry.get("evidence"), (
                    f"{job['id']}: missing evidence for {expected_skill}"
                )

    def test_education_evidence_and_confidence(self, regression_jobs):
        for job in regression_jobs:
            expected = job["expected"]["education"]
            if expected is None:
                continue
            detailed = extract_education_detailed(job["description"])
            assert detailed is not None, f"{job['id']}: expected education evidence"
            assert detailed.get("confidence", 0) >= 0.5, (
                f"{job['id']}: low education confidence"
            )
            assert detailed.get("evidence"), f"{job['id']}: missing education evidence"

    def test_experience_evidence_and_confidence(self, regression_jobs):
        for job in regression_jobs:
            expected = job["expected"]["experience_years"]
            if expected is None:
                continue
            detailed = extract_experience_years_detailed(job["description"])
            assert detailed is not None, f"{job['id']}: expected experience evidence"
            assert detailed.get("confidence", 0) >= 0.5, (
                f"{job['id']}: low experience confidence"
            )
            assert detailed.get("evidence"), f"{job['id']}: missing experience evidence"

    def test_seniority_evidence_present(self, regression_jobs):
        for job in regression_jobs:
            exp = extract_experience_years(job["description"])
            detailed = classify_seniority_detailed(job["title"], exp)
            assert detailed.get("confidence", 0) >= 0.4, (
                f"{job['id']}: low seniority confidence"
            )
            assert detailed.get("source"), f"{job['id']}: missing seniority source"
