# Placeholder for polite HTML scraping when allowed by TOS/robots.txt.
# Consider using Playwright/Selenium for rendering JS-heavy boards.
from sqlalchemy.orm import Session


def ingest_html_generic(db: Session, **src) -> int:
    # Intentionally blank scaffold
    return 0
