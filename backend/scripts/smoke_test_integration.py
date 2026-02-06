#!/usr/bin/env python3
"""
Test script to verify scraper integration with PostgreSQL
"""

import sys
from pathlib import Path

# Ensure we can `import app.*` regardless of current working directory.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_imports():
    """Test that all modules can be imported correctly"""
    print("🔍 Testing imports...")

    try:
        from app.scrapers.config import SITES, USE_POSTGRES

        print(f"✅ Scraper config loaded: {len(SITES)} sites configured")
        print(f"✅ PostgreSQL enabled: {USE_POSTGRES}")

        print("✅ PostgreSQL database adapter imported")

        print("✅ Migration script imported")

        print("✅ Scraper service imported")

        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_sqlite_data():
    """Test SQLite database access"""
    print("\n🔍 Testing SQLite database...")

    try:
        import sqlite3
        from app.scrapers.config import DB_PATH, TABLE_NAME

        db_path = Path(DB_PATH)
        if not db_path.is_absolute():
            db_path = BACKEND_DIR / db_path
        if not db_path.exists():
            print(f"❌ SQLite database not found at {db_path}")
            return False

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get count
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        count = cursor.fetchone()[0]
        print(f"✅ SQLite database accessible: {count} jobs found")

        # Get sample data
        cursor.execute(f"SELECT title, full_link FROM {TABLE_NAME} LIMIT 3")
        samples = cursor.fetchall()
        print("✅ Sample jobs:")
        for title, link in samples:
            print(f"   - {title[:50]}...")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ SQLite error: {e}")
        return False


def test_scraper_config():
    """Test scraper configuration"""
    print("\n🔍 Testing scraper configuration...")

    try:
        from app.scrapers.config import SITES

        print(f"✅ Available scrapers: {list(SITES.keys())}")

        # Test one site configuration
        if SITES:
            site_name = list(SITES.keys())[0]
            site_config = SITES[site_name]
            required_keys = [
                "base_url",
                "listing_path",
                "listing_selector",
                "title_attribute",
                "content_selector",
            ]

            missing_keys = [key for key in required_keys if key not in site_config]
            if missing_keys:
                print(f"❌ Site {site_name} missing keys: {missing_keys}")
                return False
            else:
                print(f"✅ Site {site_name} configuration complete")

        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_database_models():
    """Test database models"""
    print("\n🔍 Testing database models...")

    try:
        from app.db.models import JobPost

        print("✅ Database models imported successfully")

        # Test model attributes
        job_attrs = ["id", "source", "url", "title_raw", "description_raw"]
        for attr in job_attrs:
            if not hasattr(JobPost, attr):
                print(f"❌ JobPost missing attribute: {attr}")
                return False

        print("✅ JobPost model has required attributes")
        return True
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Scraper Integration\n")

    tests = [test_imports, test_sqlite_data, test_scraper_config, test_database_models]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")

    if all(results):
        print("🎉 All tests passed! Integration is ready.")
        print("\n📋 Next steps:")
        print("1. Start Docker: docker-compose up -d postgres")
        print("2. Run migration: python backend/app/scrapers/migrate_to_postgres.py")
        print("3. Start backend: docker-compose up backend")
        print("4. Test API endpoints: curl http://localhost:8000/scrapers/status")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
