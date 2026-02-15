from datetime import datetime
import os
import yaml

from sqlalchemy.orm import Session

from .connectors.greenhouse import ingest_greenhouse
from .connectors.lever import ingest_lever
from .connectors.rss import ingest_rss
from .connectors.html_generic import ingest_html_generic
from .connectors.gov_careers import ingest_gov_careers
from .connectors.tender_rss import ingest_tender_rss
from .connectors.telegram import ingest_telegram
from ..db.models import IngestionState

DEFAULT_CONFIG_PATHS = [
    os.path.join(os.path.dirname(__file__), "sources.yaml"),
    os.path.join(os.path.dirname(__file__), "government_sources.yaml"),
]

GOV_CONFIG_PATH = DEFAULT_CONFIG_PATHS[1]


def _load_sources(config_paths=None):
    sources = []
    for path in config_paths or DEFAULT_CONFIG_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        sources.extend(cfg.get("sources", []))
    return sources


def _source_key(src: dict) -> str:
    return str(src.get("name") or src.get("org") or src.get("url") or src.get("type"))


def _record_state(db: Session, source_key: str, count: int, status: str | None = None):
    state = (
        db.query(IngestionState)
        .filter(IngestionState.source_key == source_key)
        .one_or_none()
    )
    if not state:
        state = IngestionState(source_key=source_key)
        db.add(state)
    state.last_run_at = datetime.utcnow()
    state.last_count = count
    state.status = status
    db.commit()


def _run_source(db: Session, src: dict) -> int:
    stype = src.get("type")
    if stype == "greenhouse":
        return ingest_greenhouse(db, **src)
    if stype == "lever":
        return ingest_lever(db, **src)
    if stype == "rss":
        return ingest_rss(db, **src)
    if stype == "html_generic":
        return ingest_html_generic(db, **src)
    if stype == "gov_careers":
        return ingest_gov_careers(db, **src)
    if stype == "tender_rss":
        return ingest_tender_rss(db, **src)
    if stype == "telegram":
        return ingest_telegram(db, **src)
    return 0


def run_all_sources(db: Session, config_paths=None) -> int:
    count = 0
    for src in _load_sources(config_paths=config_paths):
        source_key = _source_key(src)
        try:
            added = _run_source(db, src)
            count += added
            _record_state(db, source_key, added, status="success")
        except Exception as e:
            _record_state(db, source_key, 0, status="error")
            print(f"[INGEST ERROR] {src}: {e}")
    return count


def run_government_sources(db: Session) -> int:
    return run_all_sources(db, config_paths=[GOV_CONFIG_PATH])


def run_incremental_sources(db: Session, config_paths=None) -> int:
    count = 0
    for src in _load_sources(config_paths=config_paths):
        source_key = _source_key(src)
        try:
            added = _run_source(db, src)
            count += added
            _record_state(db, source_key, added, status="incremental")
        except Exception as e:
            _record_state(db, source_key, 0, status="error")
            print(f"[INGEST ERROR] {src}: {e}")
    return count
