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
        # Get basic title
        title = self._safe_extract(soup, ['h1'], 'text')
        
        # Get content from printable section
        content_element = soup.find('li', id='printable')
        content_text = content_element.get_text(strip=True) if content_element else ''
        
        # Extract structured information from content
        company, location, salary, deadline, job_type, description = self._parse_myjobmag_content(content_text)
        
        return {
            'url': url,
            'source': 'myjobmag',
            'title': title,
            'company': company,
            'location': location,
            'description': description,
            'requirements': '',  # MyJobMag doesn't separate requirements
            'salary_text': salary,
            'employment_type': job_type,
            'posted_date': '',  # MyJobMag doesn't show posted date
            'application_deadline': deadline,
            'contact_info': self._extract_contact_info(content_text),
            'raw_html': html_content,
            'extracted_at': datetime.utcnow()
        }
        
    async def _extract_jobwebkenya(self, soup: BeautifulSoup, url: str, html_content: str) -> Dict:
        """Extract job details from JobWebKenya"""
        # Get basic title
        title = self._safe_extract(soup, ['h1'], 'text')
        
        # Get content from main section
        content_element = soup.find('div', class_='section single')
        content_text = content_element.get_text(strip=True) if content_element else ''
        
        # Extract structured information from content
        company, location, salary, deadline, job_type, description = self._parse_jobwebkenya_content(content_text)
        
        return {
            'url': url,
            'source': 'jobwebkenya',
            'title': title,
            'company': company,
            'location': location,
            'description': description,
            'requirements': '',  # JobWebKenya doesn't separate requirements
            'salary_text': salary,
            'employment_type': job_type,
            'posted_date': '',  # JobWebKenya doesn't show posted date
            'application_deadline': deadline,
            'contact_info': self._extract_contact_info(content_text),
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
        
    def _parse_myjobmag_content(self, content_text: str) -> tuple:
        """Parse MyJobMag content to extract structured information"""
        import re
        
        # Initialize defaults
        company = location = salary = deadline = job_type = description = ''
        
        # Extract company (before "Read more about this company")
        company_match = re.search(r'(.*?)Read more about this company', content_text, re.DOTALL)
        if company_match:
            company_text = company_match.group(1).strip()
            # Extract the first comma-separated phrase which is usually the company name
            if ',' in company_text:
                company = company_text.split(',')[0].strip()
            else:
                # If no comma, take first reasonable length phrase
                words = company_text.split()
                company = ' '.join(words[:3])  # First 3 words
        else:
            # Fallback: extract from beginning of content
            words = content_text.split()[:3]
            company = ' '.join(words)
        
        # Extract location (more precise pattern)
        location_match = re.search(r'Location([A-Za-z\s]+?)(?:Job|Field|$)', content_text)
        if location_match:
            location = location_match.group(1).strip()
        
        # Extract job type (clean up the pattern)
        job_type_match = re.search(r'Job Type([^\n]+?)(?:Qualification|$)', content_text)
        if job_type_match:
            job_type = job_type_match.group(1).strip()
        
        # Extract salary (look for KSH, KSh patterns)
        salary_match = re.search(r'(?:KSH|KSh)[\s,0-9]+', content_text, re.IGNORECASE)
        if salary_match:
            salary = salary_match.group(0).strip()
        
        # Extract deadline (after "Deadline" or "Closing")
        deadline_match = re.search(r'(?:Deadline|Closing)[\s:]+([^\n]+)', content_text, re.IGNORECASE)
        if deadline_match:
            deadline = deadline_match.group(1).strip()
        
        # Extract description (after "Job Purpose" or "Primary Responsibilities")
        desc_start_patterns = [
            r'Job Purpose[:\s]+(.*?)(?:Primary Responsibilities|Qualifications|Experience|Method of Application|$)',
            r'Primary Responsibilities[:\s]+(.*?)(?:Qualifications|Experience|Method of Application|$)'
        ]
        
        for pattern in desc_start_patterns:
            desc_match = re.search(pattern, content_text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                description = desc_match.group(1).strip()
                # Clean up description - remove excessive whitespace and newlines
                description = re.sub(r'\s+', ' ', description)
                # Limit to first 1000 characters for processing
                if len(description) > 1000:
                    description = description[:1000] + '...'
                break
        
        # If no structured description found, use a portion of the content
        if not description:
            # Take content after company info but before qualifications
            lines = content_text.split('\n')
            desc_lines = []
            skip_lines = ['Qualification', 'Experience', 'Location', 'Job Field', 'Job Purpose']
            capturing = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if any(skip in line for skip in skip_lines):
                    if capturing:
                        break
                    continue
                    
                if line.startswith('Job Purpose') or line.startswith('Primary Responsibilities'):
                    capturing = True
                    if ':' in line:
                        desc_lines.append(line.split(':', 1)[1].strip())
                    continue
                    
                if capturing and len(line) > 20:  # Skip short lines
                    desc_lines.append(line)
                    
            description = ' '.join(desc_lines[:5])  # First 5 meaningful lines
            description = re.sub(r'\s+', ' ', description)  # Clean up whitespace
        
        return company, location, salary, deadline, job_type, description
    
    def _parse_jobwebkenya_content(self, content_text: str) -> tuple:
        """Parse JobWebKenya content to extract structured information"""
        import re
        
        # Initialize defaults
        company = location = salary = deadline = job_type = description = ''
        
        # Extract company (look for company patterns)
        company_patterns = [
            r'Company[:\s]+([^\n]+)',
            r'Employer[:\s]+([^\n]+)',
            r'Organization[:\s]+([^\n]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                break
        
        # Extract location
        location_patterns = [
            r'Location[:\s]+([^\n]+)',
            r'City[:\s]+([^\n]+)',
            r'Town[:\s]+([^\n]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                break
        
        # Extract job type
        job_type_patterns = [
            r'Job Type[:\s]+([^\n]+)',
            r'Type[:\s]+([^\n]+)',
            r'Employment Type[:\s]+([^\n]+)'
        ]
        
        for pattern in job_type_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                job_type = match.group(1).strip()
                break
        
        # Extract salary
        salary_patterns = [
            r'Salary[:\s]+([^\n]+)',
            r'Pay[:\s]+([^\n]+)',
            r'(?:KSH|KSh)[\s,0-9]+',
            r'KES[\s,0-9]+'
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, content_text, re.IGNORECASE)
            if matches:
                salary = matches[0].strip()
                break
        
        # Extract deadline
        deadline_patterns = [
            r'Deadline[:\s]+([^\n]+)',
            r'Closing Date[:\s]+([^\n]+)',
            r'Expires[:\s]+([^\n]+)',
            r'Apply Before[:\s]+([^\n]+)'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                deadline = match.group(1).strip()
                break
        
        # Extract description (look for description sections)
        desc_patterns = [
            r'Description[:\s]+(.*?)(?:Requirements|Qualifications|Skills|$)',
            r'Job Description[:\s]+(.*?)(?:Requirements|Qualifications|Skills|$)',
            r'About the Role[:\s]+(.*?)(?:Requirements|Qualifications|Skills|$)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, content_text, re.DOTALL | re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                description = re.sub(r'\s+', ' ', description)  # Clean up whitespace
                if len(description) > 1000:
                    description = description[:1000] + '...'
                break
        
        return company, location, salary, deadline, job_type, description
    
    def _extract_contact_info(self, content_text: str) -> str:
        """Extract contact information from content"""
        import re
        
        # Look for email addresses
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content_text)
        if email_match:
            return email_match.group(0)
        
        # Look for phone numbers
        phone_match = re.search(r'(?:\+254|0)[7-9]\d{8}', content_text)
        if phone_match:
            return phone_match.group(0)
        
        return ''
    
    def extract_structured_data(self, html_content: str) -> Dict:
        """Extract structured data (JSON-LD, microdata) from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        structured_data = {}
        
        # Extract JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                script_content = getattr(script, 'string', None)
                if script_content:
                    data = json.loads(script_content)
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
