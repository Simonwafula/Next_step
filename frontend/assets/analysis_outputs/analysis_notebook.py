#!/usr/bin/env python3
"""Lightweight local analysis helper for the exported coursework sample."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cleaned_sample.csv"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def top(counter: Counter[str], n: int = 10) -> list[tuple[str, int]]:
    return counter.most_common(n)


def main() -> None:
    rows = load_rows(CSV_PATH)
    titles = Counter(row["title"] for row in rows if row["title"])
    companies = Counter(row["company"] for row in rows if row["company"])
    locations = Counter(row["location"] or "[NULL]" for row in rows)
    experience = Counter(row["experience_level"] or "[NULL]" for row in rows)
    employment = Counter(row["employment_type"] or "[NULL]" for row in rows)
    education = Counter(row["education"] or "[NULL]" for row in rows)
    desc_lengths = [len(row["description"] or "") for row in rows]
    skills: Counter[str] = Counter()

    for row in rows:
        raw = row["skills_json"]
        if not raw:
            continue
        try:
            skill_items = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in skill_items:
            value = (item.get("value") or "").strip()
            if value:
                skills[value] += 1

    print(f"Rows: {len(rows)}")
    print(f"Top titles: {top(titles)}")
    print(f"Top companies: {top(companies)}")
    print(f"Top locations: {top(locations)}")
    print(f"Experience levels: {top(experience)}")
    print(f"Employment types: {top(employment)}")
    print(f"Education values: {top(education)}")
    print(
        "Description lengths:",
        {
            "min": min(desc_lengths),
            "p50": median(desc_lengths),
            "avg": round(mean(desc_lengths), 2),
            "max": max(desc_lengths),
        },
    )
    print(f"Top extracted skills: {top(skills, 15)}")


if __name__ == "__main__":
    main()
