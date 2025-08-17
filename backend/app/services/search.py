from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
from ..ml.embeddings import embed_text
from ..normalization.titles import normalize_title, get_careers_for_degree, explain_title_match
import numpy as np
import re

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def extract_degree_from_query(query: str) -> str | None:
    """Extract degree information from search query"""
    degree_patterns = [
        r"i studied (\w+(?:\s+\w+)*)",
        r"degree in (\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*) graduate",
        r"(\w+(?:\s+\w+)*) degree",
        r"background in (\w+(?:\s+\w+)*)"
    ]
    
    query_lower = query.lower()
    for pattern in degree_patterns:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(1).strip()
    return None

def search_jobs(db: Session, q: str = "", location: str | None = None, seniority: str | None = None):
    """Enhanced job search with semantic matching and explanations"""
    
    # Check if query contains degree information
    degree = extract_degree_from_query(q)
    if degree:
        return search_by_degree(db, degree, location, seniority)
    
    # Build base query
    stmt = select(JobPost, Organization, Location, TitleNorm).join(
        Organization, Organization.id == JobPost.org_id, isouter=True
    ).join(Location, Location.id == JobPost.location_id, isouter=True
    ).join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)

    # Apply filters
    conditions = []
    
    if q:
        # Normalize the search query
        normalized_family, normalized_title = normalize_title(q)
        
        # Search in multiple fields
        like = f"%{q.lower()}%"
        like_norm = f"%{normalized_title.lower()}%"
        
        conditions.append(or_(
            JobPost.title_raw.ilike(like),
            JobPost.description_raw.ilike(like),
            JobPost.requirements_raw.ilike(like),
            TitleNorm.canonical_title.ilike(like_norm),
            TitleNorm.family.ilike(f"%{normalized_family}%")
        ))
    
    if location:
        like_loc = f"%{location.lower()}%"
        conditions.append(or_(
            Location.city.ilike(like_loc),
            Location.region.ilike(like_loc),
            Location.country.ilike(like_loc),
            Location.raw.ilike(like_loc)
        ))
    
    if seniority:
        conditions.append(JobPost.seniority.ilike(f"%{seniority.lower()}%"))
    
    if conditions:
        stmt = stmt.where(*conditions)
    
    # Execute query
    rows = db.execute(stmt.limit(20)).all()
    
    # Process results with explanations
    results = []
    query_embedding = embed_text(q) if q else None
    
    for jp, org, loc, title_norm in rows:
        # Calculate semantic similarity if we have embeddings
        similarity_score = 0.0
        if query_embedding and jp.embedding:
            try:
                job_embedding = eval(jp.embedding) if isinstance(jp.embedding, str) else jp.embedding
                similarity_score = cosine_similarity(query_embedding, job_embedding)
            except:
                similarity_score = 0.0
        
        # Generate explanation
        why_match = generate_match_explanation(q, jp, title_norm, similarity_score)
        
        results.append({
            "id": jp.id,
            "title": jp.title_raw,
            "organization": org.name if org else "Unknown Company",
            "location": format_location(loc),
            "url": jp.url,
            "salary_range": format_salary(jp.salary_min, jp.salary_max, jp.currency),
            "tenure": jp.tenure,
            "seniority": jp.seniority,
            "why_match": why_match,
            "similarity_score": round(similarity_score * 100, 1) if similarity_score > 0 else None
        })
    
    # Sort by similarity score if available
    if query_embedding:
        results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    
    # If no results, provide suggestions
    if not results and q:
        return suggest_alternatives(db, q, location, seniority)
    
    return results

def search_by_degree(db: Session, degree: str, location: str | None = None, seniority: str | None = None):
    """Search jobs based on degree/field of study"""
    
    # Get relevant career paths for the degree
    career_suggestions = get_careers_for_degree(degree)
    
    # Search for jobs matching these career paths
    stmt = select(JobPost, Organization, Location, TitleNorm).join(
        Organization, Organization.id == JobPost.org_id, isouter=True
    ).join(Location, Location.id == JobPost.location_id, isouter=True
    ).join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
    
    # Build conditions for career-relevant jobs
    title_conditions = []
    for career in career_suggestions:
        title_conditions.append(JobPost.title_raw.ilike(f"%{career}%"))
        title_conditions.append(TitleNorm.canonical_title.ilike(f"%{career}%"))
    
    conditions = [or_(*title_conditions)]
    
    # Apply location filter
    if location:
        like_loc = f"%{location.lower()}%"
        conditions.append(or_(
            Location.city.ilike(like_loc),
            Location.region.ilike(like_loc),
            Location.country.ilike(like_loc),
            Location.raw.ilike(like_loc)
        ))
    
    # Apply seniority filter (default to entry level for degree searches)
    if seniority:
        conditions.append(JobPost.seniority.ilike(f"%{seniority.lower()}%"))
    else:
        conditions.append(or_(
            JobPost.seniority.ilike("%entry%"),
            JobPost.seniority.ilike("%junior%"),
            JobPost.seniority.ilike("%graduate%"),
            JobPost.seniority.is_(None)
        ))
    
    stmt = stmt.where(*conditions)
    rows = db.execute(stmt.limit(20)).all()
    
    results = []
    for jp, org, loc, title_norm in rows:
        # Determine which career path this job matches
        matched_career = None
        for career in career_suggestions:
            if career.lower() in jp.title_raw.lower():
                matched_career = career
                break
        
        why_match = f"Matches {degree} background → {matched_career or 'relevant role'}"
        
        results.append({
            "id": jp.id,
            "title": jp.title_raw,
            "organization": org.name if org else "Unknown Company",
            "location": format_location(loc),
            "url": jp.url,
            "salary_range": format_salary(jp.salary_min, jp.salary_max, jp.currency),
            "tenure": jp.tenure,
            "seniority": jp.seniority,
            "why_match": why_match,
            "career_path": matched_career
        })
    
    return results

def suggest_alternatives(db: Session, original_query: str, location: str | None = None, seniority: str | None = None):
    """Suggest alternative searches when no results found"""
    
    # Try broader search terms
    normalized_family, normalized_title = normalize_title(original_query)
    
    # Search by family instead of specific title
    if normalized_family != "other":
        stmt = select(JobPost, Organization, Location, TitleNorm).join(
            Organization, Organization.id == JobPost.org_id, isouter=True
        ).join(Location, Location.id == JobPost.location_id, isouter=True
        ).join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
        
        conditions = [TitleNorm.family.ilike(f"%{normalized_family}%")]
        
        if location:
            like_loc = f"%{location.lower()}%"
            conditions.append(or_(
                Location.city.ilike(like_loc),
                Location.region.ilike(like_loc),
                Location.raw.ilike(like_loc)
            ))
        
        stmt = stmt.where(*conditions)
        rows = db.execute(stmt.limit(10)).all()
        
        if rows:
            results = []
            for jp, org, loc, title_norm in rows:
                results.append({
                    "id": jp.id,
                    "title": jp.title_raw,
                    "organization": org.name if org else "Unknown Company",
                    "location": format_location(loc),
                    "url": jp.url,
                    "salary_range": format_salary(jp.salary_min, jp.salary_max, jp.currency),
                    "why_match": f"Broader match in {normalized_family.replace('_', ' ')} field",
                    "is_suggestion": True
                })
            return results
    
    # Return empty with helpful message
    return [{
        "id": 0,
        "title": "No exact matches found",
        "organization": None,
        "location": None,
        "url": None,
        "why_match": f"Try broader terms like '{normalized_family.replace('_', ' ')}' or check spelling",
        "is_suggestion": True
    }]

def generate_match_explanation(query: str, job_post: JobPost, title_norm: TitleNorm | None, similarity_score: float) -> str:
    """Generate explanation for why a job matches the search"""
    
    explanations = []
    
    # Title match
    if query.lower() in job_post.title_raw.lower():
        explanations.append("title contains search term")
    
    # Normalized title match
    if title_norm and query.lower() in title_norm.canonical_title.lower():
        explanations.append(f"matches {title_norm.canonical_title} role family")
    
    # Semantic similarity
    if similarity_score > 0.7:
        explanations.append(f"high semantic similarity ({similarity_score*100:.0f}%)")
    elif similarity_score > 0.5:
        explanations.append(f"good semantic match ({similarity_score*100:.0f}%)")
    
    # Description match
    if query and job_post.description_raw and query.lower() in job_post.description_raw.lower():
        explanations.append("mentioned in job description")
    
    if not explanations:
        explanations.append("general relevance")
    
    return "; ".join(explanations[:3])  # Limit to top 3 explanations

def format_location(location: Location | None) -> str | None:
    """Format location information"""
    if not location:
        return None
    
    parts = []
    if location.city:
        parts.append(location.city)
    if location.region and location.region != location.city:
        parts.append(location.region)
    if location.country and location.country not in parts:
        parts.append(location.country)
    
    return ", ".join(parts) if parts else location.raw

def format_salary(min_sal: float | None, max_sal: float | None, currency: str | None) -> str | None:
    """Format salary range"""
    if not min_sal and not max_sal:
        return None
    
    curr = currency or "KES"
    
    if min_sal and max_sal:
        return f"{curr} {min_sal:,.0f} - {max_sal:,.0f}"
    elif min_sal:
        return f"{curr} {min_sal:,.0f}+"
    elif max_sal:
        return f"Up to {curr} {max_sal:,.0f}"
    
    return None
