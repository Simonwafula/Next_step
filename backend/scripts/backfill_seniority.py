#!/usr/bin/env python3
"""
Backfill seniority data for existing jobs.

This script extracts seniority level from job titles and descriptions
for jobs that don't have seniority data.

Usage:
    python scripts/backfill_seniority.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_seniority(title: str, description: str) -> Optional[str]:
    """
    Extract seniority level from title and description.

    Returns one of: 'entry', 'mid', 'senior', 'management', 'executive', or None
    """
    combined_text = f"{title or ''} {description or ''}".lower()

    # Order matters - check more specific patterns first
    seniority_patterns = {
        "executive": [
            "chief ",
            "ceo",
            "cfo",
            "cto",
            "coo",
            "cio",
            "c-level",
            "c level",
            "executive director",
            "managing director",
            "vice president",
            "vp ",
            " vp,",
            "president",
            "chairman",
            "chairperson",
        ],
        "management": [
            "manager",
            "supervisor",
            "superintendent",
            "team lead",
            "team leader",
            "lead ",
            " lead,",
            "head of",
            "head,",
            "head -",
            "coordinator",
            "principal officer",
            "director",
            "assistant director",
            "deputy director",
        ],
        "senior": [
            "senior ",
            "sr.",
            "sr ",
            "snr ",
            "principal",
            "staff ",
            "lead developer",
            "lead engineer",
            "specialist",
            "expert",
            "architect",
        ],
        "entry": [
            "entry level",
            "entry-level",
            "entrylevel",
            "junior ",
            "jr.",
            "jr ",
            "graduate",
            "trainee",
            "intern",
            "internship",
            "attachment",
            "apprentice",
            "fresh graduate",
            "recent graduate",
            "assistant ",
            "associate ",
        ],
        "mid": [
            "mid level",
            "mid-level",
            "midlevel",
            "intermediate",
            "experienced",
            # Generic officer/analyst without senior/junior qualifier
            "officer",
            "analyst",
            "accountant",
            "engineer",
            "developer",
        ],
    }

    # Check patterns in order of specificity
    for seniority in ["executive", "management", "senior", "entry", "mid"]:
        patterns = seniority_patterns[seniority]
        for pattern in patterns:
            if pattern in combined_text:
                return seniority

    return None


def is_real_job_title(title: str) -> bool:
    """
    Check if a title looks like a real job posting vs navigation/document.

    Returns False for:
    - Generic page titles (Careers, Vacancies, Downloads)
    - Document titles (Order Paper, Hansard, Circular)
    - Navigation items (Website, Portal, Login)
    - Technical/system content (loading..., Skip to content)
    """
    if not title:
        return False

    title_lower = title.lower()

    # Skip generic page titles and non-job content
    skip_patterns = [
        "vacanc",
        "careers page",
        "career opportunit",
        "downloads",
        "promotions",
        "order paper",
        "hansard",
        "circular",
        "committee",
        "website",
        "portal",
        "login",
        "form 1j",
        "composition",
        "job description page",
        "recruitment and selection",
        "advertised posts",
        "faqs",
        "active promotion",
        "current advert",
        "track advert",
        "reset grid",
        "job posting",
        "job openings",
        "loading",
        "skip to content",
        "shortlist",
        "interview schedule",
        "tender",
        "addendum",
        "notice",
        "constitution",
        "published by",
        "county government of",
        "county assembly",
        "county public service",
        "investment opportunit",
        "internship/attachment",
        "membership",
        "read notice",
        "download",
        "view detail",
        "e-recruitment",
        "job adverts",
        "job advert archive",
        "public appointments",
        "appointm",
        "insurance advert",
        "gorvenor",
        "hon.",
        "mca.",
        "tenders",
        "clearance certificate",
        "leave form",
        "bio data",
        "spas form",
        "hr manual",
        "finance bill",
        "application form",
    ]

    for pattern in skip_patterns:
        if pattern in title_lower:
            return False

    # Must have some substantive content (not just "Jobs" or similar)
    if len(title) < 15:
        return False

    # Should look like a job title - contain job-related keywords
    job_indicators = [
        "officer",
        "manager",
        "director",
        "assistant",
        "analyst",
        "engineer",
        "developer",
        "accountant",
        "specialist",
        "coordinator",
        "supervisor",
        "technician",
        "nurse",
        "doctor",
        "teacher",
        "clerk",
        "secretary",
        "administrator",
        "executive",
        "consultant",
        "driver",
        "mechanic",
        "plumber",
        "electrician",
        "technologist",
        "sales",
        "marketing",
        "finance",
        "legal",
        "medical",
        "chief officer",
        "municipal manager",
        "registrar",
        "auditor",
    ]

    has_job_indicator = any(ind in title_lower for ind in job_indicators)

    return has_job_indicator


def backfill_seniority(dry_run: bool = False):
    """Backfill seniority data for existing jobs."""
    from app.db.database import SessionLocal
    from app.db.models import JobPost

    db = SessionLocal()
    try:
        # Get jobs without seniority that have title or description
        jobs_without_seniority = (
            db.query(JobPost).filter(JobPost.seniority.is_(None)).all()
        )

        print(f"Found {len(jobs_without_seniority)} jobs without seniority")

        # Filter to only real job titles
        real_jobs = [
            j for j in jobs_without_seniority if is_real_job_title(j.title_raw)
        ]
        print(f"Of those, {len(real_jobs)} have real job titles")

        updated_count = 0
        seniority_counts = {
            "entry": 0,
            "mid": 0,
            "senior": 0,
            "management": 0,
            "executive": 0,
        }

        for job in real_jobs:
            seniority = extract_seniority(
                job.title_raw or "", job.description_raw or ""
            )

            if seniority:
                seniority_counts[seniority] += 1
                if not dry_run:
                    job.seniority = seniority
                    updated_count += 1
                else:
                    if updated_count < 10:  # Show first 10 examples
                        print(
                            f"  Would update job {job.id}: {(job.title_raw or '')[:50]}... -> {seniority}"
                        )

        if not dry_run:
            db.commit()
            print(f"\nUpdated {updated_count} jobs with seniority")
        else:
            print(f"\n[DRY RUN] Would update {sum(seniority_counts.values())} jobs")

        print("\nSeniority distribution:")
        for level, count in sorted(seniority_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {level}: {count}")

        # Show final stats
        jobs_with_seniority = (
            db.query(JobPost).filter(JobPost.seniority.isnot(None)).count()
        )

        total_jobs = db.query(JobPost).count()
        print(
            f"\nSeniority coverage: {jobs_with_seniority}/{total_jobs} ({jobs_with_seniority / total_jobs * 100:.1f}%)"
        )

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill seniority data for existing jobs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    backfill_seniority(dry_run=args.dry_run)
