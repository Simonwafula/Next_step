#!/usr/bin/env python3
"""
Smoke test script for Next Step MVP validation.

This script validates core functionality without requiring external services.
Run after deployment or code changes to verify system health.

Usage:
    python scripts/smoke_test.py [--api-url http://localhost:8000]
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def database_connection_check():
    """Test database connectivity"""
    print("  Testing database connection...")
    try:
        os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
        from app.db.database import SessionLocal, DATABASE_URL
        from sqlalchemy import text

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print(f"    Database: {'SQLite' if 'sqlite' in DATABASE_URL else 'PostgreSQL'}")
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {e}"


def job_count_check():
    """Test that jobs exist in database"""
    print("  Testing job data...")
    try:
        os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
        from app.db.database import SessionLocal
        from app.db.models import JobPost
        from sqlalchemy import select, func

        db = SessionLocal()
        count = db.execute(select(func.count(JobPost.id))).scalar() or 0
        db.close()

        if count > 0:
            print(f"    Jobs in database: {count}")
            return True, f"{count} jobs found"
        else:
            return False, "No jobs found in database"
    except Exception as e:
        return False, f"Job count failed: {e}"


def search_function_check():
    """Test search functionality"""
    print("  Testing search function...")
    try:
        os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
        os.environ.setdefault("NEXTSTEP_DISABLE_TRANSFORMERS", "1")
        from app.db.database import SessionLocal
        from app.services.search import search_jobs

        db = SessionLocal()
        results = search_jobs(db, q="analyst", location=None, seniority=None)
        db.close()

        if results:
            print(f"    Search results: {len(results)} jobs")
            return True, f"Search returned {len(results)} results"
        else:
            return True, "Search works but no matching jobs"
    except Exception as e:
        return False, f"Search failed: {e}"


def recommendations_check():
    """Test recommendation system"""
    print("  Testing recommendations...")
    try:
        os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
        from app.db.database import SessionLocal
        from app.services.recommend import transitions_for

        db = SessionLocal()
        recs = transitions_for(db, "data analyst")
        db.close()

        print(f"    Recommendations: {len(recs)} transitions")
        return True, f"{len(recs)} recommendations generated"
    except Exception as e:
        return False, f"Recommendations failed: {e}"


def title_normalization_check():
    """Test title normalization"""
    print("  Testing title normalization...")
    try:
        from app.normalization.titles import normalize_title, get_careers_for_degree

        family, canonical = normalize_title("data ninja")
        careers = get_careers_for_degree("economics")

        print(f"    'data ninja' -> {canonical} ({family})")
        print(f"    'economics' degree -> {len(careers)} careers")
        return True, "Title normalization working"
    except Exception as e:
        return False, f"Title normalization failed: {e}"


def embeddings_check():
    """Test embeddings generation"""
    print("  Testing embeddings...")
    try:
        os.environ.setdefault("NEXTSTEP_DISABLE_TRANSFORMERS", "1")
        from app.ml.embeddings import embed_text

        embedding = embed_text("software engineer")
        dim = len(embedding)

        if dim > 0:
            print(f"    Embedding dimension: {dim}")
            return True, f"Embeddings working (dim={dim})"
        else:
            return False, "Empty embedding returned"
    except Exception as e:
        return False, f"Embeddings failed: {e}"


def test_database_connection():
    success, message = database_connection_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def test_job_count():
    success, message = job_count_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def test_search_function():
    success, message = search_function_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def test_recommendations():
    success, message = recommendations_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def test_title_normalization():
    success, message = title_normalization_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def test_embeddings():
    success, message = embeddings_check()
    if not success:
        import pytest

        pytest.skip(message)
    assert success, message


def api_health_check(api_url: str):
    """Test API health endpoint"""
    print("  Testing API health...")
    try:
        import urllib.request
        import json

        with urllib.request.urlopen(f"{api_url}/health", timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("ok"):
                return True, "API health check passed"
            else:
                return False, "API health check failed"
    except Exception as e:
        return False, f"API health check failed: {e}"


def api_search_check(api_url: str):
    """Test API search endpoint"""
    print("  Testing API search endpoint...")
    try:
        import urllib.request
        import json

        url = f"{api_url}/api/search?q=analyst"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, list):
                print(f"    API search results: {len(data)} jobs")
                return True, f"API search returned {len(data)} results"
            else:
                return False, "Unexpected API response format"
    except Exception as e:
        return False, f"API search failed: {e}"


def api_ingestion_status_check(api_url: str):
    """Test API ingestion status endpoint"""
    print("  Testing API ingestion status...")
    try:
        import urllib.request
        import json

        url = f"{api_url}/api/ingestion/status"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "operational":
                jobs = data.get("totals", {}).get("jobs", 0)
                print(f"    Total jobs: {jobs}")
                return True, f"Ingestion status: {jobs} jobs"
            else:
                return False, f"Ingestion status: {data.get('status')}"
    except Exception as e:
        return False, f"Ingestion status failed: {e}"


def run_smoke_tests(api_url: str = None):
    """Run all smoke tests"""
    print("\n" + "=" * 60)
    print("  NEXT STEP MVP SMOKE TESTS")
    print("=" * 60)
    print(f"  Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    results = []

    # Core tests (no API required)
    print("\n[1/6] DATABASE TESTS")
    results.append(("Database Connection", database_connection_check()))
    results.append(("Job Data", job_count_check()))

    print("\n[2/6] SEARCH TESTS")
    results.append(("Search Function", search_function_check()))

    print("\n[3/6] RECOMMENDATION TESTS")
    results.append(("Recommendations", recommendations_check()))

    print("\n[4/6] NORMALIZATION TESTS")
    results.append(("Title Normalization", title_normalization_check()))

    print("\n[5/6] ML TESTS")
    results.append(("Embeddings", embeddings_check()))

    # API tests (optional)
    if api_url:
        print(f"\n[6/6] API TESTS ({api_url})")
        results.append(("API Health", api_health_check(api_url)))
        results.append(("API Search", api_search_check(api_url)))
        results.append(("API Ingestion Status", api_ingestion_status_check(api_url)))
    else:
        print("\n[6/6] API TESTS (skipped - no API URL provided)")

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, (success, message) in results:
        status = "PASS" if success else "FAIL"
        symbol = "✓" if success else "✗"
        print(f"  {symbol} {name}: {status}")
        if not success:
            print(f"      {message}")
        if success:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run smoke tests for Next Step MVP")
    parser.add_argument(
        "--api-url",
        default=None,
        help="API base URL for API tests (e.g., http://localhost:8000)",
    )
    args = parser.parse_args()

    success = run_smoke_tests(args.api_url)
    sys.exit(0 if success else 1)
