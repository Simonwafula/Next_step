#!/usr/bin/env python3
import argparse
import asyncio
from pathlib import Path

import httpx
import yaml

BAD_STATUSES = {404, 410}
DEFAULT_TIMEOUT = 20


def parse_args():
    parser = argparse.ArgumentParser(description="Remove broken government source URLs.")
    parser.add_argument(
        "--file",
        default=str(Path(__file__).resolve().parents[1] / "backend/app/ingestion/government_sources.yaml"),
        help="Path to government_sources.yaml",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Only report changes")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    return parser.parse_args()


async def fetch_status(client: httpx.AsyncClient, url: str) -> int | None:
    try:
        resp = await client.get(url, follow_redirects=True)
        return resp.status_code
    except Exception:
        return None


async def main():
    args = parse_args()
    path = Path(args.file)
    data = yaml.safe_load(path.read_text()) or {}
    sources = data.get("sources", [])

    sem = asyncio.Semaphore(args.concurrency)
    results: dict[str, int | None] = {}

    async with httpx.AsyncClient(
        timeout=args.timeout, headers={"User-Agent": "NextStepLinkCheck/1.0"}
    ) as client:
        async def check(url: str):
            async with sem:
                results[url] = await fetch_status(client, url)

        tasks = []
        for src in sources:
            for url in src.get("list_urls") or []:
                if url not in results:
                    tasks.append(asyncio.create_task(check(url)))
        if tasks:
            await asyncio.gather(*tasks)

    bad_urls = {url for url, status in results.items() if status in BAD_STATUSES}

    removed_sources = []
    updated_sources = []
    kept_sources = []

    for src in sources:
        list_urls = src.get("list_urls") or []
        if not list_urls:
            kept_sources.append(src)
            continue
        cleaned = [url for url in list_urls if url not in bad_urls]
        if not cleaned:
            removed_sources.append(src)
            continue
        if len(cleaned) != len(list_urls):
            src = dict(src)
            src["list_urls"] = cleaned
            updated_sources.append(src)
            kept_sources.append(src)
        else:
            kept_sources.append(src)

    print(f"Checked URLs: {len(results)}")
    print(f"Bad URLs (404/410): {len(bad_urls)}")
    print(f"Sources removed: {len(removed_sources)}")
    print(f"Sources updated: {len(updated_sources)}")
    if removed_sources:
        print("Removed sources (sample):", [s.get("name") for s in removed_sources[:10]])

    if args.dry_run:
        print("Dry run enabled. No changes written.")
        return

    data["sources"] = kept_sources
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False))
    print(f"Updated {path}")


if __name__ == "__main__":
    asyncio.run(main())
