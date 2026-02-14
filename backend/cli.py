import subprocess
import sys
from pathlib import Path

import typer

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import SessionLocal  # noqa: E402
from app.ingestion.runner import (  # noqa: E402
    run_all_sources,
    run_incremental_sources,
)
from app.ml.embeddings import run_incremental_embeddings  # noqa: E402
from app.normalization.dedupe import run_incremental_dedup  # noqa: E402
from app.scrapers.main import scrape_all_sites  # noqa: E402
from app.services.analytics import (  # noqa: E402
    refresh_analytics_baseline,
    run_drift_checks,
)
from app.services.pipeline_service import (  # noqa: E402
    PipelineOptions,
    run_incremental_pipeline,
)
from app.services.post_ingestion_processing_service import process_job_posts  # noqa: E402
from app.services.processing_log_service import (  # noqa: E402
    log_processing_event,
)
from app.services.ranking_trainer import (  # noqa: E402
    train_ranking_model,
    get_model_info,
)

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
def scrape_sites(
    max_pages: int = typer.Option(5, help="Scrape only the first N pages per site"),
    use_postgres: bool = typer.Option(
        True, help="Write scraped jobs directly into the app DB (recommended)"
    ),
):
    """Scrape configured HTML job boards and store results."""
    typer.echo("Starting site scraping...")
    result = scrape_all_sites(use_postgres=use_postgres, max_pages=max_pages)
    typer.echo(
        f"Scraping complete. Inserted {result.get('inserted_total', 0)} new jobs."
    )


@app.command()
def post_process(
    source: str = typer.Option(
        None, help="Limit post-processing to a single job_post.source"
    ),
    limit: int = typer.Option(2000, help="Max jobs to process per run"),
):
    """Run deterministic post-ingestion processing (entities, skills, quality score)."""
    typer.echo("Starting post-ingestion processing...")
    db = SessionLocal()
    try:
        result = process_job_posts(
            db,
            source=source,
            limit=limit,
            only_unprocessed=True,
            dry_run=False,
        )
        log_processing_event(
            db,
            process_type="post_process",
            status=result["status"],
            message=f"Processed {result.get('processed', 0)} jobs",
            details=result,
        )
        typer.echo(
            "Post-process complete: "
            f"{result.get('processed', 0)} processed (source={source or 'all'})."
        )
    finally:
        db.close()


@app.command()
def pipeline(
    strict: bool = typer.Option(
        True,
        help="Exit non-zero if any pipeline step errors",
    ),
    scrape: bool = typer.Option(True, help="Run HTML site scraping step"),
    ingest: bool = typer.Option(True, help="Run incremental ingestion connectors step"),
    process: bool = typer.Option(True, help="Run deterministic post-processing step"),
    dedupe: bool = typer.Option(True, help="Run incremental dedupe step"),
    embed: bool = typer.Option(True, help="Run incremental embeddings step"),
    analytics: bool = typer.Option(True, help="Refresh analytics baselines"),
    process_limit: int = typer.Option(2000, help="Max jobs to post-process"),
    scraper_max_pages: int = typer.Option(5, help="Max pages to scrape per site"),
):
    """Run the full incremental production pipeline in one command."""
    typer.echo("Starting incremental pipeline...")
    db = SessionLocal()
    try:
        opts = PipelineOptions(
            ingest_incremental=ingest,
            scrape_sites=scrape,
            post_process=process,
            post_process_limit=process_limit,
            dedupe=dedupe,
            embed=embed,
            analytics=analytics,
            scraper_max_pages=scraper_max_pages,
            scraper_use_postgres=True,
            strict=strict,
        )
        result = run_incremental_pipeline(db, opts=opts)
        typer.echo(
            f"Pipeline complete (status={result.get('status')}, "
            f"duration={result.get('duration_seconds')}s)."
        )
    except Exception as exc:
        typer.echo(f"Pipeline failed: {exc}", err=True)
        raise typer.Exit(code=1)
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
            message=(
                f"Processed {result['processed']} jobs, found "
                f"{result['duplicates_found']} duplicates"
            ),
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
            message=(f"Embedded {result['processed']} jobs with {result['model']}"),
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


@app.command()
def train_ranking(days_back: int = 30):
    """Train the learned ranking model on user interaction data."""
    typer.echo(f"Training ranking model on {days_back} days of data...")
    db = SessionLocal()
    try:
        result = train_ranking_model(db, days_back=days_back)
        if result["success"]:
            typer.echo(
                f"✓ Training successful: {result['examples_total']} "
                f"examples ({result['examples_positive']} positive)"
            )
            typer.echo(f"Model saved to: {result['model_path']}")
        else:
            typer.echo(f"✗ Training failed: {result['error']}", err=True)
            raise typer.Exit(code=1)
    finally:
        db.close()


@app.command()
def ranking_info():
    """Show information about the current ranking model."""
    info = get_model_info()
    if info["exists"]:
        typer.echo(f"Model: {info['path']}")
        typer.echo(f"Size: {info['size_bytes']} bytes")
        typer.echo(f"Last trained: {info['modified_at']}")
    else:
        typer.echo("No trained model found.")
        typer.echo(f"Expected path: {info['path']}")


if __name__ == "__main__":
    app()
