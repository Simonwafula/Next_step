from .connectors.greenhouse import ingest_greenhouse
from .connectors.lever import ingest_lever
from .connectors.rss import ingest_rss
from .connectors.html_generic import ingest_html_generic
from sqlalchemy.orm import Session
import yaml, os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sources.yaml")

def run_all_sources(db: Session) -> int:
    if not os.path.exists(CONFIG_PATH):
        return 0
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f) or {}

    count = 0
    for src in cfg.get("sources", []):
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
        except Exception as e:
            print(f"[INGEST ERROR] {src}: {e}")
    return count
