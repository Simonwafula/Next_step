# scrapers/main.py
import logging
import argparse
from .scraper import SiteSpider
from .config import SITES

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def scrape_site(
    site_name: str,
    *,
    use_postgres: bool | None = None,
    max_pages: int | None = None,
) -> dict:
    """Scrape a specific site.

    Returns a small result dict so callers (CLI, pipelines) can aggregate.
    """
    if site_name not in SITES:
        logging.error(
            f"Unknown site: {site_name}. Available sites: {list(SITES.keys())}"
        )
        return {"site": site_name, "status": "error", "error": "unknown_site"}

    try:
        logging.info(f"Starting scrape for {site_name}")
        spider = SiteSpider(site_name, use_postgres=use_postgres, max_pages=max_pages)
        inserted = spider.run()
        logging.info(f"Successfully completed scraping {site_name}")
        return {"site": site_name, "status": "success", "inserted": inserted}
    except Exception as e:
        logging.error(f"Failed to scrape {site_name}: {e}")
        return {"site": site_name, "status": "error", "error": str(e)}


def scrape_all_sites(*, use_postgres: bool | None = None, max_pages: int | None = None):
    """Scrape all configured sites."""
    results: dict[str, dict] = {}
    for site_name in SITES.keys():
        logging.info(f"\n{'=' * 50}")
        logging.info(f"SCRAPING: {site_name.upper()}")
        logging.info(f"{'=' * 50}")

        results[site_name] = scrape_site(
            site_name, use_postgres=use_postgres, max_pages=max_pages
        )

    # Summary
    logging.info(f"\n{'=' * 50}")
    logging.info("SCRAPING SUMMARY")
    logging.info(f"{'=' * 50}")

    successful = [
        site for site, res in results.items() if res.get("status") == "success"
    ]
    failed = [site for site, res in results.items() if res.get("status") != "success"]

    logging.info(f"Successful: {len(successful)} sites")
    for site in successful:
        logging.info(f"  ✓ {site}")

    if failed:
        logging.info(f"Failed: {len(failed)} sites")
        for site in failed:
            logging.info(f"  ✗ {site}")

    inserted_total = sum(
        int(res.get("inserted") or 0)
        for res in results.values()
        if isinstance(res, dict)
    )
    return {
        "status": "completed",
        "inserted_total": inserted_total,
        "successful_sites": successful,
        "failed_sites": failed,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Job site scraper")
    parser.add_argument(
        "--site",
        choices=list(SITES.keys()) + ["all"],
        default="all",
        help="Site to scrape (default: all)",
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
    parser.add_argument(
        "--list-sites", action="store_true", help="List available sites"
    )

    args = parser.parse_args()

    use_postgres = None
    if args.postgres:
        use_postgres = True
    elif args.sqlite:
        use_postgres = False

    if args.list_sites:
        print("Available sites:")
        for site in SITES.keys():
            print(f"  - {site}")
        return

    if args.site == "all":
        scrape_all_sites(use_postgres=use_postgres, max_pages=args.max_pages)
    else:
        scrape_site(args.site, use_postgres=use_postgres, max_pages=args.max_pages)


if __name__ == "__main__":
    main()
