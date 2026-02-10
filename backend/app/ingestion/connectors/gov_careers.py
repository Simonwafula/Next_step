# Generic HTML ingest for government career/vacancy pages.
from __future__ import annotations

import logging
import re
from datetime import datetime
import io
from typing import Iterable, List, Tuple, Optional
from urllib.parse import urljoin, urlparse, unquote

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...db.models import JobPost, Organization, Location
from ...services.deduplication_service import DeduplicationService

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "job",
    "jobs",
    "vacan",
    "career",
    "recruit",
    "advert",
    "opening",
    "opportun",
    "position",
    "appointment",
    "intern",
    "attachment",
    "graduate",
    "fellowship",
]
NEGATIVE_KEYWORDS = [
    "no vacancy",
    "no vacancies",
    "no open positions",
    "no openings",
    "no jobs",
    "no current openings",
]
GENERIC_LINK_TEXT = {
    "download",
    "view",
    "view advert",
    "view ad",
    "open",
    "details",
    "click here",
    "here",
    "apply",
}

DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx")
MAX_DESCRIPTION_CHARS = 4000
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024


def _coerce_list(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _has_keyword(text: str, keywords: Iterable[str]) -> bool:
    haystack = text.lower()
    return any(keyword in haystack for keyword in keywords)


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    filename = parsed.path.rstrip("/").split("/")[-1]
    if not filename:
        return "Job posting"
    filename = unquote(filename)
    for ext in DOCUMENT_EXTENSIONS:
        if filename.lower().endswith(ext):
            filename = filename[: -len(ext)]
            break
    title = filename.replace("-", " ").replace("_", " ").strip()
    return title[:255] if title else "Job posting"


def _clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _best_anchor_text(anchor) -> str:
    text = (anchor.get_text() or anchor.get("title") or "").strip()
    if text:
        lowered = text.lower()
    else:
        lowered = ""
    if not text or lowered in GENERIC_LINK_TEXT or len(text) < 4:
        parent = anchor.find_parent(["tr", "li", "article", "section", "div"])
        if parent:
            text = parent.get_text(" ", strip=True)
    return _clean_text(text)[:200]


def _extract_page_content(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = ""
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    elif soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)

    container = soup.find("article") or soup.find("main") or soup.find("section")
    text = ""
    if container:
        text = container.get_text(" ", strip=True)
    else:
        body = soup.body
        if body:
            text = body.get_text(" ", strip=True)

    title = _clean_text(title)
    text = _clean_text(text)
    if text and len(text) > MAX_DESCRIPTION_CHARS:
        text = text[:MAX_DESCRIPTION_CHARS]

    return title, text


def _extract_document_text(url: str, client: httpx.Client) -> str:
    if not url.lower().endswith(".pdf"):
        return ""
    if PdfReader is None:
        return ""
    try:
        resp = client.get(url)
        if resp.status_code >= 400:
            return ""
        if len(resp.content) > MAX_DOCUMENT_BYTES:
            return ""
        reader = PdfReader(io.BytesIO(resp.content))
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        text = _clean_text(text)
        return text[:MAX_DESCRIPTION_CHARS]
    except Exception:
        return ""


def _extract_salary_from_text(
    text: str,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extract salary information from text content.
    Returns (salary_min, salary_max, currency)

    Minimum salary threshold: 5,000 KES (very basic minimum)
    Maximum salary threshold: 50,000,000 KES (reasonable upper limit)
    """
    if not text:
        return None, None, None

    # Minimum realistic salary thresholds
    MIN_SALARY_KES = 5000  # Minimum realistic monthly salary
    MAX_SALARY_KES = 50000000  # Maximum reasonable salary
    MIN_SALARY_USD = 50  # Minimum USD salary
    MAX_SALARY_USD = 500000  # Maximum reasonable USD salary

    # Salary patterns for Kenyan job postings - ordered by specificity
    patterns = [
        # Kenyan format with /= suffix: Kshs. 157,427 – Kshs. 234,431/=
        (
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)(?:/=)?\s*[-–to]+\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)(?:/=)?",
            "KES",
            False,
        ),
        # K notation range: KES 80k-120k (requires 'k' after number)
        (
            r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d+)\s*k\s*[-–to]+\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*(\d+)\s*k",
            "KES",
            True,
        ),
        # Standard KSH range: KSH 50,000 - 100,000 (require comma for larger numbers)
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)\s*[-–to]+\s*([\d,]+)", "KES", False),
        # Salary range pattern: "salary of between X and Y"
        (
            r"salary\s+(?:of\s+)?(?:between\s+)?(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)\s*(?:and|to|-|–)\s*(?:KSH|KSh|Kshs?|KES)?\.?\s*([\d,]+)",
            "KES",
            False,
        ),
        # Single Kenyan value with /= suffix (more specific - must have /=)
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*([\d,]+)/=", "KES", False),
        # K notation single with explicit 'k': KES 80k
        (r"(?:KSH|KSh|Kshs?|KES)\.?\s*(\d+)\s*k\b", "KES", True),
        # USD range
        (r"\$\s*([\d,]+)\s*[-–to]+\s*\$?\s*([\d,]+)", "USD", False),
        # "Salary: X to Y" format (requires explicit "salary" keyword)
        (r"salary[:\s]+([\d,]+)\s*[-–to]+\s*([\d,]+)", "KES", False),
        # "Salary: X" format with comma (requires comma for validity)
        (r"salary[:\s]+([\d,]+)", "KES", False),
    ]

    def clean_value(val: str) -> float:
        cleaned = val.replace(" ", "").replace(",", "").replace("/=", "")
        return float(cleaned)

    def is_valid_salary(val: float, currency: str) -> bool:
        """Check if salary value is within reasonable bounds."""
        if currency == "USD":
            return MIN_SALARY_USD <= val <= MAX_SALARY_USD
        else:  # KES
            return MIN_SALARY_KES <= val <= MAX_SALARY_KES

    for pattern, currency, is_k_notation in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) >= 2 and groups[1]:
                    # Range
                    val1 = clean_value(groups[0])
                    val2 = clean_value(groups[1])
                    if is_k_notation:
                        val1 *= 1000
                        val2 *= 1000
                    if is_valid_salary(val1, currency) and is_valid_salary(
                        val2, currency
                    ):
                        return min(val1, val2), max(val1, val2), currency
                elif len(groups) >= 1 and groups[0]:
                    # Single value
                    val = clean_value(groups[0])
                    if is_k_notation:
                        val *= 1000
                    if is_valid_salary(val, currency):
                        return val, val, currency
            except (ValueError, AttributeError):
                continue

    return None, None, None


def _extract_seniority_from_text(title: str, description: str) -> Optional[str]:
    """Extract seniority level from title and description."""
    combined_text = f"{title} {description}".lower()

    seniority_mapping = {
        "entry": [
            "entry level",
            "entry-level",
            "junior",
            "graduate",
            "trainee",
            "intern",
            "attachment",
        ],
        "mid": ["mid level", "mid-level", "intermediate", "experienced"],
        "senior": ["senior", "lead", "principal", "sr.", "sr "],
        "management": ["manager", "supervisor", "team lead", "head of", "head,"],
        "executive": ["director", "executive", "c-level", "ceo", "cfo", "cto", "chief"],
    }

    for seniority, keywords in seniority_mapping.items():
        for keyword in keywords:
            if keyword in combined_text:
                return seniority

    # Default to mid if no specific level found
    return "mid"


def ingest_gov_careers(db: Session, **src) -> int:
    list_urls = _coerce_list(src.get("list_urls") or src.get("url"))
    if not list_urls:
        return 0

    org_name = src.get("org") or src.get("name")
    keywords = src.get("keywords") or DEFAULT_KEYWORDS
    max_links = int(src.get("max_links", 200))
    max_detail_pages = int(src.get("max_detail_pages", 20))
    fetch_detail = bool(src.get("fetch_detail", True))
    sector = src.get("sector")
    group = src.get("group")
    county = src.get("county")
    if not sector and group in ("county", "county_assembly"):
        sector = "Government"

    org = None
    if org_name:
        org = db.query(Organization).filter(Organization.name == org_name).one_or_none()
        if not org:
            org = Organization(name=org_name, verified=False, sector=sector)
            db.add(org)
            db.commit()
            db.refresh(org)
        elif sector and not org.sector:
            org.sector = sector
            db.add(org)

    location = None
    if county:
        location = (
            db.query(Location)
            .filter(
                Location.country == "Kenya",
                Location.region == county,
                Location.city.is_(None),
            )
            .one_or_none()
        )
        if not location:
            location = Location(country="Kenya", region=county, raw=county)
            db.add(location)
            db.flush()

    deduper = DeduplicationService()
    seen_urls: set[str] = set()
    added = 0

    # Government sites often have SSL certificate issues
    # Use verify=False as a fallback for sites with expired/invalid certs
    client = httpx.Client(
        timeout=30,
        follow_redirects=True,
        verify=False,  # Handle SSL cert issues common with gov sites
        headers={"User-Agent": "NextStepGovMonitor/1.0"},
    )

    try:
        detail_fetches = 0
        for list_url in list_urls:
            if not list_url:
                continue

            link_candidates: List[tuple[str, str]] = []
            context_text = list_url
            page_title = ""
            page_text = ""
            is_list_doc = list_url.lower().endswith(DOCUMENT_EXTENSIONS)

            try:
                if is_list_doc:
                    link_candidates.append((list_url, ""))
                else:
                    resp = client.get(list_url)
                    if resp.status_code >= 400:
                        logger.warning(
                            "Gov source fetch failed: %s (%s)",
                            list_url,
                            resp.status_code,
                        )
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    page_title, page_text = _extract_page_content(resp.text)
                    context_text = f"{list_url} {page_title} {page_text[:600]}".strip()
                    for anchor in soup.find_all("a", href=True):
                        href = anchor.get("href")
                        if not href:
                            continue
                        full_url = urljoin(list_url, href)
                        parsed = urlparse(full_url)
                        if parsed.scheme not in ("http", "https"):
                            continue
                        text = _best_anchor_text(anchor)
                        link_candidates.append((full_url, text))
            except Exception as exc:
                logger.warning("Gov source fetch error: %s (%s)", list_url, exc)
                continue

            context_has_keyword = _has_keyword(context_text, keywords)
            matched_links = 0
            for link_url, text in link_candidates[:max_links]:
                if link_url in seen_urls:
                    continue
                seen_urls.add(link_url)

                link_lower = f"{link_url} {text}".lower()
                is_doc = link_url.lower().endswith(DOCUMENT_EXTENSIONS)
                has_keyword = _has_keyword(link_lower, keywords)

                if not (has_keyword or (is_doc and context_has_keyword)):
                    continue
                matched_links += 1

                url_hash = deduper.generate_url_hash(link_url)
                existing = (
                    db.query(JobPost)
                    .filter(or_(JobPost.url == link_url, JobPost.url_hash == url_hash))
                    .first()  # Use first() instead of one_or_none() to handle duplicates
                )
                if existing:
                    existing.last_seen = datetime.utcnow()
                    db.add(existing)
                    continue

                title = text.strip() if text else _title_from_url(link_url)
                description = ""
                if fetch_detail and detail_fetches < max_detail_pages:
                    if not is_doc:
                        try:
                            detail_resp = client.get(link_url)
                            if detail_resp.status_code < 400:
                                page_title, page_text = _extract_page_content(
                                    detail_resp.text
                                )
                                if page_title:
                                    title = page_title
                                description = page_text
                        except Exception as exc:
                            logger.warning(
                                "Gov detail fetch failed: %s (%s)", link_url, exc
                            )
                        finally:
                            detail_fetches += 1
                    else:
                        description = _extract_document_text(link_url, client)
                        detail_fetches += 1

                # Extract salary and seniority from description
                salary_min, salary_max, currency = _extract_salary_from_text(
                    description
                )
                seniority = _extract_seniority_from_text(title, description)

                jp = JobPost(
                    source="gov_careers",
                    url=link_url,
                    source_url=link_url,
                    application_url=link_url,
                    url_hash=url_hash,
                    title_raw=title[:255],
                    org_id=org.id if org else None,
                    location_id=location.id if location else None,
                    description_raw=description,
                    attachment_flag=is_doc,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=currency,
                    seniority=seniority,
                )
                db.add(jp)
                added += 1

            if not matched_links and context_has_keyword and not is_list_doc:
                if not _has_keyword(page_text.lower(), NEGATIVE_KEYWORDS):
                    url_hash = deduper.generate_url_hash(list_url)
                    existing = (
                        db.query(JobPost)
                        .filter(
                            or_(JobPost.url == list_url, JobPost.url_hash == url_hash)
                        )
                        .first()  # Use first() instead of one_or_none() to handle duplicates
                    )
                    if not existing:
                        title = page_title or org_name or "Career opportunity"
                        description = page_text[:MAX_DESCRIPTION_CHARS]

                        # Extract salary and seniority from description
                        salary_min, salary_max, currency = _extract_salary_from_text(
                            description
                        )
                        seniority = _extract_seniority_from_text(title, description)

                        jp = JobPost(
                            source="gov_careers",
                            url=list_url,
                            source_url=list_url,
                            application_url=list_url,
                            url_hash=url_hash,
                            title_raw=title[:255],
                            org_id=org.id if org else None,
                            location_id=location.id if location else None,
                            description_raw=description,
                            salary_min=salary_min,
                            salary_max=salary_max,
                            currency=currency,
                            seniority=seniority,
                        )
                        db.add(jp)
                        added += 1

        db.commit()
    finally:
        client.close()

    return added
