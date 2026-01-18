#!/usr/bin/env python3
"""
Generate backend/app/ingestion/government_sources.yaml from the seed spreadsheet.

Requires: pandas, openpyxl, pyyaml
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


def _split_urls(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        return [u.strip() for u in value.splitlines() if u.strip()]
    return [str(value).strip()]


def _dedupe(urls):
    deduped = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def generate_sources(xlsx_path: Path) -> list[dict]:
    sources = []

    verified = pd.read_excel(xlsx_path, sheet_name="Verified Career Pages")
    for _, row in verified.iterrows():
        url = row.get("Career Page URL")
        if pd.isna(url) or not str(url).strip():
            continue
        name = str(row.get("Institution")).strip()
        sources.append(
            {
                "name": name,
                "type": "gov_careers",
                "org": name,
                "group": "national",
                "category": row.get("Type"),
                "sector": row.get("Sector"),
                "status": row.get("Status"),
                "list_urls": [str(url).strip()],
                "source_url": row.get("Source URL"),
                "notes": row.get("Notes"),
                "last_checked": row.get("Last Checked"),
            }
        )

    counties = pd.read_excel(xlsx_path, sheet_name="Counties")
    for _, row in counties.iterrows():
        county = str(row.get("County")).strip()
        urls = []
        verified_url = row.get("Verified Vacancy/Careers URL")
        if isinstance(verified_url, str) and verified_url.strip():
            urls.append(verified_url.strip())
        urls.extend(_split_urls(row.get("Candidate URLs (Guessed)")))
        deduped = _dedupe(urls)
        if not deduped:
            continue
        name = f"{county} County Government"
        sources.append(
            {
                "name": name,
                "type": "gov_careers",
                "org": name,
                "group": "county",
                "county": county,
                "homepage": row.get("County Website"),
                "status": row.get("Status"),
                "list_urls": deduped,
                "source_url": row.get("Source URL"),
                "notes": row.get("Notes"),
                "last_checked": row.get("Last Checked"),
            }
        )

    assemblies = pd.read_excel(xlsx_path, sheet_name="County_Assemblies (47)")
    for _, row in assemblies.iterrows():
        name = str(row.get("County_Assembly_Name")).strip()
        county = str(row.get("County_Name")).strip()
        urls = []
        for col in [
            "Assembly_Site_Verified_URL",
            "Career/Vacancies_URL",
            "Candidate_Assembly_URL_1",
            "Candidate_Assembly_URL_2",
        ]:
            value = row.get(col)
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())
        deduped = _dedupe(urls)
        if not deduped:
            continue
        sources.append(
            {
                "name": name,
                "type": "gov_careers",
                "org": name,
                "group": "county_assembly",
                "county": county,
                "homepage": row.get("Assembly_Site_Verified_URL"),
                "status": row.get("Status"),
                "list_urls": deduped,
                "notes": row.get("Notes"),
            }
        )

    return sources


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate government_sources.yaml from the seed spreadsheet."
    )
    parser.add_argument("xlsx", type=Path, help="Path to the seed .xlsx file")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("backend/app/ingestion/government_sources.yaml"),
        help="Output YAML path",
    )
    args = parser.parse_args()

    sources = generate_sources(args.xlsx)
    header = (
        "# Auto-generated from kenya_career_pages_seed_v2_with_county_assemblies.xlsx\n"
        "# Edit the spreadsheet and re-export rather than hand-editing large blocks.\n"
    )

    payload = {"sources": sources}
    yaml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    args.out.write_text(header + yaml_text)
    print(f"Wrote {args.out} with {len(sources)} sources")


if __name__ == "__main__":
    main()
