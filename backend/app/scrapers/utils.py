# utils.py
import logging
import time
import requests
import re

from ratelimit import limits, sleep_and_retry
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from scrapers.config import REQUESTS_PER_MINUTE
from bs4 import BeautifulSoup

# Constants
ONE_MINUTE = 60


def get_session(retries: int = 3, backoff: float = 0.3) -> requests.Session:
    """
    Build a requests.Session with retry logic.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@sleep_and_retry
@limits(calls=REQUESTS_PER_MINUTE, period=ONE_MINUTE)
def rate_limited_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """
    Perform a GET request using the provided session, obeying rate limits.
    Raises HTTPError on non-200.
    """
    logging.info(f"GET {url}")
    response = session.get(url, **kwargs)
    response.raise_for_status()
    # small delay to spread out traffic
    time.sleep(0.05)
    return response


def detect_last_page(html: str, pagination_selector: str) -> int:
    """
    Parse page-1 HTML to find the maximum page number via CSS selector.
    Returns 1 if parsing fails or no pages found.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select(pagination_selector)
    page_numbers = []
    for a in anchors:
        href = a.get("href", "")
        m = re.search(r"(?:[?&/]p(?:age)?=)(\d+)", href)
        if m:
            try:
                page_numbers.append(int(m.group(1)))
            except ValueError:
                continue
    last = max(page_numbers) if page_numbers else 1
    logging.info(f"Detected last page = {last}")
    return last
