# ruff: noqa: E402
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.database import SessionLocal
from app.services.search import search_jobs
from app.services.recommend import transitions_for


def smoke_test_services():
    db = SessionLocal()
    try:
        # 1. Test Search
        print("Testing Search (Data Analyst)...")
        results = search_jobs(db, q="Data Analyst", location="Nairobi")
        print(f"  Found {len(results)} results.")
        if results:
            print(
                f"  Top result: {results[0]['title']} at {results[0]['organization']}"
            )
            print(f"  Why match: {results[0]['why_match']}")

        # 2. Test Career Transitions
        print("\nTesting Career Transitions (Data Analyst)...")
        transitions = transitions_for(db, current="Data Analyst")
        print(f"  Suggested {len(transitions)} transitions.")
        for t in transitions:
            print(f"  -> {t['target_role']} (Score: {t['combined_score']:.2f})")

    finally:
        db.close()


if __name__ == "__main__":
    smoke_test_services()
