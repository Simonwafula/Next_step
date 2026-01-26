#!/usr/bin/env python3
"""
Backfill salary data for existing jobs.

This script extracts salary information from job descriptions
and updates jobs that don't have salary data.

Usage:
    python scripts/backfill_salary_data.py [--dry-run]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_salary_from_text(
    text: str,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extract salary information from text content.
    Returns (salary_min, salary_max, currency)

    Minimum salary threshold: 5,000 KES (very basic minimum)
    Maximum salary threshold: 50,000,000 KES (reasonable upper limit)
    """
    if not text:
        return None, None, None

    # Minimum realistic salary thresholds
    MIN_SALARY_KES = 5000  # Minimum realistic monthly salary
    MAX_SALARY_KES = 50000000  # Maximum reasonable salary
    MIN_SALARY_USD = 50  # Minimum USD salary
    MAX_SALARY_USD = 500000  # Maximum reasonable USD salary

    # Salary patterns for Kenyan job postings - ordered by specificity
    patterns = [
        # Kenyan format with /= suffix: Kshs. 157,427 – Kshs. 234,431/=
        (
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)(?:/=)?\s*[-–to]+\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)(?:/=)?",
            "KES",
            False,
        ),
        # K notation range: KES 80k-120k (requires 'k' after number)
        (
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d+)\s*k\s*[-–to]+\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*(\d+)\s*k",
            "KES",
            True,
        ),
        # Standard KSH range: KSH 50,000 - 100,000 (require comma for larger numbers)
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)\s*[-–to]+\s*([\d,]+)", "KES", False),
        # Salary range pattern: "salary of between X and Y"
        (
            r"salary\s+(?:of\s+)?(?:between\s+)?(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)\s*(?:and|to|-|–)\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)",
            "KES",
            False,
        ),
        # Single Kenyan value with /= suffix (more specific - must have /=)
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)/=", "KES", False),
        # K notation single with explicit 'k': KES 80k
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d+)\s*k\b", "KES", True),
        # USD range
        (r"\$\s*([\d,]+)\s*[-–to]+\s*\$?\s*([\d,]+)", "USD", False),
        # "Salary: X to Y" format (requires explicit "salary" keyword)
        (r"salary[:\s]+([\d,]+)\s*[-–to]+\s*([\d,]+)", "KES", False),
        # "Salary: X" format with comma (requires comma for validity)
        (r"salary[:\s]+([\d,]+)", "KES", False),
        # "X per month" format (requires comma for larger numbers)
        (r"([\d,]+)\s*(?:per|/)\s*month", "KES", False),
        # Annual salary format
        (r"([\d,]+)\s*(?:per|/)\s*(?:year|annum|p\.a\.)", "KES", False),
    ]

    def clean_value(val: str) -> float:
        cleaned = val.replace(" ", "").replace(",", "").replace("/=", "")
        return float(cleaned)

    def is_valid_salary(val: float, currency: str) -> bool:
        """Check if salary value is within reasonable bounds."""
        if currency == "USD":
            return MIN_SALARY_USD <= val <= MAX_SALARY_USD
        else:  # KES
            return MIN_SALARY_KES <= val <= MAX_SALARY_KES

    for pattern, currency, is_k_notation in patterns:
        # Use case-insensitive search
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) >= 2 and groups[1]:
                    # Range
                    val1 = clean_value(groups[0])
                    val2 = clean_value(groups[1])
                    if is_k_notation:
                        val1 *= 1000
                        val2 *= 1000
                    # Sanity check - both values should be reasonable
                    if is_valid_salary(val1, currency) and is_valid_salary(
                        val2, currency
                    ):
                        return min(val1, val2), max(val1, val2), currency
                elif len(groups) >= 1 and groups[0]:
                    # Single value
                    val = clean_value(groups[0])
                    if is_k_notation:
                        val *= 1000
                    # Sanity check
                    if is_valid_salary(val, currency):
                        return val, val, currency
            except (ValueError, AttributeError):
                continue

    return None, None, None


def extract_seniority_from_text(title: str, description: str) -> Optional[str]:
    """Extract seniority level from title and description."""
    combined_text = f"{title} {description}".lower()

    seniority_mapping = {
        "entry": [
            "entry level",
            "entry-level",
            "junior",
            "graduate",
            "trainee",
            "intern",
            "attachment",
        ],
        "mid": ["mid level", "mid-level", "intermediate", "experienced"],
        "senior": ["senior", "lead", "principal", "sr.", "sr "],
        "management": ["manager", "supervisor", "team lead", "head of", "head,"],
        "executive": ["director", "executive", "c-level", "ceo", "cfo", "cto", "chief"],
    }

    for seniority, keywords in seniority_mapping.items():
        for keyword in keywords:
            if keyword in combined_text:
                return seniority

    return None


def backfill_salary_data(dry_run: bool = False):
    """Backfill salary data for existing jobs."""
    from app.db.database import SessionLocal
    from app.db.models import JobPost

    db = SessionLocal()
    try:
        # Get jobs without salary data that have descriptions
        jobs_without_salary = (
            db.query(JobPost)
            .filter(
                JobPost.salary_min.is_(None),
                JobPost.description_raw.isnot(None),
                JobPost.description_raw != "",
            )
            .all()
        )

        print(f"Found {len(jobs_without_salary)} jobs without salary data")

        updated_count = 0
        salary_found_count = 0

        for job in jobs_without_salary:
            salary_min, salary_max, currency = extract_salary_from_text(
                job.description_raw or ""
            )
            seniority = extract_seniority_from_text(
                job.title_raw or "", job.description_raw or ""
            )

            updates_made = False

            if salary_min is not None:
                salary_found_count += 1
                if not dry_run:
                    job.salary_min = salary_min
                    job.salary_max = salary_max
                    job.currency = currency
                    updates_made = True
                else:
                    print(f"  Would update job {job.id}: {job.title_raw[:50]}...")
                    print(
                        f"    Salary: {currency} {salary_min:,.0f} - {salary_max:,.0f}"
                    )

            if seniority and not job.seniority:
                if not dry_run:
                    job.seniority = seniority
                    updates_made = True

            if updates_made:
                updated_count += 1

        if not dry_run:
            db.commit()
            print(f"\nUpdated {updated_count} jobs")
            print(f"Found salary data in {salary_found_count} jobs")
        else:
            print(
                f"\n[DRY RUN] Would update {salary_found_count} jobs with salary data"
            )

        # Show final stats
        jobs_with_salary = (
            db.query(JobPost).filter(JobPost.salary_min.isnot(None)).count()
        )

        total_jobs = db.query(JobPost).count()
        print(
            f"\nSalary coverage: {jobs_with_salary}/{total_jobs} ({jobs_with_salary / total_jobs * 100:.1f}%)"
        )

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill salary data for existing jobs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    backfill_salary_data(dry_run=args.dry_run)
