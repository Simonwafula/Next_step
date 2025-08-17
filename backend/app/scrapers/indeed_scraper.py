"""
Indeed Jobs Scraper for NextStep
Scrapes job listings from Indeed Kenya
"""

import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from urllib.parse import urljoin, quote_plus
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class IndeedScraper(BaseScraper):
    """
    Indeed Kenya jobs scraper
    """
    
    def __init__(self):
        super().__init__(
            name="Indeed",
            base_url="https://ke.indeed.com"
        )
        
    def get_job_detail_url(self, job_link: str) -> str:
        """Convert relative Indeed URL to absolute"""
        if job_link.startswith('http'):
            return job_link
        return urljoin(self.base_url, job_link)
        
    async def scrape_job_listings(self, search_terms: Optional[List[str]] = None,
                                 location: Optional[str] = None,
                                 limit: int = 50) -> List[Dict]:
        """
        Scrape Indeed job listings
        """
        jobs = []
        
        # Build search parameters
        search_query = " ".join(search_terms) if search_terms else "software developer"
        location_query = location or "Nairobi, Kenya"
        
        # Indeed search URL
        search_url = f"{self.base_url}/jobs?q={quote_plus(search_query)}&l={quote_plus(location_query)}"
        
        try:
            html = await self.fetch_page(search_url)
            if not html:
                logger.error("Failed to fetch Indeed jobs page")
                return jobs
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Indeed job cards - multiple selectors for robustness
            job_cards = (soup.find_all('div', class_='job_seen_beacon') or 
                        soup.find_all('div', {'data-jk': True}) or
                        soup.find_all('a', {'data-jk': True}))
            
            for card in job_cards[:limit]:
                try:
                    # Extract title
                    title_elem = (card.find('h2', class_='jobTitle') or 
                                 card.find('a', {'data-jk': True}) or
                                 card.find('span', title=True))
                    
                    if not title_elem:
                        continue
                        
                    # Get title text
                    if title_elem.name == 'a':
                        title = title_elem.get('title') or title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                    else:
                        title_link = title_elem.find('a')
                        if not title_link:
                            continue
                        title = title_link.get('title') or title_link.get_text(strip=True)
                        link = title_link.get('href')
                    
                    if not title or not link:
                        continue
                        
                    # Extract company
                    company_elem = (card.find('span', class_='companyName') or
                                   card.find('a', {'data-testid': 'company-name'}))
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                    
                    # Extract location
                    location_elem = card.find('div', {'data-testid': 'job-location'})
                    job_location = location_elem.get_text(strip=True) if location_elem else location_query
                    
                    # Extract salary if available
                    salary_elem = card.find('span', class_='salaryText')
                    salary = salary_elem.get_text(strip=True) if salary_elem else None
                    
                    job_record = self.create_job_record(
                        title=title,
                        link=link,
                        search_terms=search_terms or [],
                        location=job_location,
                        raw_data={
                            'company': company,
                            'salary': salary,
                            'source_location': job_location
                        }
                    )
                    
                    jobs.append(job_record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Indeed job card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping Indeed jobs: {e}")
            
        logger.info(f"Scraped {len(jobs)} jobs from Indeed")
        return jobs