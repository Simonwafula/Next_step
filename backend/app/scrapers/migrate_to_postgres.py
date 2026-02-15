#!/usr/bin/env python3
"""
Migration script to transfer scraped job data from SQLite to PostgreSQL
and integrate with the main application's data model.
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

try:
    from db.database import SessionLocal, engine
    from db.models import Base, JobPost, Organization

    from .config import DB_PATH, TABLE_NAME
except ImportError:
    from app.db.database import SessionLocal, engine
    from app.db.models import Base, JobPost, Organization
    from app.scrapers.config import DB_PATH, TABLE_NAME

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class JobDataMigrator:
    def __init__(self, sqlite_path: str = DB_PATH, table_name: str = TABLE_NAME):
        self.sqlite_path = sqlite_path
        self.table_name = table_name
        self.pg_session: Optional[Session] = None

    def connect_postgres(self):
        """Connect to PostgreSQL database"""
        try:
            Base.metadata.create_all(bind=engine)
            self.pg_session = SessionLocal()
            logging.info("Connected to PostgreSQL database")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL to use as source"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    def get_or_create_organization(self, org_name: str) -> Optional[int]:
        """Get or create organization record"""
        if not org_name or org_name.strip() == "":
            return None

        org_name = org_name.strip()

        org = (
            self.pg_session.query(Organization)
            .filter(Organization.name == org_name)
            .first()
        )

        if not org:
            org = Organization(name=org_name, verified=False)
            self.pg_session.add(org)
            self.pg_session.flush()

        return org.id

    def parse_job_content(self, content: str) -> Dict[str, Any]:
        """Parse job content to extract structured information"""
        parsed = {
            "description_raw": content,
            "requirements_raw": None,
            "organization_name": None,
            "location_raw": None,
            "salary_info": None,
        }

        lines = content.split("\n")
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100 and not line.startswith("http"):
                if any(
                    keyword in line.lower()
                    for keyword in ["company", "ltd", "inc", "corp", "limited"]
                ):
                    parsed["organization_name"] = line
                    break

        return parsed

    def migrate_jobs(self, batch_size: int = 1000) -> int:
        """Migrate jobs from SQLite to PostgreSQL"""
        if not os.path.exists(self.sqlite_path):
            logging.error(f"SQLite database not found at {self.sqlite_path}")
            return 0

        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        try:
            cursor = sqlite_conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total_count = cursor.fetchone()[0]
            logging.info(f"Found {total_count} jobs to migrate")

            migrated_count = 0
            skipped_count = 0

            for offset in range(0, total_count, batch_size):
                cursor.execute(f"""
                    SELECT id, full_link, title, content 
                    FROM {self.table_name} 
                    ORDER BY id 
                    LIMIT {batch_size} OFFSET {offset}
                """)

                batch = cursor.fetchall()
                logging.info(
                    f"Processing batch {offset // batch_size + 1}: {len(batch)} jobs"
                )

                for row in batch:
                    try:
                        existing = (
                            self.pg_session.query(JobPost)
                            .filter(JobPost.url == row["full_link"])
                            .first()
                        )

                        if existing:
                            skipped_count += 1
                            continue

                        parsed_content = self.parse_job_content(row["content"] or "")

                        org_id = None
                        if parsed_content["organization_name"]:
                            org_id = self.get_or_create_organization(
                                parsed_content["organization_name"]
                            )

                        source = self.extract_domain_from_url(row["full_link"])

                        url = row["full_link"] or ""
                        job_post = JobPost(
                            source=source,
                            url=url,
                            source_url=url,
                            application_url=url,
                            first_seen=datetime.utcnow(),
                            last_seen=datetime.utcnow(),
                            org_id=org_id,
                            title_raw=row["title"] or "",
                            description_raw=parsed_content["description_raw"],
                            requirements_raw=parsed_content["requirements_raw"],
                        )

                        self.pg_session.add(job_post)
                        migrated_count += 1

                    except Exception as e:
                        logging.error(f"Error migrating job {row['id']}: {e}")
                        continue

                try:
                    self.pg_session.commit()
                    logging.info(f"Committed batch {offset // batch_size + 1}")
                except Exception as e:
                    logging.error(f"Error committing batch: {e}")
                    self.pg_session.rollback()

            logging.info(
                f"Migration completed: {migrated_count} migrated, {skipped_count} skipped"
            )
            return migrated_count

        except Exception as e:
            logging.error(f"Migration failed: {e}")
            self.pg_session.rollback()
            raise
        finally:
            sqlite_conn.close()

    def close(self):
        """Close database connections"""
        if self.pg_session:
            self.pg_session.close()


def main():
    """Main migration function"""
    migrator = JobDataMigrator()

    try:
        migrator.connect_postgres()
        migrated_count = migrator.migrate_jobs()
        logging.info(f"Successfully migrated {migrated_count} jobs to PostgreSQL")
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main()
