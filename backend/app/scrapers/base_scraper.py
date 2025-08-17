"""
Base scraper class for NextStep job advisory platform
Scrapers collect only title and link initially, then pass to processing pipeline
"""

import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Base class for all job site scrapers in NextStep platform
    
    Scrapers follow the pattern:
    1. Scrape job listings (title + link only)
    2. Pass to processing pipeline for detailed extraction
    3. Store processed data in database
    """
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'NextStep Job Advisory Bot 1.0 (+https://nextstep.co.ke)'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    @abstractmethod
    async def scrape_job_listings(self, search_terms: Optional[List[str]] = None, 
                                 location: Optional[str] = None,
                                 limit: int = 50) -> List[Dict]:
        """
        Scrape job listings from the specific site
        
        Returns list of basic job data:
        {
            'id': str,
            'title': str,
            'link': str,
            'source': str,
            'scraped_at': datetime,
            'search_terms': List[str],
            'location': str
        }
        """
        pass
        
    @abstractmethod
    def get_job_detail_url(self, job_link: str) -> str:
        """Convert relative URL to absolute URL if needed"""
        pass
        
    async def fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Fetch a web page with error handling and retries
        """
        for attempt in range(retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
        return None
        
    def create_job_record(self, title: str, link: str, **kwargs) -> Dict:
        """
        Create standardized job record for initial storage
        """
        return {
            'id': str(uuid.uuid4()),
            'title': title.strip(),
            'link': self.get_job_detail_url(link),
            'source': self.name,
            'scraped_at': datetime.utcnow(),
            'processed': False,
            'search_terms': kwargs.get('search_terms', []),
            'location': kwargs.get('location', ''),
            'raw_data': kwargs.get('raw_data', {})
        }
        
    async def health_check(self) -> bool:
        """
        Check if the job site is accessible
        """
        try:
            async with self.session.get(self.base_url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False