"""
BrighterMonday Jobs Scraper for NextStep
Scrapes job listings from BrighterMonday Kenya
"""

import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from urllib.parse import urljoin, quote_plus
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BrighterMondayScraper(BaseScraper):
    """
    BrighterMonday Kenya jobs scraper
    """
    
    def __init__(self):
        super().__init__(
            name="BrighterMonday",
            base_url="https://www.brightermonday.co.ke"
        )
        
    def get_job_detail_url(self, job_link: str) -> str:
        """Convert relative BrighterMonday URL to absolute"""
        if job_link.startswith('http'):
            return job_link
        return urljoin(self.base_url, job_link)
        
    async def scrape_job_listings(self, search_terms: Optional[List[str]] = None,
                                 location: Optional[str] = None,
                                 limit: int = 50) -> List[Dict]:
        """
        Scrape BrighterMonday job listings
        """
        jobs = []
        
        # Build search parameters
        search_query = " ".join(search_terms) if search_terms else "software"
        location_query = location or "Nairobi"
        
        # BrighterMonday search URL
        search_url = f"{self.base_url}/jobs/search?q={quote_plus(search_query)}"
        
        try:
            html = await self.fetch_page(search_url)
            if not html:
                logger.error("Failed to fetch BrighterMonday jobs page")
                return jobs
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # BrighterMonday job cards
            job_cards = (soup.find_all('div', class_='job-item') or
                        soup.find_all('div', class_='search-job') or
                        soup.find_all('article', class_='job'))
            
            for card in job_cards[:limit]:
                try:
                    # Extract title and link
                    title_elem = (card.find('h3') or card.find('h2') or
                                 card.find('a', class_='job-title'))
                    
                    if not title_elem:
                        # Try alternative selectors
                        title_elem = card.find('a', href=re.compile(r'/jobs/'))
                        
                    if not title_elem:
                        continue
                        
                    # Get title and link
                    if title_elem.name == 'a':
                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href')
                    else:
                        link_elem = title_elem.find('a')
                        if not link_elem:
                            continue
                        title = link_elem.get_text(strip=True)
                        link = link_elem.get('href')
                    
                    if not title or not link:
                        continue
                        
                    # Extract company
                    company_elem = (card.find('div', class_='company') or
                                   card.find('span', class_='company-name') or
                                   card.find('p', class_='company'))
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                    
                    # Extract location
                    location_elem = (card.find('div', class_='location') or
                                    card.find('span', class_='location'))
                    job_location = location_elem.get_text(strip=True) if location_elem else location_query
                    
                    # Extract job type if available
                    job_type_elem = card.find('span', class_='job-type')
                    job_type = job_type_elem.get_text(strip=True) if job_type_elem else None
                    
                    # Extract deadline if available
                    deadline_elem = card.find('div', class_='deadline')
                    deadline = deadline_elem.get_text(strip=True) if deadline_elem else None
                    
                    job_record = self.create_job_record(
                        title=title,
                        link=link,
                        search_terms=search_terms or [],
                        location=job_location,
                        raw_data={
                            'company': company,
                            'job_type': job_type,
                            'deadline': deadline,
                            'source_location': job_location
                        }
                    )
                    
                    jobs.append(job_record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing BrighterMonday job card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping BrighterMonday jobs: {e}")
            
        logger.info(f"Scraped {len(jobs)} jobs from BrighterMonday")
        return jobs