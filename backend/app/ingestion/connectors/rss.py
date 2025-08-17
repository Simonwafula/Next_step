# Generic RSS/Atom ingest (for boards exposing feeds)
from sqlalchemy.orm import Session
from ...db.models import JobPost, Organization, Location
from datetime import datetime
import httpx
import re

def ingest_rss(db: Session, **src) -> int:
    url = src.get("url")
    org_name = src.get("org")
    if not url:
        return 0

    xml = httpx.get(url, timeout=30).text

    # super-simple parse (you should switch to feedparser later)
    items = re.findall(r"<item>(.*?)</item>", xml, flags=re.DOTALL | re.IGNORECASE)

    if org_name:
        org = db.query(Organization).filter(Organization.name == org_name).one_or_none()
        if not org:
            org = Organization(name=org_name, verified=False)
            db.add(org); db.commit(); db.refresh(org)
    else:
        org = None

    added = 0
    for item in items:
        link_match = re.search(r"<link>(.*?)</link>", item, flags=re.IGNORECASE)
        title_match = re.search(r"<title>(.*?)</title>", item, flags=re.IGNORECASE)
        jurl = link_match.group(1).strip() if link_match else None
        title = title_match.group(1).strip() if title_match else "Job"

        if not jurl:
            continue

        existing = db.query(JobPost).filter(JobPost.url == jurl).one_or_none()
        if existing:
            existing.last_seen = datetime.utcnow()
            db.add(existing); continue

        jp = JobPost(
            source="rss",
            url=jurl,
            title_raw=title,
            org_id=org.id if org else None,
            description_raw="",
        )
        db.add(jp); added += 1

    db.commit()
    return added
