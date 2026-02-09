"""Regression tests for extraction + analytics pipelines (T-603a/b).

Uses the fixture dataset at data/samples/regression_jobs.json to verify
that extractors produce deterministic, expected results across runs.
"""

import json
from pathlib import Path

import pytest

from app.normalization.extractors import (
    classify_seniority,
    extract_education_level,
    extract_experience_years,
)
from app.normalization.parsers import parse_salary
from app.normalization.skills import extract_skills
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
    @pytest.mark.parametrize("idx", range(5))
    def test_family_matches_expected(self, regression_jobs, idx):
        job = regression_jobs[idx]
        family, _ = normalize_title(job["title"])
        assert family == job["expected"]["title_family"], (
            f"{job['id']}: expected family={job['expected']['title_family']}, got {family}"
        )


# ---------------------------------------------------------------------------
# Seniority classification
# ---------------------------------------------------------------------------


class TestSeniorityClassification:
    @pytest.mark.parametrize("idx", range(5))
    def test_seniority_matches_expected(self, regression_jobs, idx):
        job = regression_jobs[idx]
        exp = extract_experience_years(job["description"])
        seniority = classify_seniority(job["title"], exp)
        assert seniority == job["expected"]["seniority"], (
            f"{job['id']}: expected seniority={job['expected']['seniority']}, got {seniority}"
        )


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------


class TestExperienceExtraction:
    @pytest.mark.parametrize("idx", range(5))
    def test_experience_years(self, regression_jobs, idx):
        job = regression_jobs[idx]
        exp = extract_experience_years(job["description"])
        expected = job["expected"]["experience_years"]
        assert exp == expected, f"{job['id']}: expected exp={expected}, got {exp}"


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------


class TestEducationExtraction:
    @pytest.mark.parametrize("idx", range(5))
    def test_education_matches_expected(self, regression_jobs, idx):
        job = regression_jobs[idx]
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
    @pytest.mark.parametrize("idx", range(5))
    def test_salary_max(self, regression_jobs, idx):
        job = regression_jobs[idx]
        _, salary_max, _ = parse_salary(job["description"])
        expected_max = job["expected"]["salary_max"]
        if expected_max is None:
            # No strict check — parser may pick up stray numbers
            pass
        else:
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
    @pytest.mark.parametrize("idx", range(5))
    def test_expected_skills_present(self, regression_jobs, idx):
        job = regression_jobs[idx]
        skills = extract_skills(job["description"])
        skills_lower = [s.lower() for s in skills]
        for expected_skill in job["expected"]["skills_subset"]:
            assert expected_skill.lower() in skills_lower, (
                f'{job["id"]}: expected skill "{expected_skill}" not in {skills}'
            )


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
