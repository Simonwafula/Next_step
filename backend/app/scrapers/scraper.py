# ruff: noqa: E402
import warnings

from urllib3.exceptions import NotOpenSSLWarning

warnings.filterwarnings("ignore", category=NotOpenSSLWarning, module="urllib3")

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin

import urllib3
from bs4 import BeautifulSoup

from .config import SITES, USE_POSTGRES, get_site_cfg
from .db import Database
from .postgres_db import PostgresJobDatabase
from .utils import get_session, rate_limited_get

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def setup_logging(log_file: str = "scraper.log"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode="a"),
        ],
    )


@dataclass
class JobListing:
    title: str
    full_link: str
    content: str = ""


class SiteSpider:
    def __init__(
        self,
        site_name: str,
        *,
        use_postgres: bool | None = None,
        max_pages: int | None = None,
    ):
        cfg = get_site_cfg(site_name)
        self.base_url = cfg["base_url"]
        self.list_path = cfg["listing_path"]
        self.list_sel = cfg["listing_selector"]
        self.title_attr = cfg["title_attribute"]
        self.content_sel = cfg["content_selector"]

        if use_postgres is None:
            use_postgres = USE_POSTGRES
        self.use_postgres = bool(use_postgres)
        self.max_pages = max_pages

        self.session = get_session()
        if self.use_postgres:
            self.db = PostgresJobDatabase()
        else:
            self.db = Database()

    def fetch(self, url: str):
        try:
            resp = rate_limited_get(self.session, url, verify=False)
            return resp
        except Exception as e:
            logging.error(f"Fetch error {url}: {e}")
            return None

    def parse_listings(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select(self.list_sel):
            title = (a.get(self.title_attr) or a.get_text()).strip()
            href = a.get("href", "")
            if href:
                yield title, urljoin(self.base_url, href)

    def parse_content(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        node = soup.select_one(self.content_sel)
        return node.get_text(strip=True) if node else ""

    def run(self) -> int:
        self.db.connect()
        logging.info("Starting scraper run until non-200 or empty page...")

        page = 1
        jobs = []
        while True:
            if self.max_pages is not None and page > self.max_pages:
                logging.info("Reached max_pages=%s, stopping.", self.max_pages)
                break
            url = self.base_url + self.list_path.format(page=page)
            resp = self.fetch(url)
            if not resp or resp.status_code != 200:
                logging.info(
                    f"Stopping at page {page} (HTTP {resp.status_code if resp else 'error'})"
                )
                break

            html = resp.text
            listings = list(self.parse_listings(html))
            if not listings:
                logging.info(f"No listings found on page {page}, stopping.")
                break

            logging.info(f"Page {page}: found {len(listings)} listings")
            jobs.extend(listings)
            page += 1

        logging.info(
            f"Total pages scraped: {page - 1}, total jobs collected: {len(jobs)}"
        )

        def worker(item):
            title, link = item
            resp = self.fetch(link)
            content = (
                self.parse_content(resp.text)
                if resp and resp.status_code == 200
                else ""
            )
            return (title, link, content)

        with ThreadPoolExecutor(max_workers=5) as executor:
            rows = list(executor.map(worker, jobs))

        inserted = self.db.batch_insert(rows)
        self.db.close()
        logging.info(f"Inserted {inserted} jobs into database. Scraper done.")
        return int(inserted)


def main():
    parser = argparse.ArgumentParser(
        description="Generic job scraper (choices: " + ", ".join(SITES.keys()) + ")"
    )
    parser.add_argument(
        "--site",
        required=True,
        choices=SITES.keys(),
        help="Which site to scrape (key in config.yaml)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after scraping this many listing pages (default: no limit)",
    )
    db_mode = parser.add_mutually_exclusive_group()
    db_mode.add_argument(
        "--postgres",
        action="store_true",
        help="Force PostgreSQL writes (ignores USE_POSTGRES env)",
    )
    db_mode.add_argument(
        "--sqlite",
        action="store_true",
        help="Force SQLite writes (ignores USE_POSTGRES env)",
    )
    args = parser.parse_args()

    setup_logging()
    logging.info(f"Running scraper for site: {args.site}")
    use_postgres = None
    if args.postgres:
        use_postgres = True
    elif args.sqlite:
        use_postgres = False

    spider = SiteSpider(args.site, use_postgres=use_postgres, max_pages=args.max_pages)
    inserted = spider.run()
    logging.info("Inserted %s new jobs.", inserted)


if __name__ == "__main__":
    main()
