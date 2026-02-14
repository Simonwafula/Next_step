"""
Career Insight API Routes

Endpoints for career exploration and insights.
Helps students understand what different careers entail.
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.career_insight_service import CareerInsightService
from ..services.career_visualization import career_visualizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-insights", tags=["Career Insights"])


@router.get("/{title}")
async def get_career_insight(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive career insights for a job title.

    Returns:
    - What the career entails
    - Skills needed
    - Typical responsibilities
    - Education requirements
    - Experience needed
    - Salary range
    - Top employers
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)
    return result


@router.get("/{title}/summary")
async def get_career_summary(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get a concise career summary.
    Lighter response for quick lookups.
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    summary = result.get("summary", {})
    return {
        "success": True,
        "title": title,
        "what_you_do": summary.get("what_you_do"),
        "top_skills": summary.get("skills_needed", {}).get("top_skills", [])[:5],
        "education": summary.get("education_required", {}).get("minimum"),
        "experience": summary.get("experience_needed", {}).get("level"),
        "salary_range": summary.get("salary_range", {}).get("range"),
        "outlook": summary.get("career_outlook"),
        "data_source": summary.get("data_source"),
    }


@router.get("/{title}/visualizations")
async def get_career_visualizations(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get visual representations of career data.

    Returns base64-encoded images for:
    - Word cloud of responsibilities
    - Skills bar chart
    - Education pie chart
    - Experience distribution
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    collated = result.get("detailed_breakdown", {})
    dashboard = career_visualizer.generate_career_dashboard(
        collated, title=f"{title.title()} - Career Overview"
    )

    return {
        "success": True,
        "title": title,
        "job_count": dashboard.get("job_count"),
        "visualizations": dashboard.get("visualizations", {}),
    }


@router.get("/{title}/skills-chart")
async def get_skills_chart(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    top_n: int = Query(default=10, ge=5, le=20),
    db: Session = Depends(get_db),
):
    """
    Get a bar chart showing top skills for a career.
    Returns base64-encoded PNG image.
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    skills = result.get("detailed_breakdown", {}).get("skills", {})
    chart = career_visualizer.generate_skills_bar_chart(
        skills,
        title=f"Top Skills for {title.title()}",
        top_n=top_n,
    )

    return {
        "success": True,
        "title": title,
        "chart": chart,
    }


@router.get("/{title}/wordcloud")
async def get_responsibilities_wordcloud(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get a word cloud of key responsibilities and terms.
    Returns base64-encoded PNG image.
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    responsibilities = result.get("detailed_breakdown", {}).get("responsibilities", {})
    tasks = responsibilities.get("example_tasks", [])

    if not tasks:
        return {
            "success": False,
            "error": "No responsibilities found to generate wordcloud",
        }

    text = " ".join(tasks)
    wordcloud = career_visualizer.generate_wordcloud(
        text,
        title=f"Key Terms for {title.title()}",
    )

    return {
        "success": True,
        "title": title,
        "wordcloud": wordcloud,
    }


@router.get("/{title}/education-chart")
async def get_education_chart(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get a pie chart showing education requirements distribution.
    Returns base64-encoded PNG image.
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    education = result.get("detailed_breakdown", {}).get("education", {})
    chart = career_visualizer.generate_education_pie_chart(
        education,
        title=f"Education Requirements for {title.title()}",
    )

    return {
        "success": True,
        "title": title,
        "chart": chart,
    }


@router.get("/{title}/experience-chart")
async def get_experience_chart(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get a bar chart showing experience requirements distribution.
    Returns base64-encoded PNG image.
    """
    service = CareerInsightService(db)
    result = service.get_full_career_insight(title, job_limit=job_limit)

    if not result.get("success"):
        return result

    experience = result.get("detailed_breakdown", {}).get("experience", {})
    chart = career_visualizer.generate_experience_distribution(
        experience,
        title=f"Experience Requirements for {title.title()}",
    )

    return {
        "success": True,
        "title": title,
        "chart": chart,
    }


@router.get("/{title}/raw-data")
async def get_raw_career_data(
    title: str,
    job_limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Get raw collated data for a career.
    Returns detailed breakdown without summary.
    Useful for custom visualizations or analysis.
    """
    service = CareerInsightService(db)
    jobs = service.collect_jobs_for_title(title, limit=job_limit)

    if not jobs:
        return {
            "success": False,
            "error": f"No jobs found for title: {title}",
            "jobs": [],
        }

    collated = service.collate_insights(jobs)

    return {
        "success": True,
        "title": title,
        "jobs": jobs[:10],
        "collated": collated,
    }


@router.post("/compare")
async def compare_careers(
    titles: list[str],
    job_limit: int = Query(default=50, ge=10, le=200),
    db: Session = Depends(get_db),
):
    """
    Compare multiple careers side by side.

    Returns comparative data for:
    - Skills overlap
    - Salary ranges
    - Education requirements
    - Experience levels
    """
    service = CareerInsightService(db)

    comparisons = []
    for title in titles[:5]:
        result = service.get_full_career_insight(title, job_limit=job_limit)
        if result.get("success"):
            comparisons.append(
                {
                    "title": title,
                    "summary": result.get("summary"),
                    "skills": result.get("detailed_breakdown", {})
                    .get("skills", {})
                    .get("top_10", [])[:5],
                }
            )

    return {
        "success": True,
        "careers_compared": len(comparisons),
        "comparisons": comparisons,
    }
