import typer
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import SessionLocal
from app.ingestion.runner import run_all_sources, run_incremental_sources
from app.services.analytics import refresh_analytics_baseline, run_drift_checks
import subprocess

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
def embed():
    """Generate vector embeddings for all processed jobs."""
    typer.echo("Generating embeddings...")
    subprocess.run(["python3", "../scripts/generate_embeddings.py"])


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
