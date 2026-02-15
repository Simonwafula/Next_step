from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...db.models import IngestionState, JobPost, Organization
from ...services.deduplication_service import DeduplicationService

logger = logging.getLogger(__name__)

# Keep Telegram payloads bounded; downstream processing/embeddings doesn't need
# unlimited history per post.
MAX_DESCRIPTION_CHARS = 6000

_URL_RE = re.compile(r"(https?://[^\s<>()]+)")

_DEFAULT_POSITIVE_HINTS = (
    "job",
    "vacan",
    "hiring",
    "apply",
    "deadline",
    "closing",
    "qualification",
    "requirements",
    "position",
    "role",
    "intern",
    "trainee",
    "graduate",
    "attachment",
)
_DEFAULT_NEGATIVE_HINTS = (
    "subscribe",
    "join",
    "advertise",
    "advertisement",
    "promo",
    "promotion",
    "rules",
    "admin",
)


def normalize_channel(value: str) -> str:
    """Normalize a Telegram channel/group reference to a username-like key."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    if raw.startswith("@"):
        raw = raw[1:]

    raw = raw.replace("https://", "").replace("http://", "")
    if raw.startswith("t.me/"):
        raw = raw[5:]
    if raw.startswith("telegram.me/"):
        raw = raw[11:]

    raw = raw.lstrip("/")
    return raw.split("/", 1)[0].strip()


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _URL_RE.finditer(text or ""):
        url = match.group(1).strip()
        # Strip common trailing punctuation.
        url = url.rstrip(").,;:!?]\"'")
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def pick_application_url(urls: Sequence[str]) -> str | None:
    for url in urls:
        lowered = url.lower()
        if lowered.startswith("https://t.me/") or lowered.startswith("http://t.me/"):
            continue
        if lowered.startswith("https://telegram.me/") or lowered.startswith(
            "http://telegram.me/"
        ):
            continue
        return url
    return None


def guess_title_from_text(text: str) -> str:
    """Best-effort title extraction from free-form Telegram text."""
    raw = str(text or "").strip()
    if not raw:
        return "Job opportunity"

    patterns = (
        r"(?im)^(?:position|job title|role|vacancy|opportunity)\s*[:\-]\s*(.+)$",
        r"(?im)^(?:hiring|we are hiring)\s*[:\-]\s*(.+)$",
    )
    for pat in patterns:
        m = re.search(pat, raw)
        if m and m.group(1).strip():
            title = m.group(1).strip()
            return _clean_title(title)

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "http://" in line or "https://" in line:
            continue
        if len(line) < 6:
            continue
        return _clean_title(line)

    return "Job opportunity"


def should_keep_message(
    text: str,
    *,
    min_text_len: int = 80,
    require_keywords: Sequence[str] | None = None,
    exclude_keywords: Sequence[str] | None = None,
) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    if len(cleaned) < max(0, int(min_text_len)):
        return False

    lowered = cleaned.lower()

    if exclude_keywords:
        for kw in exclude_keywords:
            if kw and str(kw).lower() in lowered:
                return False

    if require_keywords:
        if not any(str(kw).lower() in lowered for kw in require_keywords if kw):
            return False

    # Filter obvious channel meta/promo posts while keeping real job posts.
    if any(hint in lowered for hint in _DEFAULT_NEGATIVE_HINTS) and not any(
        hint in lowered for hint in _DEFAULT_POSITIVE_HINTS
    ):
        return False

    return True


def _clean_title(value: str) -> str:
    # Remove leading punctuation/emojis and collapse whitespace.
    title = re.sub(r"^[^\w]+", "", str(value or "")).strip()
    title = " ".join(title.split())
    return (title or "Job opportunity")[:255]


def _get_or_create_state(db: Session, source_key: str) -> IngestionState:
    state = (
        db.query(IngestionState)
        .filter(IngestionState.source_key == source_key)
        .one_or_none()
    )
    if state:
        return state

    state = IngestionState(source_key=source_key, meta_json={})
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def _get_or_create_org(db: Session, name: str | None) -> Organization | None:
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).one_or_none()
    if org:
        return org
    org = Organization(name=name, verified=False, sector="Social")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


async def _fetch_messages(
    *,
    channel: str,
    api_id: int,
    api_hash: str,
    session_value: str | None,
    last_cursor: int,
    max_messages: int,
    backfill_enabled: bool,
    backfill_next_max_id: int,
    backfill_limit: int,
) -> tuple[list, list, int]:
    """Return (incremental_messages, backfill_messages, initialized_backfill_next_max_id)."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    if session_value:
        client = TelegramClient(StringSession(session_value), api_id, api_hash)
    else:
        # Falls back to file session, controlled by TELEGRAM_SESSION_FILE.
        session_file = os.getenv("TELEGRAM_SESSION_FILE", "nextstep")
        client = TelegramClient(session_file, api_id, api_hash)

    async with client:
        entity = await client.get_entity(channel)

        # Initialize backfill cursor to start from the latest message id.
        if backfill_enabled and backfill_next_max_id <= 0:
            latest = await client.get_messages(entity, limit=1)
            if latest and latest[0] and getattr(latest[0], "id", None):
                backfill_next_max_id = int(latest[0].id) + 1

        inc: list = []
        if max_messages > 0:
            # reverse=True yields oldest->newest, so we can advance cursor safely.
            async for msg in client.iter_messages(
                entity,
                min_id=int(last_cursor or 0),
                limit=int(max_messages),
                reverse=True,
            ):
                inc.append(msg)

        backfill: list = []
        if backfill_enabled and backfill_limit > 0 and backfill_next_max_id > 1:
            async for msg in client.iter_messages(
                entity,
                max_id=int(backfill_next_max_id) - 1,
                limit=int(backfill_limit),
                reverse=False,  # newest->oldest
            ):
                backfill.append(msg)

        return inc, backfill, int(backfill_next_max_id)


def ingest_telegram(db: Session, **src) -> int:
    """Ingest job/opportunity posts from a Telegram channel/group.

    Requires Telethon (MTProto) and pre-authenticated session credentials.
    """
    channel = normalize_channel(str(src.get("channel") or src.get("url") or ""))
    if not channel:
        return 0

    job_source = str(src.get("source") or f"telegram:{channel}")[:120]
    org_name = str(src.get("org") or src.get("name") or f"Telegram:{channel}")[:255]

    # Use the same convention as runner._source_key (name -> org -> url -> type).
    source_key = str(
        src.get("name") or src.get("org") or src.get("url") or src.get("type")
    )

    state = _get_or_create_state(db, source_key)
    meta = dict(state.meta_json or {})

    try:
        api_id = int(os.getenv("TELEGRAM_API_ID") or "0")
        api_hash = str(os.getenv("TELEGRAM_API_HASH") or "").strip()
    except Exception:
        api_id = 0
        api_hash = ""

    session_value = str(os.getenv("TELEGRAM_SESSION") or "").strip() or None
    if api_id <= 0 or not api_hash:
        raise RuntimeError(
            "Missing TELEGRAM_API_ID / TELEGRAM_API_HASH (required for Telethon ingestion)."
        )
    if not session_value and not os.getenv("TELEGRAM_SESSION_FILE"):
        raise RuntimeError(
            "Missing TELEGRAM_SESSION or TELEGRAM_SESSION_FILE (required for non-interactive ingestion)."
        )

    max_messages = int(src.get("max_messages", 200))
    backfill_enabled = bool(src.get("backfill", True))
    backfill_limit = int(src.get("backfill_limit", 200))

    last_cursor = int(state.last_cursor or 0) if state.last_cursor else 0
    backfill_next_max_id = int(meta.get("backfill_next_max_id") or 0)

    require_keywords = src.get("keywords") or None
    exclude_keywords = src.get("exclude_keywords") or None
    min_text_len = int(src.get("min_text_len", 80))

    try:
        inc_msgs, backfill_msgs, initialized_backfill = asyncio.run(
            _fetch_messages(
                channel=channel,
                api_id=api_id,
                api_hash=api_hash,
                session_value=session_value,
                last_cursor=last_cursor,
                max_messages=max_messages,
                backfill_enabled=backfill_enabled,
                backfill_next_max_id=backfill_next_max_id,
                backfill_limit=backfill_limit,
            )
        )
    except Exception as exc:
        logger.error("Telegram ingest failed for %s: %s", channel, exc)
        raise

    deduper = DeduplicationService()
    org = _get_or_create_org(db, org_name)

    def _permalink(msg_id: int) -> str:
        return f"https://t.me/{channel}/{msg_id}"

    added = 0
    max_seen_id = last_cursor
    max_seen_at: datetime | None = None

    # Process incrementals first, then backfill.
    for msg in list(inc_msgs) + list(backfill_msgs):
        msg_id = int(getattr(msg, "id", 0) or 0)
        if msg_id <= 0:
            continue

        max_seen_id = max(max_seen_id, msg_id)
        msg_dt = getattr(msg, "date", None)
        if isinstance(msg_dt, datetime):
            # Store naive UTC timestamps (Postgres will store them as timestamp).
            msg_dt_naive = msg_dt.replace(tzinfo=None)
            if max_seen_at is None or msg_dt_naive > max_seen_at:
                max_seen_at = msg_dt_naive

        text = getattr(msg, "message", None) or getattr(msg, "raw_text", None) or ""
        text = str(text)
        if not should_keep_message(
            text,
            min_text_len=min_text_len,
            require_keywords=require_keywords,
            exclude_keywords=exclude_keywords,
        ):
            continue

        url = _permalink(msg_id)
        url_hash = deduper.generate_url_hash(url)
        existing = (
            db.query(JobPost)
            .filter(or_(JobPost.url == url, JobPost.url_hash == url_hash))
            .first()
        )
        if existing:
            existing.last_seen = datetime.utcnow()
            db.add(existing)
            continue

        urls = extract_urls(text)
        application_url = pick_application_url(urls) or url
        title = guess_title_from_text(text)

        desc = " ".join(text.split()).strip()
        if len(desc) > MAX_DESCRIPTION_CHARS:
            desc = desc[:MAX_DESCRIPTION_CHARS]

        created_at = (
            msg_dt.replace(tzinfo=None) if isinstance(msg_dt, datetime) else None
        )
        now = datetime.utcnow()
        jp = JobPost(
            source=job_source,
            url=url,
            source_url=url,
            application_url=application_url,
            url_hash=url_hash,
            first_seen=created_at or now,
            last_seen=now,
            org_id=org.id if org else None,
            title_raw=title,
            description_raw=desc or None,
        )
        db.add(jp)
        added += 1

    # Update cursor/state for incremental consumption and optional backfill.
    if max_seen_id > last_cursor:
        state.last_cursor = str(max_seen_id)
    if max_seen_at is not None:
        state.last_item_at = max_seen_at

    if backfill_enabled:
        # Use the initialized cursor if unset (or invalid), then move backwards
        # as we consume.
        if int(meta.get("backfill_next_max_id") or 0) <= 0:
            meta["backfill_next_max_id"] = initialized_backfill
        backfill_ids = [int(getattr(m, "id", 0) or 0) for m in backfill_msgs]
        backfill_ids = [i for i in backfill_ids if i > 0]
        if backfill_ids:
            meta["backfill_next_max_id"] = min(backfill_ids)
        else:
            # No more backfill items in this window.
            meta["backfill_next_max_id"] = 0

    state.meta_json = meta
    db.add(state)

    db.commit()
    return added
