from .connectors.greenhouse import ingest_greenhouse
from .connectors.lever import ingest_lever
from .connectors.rss import ingest_rss
from .connectors.html_generic import ingest_html_generic
from .connectors.gov_careers import ingest_gov_careers
from sqlalchemy.orm import Session
import yaml
import os

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


def run_all_sources(db: Session, config_paths=None) -> int:
    count = 0
    for src in _load_sources(config_paths=config_paths):
        stype = src.get("type")
        try:
            if stype == "greenhouse":
                count += ingest_greenhouse(db, **src)
            elif stype == "lever":
                count += ingest_lever(db, **src)
            elif stype == "rss":
                count += ingest_rss(db, **src)
            elif stype == "html_generic":
                count += ingest_html_generic(db, **src)
            elif stype == "gov_careers":
                count += ingest_gov_careers(db, **src)
        except Exception as e:
            print(f"[INGEST ERROR] {src}: {e}")
    return count


def run_government_sources(db: Session) -> int:
    return run_all_sources(db, config_paths=[GOV_CONFIG_PATH])
