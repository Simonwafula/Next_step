#!/usr/bin/env python3
"""Backfill normalized organization and location data for existing jobs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def backfill_normalized_entities(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    orgs_only: bool = False,
    locations_only: bool = False,
) -> dict[str, int]:
    from app.db.models import JobPost, Location, Organization
    from app.normalization.companies import normalize_company_name
    from app.normalization.locations import normalize_location

    summary = {
        "organizations_scanned": 0,
        "organizations_renamed": 0,
        "organization_job_refs_repointed": 0,
        "locations_scanned": 0,
        "locations_updated": 0,
        "location_job_refs_repointed": 0,
    }

    if not locations_only:
        org_query = db.query(Organization).order_by(Organization.id.asc())
        if limit:
            org_query = org_query.limit(limit)

        for org in org_query.all():
            summary["organizations_scanned"] += 1
            normalized = normalize_company_name(org.name)
            if not normalized or normalized == org.name:
                continue

            target = (
                db.query(Organization).filter(Organization.name == normalized).one_or_none()
            )
            if target and target.id != org.id:
                moved = (
                    db.query(JobPost)
                    .filter(JobPost.org_id == org.id)
                    .update({JobPost.org_id: target.id}, synchronize_session=False)
                )
                summary["organization_job_refs_repointed"] += int(moved or 0)
                if not target.sector and org.sector:
                    target.sector = org.sector
                    db.add(target)
            else:
                org.name = normalized
                db.add(org)
                summary["organizations_renamed"] += 1

    if not orgs_only:
        loc_query = db.query(Location).order_by(Location.id.asc())
        if limit:
            loc_query = loc_query.limit(limit)

        for loc in loc_query.all():
            summary["locations_scanned"] += 1
            raw_value = loc.raw or ", ".join(
                part for part in [loc.city, loc.region, loc.country] if part
            )
            city, region, country = normalize_location(raw_value)
            normalized_raw = " ".join((raw_value or "").split()).strip() or None

            if (city, region, country, normalized_raw) == (
                loc.city,
                loc.region,
                loc.country,
                loc.raw,
            ):
                continue

            target = (
                db.query(Location)
                .filter(
                    Location.city == city,
                    Location.region == region,
                    Location.country == country,
                )
                .one_or_none()
            )
            if target and target.id != loc.id:
                moved = (
                    db.query(JobPost)
                    .filter(JobPost.location_id == loc.id)
                    .update({JobPost.location_id: target.id}, synchronize_session=False)
                )
                summary["location_job_refs_repointed"] += int(moved or 0)
            else:
                loc.city = city
                loc.region = region
                loc.country = country
                loc.raw = normalized_raw
                db.add(loc)
                summary["locations_updated"] += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return summary


def main() -> None:
    from app.db.database import SessionLocal

    parser = argparse.ArgumentParser(
        description="Backfill normalized organization/location data for existing jobs."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--orgs-only", action="store_true")
    parser.add_argument("--locations-only", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = backfill_normalized_entities(
            db,
            dry_run=args.dry_run,
            limit=args.limit,
            orgs_only=args.orgs_only,
            locations_only=args.locations_only,
        )
        print(summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()
