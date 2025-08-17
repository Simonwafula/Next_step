"""
Job data extraction processor for extracting detailed information from job post URLs
"""

import asyncio
import aiohttp
import re
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json

logger = logging.getLogger(__name__)

class JobDataExtractor:
    """
    Extracts detailed job information from job post URLs
    """
    
    def __init__(self):
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
            
    async def extract_job_details(self, url: str, source: str) -> Optional[Dict]:
        """
        Extract detailed job information from a job post URL
        
        Returns:
        {
            'url': str,
            'source': str,
            'title': str,
            'company': str,
            'location': str,
            'description': str,
            'requirements': str,
            'salary_text': str,
            'employment_type': str,
            'posted_date': str,
            'application_deadline': str,
            'contact_info': str,
            'raw_html': str,
            'extracted_at': datetime
        }
        """
        try:
            html_content = await self._fetch_page(url)
            if not html_content:
                return None
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract based on source
            if 'brightermonday' in url.lower():
                return await self._extract_brightermonday(soup, url, html_content)
            elif 'linkedin' in url.lower():
                return await self._extract_linkedin(soup, url, html_content)
            elif 'indeed' in url.lower():
                return await self._extract_indeed(soup, url, html_content)
            elif 'careerjet' in url.lower():
                return await self._extract_careerjet(soup, url, html_content)
            elif 'myjobmag' in url.lower():
                return await self._extract_myjobmag(soup, url, html_content)
            elif 'jobwebkenya' in url.lower():
                return await self._extract_jobwebkenya(soup, url, html_content)
            else:
                return await self._extract_generic(soup, url, html_content)
                
        except Exception as e:
            logger.error(f"Error extracting job details from {url}: {e}")
            return None
            
    async def _fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch a web page with error handling and retries"""
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
        
    async def _extract_brightermonday(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from BrighterMonday"""
        return {
            'url': url,
            'source': 'brightermonday',
            'title': self._safe_extract(soup, ['h1.job-title', '.job-header h1', 'h1'], 'text'),
            'company': self._safe_extract(soup, ['.company-name', '.employer-name', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.job-location', '.location', '.job-meta .location'], 'text'),
            'description': self._safe_extract(soup, ['.job-description', '.description', '.job-content'], 'html'),
            'requirements': self._safe_extract(soup, ['.job-requirements', '.requirements', '.job-specs'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary', '.job-salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.employment-type', '.job-type', '.contract-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.posted-date', '.date-posted', '.job-date'], 'text'),
            'application_deadline': self._safe_extract(soup, ['.deadline', '.closing-date', '.expires'], 'text'),
            'contact_info': self._safe_extract(soup, ['.contact-info', '.contact', '.apply-info'], 'text'),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_linkedin(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from LinkedIn"""
        return {
            'url': url,
            'source': 'linkedin',
            'title': self._safe_extract(soup, ['h1.top-card-layout__title', '.job-title', 'h1'], 'text'),
            'company': self._safe_extract(soup, ['.topcard__org-name-link', '.company-name', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.topcard__flavor--bullet', '.job-location', '.location'], 'text'),
            'description': self._safe_extract(soup, ['.description__text', '.job-description', '.description'], 'html'),
            'requirements': self._safe_extract(soup, ['.job-criteria', '.requirements', '.qualifications'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary-main-rail', '.salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.job-criteria__text', '.employment-type', '.job-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.posted-time-ago__text', '.posted-date', '.job-date'], 'text'),
            'application_deadline': '',  # LinkedIn rarely shows deadlines
            'contact_info': '',
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_indeed(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from Indeed"""
        return {
            'url': url,
            'source': 'indeed',
            'title': self._safe_extract(soup, ['h1.jobsearch-JobInfoHeader-title', '.job-title', 'h1'], 'text'),
            'company': self._safe_extract(soup, ['.jobsearch-InlineCompanyRating', '.company-name', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.jobsearch-JobInfoHeader-subtitle', '.job-location', '.location'], 'text'),
            'description': self._safe_extract(soup, ['#jobDescriptionText', '.job-description', '.description'], 'html'),
            'requirements': self._safe_extract(soup, ['.jobsearch-JobDescriptionSection', '.requirements'], 'html'),
            'salary_text': self._safe_extract(soup, ['.jobsearch-JobMetadataHeader-item', '.salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.jobsearch-JobMetadataHeader-item', '.job-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.jobsearch-JobMetadataFooter', '.posted-date', '.job-date'], 'text'),
            'application_deadline': '',
            'contact_info': '',
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_careerjet(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from CareerJet"""
        return {
            'url': url,
            'source': 'careerjet',
            'title': self._safe_extract(soup, ['.job-title', 'h1', '.title'], 'text'),
            'company': self._safe_extract(soup, ['.company', '.employer', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.location', '.job-location'], 'text'),
            'description': self._safe_extract(soup, ['.job-description', '.description', '.content'], 'html'),
            'requirements': self._safe_extract(soup, ['.requirements', '.qualifications'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.job-type', '.employment-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.posted-date', '.date'], 'text'),
            'application_deadline': self._safe_extract(soup, ['.deadline', '.expires'], 'text'),
            'contact_info': self._safe_extract(soup, ['.contact', '.apply-info'], 'text'),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_myjobmag(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from MyJobMag"""
        return {
            'url': url,
            'source': 'myjobmag',
            'title': self._safe_extract(soup, ['.job-title', 'h1', '.title'], 'text'),
            'company': self._safe_extract(soup, ['.company-name', '.employer', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.job-location', '.location'], 'text'),
            'description': self._safe_extract(soup, ['.job-description', '.description', '.content'], 'html'),
            'requirements': self._safe_extract(soup, ['.job-requirements', '.requirements'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.job-type', '.employment-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.posted-date', '.date'], 'text'),
            'application_deadline': self._safe_extract(soup, ['.deadline', '.closing-date'], 'text'),
            'contact_info': self._safe_extract(soup, ['.contact-info', '.contact'], 'text'),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_jobwebkenya(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from JobWebKenya"""
        return {
            'url': url,
            'source': 'jobwebkenya',
            'title': self._safe_extract(soup, ['.job-title', 'h1', '.title'], 'text'),
            'company': self._safe_extract(soup, ['.company-name', '.employer', '.job-company'], 'text'),
            'location': self._safe_extract(soup, ['.job-location', '.location'], 'text'),
            'description': self._safe_extract(soup, ['.job-description', '.description', '.content'], 'html'),
            'requirements': self._safe_extract(soup, ['.job-requirements', '.requirements'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary', '.compensation'], 'text'),
            'employment_type': self._safe_extract(soup, ['.job-type', '.employment-type'], 'text'),
            'posted_date': self._safe_extract(soup, ['.posted-date', '.date'], 'text'),
            'application_deadline': self._safe_extract(soup, ['.deadline', '.closing-date'], 'text'),
            'contact_info': self._safe_extract(soup, ['.contact-info', '.contact'], 'text'),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_generic(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Generic extraction for unknown job sites"""
        return {
            'url': url,
            'source': 'generic',
            'title': self._safe_extract(soup, ['h1', '.title', '.job-title', '[class*="title"]'], 'text'),
            'company': self._safe_extract(soup, ['.company', '.employer', '[class*="company"]', '[class*="employer"]'], 'text'),
            'location': self._safe_extract(soup, ['.location', '[class*="location"]'], 'text'),
            'description': self._safe_extract(soup, ['.description', '.content', '[class*="description"]', '[class*="content"]'], 'html'),
            'requirements': self._safe_extract(soup, ['.requirements', '.qualifications', '[class*="requirement"]'], 'html'),
            'salary_text': self._safe_extract(soup, ['.salary', '.compensation', '[class*="salary"]'], 'text'),
            'employment_type': self._safe_extract(soup, ['.job-type', '.employment-type', '[class*="type"]'], 'text'),
            'posted_date': self._safe_extract(soup, ['.date', '.posted', '[class*="date"]'], 'text'),
            'application_deadline': self._safe_extract(soup, ['.deadline', '.expires', '[class*="deadline"]'], 'text'),
            'contact_info': self._safe_extract(soup, ['.contact', '[class*="contact"]'], 'text'),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    def _safe_extract(self, soup: BeautifulSoup, selectors: List[str], extract_type: str = 'text') -> str:
        """Safely extract text or HTML from soup using multiple selectors"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if extract_type == 'text':
                        return element.get_text(strip=True)
                    elif extract_type == 'html':
                        return str(element)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        return ''
        
    def extract_structured_data(self, html_content: str) -> Dict:
        """Extract structured data (JSON-LD, microdata) from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        structured_data = {}
        
        # Extract JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    structured_data['json_ld'] = data
                    break
            except json.JSONDecodeError:
                continue
                
        # Extract microdata
        job_posting = soup.find(attrs={'itemtype': 'http://schema.org/JobPosting'})
        if job_posting:
            microdata = {}
            for prop in ['title', 'description', 'datePosted', 'validThrough', 'employmentType']:
                element = job_posting.find(attrs={'itemprop': prop})
                if element:
                    microdata[prop] = element.get_text(strip=True)
            if microdata:
                structured_data['microdata'] = microdata
                
        return structured_data
