from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_, or_
from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill, MetricsDaily
from datetime import datetime, timedelta
from collections import Counter
import json

def get_weekly_insights(db: Session, location: str | None = None) -> dict:
    """Get weekly labour market insights"""
    
    # Date ranges
    week_ago = datetime.utcnow() - timedelta(days=7)
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    
    # Base conditions
    conditions = [JobPost.first_seen >= week_ago]
    prev_conditions = [
        JobPost.first_seen >= two_weeks_ago,
        JobPost.first_seen < week_ago
    ]
    
    if location:
        location_filter = or_(
            Location.city.ilike(f"%{location}%"),
            Location.region.ilike(f"%{location}%"),
            Location.country.ilike(f"%{location}%")
        )
        conditions.append(location_filter)
        prev_conditions.append(location_filter)
    
    # Current week data
    current_week_stmt = select(
        JobPost, Organization, TitleNorm
    ).join(
        Organization, Organization.id == JobPost.org_id, isouter=True
    ).join(
        TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(and_(*conditions))
    
    current_week_jobs = db.execute(current_week_stmt).all()
    
    # Previous week data for comparison
    prev_week_stmt = select(
        JobPost, Organization, TitleNorm
    ).join(
        Organization, Organization.id == JobPost.org_id, isouter=True
    ).join(
        TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(and_(*prev_conditions))
    
    prev_week_jobs = db.execute(prev_week_stmt).all()
    
    # Analyze current week
    current_companies = Counter()
    current_roles = Counter()
    current_salaries = []
    current_tenure = Counter()
    
    for job, org, title_norm in current_week_jobs:
        if org:
            current_companies[org.name] += 1
        
        role_family = title_norm.family if title_norm else "other"
        current_roles[role_family] += 1
        
        if job.salary_min:
            current_salaries.append(job.salary_min)
        
        if job.tenure:
            current_tenure[job.tenure] += 1
    
    # Analyze previous week
    prev_companies = Counter()
    prev_roles = Counter()
    
    for job, org, title_norm in prev_week_jobs:
        if org:
            prev_companies[org.name] += 1
        
        role_family = title_norm.family if title_norm else "other"
        prev_roles[role_family] += 1
    
    # Calculate trends
    trending_skills = get_trending_skills(db, days=7)
    
    return {
        "period": "Past 7 days",
        "location": location or "All locations",
        "total_postings": len(current_week_jobs),
        "week_over_week_change": len(current_week_jobs) - len(prev_week_jobs),
        "top_hiring_companies": [
            {"company": company, "postings": count}
            for company, count in current_companies.most_common(10)
        ],
        "postings_by_role_family": [
            {
                "role_family": role.replace("_", " ").title(),
                "postings": count,
                "change": count - prev_roles.get(role, 0)
            }
            for role, count in current_roles.most_common(10)
        ],
        "median_salary": calculate_median(current_salaries) if current_salaries else None,
        "salary_coverage": f"{len(current_salaries)}/{len(current_week_jobs)} postings ({len(current_salaries)/len(current_week_jobs)*100:.0f}%)" if current_week_jobs else "0%",
        "tenure_mix": [
            {"type": tenure, "count": count, "percentage": round(count/len(current_week_jobs)*100, 1)}
            for tenure, count in current_tenure.most_common()
        ] if current_week_jobs else [],
        "trending_skills": trending_skills
    }

def get_market_trends(db: Session, days: int = 30, location: str | None = None) -> dict:
    """Get market trends over specified period"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query conditions
    conditions = [JobPost.first_seen >= start_date]
    if location:
        conditions.append(or_(
            Location.city.ilike(f"%{location}%"),
            Location.region.ilike(f"%{location}%"),
            Location.country.ilike(f"%{location}%")
        ))
    
    # Daily posting counts
    daily_counts_stmt = select(
        func.date(JobPost.first_seen).label('date'),
        func.count(JobPost.id).label('count')
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(
        and_(*conditions)
    ).group_by(
        func.date(JobPost.first_seen)
    ).order_by('date')
    
    daily_counts = db.execute(daily_counts_stmt).all()
    
    # Role family trends
    role_trends_stmt = select(
        TitleNorm.family,
        func.count(JobPost.id).label('count'),
        func.date(JobPost.first_seen).label('date')
    ).join(
        TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(
        and_(*conditions)
    ).group_by(
        TitleNorm.family, func.date(JobPost.first_seen)
    ).order_by('date')
    
    role_trends = db.execute(role_trends_stmt).all()
    
    # Calculate growth rates
    growth_rates = calculate_growth_rates(daily_counts)
    
    return {
        "period": f"Past {days} days",
        "location": location or "All locations",
        "daily_posting_counts": [
            {"date": str(date), "postings": count}
            for date, count in daily_counts
        ],
        "average_daily_postings": sum(count for _, count in daily_counts) / len(daily_counts) if daily_counts else 0,
        "growth_rate": growth_rates,
        "role_family_trends": organize_role_trends(role_trends),
        "market_temperature": assess_market_temperature(daily_counts)
    }

def get_salary_insights(db: Session, role_family: str | None = None, location: str | None = None) -> dict:
    """Get salary insights by role family and location"""
    
    conditions = [JobPost.salary_min.is_not(None)]
    
    if role_family:
        conditions.append(TitleNorm.family.ilike(f"%{role_family}%"))
    
    if location:
        conditions.append(or_(
            Location.city.ilike(f"%{location}%"),
            Location.region.ilike(f"%{location}%"),
            Location.country.ilike(f"%{location}%")
        ))
    
    # Salary statistics
    salary_stats_stmt = select(
        func.percentile_cont(0.25).within_group(JobPost.salary_min).label('p25'),
        func.percentile_cont(0.5).within_group(JobPost.salary_min).label('median'),
        func.percentile_cont(0.75).within_group(JobPost.salary_min).label('p75'),
        func.min(JobPost.salary_min).label('min_salary'),
        func.max(JobPost.salary_max).label('max_salary'),
        func.count(JobPost.id).label('sample_size'),
        JobPost.currency
    ).join(
        TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(
        and_(*conditions)
    ).group_by(JobPost.currency)
    
    salary_stats = db.execute(salary_stats_stmt).all()
    
    # Salary by role family
    role_salary_stmt = select(
        TitleNorm.family,
        func.percentile_cont(0.5).within_group(JobPost.salary_min).label('median_salary'),
        func.count(JobPost.id).label('count')
    ).join(
        TitleNorm, TitleNorm.id == JobPost.title_norm_id
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(
        and_(*conditions)
    ).group_by(
        TitleNorm.family
    ).having(
        func.count(JobPost.id) >= 3  # Only include families with sufficient data
    ).order_by(desc('median_salary'))
    
    role_salaries = db.execute(role_salary_stmt).all()
    
    return {
        "role_family": role_family or "All roles",
        "location": location or "All locations",
        "salary_statistics": [
            {
                "currency": currency,
                "percentile_25": p25,
                "median": median,
                "percentile_75": p75,
                "min_salary": min_sal,
                "max_salary": max_sal,
                "sample_size": sample_size
            }
            for p25, median, p75, min_sal, max_sal, sample_size, currency in salary_stats
        ],
        "salary_by_role_family": [
            {
                "role_family": family.replace("_", " ").title() if family else "Other",
                "median_salary": median_salary,
                "job_count": count
            }
            for family, median_salary, count in role_salaries
        ],
        "data_coverage": f"Based on {sum(stats[5] for stats in salary_stats)} job postings with salary data"
    }

def get_attachment_companies(db: Session, location: str | None = None) -> dict:
    """Get companies that accept attachments/internships"""
    
    conditions = [JobPost.attachment_flag == True]
    
    if location:
        conditions.append(or_(
            Location.city.ilike(f"%{location}%"),
            Location.region.ilike(f"%{location}%"),
            Location.country.ilike(f"%{location}%")
        ))
    
    # Companies with attachment programs
    attachment_stmt = select(
        Organization.name,
        Organization.sector,
        func.count(JobPost.id).label('attachment_postings'),
        func.array_agg(JobPost.title_raw).label('role_types')
    ).join(
        JobPost, JobPost.org_id == Organization.id
    ).join(
        Location, Location.id == JobPost.location_id, isouter=True
    ).where(
        and_(*conditions)
    ).group_by(
        Organization.name, Organization.sector
    ).order_by(desc('attachment_postings'))
    
    attachment_companies = db.execute(attachment_stmt).all()
    
    # Attachment trends
    recent_attachments = db.execute(
        select(func.count(JobPost.id)).where(
            JobPost.attachment_flag == True,
            JobPost.first_seen >= datetime.utcnow() - timedelta(days=30)
        )
    ).scalar() or 0
    
    return {
        "location": location or "All locations",
        "companies_with_attachments": [
            {
                "company": name,
                "sector": sector,
                "attachment_postings": postings,
                "role_types": list(set(roles))[:5],  # Unique roles, limit to 5
                "application_advice": generate_application_advice(name, sector)
            }
            for name, sector, postings, roles in attachment_companies
        ],
        "recent_attachment_postings": recent_attachments,
        "total_companies": len(attachment_companies),
        "application_timing": "Most attachment programs recruit in Q1 (Jan-Mar) and Q3 (Jul-Sep)"
    }

def get_trending_skills(db: Session, days: int = 7) -> list[dict]:
    """Get trending skills based on recent job postings"""
    
    # Current period skills
    current_period = datetime.utcnow() - timedelta(days=days)
    prev_period = datetime.utcnow() - timedelta(days=days*2)
    
    # Current skills
    current_skills_stmt = select(
        Skill.name,
        func.count(JobSkill.id).label('current_count')
    ).join(
        JobSkill, JobSkill.skill_id == Skill.id
    ).join(
        JobPost, JobPost.id == JobSkill.job_post_id
    ).where(
        JobPost.first_seen >= current_period
    ).group_by(Skill.name)
    
    current_skills = {name: count for name, count in db.execute(current_skills_stmt).all()}
    
    # Previous period skills
    prev_skills_stmt = select(
        Skill.name,
        func.count(JobSkill.id).label('prev_count')
    ).join(
        JobSkill, JobSkill.skill_id == Skill.id
    ).join(
        JobPost, JobPost.id == JobSkill.job_post_id
    ).where(
        JobPost.first_seen >= prev_period,
        JobPost.first_seen < current_period
    ).group_by(Skill.name)
    
    prev_skills = {name: count for name, count in db.execute(prev_skills_stmt).all()}
    
    # Calculate trends
    trending = []
    for skill, current_count in current_skills.items():
        prev_count = prev_skills.get(skill, 0)
        if prev_count > 0:
            growth_rate = ((current_count - prev_count) / prev_count) * 100
        else:
            growth_rate = 100 if current_count > 0 else 0
        
        if growth_rate > 20 and current_count >= 3:  # Significant growth with minimum volume
            trending.append({
                "skill": skill,
                "current_mentions": current_count,
                "growth_rate": round(growth_rate, 1),
                "trend": "rising"
            })
    
    return sorted(trending, key=lambda x: x["growth_rate"], reverse=True)[:10]

# Helper functions
def calculate_median(values: list[float]) -> float:
    """Calculate median of a list of values"""
    if not values:
        return 0
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    return sorted_values[n//2]

def calculate_growth_rates(daily_counts: list) -> dict:
    """Calculate growth rates from daily counts"""
    if len(daily_counts) < 7:
        return {"weekly_growth": 0, "trend": "insufficient_data"}
    
    recent_week = sum(count for _, count in daily_counts[-7:])
    prev_week = sum(count for _, count in daily_counts[-14:-7]) if len(daily_counts) >= 14 else recent_week
    
    if prev_week > 0:
        weekly_growth = ((recent_week - prev_week) / prev_week) * 100
    else:
        weekly_growth = 0
    
    trend = "growing" if weekly_growth > 5 else "declining" if weekly_growth < -5 else "stable"
    
    return {
        "weekly_growth": round(weekly_growth, 1),
        "trend": trend
    }

def organize_role_trends(role_trends: list) -> dict:
    """Organize role trends by family"""
    trends_by_family = {}
    for family, count, date in role_trends:
        if family not in trends_by_family:
            trends_by_family[family] = []
        trends_by_family[family].append({"date": str(date), "count": count})
    
    return {
        family.replace("_", " ").title() if family else "Other": data
        for family, data in trends_by_family.items()
    }

def assess_market_temperature(daily_counts: list) -> str:
    """Assess overall market temperature"""
    if not daily_counts:
        return "unknown"
    
    recent_avg = sum(count for _, count in daily_counts[-7:]) / 7 if len(daily_counts) >= 7 else 0
    overall_avg = sum(count for _, count in daily_counts) / len(daily_counts)
    
    if recent_avg > overall_avg * 1.2:
        return "hot"
    elif recent_avg < overall_avg * 0.8:
        return "cool"
    else:
        return "stable"

def generate_application_advice(company_name: str, sector: str) -> str:
    """Generate application advice for attachment programs"""
    advice_templates = {
        "technology": "Apply early with portfolio/GitHub projects",
        "finance": "Highlight analytical skills and Excel proficiency",
        "healthcare": "Emphasize relevant coursework and volunteer experience",
        "ngo": "Show passion for social impact and relevant experience",
        "government": "Follow formal application procedures and deadlines"
    }
    
    sector_lower = (sector or "").lower()
    for key, advice in advice_templates.items():
        if key in sector_lower:
            return advice
    
    return "Apply with tailored CV and cover letter"
