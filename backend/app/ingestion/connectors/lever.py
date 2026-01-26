# Minimal Lever board ingest
# Public postings API: https://api.lever.co/v0/postings/{board_token}
from sqlalchemy.orm import Session
from ...db.models import JobPost, Organization, Location
from datetime import datetime
import httpx


def ingest_lever(db: Session, **src) -> int:
    token = src.get("board_token")
    org_name = src.get("org")
    if not token:
        return 0

    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    jobs = httpx.get(url, timeout=30).json()

    if org_name:
        org = db.query(Organization).filter(Organization.name == org_name).one_or_none()
        if not org:
            org = Organization(name=org_name, ats="lever", verified=True)
            db.add(org)
            db.commit()
            db.refresh(org)
    else:
        org = None

    added = 0
    for j in jobs:
        jurl = j.get("hostedUrl")
        existing = db.query(JobPost).filter(JobPost.url == jurl).one_or_none()
        if existing:
            existing.last_seen = datetime.utcnow()
            db.add(existing)
            continue

        loc = None
        loc_raw = (
            ", ".join(j.get("categories", {}).get("location", "").split("/"))
            if j.get("categories", {}).get("location")
            else None
        )
        if loc_raw:
            loc = Location(raw=loc_raw)
            db.add(loc)
            db.flush()

        jp = JobPost(
            source="lever",
            url=jurl,
            title_raw=j.get("text", ""),
            org_id=org.id if org else None,
            location_id=loc.id if loc else None,
            description_raw=j.get("descriptionPlain", ""),
            requirements_raw="",
        )
        db.add(jp)
        added += 1

    db.commit()
    return added
