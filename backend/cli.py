import typer
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import SessionLocal
from app.services.analytics import refresh_analytics_baseline
import subprocess

app = typer.Typer(help="Next Step Production Pipeline Orchestrator")

@app.command()
def ingest():
    """Run all active job scrapers."""
    typer.echo("Starting ingestion...")
    # Trigger existing scrapers/workers
    typer.echo("Ingestion complete (simulated).")

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

if __name__ == "__main__":
    app()
