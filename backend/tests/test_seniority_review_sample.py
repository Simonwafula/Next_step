from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


SAMPLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "samples"
    / "seniority_review_sample.csv"
)
EXPECTED_COLUMNS = [
    "sample_id",
    "source",
    "current_label",
    "reviewed_label",
    "review_confidence",
    "title_for_review",
    "education_bucket",
    "quality_score",
    "review_theme",
    "review_notes",
]
ALLOWED_LABELS = {"Entry", "Mid-Level", "Senior", "Executive"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SOURCES = {"brightermonday.co.ke", "gov_careers", "migration"}
EXPECTED_CURRENT_LABEL_COUNTS = {
    "Entry": 5,
    "Mid-Level": 5,
    "Senior": 5,
    "Executive": 5,
}


def _load_sample_rows() -> tuple[list[str], list[dict[str, str]]]:
    with SAMPLE_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def test_seniority_review_sample_has_expected_schema() -> None:
    fieldnames, rows = _load_sample_rows()

    assert SAMPLE_PATH.exists()
    assert fieldnames == EXPECTED_COLUMNS
    assert len(rows) == 20


def test_seniority_review_sample_values_are_balanced_and_valid() -> None:
    _, rows = _load_sample_rows()

    sample_ids = [row["sample_id"] for row in rows]
    assert len(sample_ids) == len(set(sample_ids))

    current_label_counts = Counter(row["current_label"] for row in rows)
    assert current_label_counts == EXPECTED_CURRENT_LABEL_COUNTS

    for row in rows:
        assert row["source"] in ALLOWED_SOURCES
        assert row["current_label"] in ALLOWED_LABELS
        assert row["reviewed_label"] in ALLOWED_LABELS
        assert row["review_confidence"] in ALLOWED_CONFIDENCE
        assert row["title_for_review"].strip()
        assert row["review_theme"].strip()
        assert row["review_notes"].strip()

        quality_score = float(row["quality_score"])
        assert 0.0 <= quality_score <= 1.0
