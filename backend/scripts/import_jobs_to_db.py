#!/usr/bin/env python3
"""
Import Script: JSON → PostgreSQL/SQLite Database

Imports jobs_export.json into the Next Step database.
Run on VPS after uploading JSON file.

Usage:
  python scripts/import_jobs_to_db.py --input data/migration/jobs_export.json

Environment:
  DATABASE_URL - PostgreSQL connection string (production)
  Or uses local SQLite if not set
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from sqlalchemy import create_engine, text

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    print("Error: SQLAlchemy not installed. Run: pip install sqlalchemy")
    sys.exit(1)


def iter_json_array(fp, *, chunk_size: int = 1024 * 1024):
    """Yield objects from a top-level JSON array without loading the entire file.

    The migration file can be hundreds of MB; json.load(...) builds the full
    Python list and can OOM on small VPS machines. This streaming decoder keeps
    memory bounded.
    """

    decoder = json.JSONDecoder()
    buf = ""
    idx = 0

    def read_more() -> bool:
        nonlocal buf
        chunk = fp.read(chunk_size)
        if not chunk:
            return False
        buf += chunk
        return True

    # Seek the initial '['
    while True:
        if idx >= len(buf) and not read_more():
            raise ValueError("Unexpected EOF while looking for '['")

        while idx < len(buf) and buf[idx].isspace():
            idx += 1

        if idx < len(buf):
            if buf[idx] != "[":
                raise ValueError("Expected '[' at start of JSON array")
            idx += 1
            break

    while True:
        # Skip whitespace and commas between elements.
        while True:
            if idx >= len(buf) and not read_more():
                raise ValueError("Unexpected EOF inside JSON array")

            while idx < len(buf) and buf[idx].isspace():
                idx += 1

            if idx < len(buf) and buf[idx] == ",":
                idx += 1
                continue

            break

        if idx >= len(buf):
            continue

        if buf[idx] == "]":
            return

        # Decode one element; read more data if needed.
        while True:
            try:
                obj, end = decoder.raw_decode(buf, idx)
                idx = end
                yield obj

                # Compact buffer periodically to avoid unbounded growth.
                if idx > chunk_size:
                    buf = buf[idx:]
                    idx = 0
                break
            except json.JSONDecodeError:
                if not read_more():
                    raise


def parse_args():
    parser = argparse.ArgumentParser(description="Import jobs into database")
    parser.add_argument(
        "--input", type=str, required=True, help="Path to jobs_export.json"
    )
    parser.add_argument(
        "--batch-size", type=int, default=500, help="Batch size for inserts"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate without importing"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip URLs that already exist in job_post (default)",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Do not skip existing URLs (allow ON CONFLICT updates)",
    )
    parser.set_defaults(skip_existing=True)
    return parser.parse_args()


def get_database_url():
    """Get database URL from environment or use local SQLite."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("Using DATABASE_URL from environment (PostgreSQL)")
        return db_url

    local_db = Path(__file__).parent.parent / "var" / "nextstep.sqlite"
    local_db.parent.mkdir(parents=True, exist_ok=True)
    print(f"Using local SQLite: {local_db}")
    return f"sqlite:///{local_db}"


def create_tables_if_needed(engine):
    """Create tables if they don't exist."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS organization (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE,
        sector VARCHAR(100),
        ats VARCHAR(100),
        verified BOOLEAN DEFAULT FALSE
    );
    
    CREATE TABLE IF NOT EXISTS location (
        id SERIAL PRIMARY KEY,
        country VARCHAR(100),
        region VARCHAR(100),
        city VARCHAR(100),
        raw VARCHAR(255)
    );
    
    CREATE TABLE IF NOT EXISTS title_norm (
        id SERIAL PRIMARY KEY,
        family VARCHAR(120),
        canonical_title VARCHAR(120),
        aliases JSONB DEFAULT '{}'
    );
    
    CREATE TABLE IF NOT EXISTS job_post (
        id SERIAL PRIMARY KEY,
        source VARCHAR(120) NOT NULL,
        url TEXT UNIQUE NOT NULL,
        source_url TEXT,
        application_url TEXT,
        url_hash VARCHAR(32),
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        repost_count INTEGER DEFAULT 0,
        org_id INTEGER REFERENCES organization(id),
        title_raw VARCHAR(255),
        title_norm_id INTEGER REFERENCES title_norm(id),
        location_id INTEGER REFERENCES location(id),
        tenure VARCHAR(50),
        salary_min FLOAT,
        salary_max FLOAT,
        currency VARCHAR(10),
        seniority VARCHAR(50),
        description_raw TEXT,
        description_clean TEXT,
        requirements_raw TEXT,
        education VARCHAR(120),
        attachment_flag BOOLEAN DEFAULT FALSE,
        quality_score FLOAT,
        processed_at TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );
    
    CREATE INDEX IF NOT EXISTS idx_job_post_url_hash ON job_post(url_hash);
    CREATE INDEX IF NOT EXISTS idx_job_post_title_raw ON job_post(title_raw);
    CREATE INDEX IF NOT EXISTS idx_job_post_is_active ON job_post(is_active);
    CREATE INDEX IF NOT EXISTS idx_organization_name ON organization(name);
    """

    sqlite_create_sql = """
    CREATE TABLE IF NOT EXISTS organization (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        sector TEXT,
        ats TEXT,
        verified INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS location (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT,
        region TEXT,
        city TEXT,
        raw TEXT
    );
    
    CREATE TABLE IF NOT EXISTS title_norm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family TEXT,
        canonical_title TEXT,
        aliases TEXT DEFAULT '{}'
    );
    
    CREATE TABLE IF NOT EXISTS job_post (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        source_url TEXT,
        application_url TEXT,
        url_hash TEXT,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        repost_count INTEGER DEFAULT 0,
        org_id INTEGER REFERENCES organization(id),
        title_raw TEXT,
        title_norm_id INTEGER REFERENCES title_norm(id),
        location_id INTEGER REFERENCES location(id),
        tenure TEXT,
        salary_min REAL,
        salary_max REAL,
        currency TEXT,
        seniority TEXT,
        description_raw TEXT,
        description_clean TEXT,
        requirements_raw TEXT,
        education TEXT,
        attachment_flag INTEGER DEFAULT 0,
        quality_score REAL,
        processed_at TIMESTAMP,
        is_active INTEGER DEFAULT 1
    );
    
    CREATE INDEX IF NOT EXISTS idx_job_post_url_hash ON job_post(url_hash);
    CREATE INDEX IF NOT EXISTS idx_job_post_is_active ON job_post(is_active);
    """

    is_sqlite = "sqlite" in str(engine.url)
    sql = sqlite_create_sql if is_sqlite else create_sql

    with engine.connect() as conn:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"Warning: {e}")
        conn.commit()

    print("Tables verified/created")


_ORG_CACHE: dict[str, int] = {}
_LOC_CACHE: dict[tuple[str, str, str, str], int] = {}


def get_or_create_org(conn, name: str) -> int | None:
    """Get or create organization, return ID."""
    if not name:
        return None

    is_sqlite = "sqlite" in str(conn.engine.url)
    name = name.strip()[:255]

    cached = _ORG_CACHE.get(name)
    if cached is not None:
        return cached

    if is_sqlite:
        result = conn.execute(
            text("SELECT id FROM organization WHERE name = :name"), {"name": name}
        ).fetchone()

        if result:
            _ORG_CACHE[name] = result[0]
            return result[0]

        result = conn.execute(
            # Explicitly set verified to avoid NOT NULL issues if the table
            # was created via migrations (no server default).
            text("INSERT INTO organization (name, verified) VALUES (:name, 0)"),
            {"name": name},
        )
        org_id = result.lastrowid
        if org_id is not None:
            _ORG_CACHE[name] = org_id
        return org_id
    else:
        result = conn.execute(
            text("""
                INSERT INTO organization (name, verified) 
                VALUES (:name, FALSE)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """),
            {"name": name},
        ).fetchone()
        org_id = result[0] if result else None
        if org_id is not None:
            _ORG_CACHE[name] = org_id
        return org_id


def get_or_create_location(
    conn, country: str, region: str, city: str, raw: str
) -> int | None:
    """Get or create location, return ID."""
    if not any([country, region, city, raw]):
        return None

    is_sqlite = "sqlite" in str(conn.engine.url)

    country_norm = (country or "").strip()[:100]
    region_norm = (region or "").strip()[:100]
    city_norm = (city or "").strip()[:100]
    raw_norm = (raw or "").strip()[:255]
    cache_key = (country_norm, region_norm, city_norm, raw_norm)

    cached = _LOC_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if is_sqlite:
        result = conn.execute(
            text("""
                SELECT id FROM location 
                WHERE COALESCE(country, '') = COALESCE(:country, '')
                AND COALESCE(region, '') = COALESCE(:region, '')
                AND COALESCE(city, '') = COALESCE(:city, '')
                AND COALESCE(raw, '') = COALESCE(:raw, '')
                LIMIT 1
            """),
            {
                "country": country_norm,
                "region": region_norm,
                "city": city_norm,
                "raw": raw_norm,
            },
        ).fetchone()

        if result:
            _LOC_CACHE[cache_key] = result[0]
            return result[0]

        result = conn.execute(
            text(
                "INSERT INTO location (country, region, city, raw) VALUES (:country, :region, :city, :raw)"
            ),
            {
                "country": country_norm or None,
                "region": region_norm or None,
                "city": city_norm or None,
                "raw": raw_norm or None,
            },
        )
        loc_id = result.lastrowid
        if loc_id is not None:
            _LOC_CACHE[cache_key] = loc_id
        return loc_id
    else:
        # The production schema does NOT enforce uniqueness on location fields,
        # so ON CONFLICT is ineffective. Do a SELECT first to avoid ballooning
        # the location table with duplicates.
        result = conn.execute(
            text("""
                SELECT id FROM location 
                WHERE COALESCE(country, '') = COALESCE(:country, '')
                AND COALESCE(region, '') = COALESCE(:region, '')
                AND COALESCE(city, '') = COALESCE(:city, '')
                AND COALESCE(raw, '') = COALESCE(:raw, '')
                LIMIT 1
            """),
            {
                "country": country_norm,
                "region": region_norm,
                "city": city_norm,
                "raw": raw_norm,
            },
        ).fetchone()
        if result:
            _LOC_CACHE[cache_key] = result[0]
            return result[0]

        result = conn.execute(
            text("""
                INSERT INTO location (country, region, city, raw) 
                VALUES (:country, :region, :city, :raw)
                RETURNING id
            """),
            {
                "country": country_norm or None,
                "region": region_norm or None,
                "city": city_norm or None,
                "raw": raw_norm or None,
            },
        ).fetchone()

        loc_id = result[0] if result else None
        if loc_id is not None:
            _LOC_CACHE[cache_key] = loc_id
        return loc_id


def import_job(conn, job: dict, skip_existing: bool = True) -> tuple[bool, str]:
    """Import a single job. Returns (success, message)."""
    url = job.get("url")
    if not url:
        return False, "No URL"

    is_sqlite = "sqlite" in str(conn.engine.url)

    if skip_existing:
        existing = conn.execute(
            text("SELECT id FROM job_post WHERE url = :url"), {"url": url}
        ).fetchone()

        if existing:
            return False, "Already exists"

    org_id = get_or_create_org(conn, job.get("organization_name"))

    location_id = get_or_create_location(
        conn,
        job.get("location_country"),
        job.get("location_region"),
        job.get("location_city"),
        job.get("location_raw"),
    )

    first_seen = job.get("first_seen")
    if isinstance(first_seen, str):
        try:
            first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        except ValueError:
            first_seen = datetime.utcnow()
    else:
        first_seen = datetime.utcnow()

    last_seen = job.get("last_seen")
    if isinstance(last_seen, str):
        try:
            last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        except ValueError:
            last_seen = datetime.utcnow()
    else:
        last_seen = datetime.utcnow()

    title_raw = (job.get("title_raw") or "").strip()[:255]

    # Production schema requires a non-null attachment_flag, but the migration
    # JSON does not include it.
    attachment_flag = bool(job.get("attachment_flag") or False)

    if is_sqlite:
        insert_sql = text("""
            INSERT INTO job_post (
                source, url, source_url, application_url, url_hash,
                first_seen, last_seen, repost_count, org_id, title_raw, location_id,
                tenure, salary_min, salary_max, currency, seniority, attachment_flag,
                description_raw, education, is_active
            ) VALUES (
                :source, :url, :source_url, :application_url, :url_hash,
                :first_seen, :last_seen, :repost_count, :org_id, :title_raw, :location_id,
                :tenure, :salary_min, :salary_max, :currency, :seniority, :attachment_flag,
                :description_raw, :education, :is_active
            )
        """)
    else:
        insert_sql = text("""
            INSERT INTO job_post (
                source, url, source_url, application_url, url_hash,
                first_seen, last_seen, repost_count, org_id, title_raw, location_id,
                tenure, salary_min, salary_max, currency, seniority, attachment_flag,
                description_raw, education, is_active
            ) VALUES (
                :source, :url, :source_url, :application_url, :url_hash,
                :first_seen, :last_seen, :repost_count, :org_id, :title_raw, :location_id,
                :tenure, :salary_min, :salary_max, :currency, :seniority, :attachment_flag,
                :description_raw, :education, :is_active
            )
            ON CONFLICT (url) DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                repost_count = job_post.repost_count + 1
        """)

    conn.execute(
        insert_sql,
        {
            "source": job.get("source", "migration"),
            "url": url,
            "source_url": job.get("source_url"),
            "application_url": job.get("application_url"),
            "url_hash": job.get("url_hash"),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "repost_count": 0,
            "org_id": org_id,
            "title_raw": title_raw,
            "location_id": location_id,
            "tenure": (job.get("tenure") or None)[:50]
            if isinstance(job.get("tenure"), str)
            else job.get("tenure"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "currency": (job.get("currency") or "KES")[:10],
            "seniority": (job.get("seniority") or None)[:50]
            if isinstance(job.get("seniority"), str)
            else job.get("seniority"),
            "attachment_flag": attachment_flag,
            "description_raw": job.get("description_raw"),
            "education": (job.get("education") or None)[:120]
            if isinstance(job.get("education"), str)
            else job.get("education"),
            "is_active": True,
        },
    )

    return True, "Imported"


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    print(f"Loading jobs from: {input_path}")

    if args.dry_run:
        print("\nDRY RUN - Validating jobs...")
        errors = []
        with open(input_path, "r", encoding="utf-8") as f:
            jobs_iter = iter_json_array(f)
            for i, job in enumerate(jobs_iter):
                if i >= 100:
                    break
                if not job.get("url"):
                    errors.append(f"Job {i}: Missing URL")
                if not job.get("title_raw"):
                    errors.append(f"Job {i}: Missing title")

        if errors:
            print(f"Found {len(errors)} errors in first 100 jobs:")
            for err in errors[:10]:
                print(f"  - {err}")
        else:
            print("First 100 jobs look valid!")
        return

    db_url = get_database_url()
    engine = create_engine(db_url)

    create_tables_if_needed(engine)

    stats = {
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "errors": 0,
    }

    batch_size = max(1, int(args.batch_size))

    with open(input_path, "r", encoding="utf-8") as f:
        jobs_iter = iter_json_array(f)
        with engine.connect() as conn:
            for job in jobs_iter:
                stats["processed"] += 1
                try:
                    # Savepoint per job: a single bad row shouldn't poison the
                    # whole transaction (Postgres aborts the transaction on
                    # error until a rollback).
                    with conn.begin_nested():
                        success, message = import_job(conn, job, args.skip_existing)
                    if success:
                        stats["imported"] += 1
                    elif "Already exists" in message:
                        stats["skipped"] += 1
                    else:
                        stats["errors"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    if stats["errors"] <= 10:
                        print(f"  Error on job {stats['processed']}: {e}")
                    # If the outer transaction is aborted, recover so we can
                    # keep importing (may drop uncommitted work in the batch).
                    if "InFailedSqlTransaction" in str(e):
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    continue

                if stats["processed"] % batch_size == 0:
                    print(f"  Processing {stats['processed']:,}...")
                    conn.commit()

            conn.commit()

    # Use a fresh connection to avoid querying on a closed connection.
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM job_post")).fetchone()
        final_count = result[0] if result else 0

    print(f"\n{'=' * 50}")
    print("IMPORT COMPLETE")
    print(f"{'=' * 50}")
    print(f"Total jobs processed:{stats['processed']:,}")
    print(f"Imported:            {stats['imported']:,}")
    print(f"Skipped (existing):  {stats['skipped']:,}")
    print(f"Errors:              {stats['errors']:,}")
    print(f"{'=' * 50}")
    print(f"Total jobs in DB:    {final_count:,}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
