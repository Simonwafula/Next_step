# ruff: noqa: E402
import sqlite3
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from app.normalization import (
    normalize_title,
    normalize_company_name,
    normalize_location,
    extract_and_normalize_skills,
)


def test_normalization_on_real_data(db_path, limit=50):
    if not os.path.exists(db_path):
        print(f"Error: DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get some sample jobs
    cursor.execute("SELECT title, content FROM jobs_data LIMIT ?", (limit,))
    rows = cursor.fetchall()

    print(f"--- Normalization Test on {len(rows)} samples ---")
    print(
        f"{'Original Title':<40} | {'Normalized Title':<30} | {'Location':<15} | {'Company':<15}"
    )
    print("-" * 110)

    for title, content in rows:
        # Title normalization
        family, canon_title = normalize_title(title)

        # Heuristic: sometimes company is in title "Title at Company" or "Title - Company"
        company_raw = "Unknown"
        if " at " in title:
            company_raw = title.split(" at ")[-1]
        elif " - " in title:
            company_raw = title.split(" - ")[-1]

        norm_company = normalize_company_name(company_raw)

        # Location: search in title or first 100 chars of content
        loc_raw = "Nairobi"  # Default
        if "(" in title and ")" in title:
            loc_raw = title[title.find("(") + 1 : title.find(")")]

        norm_loc = normalize_location(loc_raw)

        # Skills
        _ = extract_and_normalize_skills(content)

        print(
            f"{title[:38]:<40} | {canon_title[:28]:<30} | {norm_loc[0]:<15} | {norm_company:<15}"
        )

    conn.close()


if __name__ == "__main__":
    db_path = os.getenv("JOBS_DB_PATH", "jobs.sqlite3")
    test_normalization_on_real_data(db_path)
