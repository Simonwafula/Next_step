"""
Enhanced Job Deduplication Service

This service provides advanced deduplication logic for job postings including:
- URL normalization and matching
- Fuzzy title matching
- Content similarity using embeddings
- Company + title + location composite matching
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from difflib import SequenceMatcher
from datetime import datetime
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import JobPost, Organization
from ..ml.embeddings import generate_embeddings

logger = logging.getLogger(__name__)


class DeduplicationService:
    """
    Advanced job deduplication service with multiple matching strategies
    """

    # Similarity thresholds
    URL_SIMILARITY_THRESHOLD = 0.85
    TITLE_SIMILARITY_THRESHOLD = 0.80
    CONTENT_SIMILARITY_THRESHOLD = 0.90
    FUZZY_MATCH_THRESHOLD = 0.85

    def __init__(self):
        """Initialize deduplication service"""
        self.url_params_to_remove = [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "source",
            "referrer",
            "tracking",
            "track",
            "campaign",
            "fbclid",
            "gclid",
            "msclkid",
            "_ga",
            "mc_cid",
            "mc_eid",
        ]

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing tracking parameters and standardizing format

        Args:
            url: Raw URL string

        Returns:
            Normalized URL string
        """
        if not url:
            return ""

        try:
            # Parse URL
            parsed = urlparse(url.lower().strip())

            # Remove tracking parameters
            query_params = parse_qs(parsed.query)
            cleaned_params = {
                k: v
                for k, v in query_params.items()
                if k not in self.url_params_to_remove
            }

            # Rebuild query string
            new_query = urlencode(cleaned_params, doseq=True)

            # Remove common URL variations
            path = parsed.path.rstrip("/")

            # Rebuild URL without tracking params
            normalized = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    path,
                    parsed.params,
                    new_query,
                    "",  # Remove fragment
                )
            )

            return normalized

        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url.lower().strip()

    def generate_url_hash(self, url: str) -> str:
        """
        Generate a hash from normalized URL for quick lookups

        Args:
            url: URL string

        Returns:
            MD5 hash of normalized URL
        """
        normalized = self.normalize_url(url)
        return hashlib.md5(normalized.encode()).hexdigest()

    def normalize_title(self, title: str) -> str:
        """
        Normalize job title for comparison

        Args:
            title: Raw job title

        Returns:
            Normalized title string
        """
        if not title:
            return ""

        # Convert to lowercase
        title = title.lower().strip()

        # Remove common prefixes/suffixes
        patterns_to_remove = [
            r"^jobs?\s+at\s+",
            r"^vacancies\s+at\s+",
            r"^careers?\s+at\s+",
            r"^positions?\s+at\s+",
            r"^openings?\s+at\s+",
            r"\s*-\s*urgent$",
            r"\s*-\s*immediate\s+hire$",
            r"\s*\(.*?\)\s*$",  # Remove parenthetical content
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Normalize whitespace
        title = re.sub(r"\s+", " ", title).strip()

        # Remove special characters but keep alphanumeric and basic punctuation
        title = re.sub(r"[^\w\s\-&+]", "", title)

        return title

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two job titles

        Args:
            title1: First job title
            title2: Second job title

        Returns:
            Similarity score between 0 and 1
        """
        if not title1 or not title2:
            return 0.0

        # Normalize both titles
        norm_title1 = self.normalize_title(title1)
        norm_title2 = self.normalize_title(title2)

        # Use SequenceMatcher for fuzzy string matching
        similarity = SequenceMatcher(None, norm_title1, norm_title2).ratio()

        return similarity

    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate content similarity using embeddings

        Args:
            content1: First content text
            content2: Second content text

        Returns:
            Cosine similarity between 0 and 1
        """
        if not content1 or not content2:
            return 0.0

        try:
            # Generate embeddings for both texts
            embeddings = generate_embeddings([content1, content2])

            if len(embeddings) != 2:
                return 0.0

            # Calculate cosine similarity
            embedding1, embedding2 = embeddings

            import numpy as np

            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Normalize to 0-1 range (cosine similarity is -1 to 1)
            return (similarity + 1) / 2

        except Exception as e:
            logger.warning(f"Error calculating content similarity: {e}")
            return 0.0

    async def find_duplicate_by_url(
        self, db: AsyncSession, url: str
    ) -> Optional[JobPost]:
        """
        Find existing job by exact URL match (after normalization)

        Args:
            db: Database session
            url: Job URL

        Returns:
            Existing JobPost or None
        """
        url_hash = self.generate_url_hash(url)

        try:
            result = await db.execute(
                select(JobPost).where(JobPost.url_hash == url_hash)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error finding duplicate by URL: {e}")
            return None

    async def find_duplicates_by_title_company(
        self,
        db: AsyncSession,
        title: str,
        company_name: Optional[str] = None,
        location_id: Optional[int] = None,
        days_lookback: int = 30,
    ) -> List[Tuple[JobPost, float]]:
        """
        Find potential duplicates by fuzzy title matching + company + location

        Args:
            db: Database session
            title: Job title
            company_name: Company name (optional)
            location_id: Location ID (optional)
            days_lookback: How many days to look back for duplicates

        Returns:
            List of (JobPost, similarity_score) tuples
        """
        if not title:
            return []

        try:
            # Build query
            query = select(JobPost)

            # Filter by company if provided
            if company_name:
                org_query = select(Organization.id).where(
                    func.lower(Organization.name) == company_name.lower()
                )
                org_result = await db.execute(org_query)
                org_id = org_result.scalar_one_or_none()

                if org_id:
                    query = query.where(JobPost.org_id == org_id)

            # Filter by location if provided
            if location_id:
                query = query.where(JobPost.location_id == location_id)

            # Only look at recent jobs
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
            query = query.where(JobPost.first_seen >= cutoff_date)

            # Limit to reasonable number
            query = query.limit(100)

            result = await db.execute(query)
            candidates = result.scalars().all()

            # Calculate similarity for each candidate
            matches = []
            for candidate in candidates:
                similarity = self.calculate_title_similarity(title, candidate.title_raw)
                if similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                    matches.append((candidate, similarity))

            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)

            return matches

        except Exception as e:
            logger.error(f"Error finding duplicates by title/company: {e}")
            return []

    async def find_duplicates_by_content(
        self,
        db: AsyncSession,
        content: str,
        org_id: Optional[int] = None,
        days_lookback: int = 30,
    ) -> List[Tuple[JobPost, float]]:
        """
        Find duplicates using content similarity (embeddings)

        Args:
            db: Database session
            content: Job description/content
            org_id: Organization ID (optional)
            days_lookback: How many days to look back

        Returns:
            List of (JobPost, similarity_score) tuples
        """
        if not content or len(content.strip()) < 50:
            return []

        try:
            # Generate embedding for input content
            embeddings = generate_embeddings([content])
            if not embeddings or len(embeddings) == 0:
                return []

            input_embedding = embeddings[0]

            # Build query for recent jobs
            query = select(JobPost).where(JobPost.embedding.isnot(None))

            if org_id:
                query = query.where(JobPost.org_id == org_id)

            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
            query = query.where(JobPost.first_seen >= cutoff_date)

            query = query.limit(100)

            result = await db.execute(query)
            candidates = result.scalars().all()

            # Calculate content similarity
            matches = []
            for candidate in candidates:
                if candidate.embedding is None:
                    continue

                # Calculate cosine similarity
                import numpy as np

                similarity = np.dot(input_embedding, candidate.embedding) / (
                    np.linalg.norm(input_embedding)
                    * np.linalg.norm(candidate.embedding)
                )

                # Normalize to 0-1
                similarity = (similarity + 1) / 2

                if similarity >= self.CONTENT_SIMILARITY_THRESHOLD:
                    matches.append((candidate, similarity))

            # Sort by similarity
            matches.sort(key=lambda x: x[1], reverse=True)

            return matches

        except Exception as e:
            logger.error(f"Error finding duplicates by content: {e}")
            return []

    async def find_all_duplicates(
        self,
        db: AsyncSession,
        url: str,
        title: str,
        content: str,
        company_name: Optional[str] = None,
        location_id: Optional[int] = None,
        org_id: Optional[int] = None,
    ) -> Dict:
        """
        Comprehensive duplicate detection using all strategies

        Args:
            db: Database session
            url: Job URL
            title: Job title
            content: Job content/description
            company_name: Company name
            location_id: Location ID
            org_id: Organization ID

        Returns:
            Dictionary with duplicate detection results
        """
        results = {
            "is_duplicate": False,
            "duplicate_type": None,
            "duplicate_job": None,
            "confidence": 0.0,
            "matches": {"url": None, "title_company": [], "content": []},
        }

        # 1. Check exact URL match (highest priority)
        url_match = await self.find_duplicate_by_url(db, url)
        if url_match:
            results["is_duplicate"] = True
            results["duplicate_type"] = "exact_url"
            results["duplicate_job"] = url_match
            results["confidence"] = 1.0
            results["matches"]["url"] = url_match
            return results

        # 2. Check fuzzy title + company match
        title_matches = await self.find_duplicates_by_title_company(
            db, title, company_name, location_id
        )
        results["matches"]["title_company"] = title_matches

        if title_matches and title_matches[0][1] >= 0.95:
            # Very high title similarity with same company
            results["is_duplicate"] = True
            results["duplicate_type"] = "fuzzy_title_company"
            results["duplicate_job"] = title_matches[0][0]
            results["confidence"] = title_matches[0][1]
            return results

        # 3. Check content similarity (embedding-based)
        content_matches = await self.find_duplicates_by_content(db, content, org_id)
        results["matches"]["content"] = content_matches

        if (
            content_matches
            and content_matches[0][1] >= self.CONTENT_SIMILARITY_THRESHOLD
        ):
            results["is_duplicate"] = True
            results["duplicate_type"] = "content_similarity"
            results["duplicate_job"] = content_matches[0][0]
            results["confidence"] = content_matches[0][1]
            return results

        # No duplicates found
        return results

    async def merge_duplicate_data(
        self, db: AsyncSession, existing_job: JobPost, new_data: Dict
    ) -> JobPost:
        """
        Merge new data into existing job post (update with better information)

        Args:
            db: Database session
            existing_job: Existing job post
            new_data: New job data dictionary

        Returns:
            Updated JobPost
        """
        try:
            # Update last_seen timestamp
            existing_job.last_seen = datetime.utcnow()

            # Increment repost count (signal of urgency/popularity)
            if hasattr(existing_job, "repost_count"):
                existing_job.repost_count = (existing_job.repost_count or 0) + 1

            # Update fields if new data is more complete
            if new_data.get("description_raw") and len(
                new_data["description_raw"]
            ) > len(existing_job.description_raw or ""):
                existing_job.description_raw = new_data["description_raw"]

            if new_data.get("requirements_raw") and len(
                new_data["requirements_raw"]
            ) > len(existing_job.requirements_raw or ""):
                existing_job.requirements_raw = new_data["requirements_raw"]

            # Update salary if not present
            if not existing_job.salary_min and new_data.get("salary_min"):
                existing_job.salary_min = new_data["salary_min"]
                existing_job.salary_max = new_data.get("salary_max")
                existing_job.currency = new_data.get("currency")

            # Update location if not present
            if not existing_job.location_id and new_data.get("location_id"):
                existing_job.location_id = new_data["location_id"]

            await db.commit()
            await db.refresh(existing_job)

            logger.info(f"Merged duplicate data for job {existing_job.id}")
            return existing_job

        except Exception as e:
            await db.rollback()
            logger.error(f"Error merging duplicate data: {e}")
            return existing_job

    def generate_deduplication_report(self, jobs_data: List[Dict]) -> Dict:
        """
        Generate a report on duplicate detection for a batch of jobs

        Args:
            jobs_data: List of job data dictionaries

        Returns:
            Deduplication statistics
        """
        report = {
            "total_jobs": len(jobs_data),
            "unique_jobs": 0,
            "duplicates": 0,
            "duplicate_by_type": {
                "exact_url": 0,
                "fuzzy_title_company": 0,
                "content_similarity": 0,
            },
            "average_confidence": 0.0,
            "generated_at": datetime.utcnow(),
        }

        # Count duplicates by type
        duplicate_confidences = []

        for job in jobs_data:
            if job.get("is_duplicate"):
                report["duplicates"] += 1
                dup_type = job.get("duplicate_type")
                if dup_type:
                    report["duplicate_by_type"][dup_type] = (
                        report["duplicate_by_type"].get(dup_type, 0) + 1
                    )

                confidence = job.get("confidence", 0.0)
                duplicate_confidences.append(confidence)
            else:
                report["unique_jobs"] += 1

        # Calculate average confidence
        if duplicate_confidences:
            report["average_confidence"] = sum(duplicate_confidences) / len(
                duplicate_confidences
            )

        return report


# Singleton instance
deduplication_service = DeduplicationService()
