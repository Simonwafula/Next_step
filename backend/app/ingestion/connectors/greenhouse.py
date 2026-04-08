# Minimal Greenhouse board ingest (public boards)
# Docs pattern: https://boards.greenhouse.io/{board_token}
from datetime import datetime
import httpx

from sqlalchemy.orm import Session

from ...db.models import JobPost, Location, Organization
from ...normalization.companies import normalize_company_name
from ...normalization.locations import normalize_location


def ingest_greenhouse(db: Session, **src) -> int:
    token = src.get("board_token")
    org_name = src.get("org")

    if not token:
        return 0

    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    jobs = httpx.get(url, timeout=30).json().get("jobs", [])
    if org_name:
        org_name = normalize_company_name(org_name)
        org = db.query(Organization).filter(Organization.name == org_name).one_or_none()
        if not org:
            org = Organization(name=org_name, ats="greenhouse", verified=True)
            db.add(org)
            db.commit()
            db.refresh(org)
    else:
        org = None

    added = 0
    for j in jobs:
        jurl = j.get("absolute_url")
        existing = db.query(JobPost).filter(JobPost.url == jurl).one_or_none()
        if existing:
            existing.last_seen = datetime.utcnow()
            db.add(existing)
            continue

        loc = None
        if j.get("location", {}).get("name"):
            loc_raw = j["location"]["name"]
            city, region, country = normalize_location(loc_raw)
            loc = (
                db.query(Location)
                .filter(
                    Location.city == city,
                    Location.region == region,
                    Location.country == country,
                )
                .one_or_none()
            )
            if not loc:
                loc = Location(
                    raw=" ".join(loc_raw.split()),
                    city=city,
                    region=region,
                    country=country,
                )
                db.add(loc)
                db.flush()

        jp = JobPost(
            source="greenhouse",
            url=jurl,
            source_url=jurl,
            application_url=jurl,
            title_raw=j.get("title", ""),
            org_id=org.id if org else None,
            location_id=loc.id if loc else None,
            description_raw="",
            requirements_raw="",
        )
        db.add(jp)
        added += 1

    db.commit()
    return added
