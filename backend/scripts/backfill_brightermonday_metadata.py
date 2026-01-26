#!/usr/bin/env python3
"""
Backfill company and location data for BrighterMonday jobs.

BrighterMonday job descriptions contain company name and location in a
structured format at the beginning:
"[Job Title] [Company Name] [Category] [Date] ... [Location] Full Time ..."

This script extracts this metadata from descriptions.

Usage:
    python scripts/backfill_brightermonday_metadata.py [--dry-run]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Common Kenyan cities/locations
KENYAN_LOCATIONS = [
    "Nairobi",
    "Mombasa",
    "Kisumu",
    "Nakuru",
    "Eldoret",
    "Thika",
    "Malindi",
    "Kitale",
    "Garissa",
    "Nyeri",
    "Machakos",
    "Meru",
    "Lamu",
    "Nanyuki",
    "Kakamega",
    "Kisii",
    "Kericho",
    "Naivasha",
    "Embu",
    "Isiolo",
    "Kenya",
    "Remote",
    "Hybrid",
    "Work From Home",
    "WFH",
]

# Company suffixes to help identify company names
COMPANY_SUFFIXES = [
    "Ltd",
    "Limited",
    "LTD",
    "LIMITED",
    "Inc",
    "INC",
    "Incorporated",
    "Co",
    "CO",
    "Company",
    "Corp",
    "Corporation",
    "PLC",
    "Plc",
    "Group",
    "GROUP",
    "Services",
    "SERVICES",
    "Solutions",
    "SOLUTIONS",
    "Enterprises",
    "ENTERPRISES",
    "Kenya",
    "KENYA",
    "Africa",
    "AFRICA",
    "International",
    "INTERNATIONAL",
]


def extract_company_from_description(description: str, title: str) -> Optional[str]:
    """
    Extract company name from BrighterMonday description format.

    Format: "[Job Title] [Company Name] [Category] [Date]..."
    Example: "Sales Executive Safety Hub Company Ltd Sales 3 days ago..."
    """
    if not description:
        return None

    # Get the first 500 chars for analysis
    header = description[:500]

    # Try to find company name after the job title
    # Pattern: title followed by company name (ending with Ltd, Limited, etc.)
    for suffix in COMPANY_SUFFIXES:
        # Look for pattern: "Title CompanyName Suffix"
        pattern = rf"{re.escape(title)}\s+(.+?\s+{re.escape(suffix)})\b"
        match = re.search(pattern, header, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up - remove category words that might be included
            company = re.sub(
                r"\s+(Sales|Marketing|IT|HR|Finance|Admin|Engineering)\s*$",
                "",
                company,
                flags=re.IGNORECASE,
            )
            if len(company) > 3 and len(company) < 100:
                return company

    # Alternative: look for company suffixes in the header
    for suffix in COMPANY_SUFFIXES:
        pattern = rf"([A-Z][A-Za-z\s&\-\.]+\s+{re.escape(suffix)})\b"
        match = re.search(pattern, header)
        if match:
            company = match.group(1).strip()
            # Skip if it's the title
            if company.lower() != title.lower() and len(company) > 3:
                return company

    return None


def extract_location_from_description(description: str) -> Optional[str]:
    """
    Extract location from BrighterMonday description.

    Format: "... [Location] Full Time [Industry] ..."
    Example: "... Nairobi Full Time Manufacturing & Warehousing ..."
    """
    if not description:
        return None

    # Get first 500 chars
    header = description[:500]

    # Look for known Kenyan locations
    for location in KENYAN_LOCATIONS:
        # Location typically appears before "Full Time" or "Part Time"
        pattern = (
            rf"\b({re.escape(location)})\s+(?:Full\s*Time|Part\s*Time|Contract|Remote)"
        )
        match = re.search(pattern, header, re.IGNORECASE)
        if match:
            return location

    # Fallback: just look for the location name
    for location in KENYAN_LOCATIONS:
        if location.lower() in header.lower():
            return location

    return None


def backfill_brightermonday_metadata(dry_run: bool = False):
    """Backfill company and location for BrighterMonday jobs."""
    from app.db.database import SessionLocal
    from app.db.models import JobPost, Organization, Location

    db = SessionLocal()
    try:
        # Get BrighterMonday jobs with descriptions but missing org/location
        jobs = (
            db.query(JobPost)
            .filter(
                JobPost.source == "brightermonday",
                JobPost.description_raw.isnot(None),
                JobPost.description_raw != "",
            )
            .all()
        )

        print(f"Found {len(jobs)} BrighterMonday jobs with descriptions")

        company_updated = 0
        location_updated = 0
        companies_found = {}
        locations_found = {}

        for job in jobs:
            updates_made = False

            # Extract company if missing
            if not job.org_id:
                company_name = extract_company_from_description(
                    job.description_raw, job.title_raw or ""
                )
                if company_name:
                    companies_found[company_name] = (
                        companies_found.get(company_name, 0) + 1
                    )

                    if not dry_run:
                        # Get or create organization
                        org = (
                            db.query(Organization)
                            .filter(Organization.name == company_name)
                            .first()
                        )
                        if not org:
                            org = Organization(name=company_name, verified=False)
                            db.add(org)
                            db.flush()
                        job.org_id = org.id
                        updates_made = True
                    company_updated += 1

            # Extract location if missing
            if not job.location_id:
                location_name = extract_location_from_description(job.description_raw)
                if location_name:
                    locations_found[location_name] = (
                        locations_found.get(location_name, 0) + 1
                    )

                    if not dry_run:
                        # Get or create location
                        loc = (
                            db.query(Location)
                            .filter(
                                Location.country == "Kenya",
                                Location.city == location_name,
                            )
                            .first()
                        )
                        if not loc:
                            loc = Location(
                                country="Kenya", city=location_name, raw=location_name
                            )
                            db.add(loc)
                            db.flush()
                        job.location_id = loc.id
                        updates_made = True
                    location_updated += 1

        if not dry_run:
            db.commit()
            print(f"\nUpdated {company_updated} jobs with company")
            print(f"Updated {location_updated} jobs with location")
        else:
            print(f"\n[DRY RUN] Would update {company_updated} jobs with company")
            print(f"[DRY RUN] Would update {location_updated} jobs with location")

        # Show top companies found
        if companies_found:
            print(f"\nTop companies found:")
            for company, count in sorted(companies_found.items(), key=lambda x: -x[1])[
                :10
            ]:
                print(f"  {company}: {count}")

        # Show locations found
        if locations_found:
            print(f"\nLocations found:")
            for loc, count in sorted(locations_found.items(), key=lambda x: -x[1]):
                print(f"  {loc}: {count}")

        # Final stats
        jobs_with_org = (
            db.query(JobPost)
            .filter(JobPost.source == "brightermonday", JobPost.org_id.isnot(None))
            .count()
        )
        jobs_with_loc = (
            db.query(JobPost)
            .filter(JobPost.source == "brightermonday", JobPost.location_id.isnot(None))
            .count()
        )
        total_bm = db.query(JobPost).filter(JobPost.source == "brightermonday").count()

        print(f"\nBrighterMonday coverage:")
        print(
            f"  With organization: {jobs_with_org}/{total_bm} ({jobs_with_org / total_bm * 100:.1f}%)"
        )
        print(
            f"  With location: {jobs_with_loc}/{total_bm} ({jobs_with_loc / total_bm * 100:.1f}%)"
        )

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill BrighterMonday metadata")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    backfill_brightermonday_metadata(dry_run=args.dry_run)
