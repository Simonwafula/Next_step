#!/usr/bin/env python3
"""
Test script to verify improved structured data extraction
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.processors.job_extractor import JobDataExtractor
from app.db.database import SessionLocal
from app.db.models import JobPost
from sqlalchemy import text


async def test_extraction_improvements():
    """Test extraction improvements on sample jobs"""

    # Test URLs from our working sources
    test_jobs = [
        {
            "url": "https://www.myjobmag.co.ke/job/rto-guest-trainer-hcs-affiliates-group",
            "source": "myjobmag",
        }
    ]

    results = []

    async with JobDataExtractor() as extractor:
        for job in test_jobs:
            print(f"\n=== Testing {job['source']} ===")
            print(f"URL: {job['url']}")

            data = await extractor.extract_job_details(job["url"], job["source"])

            if data:
                # Calculate quality metrics
                fields = ["title", "company", "location", "description", "salary_text"]
                filled_fields = sum(
                    1 for field in fields if data.get(field, "").strip()
                )
                quality_score = (filled_fields / len(fields)) * 100

                print(f"✅ Extraction successful")
                print(f"   Title: {data.get('title', 'NOT FOUND')[:50]}...")
                print(f"   Company: {data.get('company', 'NOT FOUND')[:50]}...")
                print(f"   Location: {data.get('location', 'NOT FOUND')[:50]}...")
                print(f"   Salary: {data.get('salary_text', 'NOT FOUND')[:50]}...")
                print(f"   Description: {len(data.get('description', ''))} chars")
                print(
                    f"   Job Type: {data.get('employment_type', 'NOT FOUND')[:30]}..."
                )
                print(f"   Contact: {data.get('contact_info', 'NOT FOUND')[:50]}...")
                print(f"   Quality Score: {quality_score:.1f}%")

                results.append(
                    {
                        "source": job["source"],
                        "success": True,
                        "quality_score": quality_score,
                        "fields_extracted": filled_fields,
                        "data": data,
                    }
                )
            else:
                print(f"❌ Extraction failed")
                results.append(
                    {
                        "source": job["source"],
                        "success": False,
                        "quality_score": 0,
                        "fields_extracted": 0,
                        "data": None,
                    }
                )

    # Summary
    print(f"\n=== EXTRACTION SUMMARY ===")
    successful_tests = sum(1 for r in results if r["success"])
    avg_quality = (
        sum(r["quality_score"] for r in results) / len(results) if results else 0
    )

    print(f"Tests run: {len(results)}")
    print(f"Successful extractions: {successful_tests}")
    print(f"Average quality score: {avg_quality:.1f}%")

    # Check current database quality
    print(f"\n=== DATABASE QUALITY CHECK ===")
    db = SessionLocal()
    try:
        total_jobs = db.execute(text("SELECT COUNT(*) FROM job_post")).scalar()
        print(f"Total jobs in database: {total_jobs}")

        if total_jobs > 0:
            with_company = db.execute(
                text("SELECT COUNT(*) FROM job_post WHERE org_id IS NOT NULL")
            ).scalar()
            with_location = db.execute(
                text("SELECT COUNT(*) FROM job_post WHERE location_id IS NOT NULL")
            ).scalar()
            with_salary = db.execute(
                text("SELECT COUNT(*) FROM job_post WHERE salary_min IS NOT NULL")
            ).scalar()

            print(
                f"Jobs with company: {with_company} ({with_company / total_jobs * 100:.1f}%)"
            )
            print(
                f"Jobs with location: {with_location} ({with_location / total_jobs * 100:.1f}%)"
            )
            print(
                f"Jobs with salary: {with_salary} ({with_salary / total_jobs * 100:.1f}%)"
            )

            overall_quality = (
                (with_company + with_location + with_salary) / (total_jobs * 3)
            ) * 100
            print(f"Overall database quality: {overall_quality:.1f}%")

    except Exception as e:
        print(f"Database quality check failed: {e}")
    finally:
        db.close()

    # Recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    if avg_quality >= 80:
        print("✅ Excellent extraction quality achieved!")
    elif avg_quality >= 60:
        print("⚠️ Good extraction quality, room for improvement")
    else:
        print("❌ Poor extraction quality, needs significant work")

    print("Next steps:")
    print("1. Implement quarantine mechanism for incomplete jobs")
    print("2. Add structured extraction for salary ranges")
    print("3. Implement dedupe keys with URL hashing")
    print("4. Add more job sources for diversity")

    return results


if __name__ == "__main__":
    asyncio.run(test_extraction_improvements())
