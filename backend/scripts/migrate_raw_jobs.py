#!/usr/bin/env python3
"""
Migration Script: Raw SQLite → App Database Format

Reads from jobs.sqlite3 (raw scraped data)
Outputs:
  1. jobs_export.json (for API upload)
  2. jobs_import.sql (for direct PostgreSQL import)

Usage:
  python scripts/migrate_raw_jobs.py [--limit N] [--output-dir ./data/migration]

Run on LOCAL machine, then upload outputs to VPS.
"""

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate raw jobs to app format")
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of jobs to process"
    )
    parser.add_argument(
        "--output-dir", type=str, default="./data/migration", help="Output directory"
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for processing"
    )
    parser.add_argument(
        "--source", type=str, default="migration", help="Source identifier"
    )
    return parser.parse_args()


def extract_organization(content: str, title: str) -> str | None:
    """Extract organization name from job content."""
    patterns = [
        r"^\s*([A-Z][A-Za-z0-9\s&'-]+(?:Ltd|Limited|Inc|Corp|Corporation|Company|Co|PLC|Group|Agency|Consulting|Partners|Foundation|Trust|University|College|Hospital|Bank|Insurance|Solutions|Services|Technologies|Tech|Systems|Enterprises|International|Global|Africa|Kenya))\s*$",
        r"^Company[:\s]+([A-Za-z0-9\s&'-]+)",
    ]

    lines = content.split("\n")
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        if not line or len(line) < 3:
            continue

        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                if (
                    org
                    and len(org) > 2
                    and org.lower() not in ["job", "new", "featured", "apply"]
                ):
                    return org

    if "|" in title:
        parts = title.split("|")
        if len(parts) > 1:
            org = parts[-1].strip()
            if org and len(org) > 2:
                return org

    return None


def extract_location(content: str) -> dict[str, str | None]:
    """Extract location information from job content."""
    result = {"country": None, "region": None, "city": None, "raw": None}

    kenyan_cities = [
        "nairobi",
        "mombasa",
        "kisumu",
        "nakuru",
        "eldoret",
        "thika",
        "malindi",
        "kitale",
        "garissa",
        "kakamega",
        "machakos",
        "nyeri",
        "kericho",
        "lamu",
        "westlands",
        "karen",
        "kilimani",
        "industrial area",
        "cbd",
        "upper hill",
    ]

    kenyan_regions = [
        "nairobi county",
        "mombasa county",
        "kisumu county",
        "nakuru county",
        "kiambu county",
        "machakos county",
        "kajiado county",
        "uasin gishu",
    ]

    outside_kenya = [
        "outside kenya",
        "qatar",
        "uae",
        "dubai",
        "saudi arabia",
        "rwanda",
        "uganda",
        "tanzania",
        "ethiopia",
        "south sudan",
        "somalia",
        "remote",
        "global",
        "international",
    ]

    content_lower = content.lower()

    for location in outside_kenya:
        if location in content_lower:
            result["raw"] = location.title()
            if location == "remote":
                result["country"] = "Kenya"
                result["city"] = "Remote"
            elif location in ["global", "international"]:
                result["country"] = "International"
            else:
                result["country"] = (
                    location.title() if location != "outside kenya" else "International"
                )
            return result

    for city in kenyan_cities:
        if city in content_lower:
            result["city"] = city.title()
            result["country"] = "Kenya"
            result["raw"] = city.title()
            return result

    for region in kenyan_regions:
        if region in content_lower:
            result["region"] = region.title()
            result["country"] = "Kenya"
            result["raw"] = region.title()
            return result

    location_patterns = [
        r"Location[:\s]+([A-Za-z\s,]+)",
        r"Based in[:\s]+([A-Za-z\s,]+)",
        r"Work Location[:\s]+([A-Za-z\s,]+)",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            result["raw"] = match.group(1).strip()
            return result

    return result


def extract_salary(content: str) -> dict[str, Any]:
    """Extract salary information from job content."""
    result = {"min": None, "max": None, "currency": "KES", "raw": None}

    if re.search(
        r"confidential|negotiable|competitive|commensurate", content, re.IGNORECASE
    ):
        result["raw"] = "Confidential"
        return result

    kes_patterns = [
        r"KES\s*([\d,]+)\s*[-–to]+\s*([\d,]+)",
        r"([\d,]+)\s*[-–]\s*([\d,]+)\s*KES",
        r"KSh\s*([\d,]+)\s*[-–to]+\s*([\d,]+)",
        r"([\d,]+)\s*[-–]\s*([\d,]+)\s*KSh",
    ]

    for pattern in kes_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            min_val = int(match.group(1).replace(",", ""))
            max_val = int(match.group(2).replace(",", ""))
            result["min"] = min_val
            result["max"] = max_val
            result["currency"] = "KES"
            result["raw"] = f"KES {min_val:,} - {max_val:,}"
            return result

    single_patterns = [
        r"KES\s*([\d,]+)",
        r"KSh\s*([\d,]+)",
    ]

    for pattern in single_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(",", "").strip()
            if val_str and val_str.isdigit():
                val = int(val_str)
                result["min"] = val
                result["max"] = val
                result["currency"] = "KES"
                result["raw"] = f"KES {val:,}"
                return result

    return result


def extract_seniority(content: str) -> str | None:
    """Extract seniority level from job content."""
    content_lower = content.lower()

    if any(
        x in content_lower
        for x in ["entry level", "internship", "graduate trainee", "fresh graduate"]
    ):
        return "entry"
    if any(x in content_lower for x in ["junior", "associate", "trainee"]):
        return "junior"
    if any(x in content_lower for x in ["senior", "lead", "principal", "head of"]):
        return "senior"
    if any(
        x in content_lower
        for x in ["manager", "director", "vp", "vice president", "chief", "executive"]
    ):
        return "executive"
    if any(x in content_lower for x in ["mid-level", "mid level", "experienced"]):
        return "mid"

    exp_match = re.search(
        r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|relevant)", content_lower
    )
    if exp_match:
        years = int(exp_match.group(1))
        if years <= 1:
            return "entry"
        elif years <= 3:
            return "junior"
        elif years <= 5:
            return "mid"
        elif years <= 10:
            return "senior"
        else:
            return "executive"

    return None


def extract_experience(content: str) -> dict[str, Any]:
    """Extract experience requirements."""
    result = {"min_years": None, "max_years": None, "raw": None}

    patterns = [
        r"(\d+)\s*[-–]\s*(\d+)\s*years?\s*(?:of\s+)?(?:experience|relevant)",
        r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|relevant)",
        r"minimum\s*(?:of\s+)?(\d+)\s*years?",
        r"at least\s*(\d+)\s*years?",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            if match.lastindex >= 2:
                result["min_years"] = int(match.group(1))
                result["max_years"] = int(match.group(2))
            else:
                result["min_years"] = int(match.group(1))
            result["raw"] = match.group(0)
            return result

    return result


def extract_education(content: str) -> str | None:
    """Extract education requirements."""
    content_lower = content.lower()

    if "phd" in content_lower or "doctorate" in content_lower:
        return "PhD"
    if (
        "master" in content_lower
        or "mba" in content_lower
        or "msc" in content_lower
        or "ma" in content_lower
    ):
        return "Master's Degree"
    if (
        "bachelor" in content_lower
        or "degree" in content_lower
        or "bsc" in content_lower
        or "ba" in content_lower
    ):
        return "Bachelor's Degree"
    if "diploma" in content_lower or "hnd" in content_lower:
        return "Diploma"
    if "certificate" in content_lower:
        return "Certificate"

    return None


def extract_tenure(content: str) -> str | None:
    """Extract employment type."""
    content_lower = content.lower()

    if "full-time" in content_lower or "full time" in content_lower:
        return "Full-time"
    if "part-time" in content_lower or "part time" in content_lower:
        return "Part-time"
    if "contract" in content_lower:
        return "Contract"
    if "internship" in content_lower or "intern" in content_lower:
        return "Internship"
    if "temporary" in content_lower:
        return "Temporary"

    return "Full-time"


def parse_posted_date(content: str) -> datetime | None:
    """Parse relative posted date."""
    content_lower = content.lower()

    if "today" in content_lower or "just now" in content_lower:
        return datetime.utcnow()

    match = re.search(r"(\d+)\s*(?:day|days|hour|hours)\s*ago", content_lower)
    if match:
        num = int(match.group(1))
        if "hour" in content_lower:
            return datetime.utcnow() - timedelta(hours=num)
        return datetime.utcnow() - timedelta(days=num)

    match = re.search(r"(\d+)\s*(?:week|weeks)\s*ago", content_lower)
    if match:
        num = int(match.group(1))
        return datetime.utcnow() - timedelta(weeks=num)

    match = re.search(r"(\d+)\s*(?:month|months)\s*ago", content_lower)
    if match:
        num = int(match.group(1))
        return datetime.utcnow() - timedelta(days=num * 30)

    return None


def generate_url_hash(url: str) -> str:
    """Generate MD5 hash of URL."""
    return hashlib.md5(url.encode()).hexdigest()


def process_job(row: tuple, source: str) -> dict[str, Any]:
    """Process a single job row into app format."""
    job_id, full_link, title, content = row

    if not title or not full_link:
        return None

    content = content or ""

    org_name = extract_organization(content, title)
    location = extract_location(content)
    salary = extract_salary(content)
    seniority = extract_seniority(content)
    experience = extract_experience(content)
    education = extract_education(content)
    tenure = extract_tenure(content)
    posted_date = parse_posted_date(content)

    job = {
        "source": source,
        "url": full_link,
        "source_url": full_link,
        "application_url": full_link,
        "url_hash": generate_url_hash(full_link),
        "title_raw": title[:255] if title else None,
        "description_raw": content,
        "organization_name": org_name,
        "location_country": location["country"],
        "location_region": location["region"],
        "location_city": location["city"],
        "location_raw": location["raw"],
        "salary_min": salary["min"],
        "salary_max": salary["max"],
        "currency": salary["currency"],
        "salary_raw": salary["raw"],
        "seniority": seniority,
        "experience_min_years": experience["min_years"],
        "experience_max_years": experience["max_years"],
        "experience_raw": experience["raw"],
        "education": education,
        "tenure": tenure,
        "first_seen": (posted_date or datetime.utcnow()).isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "is_active": True,
    }

    return job


def main():
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = Path(__file__).parent.parent.parent / "jobs.sqlite3"
    if not db_path.exists():
        db_path = Path(__file__).parent.parent / "jobs.sqlite3"
    if not db_path.exists():
        print("Error: Database not found")
        print(f"  Tried: {Path(__file__).parent.parent.parent / 'jobs.sqlite3'}")
        print(f"  Tried: {Path(__file__).parent.parent / 'jobs.sqlite3'}")
        return

    print(f"Reading from: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count_query = "SELECT COUNT(*) FROM jobs_data"
    cursor.execute(count_query)
    total_jobs = cursor.fetchone()[0]
    print(f"Total jobs in database: {total_jobs:,}")

    query = """
        SELECT id, full_link, title, content 
        FROM jobs_data 
        WHERE full_link IS NOT NULL AND title IS NOT NULL
        ORDER BY id
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    print(f"Processing {len(rows):,} jobs...")

    jobs = []
    stats = {
        "total": 0,
        "with_org": 0,
        "with_location": 0,
        "with_salary": 0,
        "with_seniority": 0,
        "with_education": 0,
        "skipped": 0,
    }

    for i, row in enumerate(rows):
        if (i + 1) % 10000 == 0:
            print(f"  Processed {i + 1:,} / {len(rows):,}...")

        job = process_job(row, args.source)
        if job:
            jobs.append(job)
            stats["total"] += 1
            if job["organization_name"]:
                stats["with_org"] += 1
            if job["location_raw"] or job["location_city"]:
                stats["with_location"] += 1
            if job["salary_raw"]:
                stats["with_salary"] += 1
            if job["seniority"]:
                stats["with_seniority"] += 1
            if job["education"]:
                stats["with_education"] += 1
        else:
            stats["skipped"] += 1

    conn.close()

    json_path = output_dir / "jobs_export.json"
    print(f"\nWriting JSON to: {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    sql_path = output_dir / "jobs_import.sql"
    print(f"Writing SQL to: {sql_path}")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- Next Step Job Import Script\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()}\n")
        f.write(f"-- Total jobs: {len(jobs):,}\n\n")
        f.write("BEGIN;\n\n")

        for job in jobs[:100]:
            f.write(
                f"-- Sample job: {job['title_raw'][:50] if job['title_raw'] else 'N/A'}...\n"
            )
            break

        f.write(f"\n-- Import {len(jobs):,} jobs\n")
        f.write("-- Run: psql -d nextstep -f jobs_import.sql\n")
        f.write("-- Or use the JSON file with the Python import script\n\n")
        f.write("COMMIT;\n")

    print(f"\n{'=' * 50}")
    print("MIGRATION STATS")
    print(f"{'=' * 50}")
    print(f"Total processed:    {stats['total']:,}")
    print(
        f"With organization:  {stats['with_org']:,} ({100 * stats['with_org'] / max(stats['total'], 1):.1f}%)"
    )
    print(
        f"With location:      {stats['with_location']:,} ({100 * stats['with_location'] / max(stats['total'], 1):.1f}%)"
    )
    print(
        f"With salary:        {stats['with_salary']:,} ({100 * stats['with_salary'] / max(stats['total'], 1):.1f}%)"
    )
    print(
        f"With seniority:     {stats['with_seniority']:,} ({100 * stats['with_seniority'] / max(stats['total'], 1):.1f}%)"
    )
    print(
        f"With education:     {stats['with_education']:,} ({100 * stats['with_education'] / max(stats['total'], 1):.1f}%)"
    )
    print(f"Skipped:            {stats['skipped']:,}")
    print(f"{'=' * 50}")
    print("\nOutput files:")
    print(f"  - {json_path} ({json_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  - {sql_path}")
    print("\nNext steps:")
    print("  1. Upload jobs_export.json to VPS")
    print("  2. Run: python scripts/import_jobs_to_db.py --input jobs_export.json")
    print("  3. Verify: SELECT COUNT(*) FROM job_post;")


if __name__ == "__main__":
    main()
