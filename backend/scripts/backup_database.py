#!/usr/bin/env python3
"""
Database backup script for Next Step.

Supports both SQLite and PostgreSQL databases.
Creates timestamped backups with optional compression.

Usage:
    python scripts/backup_database.py [--output-dir ./backups] [--compress]
"""

import argparse
import gzip
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv("DATABASE_URL", "sqlite:///var/nextstep.sqlite")


def backup_sqlite(db_path: str, output_dir: Path, compress: bool = False) -> Path:
    """
    Backup SQLite database.

    Args:
        db_path: Path to SQLite database file
        output_dir: Directory to save backup
        compress: Whether to compress the backup

    Returns:
        Path to backup file
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"nextstep_backup_{timestamp}.sqlite"
    backup_path = output_dir / backup_name

    logger.info(f"Backing up SQLite database: {db_path}")

    # Copy the database file
    shutil.copy2(db_path, backup_path)

    if compress:
        compressed_path = backup_path.with_suffix(".sqlite.gz")
        logger.info(f"Compressing backup to: {compressed_path}")

        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed backup
        backup_path.unlink()
        backup_path = compressed_path

    logger.info(f"Backup created: {backup_path}")
    return backup_path


def backup_postgres(
    database_url: str, output_dir: Path, compress: bool = False
) -> Path:
    """
    Backup PostgreSQL database using pg_dump.

    Args:
        database_url: PostgreSQL connection URL
        output_dir: Directory to save backup
        compress: Whether to compress the backup

    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"nextstep_backup_{timestamp}.sql"
    backup_path = output_dir / backup_name

    logger.info("Backing up PostgreSQL database...")

    # Parse database URL
    # postgresql://user:pass@host:port/dbname
    from urllib.parse import urlparse

    parsed = urlparse(database_url)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    pg_dump_args = [
        "pg_dump",
        "-h",
        parsed.hostname or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "postgres",
        "-d",
        parsed.path.lstrip("/"),
        "-F",
        "p",  # Plain text format
        "-f",
        str(backup_path),
    ]

    try:
        subprocess.run(pg_dump_args, env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"pg_dump failed: {e.stderr.decode()}")
        raise

    if compress:
        compressed_path = backup_path.with_suffix(".sql.gz")
        logger.info(f"Compressing backup to: {compressed_path}")

        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        backup_path.unlink()
        backup_path = compressed_path

    logger.info(f"Backup created: {backup_path}")
    return backup_path


def cleanup_old_backups(output_dir: Path, keep_count: int = 10):
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        output_dir: Directory containing backups
        keep_count: Number of backups to keep
    """
    backup_files = sorted(
        [f for f in output_dir.glob("nextstep_backup_*")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if len(backup_files) > keep_count:
        for old_backup in backup_files[keep_count:]:
            logger.info(f"Removing old backup: {old_backup}")
            old_backup.unlink()


def main():
    parser = argparse.ArgumentParser(description="Backup Next Step database")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backups"),
        help="Directory to save backups (default: ./backups)",
    )
    parser.add_argument(
        "--compress", action="store_true", help="Compress backup with gzip"
    )
    parser.add_argument(
        "--keep", type=int, default=10, help="Number of backups to keep (default: 10)"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL (overrides DATABASE_URL env var)",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Get database URL
    database_url = args.database_url or get_database_url()
    logger.info(
        f"Database type: {'SQLite' if 'sqlite' in database_url else 'PostgreSQL'}"
    )

    try:
        if database_url.startswith("sqlite"):
            # Extract path from sqlite:///path/to/db
            db_path = database_url.replace("sqlite:///", "")
            backup_path = backup_sqlite(db_path, args.output_dir, args.compress)
        else:
            backup_path = backup_postgres(database_url, args.output_dir, args.compress)

        # Get backup size
        size_bytes = backup_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        logger.info(f"Backup size: {size_mb:.2f} MB")

        # Cleanup old backups
        cleanup_old_backups(args.output_dir, args.keep)

        print(f"\n✓ Backup successful: {backup_path}")
        return 0

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
