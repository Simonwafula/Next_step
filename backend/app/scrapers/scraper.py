# scrapers/scraper.py
import warnings
from urllib3.exceptions import NotOpenSSLWarning

# Suppress the LibreSSL/OpenSSL compatibility warning before urllib3 loads.
warnings.filterwarnings("ignore", category=NotOpenSSLWarning, module="urllib3")

import argparse
import logging
import urllib3
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin

# Absolute imports assuming `scrapers/` is on PYTHONPATH
from scrapers.config import SITES, get_site_cfg, USE_POSTGRES
from scrapers.db import Database
from scrapers.postgres_db import PostgresJobDatabase
from scrapers.utils import get_session, rate_limited_get

# Suppress generic InsecureRequestWarning
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
    def __init__(self, site_name: str):
        cfg = get_site_cfg(site_name)
        self.base_url = cfg["base_url"]
        self.list_path = cfg["listing_path"]
        self.list_sel = cfg["listing_selector"]
        self.title_attr = cfg["title_attribute"]
        self.content_sel = cfg["content_selector"]

        self.session = get_session()
        # Use PostgreSQL or SQLite based on configuration
        if USE_POSTGRES:
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

    def run(self):
        self.db.connect()
        logging.info("Starting scraper run until non-200 or empty page...")

        page = 1
        jobs = []
        while True:
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
    args = parser.parse_args()

    setup_logging()
    logging.info(f"Running scraper for site: {args.site}")
    spider = SiteSpider(args.site)
    spider.run()


if __name__ == "__main__":
    main()
