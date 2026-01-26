from email.utils import parsedate_to_datetime
from datetime import datetime
import re

import httpx
from sqlalchemy.orm import Session

from ...db.models import TenderNotice


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None


def ingest_tender_rss(db: Session, **src) -> int:
    url = src.get("url")
    if not url:
        return 0

    source = src.get("source") or "tender_rss"
    org_name = src.get("org")
    category = src.get("category")
    location = src.get("location")

    xml = httpx.get(url, timeout=30).text
    items = re.findall(r"<item>(.*?)</item>", xml, flags=re.DOTALL | re.IGNORECASE)

    added = 0
    for item in items:
        link_match = re.search(r"<link>(.*?)</link>", item, flags=re.IGNORECASE)
        title_match = re.search(r"<title>(.*?)</title>", item, flags=re.IGNORECASE)
        guid_match = re.search(r"<guid.*?>(.*?)</guid>", item, flags=re.IGNORECASE)
        date_match = re.search(r"<pubDate>(.*?)</pubDate>", item, flags=re.IGNORECASE)
        description_match = re.search(
            r"<description>(.*?)</description>", item, flags=re.IGNORECASE | re.DOTALL
        )

        tender_url = link_match.group(1).strip() if link_match else None
        title = title_match.group(1).strip() if title_match else None
        external_id = guid_match.group(1).strip() if guid_match else None
        published_at = _parse_date(date_match.group(1).strip()) if date_match else None
        description = description_match.group(1).strip() if description_match else None

        if not title:
            continue

        existing = None
        if external_id:
            existing = (
                db.query(TenderNotice)
                .filter(TenderNotice.external_id == external_id)
                .one_or_none()
            )
        if not existing and tender_url:
            existing = (
                db.query(TenderNotice)
                .filter(TenderNotice.url == tender_url)
                .one_or_none()
            )
        if existing:
            continue

        notice = TenderNotice(
            source=source,
            external_id=external_id,
            title=title,
            organization=org_name,
            category=category,
            location=location,
            published_at=published_at,
            url=tender_url,
            description_raw=description,
            meta_json=src,
        )
        db.add(notice)
        added += 1

    db.commit()
    return added
