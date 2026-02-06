"""
Job data extraction processor for extracting detailed information from job post URLs
"""

import asyncio
import aiohttp
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
from bs4 import BeautifulSoup
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
                "User-Agent": "NextStep Job Advisory Bot 1.0 (+https://nextstep.co.ke)"
            },
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

            soup = BeautifulSoup(html_content, "html.parser")

            # Extract based on source
            if "brightermonday" in url.lower():
                return await self._extract_brightermonday(soup, url, html_content)
            elif "linkedin" in url.lower():
                return await self._extract_linkedin(soup, url, html_content)
            elif "indeed" in url.lower():
                return await self._extract_indeed(soup, url, html_content)
            elif "careerjet" in url.lower():
                return await self._extract_careerjet(soup, url, html_content)
            elif "myjobmag" in url.lower():
                return await self._extract_myjobmag(soup, url, html_content)
            elif "jobwebkenya" in url.lower():
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
                        wait_time = 2**attempt
                        logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < retries - 1:
                    await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2**attempt)

        return None

    async def _extract_brightermonday(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from BrighterMonday"""
        # BrighterMonday uses article.job__details for job description
        description = self._safe_extract(
            soup,
            [
                "article.job__details",
                ".job-description",
                ".description",
                ".job-content",
            ],
            "html",
        )

        # Also try to extract salary from meta or content
        salary_text = self._safe_extract(
            soup, [".salary", ".job-salary", ".compensation", "[data-salary]"], "text"
        )

        # If no explicit salary, try to find it in the description
        if not salary_text and description:
            # Look for salary patterns in description
            import re

            salary_patterns = [
                r"(?:KSH|KSh|Kshs?|KES)\.?\s*[\d,]+(?:\s*[-–to]+\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*[\d,]+)?",
                r"salary[:\s]+(?:KSH|KSh|Kshs?|KES)?\.?\s*[\d,]+",
            ]
            for pattern in salary_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    salary_text = match.group(0)
                    break

        return {
            "url": url,
            "source": "brightermonday",
            "title": self._safe_extract(
                soup,
                ["h1.job-title", "h1.job__header-title", ".job-header h1", "h1"],
                "text",
            ),
            "company": self._safe_extract(
                soup,
                [
                    ".company-name",
                    ".employer-name",
                    ".job-company",
                    'a[data-cy="job-company"]',
                ],
                "text",
            ),
            "location": self._safe_extract(
                soup,
                [
                    ".job-location",
                    ".location",
                    ".job-meta .location",
                    '[data-cy="job-location"]',
                ],
                "text",
            ),
            "description": description,
            "requirements": self._safe_extract(
                soup, [".job-requirements", ".requirements", ".job-specs"], "html"
            ),
            "salary_text": salary_text,
            "employment_type": self._safe_extract(
                soup,
                [
                    ".employment-type",
                    ".job-type",
                    ".contract-type",
                    '[data-cy="job-type"]',
                ],
                "text",
            ),
            "posted_date": self._safe_extract(
                soup,
                [".posted-date", ".date-posted", ".job-date", '[data-cy="job-date"]'],
                "text",
            ),
            "application_deadline": self._safe_extract(
                soup, [".deadline", ".closing-date", ".expires"], "text"
            ),
            "contact_info": self._safe_extract(
                soup, [".contact-info", ".contact", ".apply-info"], "text"
            ),
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_linkedin(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from LinkedIn"""
        return {
            "url": url,
            "source": "linkedin",
            "title": self._safe_extract(
                soup, ["h1.top-card-layout__title", ".job-title", "h1"], "text"
            ),
            "company": self._safe_extract(
                soup,
                [".topcard__org-name-link", ".company-name", ".job-company"],
                "text",
            ),
            "location": self._safe_extract(
                soup, [".topcard__flavor--bullet", ".job-location", ".location"], "text"
            ),
            "description": self._safe_extract(
                soup, [".description__text", ".job-description", ".description"], "html"
            ),
            "requirements": self._safe_extract(
                soup, [".job-criteria", ".requirements", ".qualifications"], "html"
            ),
            "salary_text": self._safe_extract(
                soup, [".salary-main-rail", ".salary", ".compensation"], "text"
            ),
            "employment_type": self._safe_extract(
                soup, [".job-criteria__text", ".employment-type", ".job-type"], "text"
            ),
            "posted_date": self._safe_extract(
                soup, [".posted-time-ago__text", ".posted-date", ".job-date"], "text"
            ),
            "application_deadline": "",  # LinkedIn rarely shows deadlines
            "contact_info": "",
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_indeed(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from Indeed"""
        return {
            "url": url,
            "source": "indeed",
            "title": self._safe_extract(
                soup, ["h1.jobsearch-JobInfoHeader-title", ".job-title", "h1"], "text"
            ),
            "company": self._safe_extract(
                soup,
                [".jobsearch-InlineCompanyRating", ".company-name", ".job-company"],
                "text",
            ),
            "location": self._safe_extract(
                soup,
                [".jobsearch-JobInfoHeader-subtitle", ".job-location", ".location"],
                "text",
            ),
            "description": self._safe_extract(
                soup,
                ["#jobDescriptionText", ".job-description", ".description"],
                "html",
            ),
            "requirements": self._safe_extract(
                soup, [".jobsearch-JobDescriptionSection", ".requirements"], "html"
            ),
            "salary_text": self._safe_extract(
                soup,
                [".jobsearch-JobMetadataHeader-item", ".salary", ".compensation"],
                "text",
            ),
            "employment_type": self._safe_extract(
                soup, [".jobsearch-JobMetadataHeader-item", ".job-type"], "text"
            ),
            "posted_date": self._safe_extract(
                soup,
                [".jobsearch-JobMetadataFooter", ".posted-date", ".job-date"],
                "text",
            ),
            "application_deadline": "",
            "contact_info": "",
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_careerjet(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from CareerJet"""
        return {
            "url": url,
            "source": "careerjet",
            "title": self._safe_extract(soup, [".job-title", "h1", ".title"], "text"),
            "company": self._safe_extract(
                soup, [".company", ".employer", ".job-company"], "text"
            ),
            "location": self._safe_extract(
                soup, [".location", ".job-location"], "text"
            ),
            "description": self._safe_extract(
                soup, [".job-description", ".description", ".content"], "html"
            ),
            "requirements": self._safe_extract(
                soup, [".requirements", ".qualifications"], "html"
            ),
            "salary_text": self._safe_extract(
                soup, [".salary", ".compensation"], "text"
            ),
            "employment_type": self._safe_extract(
                soup, [".job-type", ".employment-type"], "text"
            ),
            "posted_date": self._safe_extract(soup, [".posted-date", ".date"], "text"),
            "application_deadline": self._safe_extract(
                soup, [".deadline", ".expires"], "text"
            ),
            "contact_info": self._safe_extract(
                soup, [".contact", ".apply-info"], "text"
            ),
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_myjobmag(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from MyJobMag"""
        # Get basic title
        title = self._safe_extract(soup, ["h1"], "text")

        # Get content from printable section
        content_element = soup.find("li", id="printable")
        content_text = (
            content_element.get_text(separator=" ", strip=True)
            if content_element
            else ""
        )

        # Extract company from title (format: "Job Title at Company Name")
        company = self._extract_company_from_title(title)

        # Extract structured information from content
        content_company, location, salary, deadline, job_type, description = (
            self._parse_myjobmag_content(content_text)
        )

        # Use content company if title extraction failed
        if not company and content_company:
            company = content_company

        return {
            "url": url,
            "source": "myjobmag",
            "title": title,
            "company": company,
            "location": location,
            "description": description
            or content_text[:1500],  # Use content as fallback description
            "requirements": "",  # MyJobMag doesn't separate requirements
            "salary_text": salary,
            "employment_type": job_type,
            "posted_date": "",  # MyJobMag doesn't show posted date
            "application_deadline": deadline,
            "contact_info": self._extract_contact_info(content_text),
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_jobwebkenya(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Extract job details from JobWebKenya"""
        # Get basic title
        title = self._safe_extract(soup, ["h1"], "text")

        # Get content from main section
        content_element = soup.find("div", class_="section single")
        content_text = (
            content_element.get_text(separator=" ", strip=True)
            if content_element
            else ""
        )

        # Extract company from title (format: "Job Title at Company Name")
        company = self._extract_company_from_title(title)

        # Extract structured information from content
        content_company, location, salary, deadline, job_type, description = (
            self._parse_jobwebkenya_content(content_text)
        )

        # Use content company if title extraction failed
        if not company and content_company:
            company = content_company

        return {
            "url": url,
            "source": "jobwebkenya",
            "title": title,
            "company": company,
            "location": location,
            "description": description
            or content_text[:1500],  # Use content as fallback description
            "requirements": "",  # JobWebKenya doesn't separate requirements
            "salary_text": salary,
            "employment_type": job_type,
            "posted_date": "",  # JobWebKenya doesn't show posted date
            "application_deadline": deadline,
            "contact_info": self._extract_contact_info(content_text),
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    async def _extract_generic(
        self, soup: BeautifulSoup, url: str, html_content: str
    ) -> Dict:
        """Generic extraction for unknown job sites"""
        return {
            "url": url,
            "source": "generic",
            "title": self._safe_extract(
                soup, ["h1", ".title", ".job-title", '[class*="title"]'], "text"
            ),
            "company": self._safe_extract(
                soup,
                [".company", ".employer", '[class*="company"]', '[class*="employer"]'],
                "text",
            ),
            "location": self._safe_extract(
                soup, [".location", '[class*="location"]'], "text"
            ),
            "description": self._safe_extract(
                soup,
                [
                    ".description",
                    ".content",
                    '[class*="description"]',
                    '[class*="content"]',
                ],
                "html",
            ),
            "requirements": self._safe_extract(
                soup,
                [".requirements", ".qualifications", '[class*="requirement"]'],
                "html",
            ),
            "salary_text": self._safe_extract(
                soup, [".salary", ".compensation", '[class*="salary"]'], "text"
            ),
            "employment_type": self._safe_extract(
                soup, [".job-type", ".employment-type", '[class*="type"]'], "text"
            ),
            "posted_date": self._safe_extract(
                soup, [".date", ".posted", '[class*="date"]'], "text"
            ),
            "application_deadline": self._safe_extract(
                soup, [".deadline", ".expires", '[class*="deadline"]'], "text"
            ),
            "contact_info": self._safe_extract(
                soup, [".contact", '[class*="contact"]'], "text"
            ),
            "raw_html": html_content,
            "extracted_at": datetime.utcnow(),
        }

    def _safe_extract(
        self, soup: BeautifulSoup, selectors: List[str], extract_type: str = "text"
    ) -> str:
        """Safely extract text or HTML from soup using multiple selectors"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if extract_type == "text":
                        return element.get_text(strip=True)
                    elif extract_type == "html":
                        return str(element)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        return ""

    def _extract_company_from_title(self, title: str) -> str:
        """Extract company name from title (format: 'Job Title at Company Name')"""
        if not title:
            return ""

        # Common patterns for company in title
        # Format 1: "Job Title at Company Name"
        if " at " in title.lower():
            parts = title.rsplit(" at ", 1)
            if len(parts) == 2:
                company = parts[1].strip()
                # Clean up common suffixes in parentheses
                if "(" in company:
                    company = company.split("(")[0].strip()
                return company

        # Format 2: "Job Title - Company Name"
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                company = parts[1].strip()
                return company

        return ""

    def _parse_myjobmag_content(self, content_text: str) -> tuple:
        """Parse MyJobMag content to extract structured information"""

        # Initialize defaults
        company = location = salary = deadline = job_type = description = ""

        # Extract company (before "Read more about this company")
        company_match = re.search(r"^([^,]+)", content_text.strip())
        if company_match:
            company_text = company_match.group(1).strip()
            # Clean up - remove common non-company text
            if len(company_text) < 100 and "Read more" not in company_text:
                company = company_text

        # Extract location - improved pattern for MyJobMag format
        # Format: "Location Nairobi Job Field" or "Location Nairobi"
        location_patterns = [
            r"Location\s+([A-Za-z\s,]+?)(?=\s*Job|\s*Field|\s*Qualification|\s*$)",
            r"Location[:\s]+([A-Za-z\s,]+)",
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, content_text, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
                # Clean up trailing words
                location = re.sub(
                    r"\s+(Job|Field|Qualification).*$",
                    "",
                    location,
                    flags=re.IGNORECASE,
                )
                break

        # Extract job type - improved pattern
        # Format: "Job Type Full Time , Onsite"
        job_type_patterns = [
            r"Job Type\s+([^Q\n]+?)(?=\s*Qualification|\s*Experience|\s*Location|\s*$)",
            r"Job Type[:\s]+([^\n]+)",
        ]
        for pattern in job_type_patterns:
            job_type_match = re.search(pattern, content_text, re.IGNORECASE)
            if job_type_match:
                job_type = job_type_match.group(1).strip()
                # Clean up
                job_type = re.sub(r"\s+", " ", job_type).strip(" ,")
                break

        # Extract salary (look for KSH, KSh, KES patterns - more specific)
        # Handle Kenyan format: Kshs. 157, 427 – Kshs. 234, 431/=
        salary_patterns = [
            # Range with /= suffix: Kshs. 157, 427 – Kshs. 234, 431/=
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)\s*[-–]\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)",
            # Single value: KSH 50,000 or Kshs. 157, 427/=
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)",
        ]
        for pattern in salary_patterns:
            salary_match = re.search(pattern, content_text, re.IGNORECASE)
            if salary_match:
                salary = salary_match.group(0).strip()
                # Limit salary text length
                if len(salary) > 80:
                    salary = salary[:80]
                break

        # Extract deadline (after "Deadline" or "Closing" or "Apply Before")
        deadline_patterns = [
            r"(?:Deadline|Closing\s*Date|Apply\s*Before)[:\s]+([^\n]+)",
            r"(?:Deadline|Closing)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pattern in deadline_patterns:
            deadline_match = re.search(pattern, content_text, re.IGNORECASE)
            if deadline_match:
                deadline = deadline_match.group(1).strip()
                break

        # Extract description (after "Job Purpose" or "Primary Responsibilities")
        desc_patterns = [
            r"Job Purpose[:\s]+(.*?)(?=Primary Responsibilities|Qualifications|Experience Required|Method of Application|How to Apply|$)",
            r"Primary Responsibilities[:\s]+(.*?)(?=Qualifications|Experience|Method of Application|How to Apply|$)",
            r"(?:Job\s*)?Description[:\s]+(.*?)(?=Qualifications|Requirements|Experience|How to Apply|$)",
        ]

        for pattern in desc_patterns:
            desc_match = re.search(pattern, content_text, re.DOTALL | re.IGNORECASE)
            if desc_match:
                description = desc_match.group(1).strip()
                # Clean up description - remove excessive whitespace
                description = re.sub(r"\s+", " ", description)
                if len(description) > 1500:
                    description = description[:1500] + "..."
                break

        return company, location, salary, deadline, job_type, description

    def _parse_jobwebkenya_content(self, content_text: str) -> tuple:
        """Parse JobWebKenya content to extract structured information"""

        # Initialize defaults
        company = location = salary = deadline = job_type = description = ""

        # Extract company (look for company patterns)
        # JobWebKenya format: "Company: Company Name"
        company_patterns = [
            r"Company[:\s]+([^\n]+?)(?=\s*Location|\s*State|\s*$)",
            r"Employer[:\s]+([^\n]+?)(?=\s*Location|\s*State|\s*$)",
            r"Organization[:\s]+([^\n]+?)(?=\s*Location|\s*State|\s*$)",
        ]

        for pattern in company_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                break

        # Extract location - JobWebKenya often has separate State field
        # Format: "Location: Kenya State: Nairobi"
        state_match = re.search(
            r"State[:\s]+([^\n]+?)(?=\s*Job|\s*type|\s*category|\s*$)",
            content_text,
            re.IGNORECASE,
        )
        location_match = re.search(
            r"Location[:\s]+([^\n]+?)(?=\s*State|\s*Job|\s*type|\s*$)",
            content_text,
            re.IGNORECASE,
        )

        if state_match:
            location = state_match.group(1).strip()
        elif location_match:
            location = location_match.group(1).strip()

        # Extract job type
        # Format: "Job type: Full-Time"
        job_type_patterns = [
            r"Job\s*type[:\s]+([^\n]+?)(?=\s*Job\s*category|\s*$)",
            r"Employment\s*Type[:\s]+([^\n]+)",
            r"Type[:\s]+([^\n]+?)(?=\s*category|\s*$)",
        ]

        for pattern in job_type_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                job_type = match.group(1).strip()
                break

        # Extract salary - more specific patterns
        # Handle Kenyan format: Kshs. 157, 427 – Kshs. 234, 431/=
        salary_patterns = [
            # Range with /= suffix: Kshs. 157, 427 – Kshs. 234, 431/=
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)\s*[-–]\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)",
            # Single value: KSH 50,000 or Kshs. 157, 427/=
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d{1,3}(?:[,\s]+\d{3})*(?:/=)?)",
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                salary = match.group(0).strip()
                # Limit salary text length
                if len(salary) > 80:
                    salary = salary[:80]
                break

        # Extract deadline
        deadline_patterns = [
            r"Deadline[:\s]+([^\n]+)",
            r"Closing\s*Date[:\s]+([^\n]+)",
            r"Apply\s*Before[:\s]+([^\n]+)",
            r"Expires[:\s]+([^\n]+)",
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                deadline = match.group(1).strip()
                break

        # Extract description
        # JobWebKenya often has content after "Job Description" heading
        desc_patterns = [
            r"Job\s*Description\s+(.*?)(?=Duties|Responsibilities|Requirements|Qualifications|Skills|How to Apply|$)",
            r"Description[:\s]+(.*?)(?=Requirements|Qualifications|Skills|How to Apply|$)",
            r"About\s*(?:the\s*)?Role[:\s]+(.*?)(?=Requirements|Qualifications|Skills|$)",
        ]

        for pattern in desc_patterns:
            match = re.search(pattern, content_text, re.DOTALL | re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                description = re.sub(r"\s+", " ", description)
                if len(description) > 1500:
                    description = description[:1500] + "..."
                break

        return company, location, salary, deadline, job_type, description

    def _extract_contact_info(self, content_text: str) -> str:
        """Extract contact information from content"""

        # Look for email addresses
        email_match = re.search(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content_text
        )
        if email_match:
            return email_match.group(0)

        # Look for phone numbers
        phone_match = re.search(r"(?:\+254|0)[7-9]\d{8}", content_text)
        if phone_match:
            return phone_match.group(0)

        return ""

    def extract_structured_data(self, html_content: str) -> Dict:
        """Extract structured data (JSON-LD, microdata) from HTML"""
        soup = BeautifulSoup(html_content, "html.parser")
        structured_data = {}

        # Extract JSON-LD
        json_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_scripts:
            try:
                script_content = getattr(script, "string", None)
                if script_content:
                    data = json.loads(script_content)
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        structured_data["json_ld"] = data
                        break
            except json.JSONDecodeError:
                continue

        # Extract microdata
        job_posting = soup.find(attrs={"itemtype": "http://schema.org/JobPosting"})
        if job_posting:
            microdata = {}
            for prop in [
                "title",
                "description",
                "datePosted",
                "validThrough",
                "employmentType",
            ]:
                element = job_posting.find(attrs={"itemprop": prop})
                if element:
                    microdata[prop] = element.get_text(strip=True)
            if microdata:
                structured_data["microdata"] = microdata

        return structured_data
