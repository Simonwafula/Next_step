"""
Data cleaning and normalization processor for job data
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from ..normalization.titles import normalize_title
from ..normalization.skills import extract_skills

logger = logging.getLogger(__name__)

class JobDataCleaner:
    """
    Cleans and normalizes extracted job data
    """
    
    def __init__(self):
        self.salary_patterns = [
            r'ksh?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*ksh?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*ksh?',
            r'ksh?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*ksh?',
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        self.employment_type_mapping = {
            'full time': 'full-time',
            'fulltime': 'full-time',
            'full-time': 'full-time',
            'part time': 'part-time',
            'parttime': 'part-time',
            'part-time': 'part-time',
            'contract': 'contract',
            'temporary': 'temporary',
            'temp': 'temporary',
            'internship': 'internship',
            'intern': 'internship',
            'freelance': 'freelance',
            'consultant': 'contract',
            'permanent': 'full-time',
        }
        
        self.seniority_mapping = {
            'entry level': 'entry',
            'entry-level': 'entry',
            'junior': 'entry',
            'graduate': 'entry',
            'mid level': 'mid',
            'mid-level': 'mid',
            'intermediate': 'mid',
            'senior': 'senior',
            'lead': 'senior',
            'principal': 'senior',
            'manager': 'management',
            'director': 'management',
            'head': 'management',
            'executive': 'executive',
            'c-level': 'executive',
        }
        
    def clean_job_data(self, raw_data: Dict) -> Dict:
        """
        Clean and normalize all job data fields
        
        Args:
            raw_data: Raw extracted job data
            
        Returns:
            Cleaned and normalized job data
        """
        try:
            cleaned_data = {
                'url': raw_data.get('url', ''),
                'source': raw_data.get('source', ''),
                'extracted_at': raw_data.get('extracted_at', datetime.utcnow()),
                'raw_html': raw_data.get('raw_html', ''),
            }
            
            # Clean and normalize title
            title_raw = self._clean_text(raw_data.get('title', ''))
            title_family, title_canonical = normalize_title(title_raw)
            cleaned_data.update({
                'title_raw': title_raw,
                'title_family': title_family,
                'title_canonical': title_canonical,
            })
            
            # Clean company name
            cleaned_data['company_name'] = self._clean_company_name(raw_data.get('company', ''))
            
            # Clean and parse location
            location_data = self._parse_location(raw_data.get('location', ''))
            cleaned_data.update(location_data)
            
            # Clean description and requirements
            description_raw = self._clean_html_text(raw_data.get('description', ''))
            requirements_raw = self._clean_html_text(raw_data.get('requirements', ''))
            
            cleaned_data.update({
                'description_raw': description_raw,
                'requirements_raw': requirements_raw,
            })
            
            # Extract skills from description and requirements
            combined_text = f"{description_raw} {requirements_raw}"
            skills = extract_skills(combined_text)
            cleaned_data['skills'] = skills
            
            # Parse salary information
            salary_data = self._parse_salary(raw_data.get('salary_text', ''))
            cleaned_data.update(salary_data)
            
            # Normalize employment type
            cleaned_data['employment_type'] = self._normalize_employment_type(
                raw_data.get('employment_type', '')
            )
            
            # Extract seniority from title and description
            cleaned_data['seniority'] = self._extract_seniority(title_raw, description_raw)
            
            # Parse dates
            cleaned_data['posted_date'] = self._parse_date(raw_data.get('posted_date', ''))
            cleaned_data['application_deadline'] = self._parse_date(raw_data.get('application_deadline', ''))
            
            # Clean contact info
            cleaned_data['contact_info'] = self._clean_text(raw_data.get('contact_info', ''))
            
            # Extract education requirements
            cleaned_data['education'] = self._extract_education(combined_text)
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Error cleaning job data: {e}")
            return raw_data
            
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ''
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-\.\,\(\)\&\+\#]', '', text)
        
        return text
        
    def _clean_html_text(self, html_text: str) -> str:
        """Clean HTML text content"""
        if not html_text:
            return ''
            
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_text)
        
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
        
    def _clean_company_name(self, company: str) -> str:
        """Clean and normalize company name"""
        if not company:
            return ''
            
        company = self._clean_text(company)
        
        # Remove common suffixes
        suffixes = ['ltd', 'limited', 'inc', 'incorporated', 'corp', 'corporation', 'llc', 'plc']
        for suffix in suffixes:
            pattern = rf'\b{suffix}\.?\b'
            company = re.sub(pattern, '', company, flags=re.IGNORECASE)
            
        return company.strip()
        
    def _parse_location(self, location: str) -> Dict:
        """Parse location string into structured data"""
        if not location:
            return {
                'location_raw': '',
                'country': None,
                'region': None,
                'city': None,
            }
            
        location_clean = self._clean_text(location)
        
        # Common Kenya locations
        kenya_cities = [
            'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika', 'malindi',
            'kitale', 'garissa', 'kakamega', 'machakos', 'meru', 'nyeri', 'kericho'
        ]
        
        city = None
        region = None
        country = 'Kenya'  # Default for Kenyan job sites
        
        location_lower = location_clean.lower()
        
        # Extract city
        for city_name in kenya_cities:
            if city_name in location_lower:
                city = city_name.title()
                break
                
        # Extract region/county
        if 'nairobi' in location_lower:
            region = 'Nairobi'
        elif 'mombasa' in location_lower:
            region = 'Mombasa'
        elif 'central' in location_lower:
            region = 'Central'
        elif 'western' in location_lower:
            region = 'Western'
        elif 'eastern' in location_lower:
            region = 'Eastern'
        elif 'nyanza' in location_lower:
            region = 'Nyanza'
        elif 'rift valley' in location_lower:
            region = 'Rift Valley'
        elif 'coast' in location_lower:
            region = 'Coast'
        elif 'north eastern' in location_lower:
            region = 'North Eastern'
            
        return {
            'location_raw': location_clean,
            'country': country,
            'region': region,
            'city': city,
        }
        
    def _parse_salary(self, salary_text: str) -> Dict:
        """Parse salary information"""
        if not salary_text:
            return {
                'salary_min': None,
                'salary_max': None,
                'currency': None,
                'salary_period': None,
            }
            
        salary_clean = salary_text.lower().replace(',', '')
        
        # Determine currency
        currency = 'KES'  # Default
        if '$' in salary_text or 'usd' in salary_clean:
            currency = 'USD'
        elif '€' in salary_text or 'eur' in salary_clean:
            currency = 'EUR'
        elif '£' in salary_text or 'gbp' in salary_clean:
            currency = 'GBP'
            
        # Determine period
        salary_period = 'monthly'  # Default
        if any(word in salary_clean for word in ['annual', 'yearly', 'year', 'per year']):
            salary_period = 'annual'
        elif any(word in salary_clean for word in ['hourly', 'hour', 'per hour']):
            salary_period = 'hourly'
        elif any(word in salary_clean for word in ['daily', 'day', 'per day']):
            salary_period = 'daily'
            
        # Extract salary amounts
        salary_min = None
        salary_max = None
        
        for pattern in self.salary_patterns:
            match = re.search(pattern, salary_clean, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # Range
                    try:
                        salary_min = float(groups[0].replace(',', ''))
                        salary_max = float(groups[1].replace(',', ''))
                    except ValueError:
                        continue
                elif len(groups) == 1:  # Single value
                    try:
                        salary_min = float(groups[0].replace(',', ''))
                        salary_max = salary_min
                    except ValueError:
                        continue
                break
                
        return {
            'salary_min': salary_min,
            'salary_max': salary_max,
            'currency': currency,
            'salary_period': salary_period,
        }
        
    def _normalize_employment_type(self, employment_type: str) -> Optional[str]:
        """Normalize employment type"""
        if not employment_type:
            return None
            
        employment_clean = employment_type.lower().strip()
        
        for key, normalized in self.employment_type_mapping.items():
            if key in employment_clean:
                return normalized
                
        return employment_clean if employment_clean else None
        
    def _extract_seniority(self, title: str, description: str) -> Optional[str]:
        """Extract seniority level from title and description"""
        combined_text = f"{title} {description}".lower()
        
        for key, seniority in self.seniority_mapping.items():
            if key in combined_text:
                return seniority
                
        # Default based on common patterns
        if any(word in combined_text for word in ['junior', 'graduate', 'entry', 'trainee']):
            return 'entry'
        elif any(word in combined_text for word in ['senior', 'lead', 'principal']):
            return 'senior'
        elif any(word in combined_text for word in ['manager', 'director', 'head']):
            return 'management'
            
        return 'mid'  # Default
        
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
            
        date_clean = date_str.lower().strip()
        
        # Handle relative dates
        if 'today' in date_clean:
            return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif 'yesterday' in date_clean:
            return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif 'ago' in date_clean:
            # Extract number of days/hours ago
            match = re.search(r'(\d+)\s*(day|hour|week|month)', date_clean)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                
                if unit == 'day':
                    return datetime.utcnow() - timedelta(days=num)
                elif unit == 'hour':
                    return datetime.utcnow() - timedelta(hours=num)
                elif unit == 'week':
                    return datetime.utcnow() - timedelta(weeks=num)
                elif unit == 'month':
                    return datetime.utcnow() - timedelta(days=num * 30)
                    
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_clean, fmt)
            except ValueError:
                continue
                
        return None
        
    def _extract_education(self, text: str) -> Optional[str]:
        """Extract education requirements from text"""
        if not text:
            return None
            
        text_lower = text.lower()
        
        # Education levels
        education_levels = [
            'phd', 'doctorate', 'doctoral',
            'masters', 'master\'s', 'msc', 'mba', 'ma',
            'bachelors', 'bachelor\'s', 'degree', 'bsc', 'ba',
            'diploma', 'certificate', 'certification',
            'high school', 'secondary', 'kcse',
        ]
        
        for level in education_levels:
            if level in text_lower:
                if level in ['phd', 'doctorate', 'doctoral']:
                    return 'doctorate'
                elif level in ['masters', 'master\'s', 'msc', 'mba', 'ma']:
                    return 'masters'
                elif level in ['bachelors', 'bachelor\'s', 'degree', 'bsc', 'ba']:
                    return 'bachelors'
                elif level in ['diploma']:
                    return 'diploma'
                elif level in ['certificate', 'certification']:
                    return 'certificate'
                elif level in ['high school', 'secondary', 'kcse']:
                    return 'secondary'
                    
        return None
