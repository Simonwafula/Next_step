# scrapers/postgres_db.py
import logging
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

# Add the parent directory to the path to import from the main app
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

try:
    from db.database import SessionLocal, engine
    from db.models import Base, JobPost, Organization, Location
except ImportError:
    # Try absolute imports if relative imports fail
    from app.db.database import SessionLocal, engine
    from app.db.models import Base, JobPost, Organization, Location

logging.basicConfig(level=logging.INFO)

class PostgresJobDatabase:
    def __init__(self):
        self.session: Optional[Session] = None

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            # Ensure tables exist
            Base.metadata.create_all(bind=engine)
            self.session = SessionLocal()
            logging.info("Connected to PostgreSQL database")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.session:
            self.session.close()
            logging.info("PostgreSQL database connection closed.")

    def extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL to use as source"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    def get_or_create_organization(self, org_name: str) -> Optional[int]:
        """Get or create organization record"""
        if not org_name or org_name.strip() == "":
            return None
            
        org_name = org_name.strip()
        
        try:
            # Check if organization exists
            org = self.session.query(Organization).filter(
                Organization.name == org_name
            ).first()
            
            if not org:
                org = Organization(name=org_name, verified=False)
                self.session.add(org)
                self.session.flush()  # Get the ID without committing
                
            return org.id
        except Exception as e:
            logging.error(f"Error getting/creating organization '{org_name}': {e}")
            return None

    def parse_job_content(self, content: str) -> Dict[str, Any]:
        """Parse job content to extract structured information"""
        parsed = {
            'description_raw': content,
            'requirements_raw': None,
            'organization_name': None,
            'location_raw': None,
            'salary_info': None
        }
        
        if not content:
            return parsed
        
        # Try to extract organization name from content
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 100 and not line.startswith('http'):
                # Potential company name
                if any(keyword in line.lower() for keyword in ['company', 'ltd', 'inc', 'corp', 'limited']):
                    parsed['organization_name'] = line
                    break
        
        return parsed

    def batch_insert(self, rows: List[Tuple[str, str, str]]) -> int:
        """
        Insert multiple rows into the job_post table.
        `rows` is an iterable of (title, full_link, content) tuples.
        Returns number of new rows inserted.
        """
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")

        inserted = 0
        try:
            for title, link, content in rows:
                try:
                    # Check if job already exists
                    existing = self.session.query(JobPost).filter(
                        JobPost.url == link
                    ).first()
                    
                    if existing:
                        # Update last_seen timestamp
                        existing.last_seen = datetime.utcnow()
                        continue
                    
                    # Parse job content
                    parsed_content = self.parse_job_content(content or "")
                    
                    # Get or create organization
                    org_id = None
                    if parsed_content['organization_name']:
                        org_id = self.get_or_create_organization(parsed_content['organization_name'])
                    
                    # Extract source from URL
                    source = self.extract_domain_from_url(link)
                    
                    # Create job post
                    job_post = JobPost(
                        source=source,
                        url=link,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow(),
                        org_id=org_id,
                        title_raw=title or "",
                        description_raw=parsed_content['description_raw'],
                        requirements_raw=parsed_content['requirements_raw']
                    )
                    
                    self.session.add(job_post)
                    inserted += 1
                    
                except IntegrityError as e:
                    logging.warning(f"Duplicate job URL '{link}': {e}")
                    self.session.rollback()
                    continue
                except Exception as e:
                    logging.error(f"Error inserting job '{title}': {e}")
                    self.session.rollback()
                    continue
            
            # Commit all changes
            self.session.commit()
            logging.info(f"Inserted {inserted} new jobs into PostgreSQL database.")
            
        except Exception as e:
            logging.error(f"Batch insert failed: {e}")
            self.session.rollback()
            raise
            
        return inserted

    def get_job_count(self) -> int:
        """Get total number of jobs in the database"""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            count = self.session.query(JobPost).count()
            return count
        except Exception as e:
            logging.error(f"Error getting job count: {e}")
            return 0

    def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs from the database"""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            jobs = self.session.query(JobPost).order_by(
                JobPost.first_seen.desc()
            ).limit(limit).all()
            
            result = []
            for job in jobs:
                result.append({
                    'id': job.id,
                    'title': job.title_raw,
                    'url': job.url,
                    'source': job.source,
                    'first_seen': job.first_seen,
                    'organization_id': job.org_id
                })
            
            return result
        except Exception as e:
            logging.error(f"Error getting recent jobs: {e}")
            return []
