from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from ..db.models import TitleNorm, JobPost, Skill, JobSkill, Organization
from ..ml.embeddings import embed_text
from ..normalization.titles import normalize_title, TITLE_ALIASES
import numpy as np
from collections import Counter

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def get_skills_for_role(db: Session, role_title: str, limit: int = 20) -> list[tuple[str, float]]:
    """Get most common skills for a specific role with frequency scores"""
    
    # Find jobs matching this role
    stmt = select(JobPost, Skill, JobSkill.confidence).join(
        JobSkill, JobPost.id == JobSkill.job_post_id
    ).join(Skill, Skill.id == JobSkill.skill_id).where(
        JobPost.title_raw.ilike(f"%{role_title}%")
    )
    
    rows = db.execute(stmt).all()
    
    # Count skill frequencies
    skill_counts = Counter()
    total_jobs = len(set(row[0].id for row in rows))
    
    for job_post, skill, confidence in rows:
        skill_counts[skill.name] += confidence or 0.5
    
    # Calculate frequency percentages
    skills_with_freq = []
    for skill_name, count in skill_counts.most_common(limit):
        frequency = (count / total_jobs) * 100 if total_jobs > 0 else 0
        skills_with_freq.append((skill_name, frequency))
    
    return skills_with_freq

def calculate_skill_overlap(current_skills: list[str], target_skills: list[tuple[str, float]]) -> tuple[float, list[str]]:
    """Calculate skill overlap percentage and identify missing skills"""
    
    if not target_skills:
        return 0.0, []
    
    current_skills_lower = [skill.lower() for skill in current_skills]
    target_skills_names = [skill[0].lower() for skill, freq in target_skills]
    
    # Find overlapping skills
    overlapping = set(current_skills_lower) & set(target_skills_names)
    overlap_percentage = (len(overlapping) / len(target_skills_names)) * 100 if target_skills_names else 0
    
    # Find missing high-frequency skills (top skills not in current skillset)
    missing_skills = []
    for skill_name, frequency in target_skills[:10]:  # Focus on top 10 skills
        if skill_name.lower() not in current_skills_lower and frequency > 20:  # Only high-frequency skills
            missing_skills.append(skill_name)
    
    return overlap_percentage, missing_skills[:3]  # Return top 3 missing skills

def extract_skills_from_text(text: str) -> list[str]:
    """Extract skills from job description or user input"""
    
    # Common skills patterns (this could be enhanced with NLP)
    common_skills = [
        "python", "sql", "excel", "powerbi", "tableau", "r", "stata", "spss",
        "javascript", "html", "css", "react", "node.js", "java", "c++",
        "project management", "data analysis", "machine learning", "statistics",
        "communication", "leadership", "teamwork", "problem solving",
        "microsoft office", "google analytics", "salesforce", "crm",
        "financial modeling", "budgeting", "forecasting", "accounting",
        "research", "writing", "presentation", "training", "mentoring"
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    return found_skills

def transitions_for(db: Session, current: str):
    """Enhanced career transition recommendations with real skill gap analysis"""
    
    # Normalize current role
    current_family, current_canonical = normalize_title(current)
    
    # Extract skills from current role description if available
    current_skills = extract_skills_from_text(current)
    
    # Get embeddings for semantic similarity
    current_embedding = embed_text(current)
    
    # Get all available career paths
    titles = db.execute(select(TitleNorm)).scalars().all()
    
    # Calculate similarities and get recommendations
    scored_transitions = []
    
    for title_norm in titles:
        # Skip if it's the same role
        if title_norm.canonical_title.lower() == current_canonical.lower():
            continue
        
        # Calculate semantic similarity
        target_embedding = embed_text(f"{title_norm.family} {title_norm.canonical_title}")
        semantic_similarity = cosine_similarity(current_embedding, target_embedding)
        
        # Get skills for target role
        target_skills = get_skills_for_role(db, title_norm.canonical_title)
        
        # Calculate skill overlap
        skill_overlap, missing_skills = calculate_skill_overlap(current_skills, target_skills)
        
        # Combined score (semantic similarity + skill overlap)
        combined_score = (semantic_similarity * 0.6) + (skill_overlap / 100 * 0.4)
        
        # Get market demand (number of recent postings)
        market_demand = db.execute(
            select(func.count(JobPost.id)).where(
                JobPost.title_raw.ilike(f"%{title_norm.canonical_title}%")
            )
        ).scalar() or 0
        
        scored_transitions.append({
            "target_role": title_norm.canonical_title,
            "role_family": title_norm.family,
            "overlap": round(max(semantic_similarity * 100, skill_overlap), 1),
            "gap_skills": missing_skills,
            "market_demand": market_demand,
            "combined_score": combined_score,
            "explanation": generate_transition_explanation(
                current_canonical, title_norm.canonical_title, 
                semantic_similarity, skill_overlap, missing_skills
            )
        })
    
    # Sort by combined score and filter for realistic transitions
    scored_transitions.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # Filter for transitions with reasonable overlap (>30%) or high market demand
    realistic_transitions = [
        t for t in scored_transitions 
        if t["overlap"] > 30 or t["market_demand"] > 5
    ]
    
    return realistic_transitions[:5]  # Return top 5 recommendations

def generate_transition_explanation(current_role: str, target_role: str, 
                                  semantic_sim: float, skill_overlap: float, 
                                  missing_skills: list[str]) -> str:
    """Generate explanation for career transition recommendation"""
    
    explanations = []
    
    # Semantic similarity explanation
    if semantic_sim > 0.7:
        explanations.append("highly related field")
    elif semantic_sim > 0.5:
        explanations.append("related skillset")
    
    # Skill overlap explanation
    if skill_overlap > 70:
        explanations.append("strong skill match")
    elif skill_overlap > 50:
        explanations.append("good skill foundation")
    
    # Missing skills guidance
    if missing_skills:
        if len(missing_skills) <= 2:
            explanations.append(f"learn {', '.join(missing_skills)}")
        else:
            explanations.append(f"develop {len(missing_skills)} key skills")
    
    # Career progression logic
    if "senior" in target_role.lower() and "senior" not in current_role.lower():
        explanations.append("natural progression path")
    elif "analyst" in current_role.lower() and "manager" in target_role.lower():
        explanations.append("management track")
    
    return "; ".join(explanations) if explanations else "career pivot opportunity"

def get_trending_transitions(db: Session, days: int = 30) -> list[dict]:
    """Get trending career transitions based on recent job postings"""
    from datetime import datetime, timedelta

    # Calculate cutoff date for SQLite compatibility
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get roles with increasing demand
    stmt = select(
        JobPost.title_raw,
        func.count(JobPost.id).label('count')
    ).where(
        JobPost.first_seen >= cutoff_date
    ).group_by(JobPost.title_raw).having(
        func.count(JobPost.id) > 2
    ).order_by(desc('count'))
    
    trending_roles = db.execute(stmt).all()
    
    trending_transitions = []
    for role, count in trending_roles[:10]:
        family, canonical = normalize_title(role)
        trending_transitions.append({
            "role": canonical,
            "family": family,
            "recent_postings": count,
            "trend": "increasing demand"
        })
    
    return trending_transitions

def get_salary_insights_for_transition(db: Session, target_role: str) -> dict:
    """Get salary insights for a target role (SQLite compatible)"""

    # SQLite doesn't support percentile_cont, so we calculate median manually
    # First, get all salary values for the role
    stmt = select(
        JobPost.salary_min,
        JobPost.salary_max
    ).where(
        JobPost.title_raw.ilike(f"%{target_role}%"),
        JobPost.salary_min.is_not(None)
    ).order_by(JobPost.salary_min)

    rows = db.execute(stmt).all()
    sample_size = len(rows)

    if sample_size > 0:
        # Calculate median (middle value or average of two middle values)
        salary_mins = [row.salary_min for row in rows if row.salary_min is not None]
        salary_maxs = [row.salary_max for row in rows if row.salary_max is not None]

        def calculate_median(values):
            if not values:
                return None
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mid = n // 2
            if n % 2 == 0:
                return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            return sorted_vals[mid]

        median_min = calculate_median(salary_mins)
        median_max = calculate_median(salary_maxs) if salary_maxs else None

        return {
            "median_salary_min": median_min,
            "median_salary_max": median_max,
            "sample_size": sample_size,
            "coverage": f"Based on {sample_size} job postings with salary data"
        }

    return {
        "median_salary_min": None,
        "median_salary_max": None,
        "sample_size": 0,
        "coverage": "Limited salary data available"
    }
