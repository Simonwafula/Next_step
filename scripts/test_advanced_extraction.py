# ruff: noqa: E402
import sqlite3
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from app.normalization import (
    extract_education_level,
    extract_experience_years,
    classify_seniority,
)


def test_advanced_extraction(db_path, limit=50):
    if not os.path.exists(db_path):
        print(f"Error: DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT title, content FROM jobs_data LIMIT ?", (limit,))
    rows = cursor.fetchall()

    print(f"--- Advanced Extraction Test on {len(rows)} samples ---")
    print(f"{'Title':<40} | {'Edu':<10} | {'Exp':<5} | {'Seniority':<10}")
    print("-" * 75)

    stats = {"edu": {}, "sen": {}, "exp": 0, "exp_count": 0}

    for title, content in rows:
        edu = extract_education_level(content) or "N/A"
        exp = extract_experience_years(content)
        sen = classify_seniority(title, exp)

        print(
            f"{title[:38]:<40} | {edu:<10} | {str(exp) if exp else 'N/A':<5} | {sen:<10}"
        )

        stats["edu"][edu] = stats["edu"].get(edu, 0) + 1
        stats["sen"][sen] = stats["sen"].get(sen, 0) + 1
        if exp:
            stats["exp"] += exp
            stats["exp_count"] += 1

    print("-" * 75)
    print("Summary Stats:")
    print(f"Education: {stats['edu']}")
    print(f"Seniority: {stats['sen']}")
    if stats["exp_count"] > 0:
        print(f"Avg Exp Years: {stats['exp'] / stats['exp_count']:.1f}")

    conn.close()


if __name__ == "__main__":
    db_path = os.getenv("JOBS_DB_PATH", "jobs.sqlite3")
    test_advanced_extraction(db_path)
