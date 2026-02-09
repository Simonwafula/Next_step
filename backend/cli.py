import subprocess
import sys
from pathlib import Path

import typer

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import SessionLocal
from app.ingestion.runner import run_all_sources, run_incremental_sources
from app.ml.embeddings import run_incremental_embeddings
from app.normalization.dedupe import run_incremental_dedup
from app.services.analytics import refresh_analytics_baseline, run_drift_checks
from app.services.processing_log_service import log_processing_event

app = typer.Typer(help="Next Step Production Pipeline Orchestrator")


@app.command()
def ingest():
    """Run all active job scrapers."""
    typer.echo("Starting ingestion...")
    db = SessionLocal()
    try:
        count = run_all_sources(db)
        typer.echo(f"Ingestion complete. Added {count} records.")
    finally:
        db.close()


@app.command()
def ingest_incremental():
    """Run incremental job ingestion with state tracking."""
    typer.echo("Starting incremental ingestion...")
    db = SessionLocal()
    try:
        count = run_incremental_sources(db)
        typer.echo(f"Incremental ingestion complete. Added {count} records.")
    finally:
        db.close()


@app.command()
def process(limit: int = 100):
    """Run normalization and extraction pipeline."""
    typer.echo(f"Processing top {limit} jobs...")
    subprocess.run(["python3", "../scripts/run_pipeline_v1.py", "--limit", str(limit)])


@app.command()
def dedupe(batch_size: int = 500):
    """Run incremental deduplication on new jobs."""
    typer.echo("Running incremental deduplication...")
    db = SessionLocal()
    try:
        result = run_incremental_dedup(db, batch_size=batch_size)
        log_processing_event(
            db,
            process_type="dedup",
            status=result["status"],
            message=f"Processed {result['processed']} jobs, found {result['duplicates_found']} duplicates",
            details=result,
        )
        typer.echo(
            f"Dedup complete: {result['processed']} processed, "
            f"{result['duplicates_found']} duplicates found."
        )
    finally:
        db.close()


@app.command()
def embed(batch_size: int = 100):
    """Generate vector embeddings for unembedded jobs."""
    typer.echo("Running incremental embedding generation...")
    db = SessionLocal()
    try:
        result = run_incremental_embeddings(db, batch_size=batch_size)
        log_processing_event(
            db,
            process_type="embedding",
            status=result["status"],
            message=f"Embedded {result['processed']} jobs with {result['model']}",
            details=result,
        )
        typer.echo(
            f"Embedding complete: {result['processed']} jobs embedded "
            f"(model: {result['model']})."
        )
    finally:
        db.close()


@app.command()
def analytics():
    """Refresh intelligence analytics tables."""
    typer.echo("Refreshing analytics...")
    db = SessionLocal()
    try:
        results = refresh_analytics_baseline(db)
        typer.echo(results["message"])
    finally:
        db.close()


@app.command()
def drift():
    """Run drift checks for skills, titles, and salary distributions."""
    typer.echo("Running drift checks...")
    db = SessionLocal()
    try:
        results = run_drift_checks(db)
        typer.echo(f"Skills drift score: {results['skills']['drift_score']}")
        typer.echo(f"Titles drift score: {results['titles']['drift_score']}")
    finally:
        db.close()


if __name__ == "__main__":
    app()
