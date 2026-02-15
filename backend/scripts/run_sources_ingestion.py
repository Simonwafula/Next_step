from __future__ import annotations

# ruff: noqa: E402

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

# Ensure the backend root (containing the `app/` package) is importable even when
# this script is executed from `backend/scripts/`.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.db.database import SessionLocal
from app.ingestion.runner import run_all_sources
from app.services.post_ingestion_processing_service import process_job_posts


def _default_config_paths() -> list[str]:
    backend_dir = Path(__file__).resolve().parents[1]
    return [str(backend_dir / "app" / "ingestion" / "sources.yaml")]


def _load_sources_from_configs(config_paths: list[str]) -> list[dict]:
    sources: list[dict] = []
    for path in config_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            sources.extend(cfg.get("sources", []) or [])
        except Exception:
            # CLI helper: tolerate unreadable configs so ingestion can still run
            # (runner will surface its own per-source errors).
            continue
    return sources


def _default_process_sources(config_paths: list[str]) -> list[str]:
    values: set[str] = set()
    for src in _load_sources_from_configs(config_paths):
        val = str(src.get("source") or "").strip()
        if val:
            values.add(val)
    return sorted(values)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest non-job-board sources from YAML and post-process new rows."
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Path to an ingestion YAML file. Can be repeated. Default: app/ingestion/sources.yaml",
    )
    parser.add_argument(
        "--process-limit",
        type=int,
        default=int(os.getenv("POST_PROCESS_LIMIT", "2000")),
        help="Max number of unprocessed JobPost rows to post-process (default: POST_PROCESS_LIMIT or 2000).",
    )
    parser.add_argument(
        "--process-source",
        action="append",
        default=[],
        help="If provided, post-process only these JobPost.source values (can be repeated).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run post-processing in dry-run mode (does not write changes).",
    )
    parser.add_argument(
        "--no-process",
        action="store_true",
        help="Only ingest; skip post-processing.",
    )
    args = parser.parse_args()

    config_paths = [p for p in (args.config or []) if str(p).strip()]
    if not config_paths:
        config_paths = _default_config_paths()

    db = SessionLocal()
    try:
        ingested = run_all_sources(db, config_paths=config_paths)
        post_process_results = []
        if not args.no_process:
            process_sources = (
                [str(s).strip() for s in (args.process_source or []) if str(s).strip()]
                if args.process_source
                else _default_process_sources(config_paths)
            )
            if process_sources:
                for src in process_sources:
                    post_process_results.append(
                        process_job_posts(
                            db,
                            source=src,
                            limit=args.process_limit,
                            only_unprocessed=True,
                            dry_run=bool(args.dry_run),
                        )
                    )
            else:
                post_process_results.append(
                    process_job_posts(
                        db,
                        source=None,
                        limit=args.process_limit,
                        only_unprocessed=True,
                        dry_run=bool(args.dry_run),
                    )
                )

        print(
            json.dumps(
                {
                    "ingested": ingested,
                    "config_paths": config_paths,
                    "post_process": post_process_results,
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
