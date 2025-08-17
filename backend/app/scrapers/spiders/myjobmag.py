import logging
import sqlite3
import urllib3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class JobListing:
    """Simple data class for job information"""
    title: str
    full_link: str
    content: str = ''

class Database:
    def __init__(self, db_path: str = 'jobs.sqlite3'):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Create database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.setup_tables()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def setup_tables(self):
        """Set up database tables"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS jobs_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_link TEXT UNIQUE,
            title TEXT,
            content TEXT
        )
        ''')
        self.conn.commit()

    def batch_insert(self, jobs: List[JobListing]) -> int:
        """Insert a batch of jobs and return number of successful insertions"""
        cursor = self.conn.cursor()
        inserted = 0
        
        for job in jobs:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO jobs_data (title, full_link, content)
                    VALUES (?, ?, ?)
                ''', (job.title, job.full_link, job.content))
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.Error as e:
                logging.error(f"Error inserting job {job.title}: {e}")
        
        self.conn.commit()
        return inserted

class RequestsClient:
    """Handle HTTP requests with retry logic"""
    def __init__(self, retries: int = 3, backoff_factor: float = 0.3):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

class JobScraper:
    def __init__(self, base_url: str = "https://www.myjobmag.co.ke"):
        self.base_url = base_url
        self.client = RequestsClient()
        self.db = Database()

    def parse_job_content(self, html: str) -> str:
        """Extract job content from the job page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            job_content = soup.find('li', id='printable')
            return job_content.text.strip() if job_content else ''
        except Exception as e:
            logging.error(f"Error parsing job content: {e}")
            return ''

    def fetch_job_listings(self, page: int) -> List[JobListing]:
        """Fetch and parse job listings from a single page"""
        url = f"{self.base_url}/jobs/page/{page}"
        response = self.client.get(url)
        if not response:
            return []

        listings = []
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for job in soup.find_all('li', class_='mag-b'):
            try:
                title = job.text.strip()
                link_tag = job.find('a')
                if not link_tag:
                    continue
                    
                full_link = urljoin(self.base_url, link_tag.get('href'))
                listings.append(JobListing(title=title, full_link=full_link))
                
            except Exception as e:
                logging.error(f"Error parsing job listing: {e}")
                continue

        return listings

    def process_job(self, job: JobListing) -> JobListing:
        """Fetch and add content to a job listing"""
        response = self.client.get(job.full_link)
        if response:
            job.content = self.parse_job_content(response.text)
        return job

    def scrape(self, start_page: int = 1, end_page: int = 3764, 
               max_workers: int = 10, batch_size: int = 20):
        """Main scraping method using thread pool for concurrent processing"""
        logging.info(f"Starting scraping from page {start_page} to {end_page}")
        self.db.connect()
        
        try:
            for page in range(start_page, end_page + 1):
                logging.info(f"Processing page {page}")
                job_listings = self.fetch_job_listings(page)
                
                if not job_listings:
                    logging.warning(f"No jobs found on page {page}")
                    continue

                # Process job details concurrently
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_job = {
                        executor.submit(self.process_job, job): job 
                        for job in job_listings
                    }

                    completed_jobs = []
                    for future in as_completed(future_to_job):
                        try:
                            job = future.result()
                            completed_jobs.append(job)
                            
                            if len(completed_jobs) >= batch_size:
                                inserted = self.db.batch_insert(completed_jobs)
                                logging.info(f"Inserted {inserted} jobs from batch")
                                completed_jobs = []
                                
                        except Exception as e:
                            logging.error(f"Error processing job: {e}")

                    # Insert any remaining jobs
                    if completed_jobs:
                        inserted = self.db.batch_insert(completed_jobs)
                        logging.info(f"Inserted {inserted} jobs from final batch")

                sleep(1)  # Pause between pages
                
        finally:
            self.db.close()

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scraper.log')
        ]
    )

if __name__ == '__main__':
    setup_logging()
    try:
        scraper = JobScraper()
        scraper.scrape(start_page=1, end_page=3764, max_workers=10)
        logging.info("Scraping completed successfully!")
    except Exception as e:
        logging.error(f"Fatal error in main script execution: {e}", exc_info=True)