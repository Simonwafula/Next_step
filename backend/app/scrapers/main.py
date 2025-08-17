# scrapers/main.py
import logging
import argparse
from datetime import datetime
from scraper import SiteSpider
from config import SITES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def scrape_site(site_name: str):
    """Scrape a specific site"""
    if site_name not in SITES:
        logging.error(f"Unknown site: {site_name}. Available sites: {list(SITES.keys())}")
        return False

    try:
        logging.info(f"Starting scrape for {site_name}")
        spider = SiteSpider(site_name)
        spider.run()
        logging.info(f"Successfully completed scraping {site_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to scrape {site_name}: {e}")
        return False


def scrape_all_sites():
    """Scrape all configured sites"""
    results = {}
    for site_name in SITES.keys():
        logging.info(f"\n{'=' * 50}")
        logging.info(f"SCRAPING: {site_name.upper()}")
        logging.info(f"{'=' * 50}")

        results[site_name] = scrape_site(site_name)

    # Summary
    logging.info(f"\n{'=' * 50}")
    logging.info("SCRAPING SUMMARY")
    logging.info(f"{'=' * 50}")

    successful = [site for site, success in results.items() if success]
    failed = [site for site, success in results.items() if not success]

    logging.info(f"Successful: {len(successful)} sites")
    for site in successful:
        logging.info(f"  ✓ {site}")

    if failed:
        logging.info(f"Failed: {len(failed)} sites")
        for site in failed:
            logging.info(f"  ✗ {site}")


def main():
    parser = argparse.ArgumentParser(description="Job site scraper")
    parser.add_argument(
        '--site',
        choices=list(SITES.keys()) + ['all'],
        default='all',
        help='Site to scrape (default: all)'
    )
    parser.add_argument(
        '--list-sites',
        action='store_true',
        help='List available sites'
    )

    args = parser.parse_args()

    if args.list_sites:
        print("Available sites:")
        for site in SITES.keys():
            print(f"  - {site}")
        return

    if args.site == 'all':
        scrape_all_sites()
    else:
        scrape_site(args.site)


if __name__ == "__main__":
    main()