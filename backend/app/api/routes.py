from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..schemas.base import JobPostOut, RecommendOut
from ..db.database import get_db
from ..services.search import search_jobs
from ..services.recommend import transitions_for, get_trending_transitions, get_salary_insights_for_transition
from ..services.lmi import (
    get_weekly_insights, get_market_trends, get_salary_insights, 
    get_attachment_companies, get_trending_skills
)
from ..services.scraper_service import scraper_service
from ..services.auth_service import get_current_user_optional
from ..normalization.titles import get_careers_for_degree, normalize_title
from ..ingestion.runner import run_all_sources
from .auth_routes import router as auth_router
from .user_routes import router as user_router
from .integration_routes import router as integration_router

api_router = APIRouter()

# Include authentication and user management routes
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(user_router, prefix="/users", tags=["user-management"])
api_router.include_router(integration_router, prefix="/integrations", tags=["integrations"])

# Enhanced Job Search & Title Translation
@api_router.get("/search", response_model=list[dict])
def search(q: str = Query("", description="Search query, job title, or 'I studied [degree]'"),
           location: str | None = Query(None, description="Location filter"),
           seniority: str | None = Query(None, description="Seniority level"),
           personalized: bool = Query(False, description="Enable personalized results"),
           db: Session = Depends(get_db),
           current_user = Depends(get_current_user_optional)):
    """
    Enhanced job search with semantic matching and degree-to-career translation.
    Now supports personalized results for authenticated users.
    
    Examples:
    - "data analyst jobs Nairobi"
    - "I studied economics"
    - "statistician jobs"
    """
    # Enhanced search with optional personalization
    results = search_jobs(
        db, 
        q=q, 
        location=location, 
        seniority=seniority,
        user=current_user if personalized and current_user else None
    )
    
    # Add personalization metadata if user is authenticated
    if current_user and personalized:
        return {
            "results": results,
            "personalized": True,
            "user_profile_used": bool(current_user.profile),
            "total": len(results)
        }
    
    return results

@api_router.get("/translate-title")
def translate_title(title: str = Query(..., description="Job title to normalize")):
    """
    Translate messy job titles into standard career families.
    
    Example: "data ninja" → Data Analyst (Data Analytics family)
    """
    family, canonical = normalize_title(title)
    return {
        "original_title": title,
        "normalized_family": family.replace("_", " ").title(),
        "canonical_title": canonical,
        "explanation": f"Mapped '{title}' to {family.replace('_', ' ')} family as '{canonical}'"
    }

@api_router.get("/careers-for-degree")
def careers_for_degree(degree: str = Query(..., description="Degree or field of study")):
    """
    Get relevant career paths for a given degree.
    
    Example: "economics" → [Data Analyst, Financial Analyst, Policy Analyst, ...]
    """
    careers = get_careers_for_degree(degree)
    return {
        "degree": degree,
        "relevant_careers": careers,
        "explanation": f"Based on {degree} background, these roles match your skills and knowledge"
    }

# Enhanced Career Pathways & Transitions
@api_router.get("/recommend", response_model=list[dict])
def recommend(current: str = Query(..., description="Current role or background"),
              db: Session = Depends(get_db)):
    """
    Get career transition recommendations with real skill gap analysis.
    
    Returns overlap percentage and up to 3 missing skills for each transition.
    """
    recs = transitions_for(db, current)
    return recs

@api_router.get("/trending-transitions")
def trending_transitions(days: int = Query(30, description="Days to analyze"),
                        db: Session = Depends(get_db)):
    """Get trending career transitions based on recent job market activity."""
    trends = get_trending_transitions(db, days=days)
    return {
        "period": f"Past {days} days",
        "trending_roles": trends
    }

@api_router.get("/transition-salary")
def transition_salary(target_role: str = Query(..., description="Target role for transition"),
                     db: Session = Depends(get_db)):
    """Get salary insights for a specific career transition target."""
    insights = get_salary_insights_for_transition(db, target_role)
    return {
        "target_role": target_role,
        "salary_insights": insights
    }

# Labour Market Intelligence (LMI)
@api_router.get("/lmi/weekly-insights")
def weekly_insights(location: str | None = Query(None, description="Location filter"),
                   db: Session = Depends(get_db)):
    """
    Get weekly labour market insights including:
    - Top hiring companies
    - Postings by role family  
    - Median salary data
    - Tenure mix (FT/contract/internship)
    - Trending skills
    """
    insights = get_weekly_insights(db, location=location)
    return insights

@api_router.get("/lmi/market-trends")
def market_trends(days: int = Query(30, description="Days to analyze"),
                 location: str | None = Query(None, description="Location filter"),
                 db: Session = Depends(get_db)):
    """
    Get market trends over specified period including:
    - Daily posting counts
    - Growth rates
    - Role family trends
    - Market temperature assessment
    """
    trends = get_market_trends(db, days=days, location=location)
    return trends

@api_router.get("/lmi/salary-insights")
def salary_insights(role_family: str | None = Query(None, description="Role family filter"),
                   location: str | None = Query(None, description="Location filter"),
                   db: Session = Depends(get_db)):
    """
    Get salary insights by role family and location including:
    - Percentile breakdowns (25th, 50th, 75th)
    - Salary by role family
    - Data coverage transparency
    """
    insights = get_salary_insights(db, role_family=role_family, location=location)
    return insights

@api_router.get("/lmi/trending-skills")
def trending_skills(days: int = Query(7, description="Days to analyze"),
                   db: Session = Depends(get_db)):
    """Get trending skills with week-over-week growth rates."""
    skills = get_trending_skills(db, days=days)
    return {
        "period": f"Past {days} days",
        "trending_skills": skills
    }

@api_router.get("/lmi/coverage-stats")
def coverage_stats(db: Session = Depends(get_db)):
    """Get data coverage statistics for transparency."""
    from sqlalchemy import select, func
    from ..db.models import JobPost, JobSkill
    
    total_posts = db.execute(select(func.count(JobPost.id))).scalar() or 0
    posts_with_salary = db.execute(
        select(func.count(JobPost.id)).where(JobPost.salary_min.is_not(None))
    ).scalar() or 0
    posts_with_skills = db.execute(
        select(func.count(JobPost.id.distinct())).join_from(JobPost, JobSkill)
    ).scalar() or 0
    
    return {
        "total_job_postings": total_posts,
        "salary_data_coverage": {
            "count": posts_with_salary,
            "percentage": round(posts_with_salary / total_posts * 100, 1) if total_posts > 0 else 0
        },
        "skills_data_coverage": {
            "count": posts_with_skills,
            "percentage": round(posts_with_skills / total_posts * 100, 1) if total_posts > 0 else 0
        },
        "note": "Coverage percentages show how much of our data includes salary/skills information"
    }

# Attachments & Graduate Intakes
@api_router.get("/attachments")
def attachments(location: str | None = Query(None, description="Location filter"),
               db: Session = Depends(get_db)):
    """
    Get companies that accept interns/attachments including:
    - Company details and sectors
    - Role types available
    - Application advice
    - Intake timing information
    """
    companies = get_attachment_companies(db, location=location)
    return companies

@api_router.get("/graduate-programs")
def graduate_programs(location: str | None = Query(None, description="Location filter"),
                     sector: str | None = Query(None, description="Sector filter"),
                     db: Session = Depends(get_db)):
    """Get graduate trainee programs and entry-level opportunities."""
    from sqlalchemy import select, and_, or_
    from ..db.models import JobPost, Organization, Location
    
    conditions = [
        or_(
            JobPost.seniority.ilike("%graduate%"),
            JobPost.seniority.ilike("%entry%"),
            JobPost.seniority.ilike("%trainee%"),
            JobPost.title_raw.ilike("%graduate%"),
            JobPost.title_raw.ilike("%trainee%")
        )
    ]
    
    if location:
        conditions.append(or_(
            Location.city.ilike(f"%{location}%"),
            Location.region.ilike(f"%{location}%"),
            Location.country.ilike(f"%{location}%")
        ))
    
    if sector:
        conditions.append(Organization.sector.ilike(f"%{sector}%"))
    
    stmt = select(JobPost, Organization, Location).join(
        Organization, Organization.id == JobPost.org_id, isouter=True
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(and_(*conditions)).limit(50)
    
    programs = db.execute(stmt).all()
    
    return {
        "location": location or "All locations",
        "sector": sector or "All sectors",
        "graduate_programs": [
            {
                "title": job.title_raw,
                "company": org.name if org else "Unknown",
                "sector": org.sector if org else None,
                "location": f"{loc.city}, {loc.country}" if loc and loc.city else (loc.raw if loc else None),
                "url": job.url,
                "seniority": job.seniority,
                "program_type": "Graduate Trainee" if "trainee" in job.title_raw.lower() else "Entry Level"
            }
            for job, org, loc in programs
        ],
        "total_programs": len(programs),
        "application_advice": "Apply early for graduate programs as they often have specific intake periods"
    }

# Scraper endpoints
@api_router.get("/scrapers/status")
async def scraper_status():
    """Get status of scrapers and database."""
    return await scraper_service.get_scraper_status()

@api_router.post("/scrapers/run/{site_name}")
async def run_scraper(site_name: str):
    """Run scraper for a specific site."""
    return await scraper_service.run_scraper_for_site(site_name)

@api_router.post("/scrapers/run-all")
async def run_all_scrapers():
    """Run scrapers for all configured sites."""
    return await scraper_service.run_all_scrapers()

@api_router.post("/scrapers/migrate")
async def migrate_sqlite_to_postgres():
    """Migrate data from SQLite to PostgreSQL."""
    return await scraper_service.migrate_sqlite_to_postgres()

@api_router.get("/scrapers/recent-jobs")
async def get_recent_jobs(limit: int = Query(10, description="Number of recent jobs to return")):
    """Get recent jobs from the database."""
    return await scraper_service.get_recent_jobs(limit)

# Admin endpoints
@api_router.post("/admin/ingest")
def admin_ingest(db: Session = Depends(get_db)):
    """Run job ingestion from all configured sources."""
    count = run_all_sources(db)
    return {"ingested": count}
