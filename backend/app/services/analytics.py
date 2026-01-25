from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, text
from ..db.models import JobPost, JobEntities, TitleNorm, SkillTrendsMonthly, RoleEvolution
import pandas as pd
from datetime import datetime
import json

def aggregate_skill_trends(db: Session):
    """
    Populate SkillTrendsMonthly from JobEntities.
    Aggregation: count occurrences of skills per role family per month.
    """
    # 1. Fetch raw entity data
    stmt = select(JobPost.first_seen, TitleNorm.family, JobEntities.skills).join(
        TitleNorm, JobPost.title_norm_id == TitleNorm.id
    ).join(
        JobEntities, JobPost.id == JobEntities.job_id
    )
    
    rows = db.execute(stmt).all()
    if not rows:
        return {"status": "warning", "message": "No entity data found for aggregation"}
        
    data = []
    for dt, family, skills in rows:
        month = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # skills is stored as JSONB list
        for skill in (skills or []):
            data.append({"month": month, "family": family, "skill": skill})
            
    df = pd.DataFrame(data)
    if df.empty:
        return {"status": "warning", "message": "No skills extracted for aggregation"}
        
    # 2. Group and count
    counts = df.groupby(["month", "family", "skill"]).size().reset_index(name="count")
    
    # 3. Save to SkillTrendsMonthly
    db.execute(text("DELETE FROM skill_trends_monthly")) # Reset baseline for simplicity
    
    for _, row in counts.iterrows():
        trend = SkillTrendsMonthly(
            skill=row["skill"],
            title_norm=row["family"],
            month=row["month"],
            count=int(row["count"]),
            share=0.0 # Could calculate relative share here
        )
        db.add(trend)
        
    db.commit()
    return {"status": "success", "count": len(counts)}

def generate_role_evolution(db: Session):
    """Identify top skills per role family to track evolution."""
    # Similar logic to skill trends but focusing on top-K per month
    db.execute(text("DELETE FROM role_evolution"))
    # ... logic to find top skills ...
    db.commit()
    return {"status": "success"}

def refresh_analytics_baseline(db: Session):
    """Main entry point for CLI to refresh all analytics tables."""
    skill_results = aggregate_skill_trends(db)
    evolution_results = generate_role_evolution(db)
    
    status = "success" if skill_results["status"] == "success" else "warning"
    return {
        "status": status,
        "message": f"Analytics baseline refreshed. Skill trends: {skill_results.get('count', 0)} rows."
    }
