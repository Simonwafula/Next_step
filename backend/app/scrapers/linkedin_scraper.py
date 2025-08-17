"""
LinkedIn Jobs Scraper for NextStep
Scrapes job listings and extracts basic information
"""

import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """
    LinkedIn Jobs scraper
    Note: LinkedIn has strict anti-scraping measures
    This is a basic implementation for educational purposes
    """
    
    def __init__(self):
        super().__init__(
            name="LinkedIn",
            base_url="https://www.linkedin.com/jobs"
        )
        
    def get_job_detail_url(self, job_link: str) -> str:
        """Convert relative LinkedIn URL to absolute"""
        if job_link.startswith('http'):
            return job_link
        return f"https://www.linkedin.com{job_link}"
        
    async def scrape_job_listings(self, search_terms: Optional[List[str]] = None,
                                 location: Optional[str] = None,
                                 limit: int = 50) -> List[Dict]:
        """
        Scrape LinkedIn job listings
        """
        jobs = []
        
        # Build search URL
        search_query = " ".join(search_terms) if search_terms else "software developer"
        location_query = location or "Kenya"
        
        # LinkedIn job search URL structure
        search_url = f"{self.base_url}/search/?keywords={search_query}&location={location_query}"
        
        try:
            html = await self.fetch_page(search_url)
            if not html:
                logger.error(f"Failed to fetch LinkedIn jobs page")
                return jobs
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # LinkedIn job cards selector (may change frequently)
            job_cards = soup.find_all('div', class_=re.compile(r'job-search-card|base-search-card'))
            
            for card in job_cards[:limit]:
                try:
                    # Extract title
                    title_elem = card.find('h3', class_=re.compile(r'base-search-card__title')) or \
                                card.find('a', {'data-tracking-control-name': re.compile(r'public_jobs_jserp-result_search-card')})
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    
                    # Extract link
                    link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                        
                    link = link_elem.get('href')
                    
                    # Extract additional metadata
                    company_elem = card.find('h4', class_=re.compile(r'base-search-card__subtitle'))
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                    
                    location_elem = card.find('span', class_=re.compile(r'job-search-card__location'))
                    job_location = location_elem.get_text(strip=True) if location_elem else location_query
                    
                    job_record = self.create_job_record(
                        title=title,
                        link=link,
                        search_terms=search_terms or [],
                        location=job_location,
                        raw_data={
                            'company': company,
                            'source_location': job_location
                        }
                    )
                    
                    jobs.append(job_record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing LinkedIn job card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping LinkedIn jobs: {e}")
            
        logger.info(f"Scraped {len(jobs)} jobs from LinkedIn")
        return jobs