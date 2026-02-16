import os
import re
from collections import Counter

import numpy as np
from sqlalchemy import func, or_, select, union
from sqlalchemy.orm import Session

from ..db.models import JobPost, Organization, Location, TitleNorm
from ..ml.embeddings import embed_text
from ..normalization.titles import get_careers_for_degree, normalize_title
from .ranking import rank_results
from .salary_service import salary_service


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
        r"background in (\w+(?:\s+\w+)*)",
    ]

    query_lower = query.lower()
    for pattern in degree_patterns:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(1).strip()
    return None


def search_jobs(
    db: Session,
    q: str = "",
    location: str | None = None,
    seniority: str | None = None,
    title: str | None = None,
    company: str | None = None,
    role_family: str | None = None,
    county: str | None = None,
    sector: str | None = None,
    high_confidence_only: bool = False,
    limit: int = 20,
    offset: int = 0,
):
    """Public search (O0): jobs + title/company aggregates for filtering."""

    has_more = False

    # Check if query contains degree information
    degree = extract_degree_from_query(q)
    if degree:
        jobs = search_by_degree(db, degree, location, seniority) or []
        clusters = Counter()
        companies = Counter()
        for row in jobs:
            title_value = row.get("title")
            company_value = row.get("organization")
            if title_value:
                clusters[title_value] += 1
            if title_value and company_value:
                companies[(title_value, company_value)] += 1

        return {
            "results": jobs,
            "jobs": jobs,
            "total": len(jobs),
            "limit": int(limit),
            "offset": int(offset),
            "has_more": False,
            "title_clusters": [
                {"title": t, "count_ads": int(c)} for t, c in clusters.most_common(50)
            ],
            "companies_hiring": [
                {"title": t, "company": co, "count_ads": int(c)}
                for (t, co), c in companies.most_common(200)
            ],
            "selected": {"title": title, "company": company},
            "meta": {"degree": degree},
        }

    try:
        bind = db.get_bind()
        dialect_name = bind.dialect.name if bind else ""
    except Exception:
        dialect_name = ""
    is_postgres = dialect_name == "postgresql"

    # Base joined query (jobs)
    stmt_jobs = (
        select(JobPost, Organization, Location, TitleNorm)
        .join(Organization, Organization.id == JobPost.org_id, isouter=True)
        .join(Location, Location.id == JobPost.location_id, isouter=True)
        .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
        .where(JobPost.is_active.is_(True))
    )

    filters = []
    location_condition = None
    if location:
        like_loc = f"%{location.lower()}%"
        location_condition = or_(
            Location.city.ilike(like_loc),
            Location.region.ilike(like_loc),
            Location.country.ilike(like_loc),
            Location.raw.ilike(like_loc),
        )
        filters.append(location_condition)

    seniority_condition = None
    if seniority:
        seniority_condition = JobPost.seniority.ilike(f"%{seniority.lower()}%")
        filters.append(seniority_condition)

    if role_family:
        filters.append(TitleNorm.family.ilike(f"%{role_family.lower()}%"))

    if county:
        like_county = f"%{county.lower()}%"
        filters.append(
            or_(
                Location.region.ilike(like_county),
                Location.city.ilike(like_county),
                Location.raw.ilike(like_county),
            )
        )

    if sector:
        filters.append(Organization.sector.ilike(f"%{sector.lower()}%"))

    if high_confidence_only:
        filters.append(JobPost.quality_score.is_not(None))
        filters.append(JobPost.quality_score >= 0.7)

    normalized_family = None
    normalized_title = None
    like = None
    like_norm = None
    title_norm_ids = None
    job_text = None
    ids_subq = None

    if q:
        normalized_family, normalized_title = normalize_title(q)
        like = f"%{q.lower()}%"
        like_norm = f"%{normalized_title.lower()}%"

        # Postgres query planning for large ORs across multiple joined tables is
        # extremely expensive (it can devolve into full table scans + hash joins).
        # Prefer a title-focused predicate that keeps queries index-friendly.
        if is_postgres:
            title_norm_stmt = select(TitleNorm.id)
            title_norm_clauses = [TitleNorm.canonical_title.ilike(like_norm)]
            if normalized_family and normalized_family != "other":
                title_norm_clauses.append(
                    TitleNorm.family.ilike(f"%{normalized_family}%")
                )
            title_norm_ids = title_norm_stmt.where(or_(*title_norm_clauses)).limit(2000)

            job_text = or_(
                JobPost.title_raw.ilike(like),
                JobPost.title_norm_id.in_(title_norm_ids),
            )
        else:
            clauses = [
                JobPost.title_raw.ilike(like),
                JobPost.description_raw.ilike(like),
                JobPost.requirements_raw.ilike(like),
                TitleNorm.canonical_title.ilike(like_norm),
            ]
            if normalized_family and normalized_family != "other":
                clauses.append(TitleNorm.family.ilike(f"%{normalized_family}%"))
            job_text = or_(*clauses)

    if filters:
        stmt_jobs = stmt_jobs.where(*filters)

    if q and job_text is not None:
        if is_postgres:
            # Fast probe to detect broad queries and pick a safer plan.
            probe_limit = 200
            stmt_probe = (
                select(JobPost.id)
                .select_from(JobPost)
                .join(Location, Location.id == JobPost.location_id, isouter=True)
                .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
                .where(JobPost.is_active.is_(True))
                .where(job_text)
            )
            if filters:
                stmt_probe = stmt_probe.where(*filters)
            probe_rows = db.execute(
                stmt_probe.order_by(JobPost.first_seen.desc()).limit(probe_limit)
            ).all()
            is_broad = len(probe_rows) >= probe_limit

            if is_broad:
                stmt_jobs = stmt_jobs.where(job_text)
            else:
                candidate_limit = max(int(offset) + int(limit) + 1, 200)
                ids_base = (
                    select(JobPost.id.label("job_id"))
                    .select_from(JobPost)
                    .join(
                        Location,
                        Location.id == JobPost.location_id,
                        isouter=True,
                    )
                    .join(
                        TitleNorm,
                        TitleNorm.id == JobPost.title_norm_id,
                        isouter=True,
                    )
                    .where(JobPost.is_active.is_(True))
                )
                if filters:
                    ids_base = ids_base.where(*filters)

                branches = [
                    ids_base.where(JobPost.title_raw.ilike(like))
                    .order_by(JobPost.first_seen.desc())
                    .limit(candidate_limit),
                    ids_base.where(JobPost.description_raw.ilike(like))
                    .order_by(JobPost.first_seen.desc())
                    .limit(candidate_limit),
                    ids_base.where(JobPost.requirements_raw.ilike(like))
                    .order_by(JobPost.first_seen.desc())
                    .limit(candidate_limit),
                    ids_base.where(TitleNorm.canonical_title.ilike(like_norm))
                    .order_by(JobPost.first_seen.desc())
                    .limit(candidate_limit),
                ]
                if normalized_family and normalized_family != "other":
                    branches.append(
                        ids_base.where(TitleNorm.family.ilike(f"%{normalized_family}%"))
                        .order_by(JobPost.first_seen.desc())
                        .limit(candidate_limit)
                    )

                ids_subq = union(*branches).subquery()
                stmt_jobs = stmt_jobs.where(JobPost.id.in_(select(ids_subq.c.job_id)))
        else:
            stmt_jobs = stmt_jobs.where(job_text)

    # Aggregate facets from a bounded sample so the UI can offer filters without
    # running multiple expensive GROUP BY queries over the full corpus.
    cluster_title_expr = func.coalesce(TitleNorm.canonical_title, JobPost.title_raw)
    county_expr = func.coalesce(Location.region, Location.city, Location.raw)
    facet_limit = 500 if is_postgres else 2000

    stmt_facets = (
        select(
            JobPost.id.label("job_id"),
            cluster_title_expr.label("cluster_title"),
            Organization.name.label("org_name"),
            TitleNorm.family.label("role_family"),
            JobPost.seniority.label("seniority"),
            county_expr.label("county"),
            Organization.sector.label("sector"),
        )
        .select_from(JobPost)
        .join(Organization, Organization.id == JobPost.org_id, isouter=True)
        .join(Location, Location.id == JobPost.location_id, isouter=True)
        .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
        .where(JobPost.is_active.is_(True))
    )
    if filters:
        stmt_facets = stmt_facets.where(*filters)
    if q and job_text is not None:
        if ids_subq is not None:
            stmt_facets = stmt_facets.where(JobPost.id.in_(select(ids_subq.c.job_id)))
        else:
            stmt_facets = stmt_facets.where(job_text)
    stmt_facets = stmt_facets.order_by(JobPost.first_seen.desc()).limit(facet_limit)

    facet_rows = db.execute(stmt_facets).all()
    clusters = Counter()
    companies = Counter()
    role_families = Counter()
    seniority_buckets = Counter()
    counties_hiring = Counter()
    sectors_hiring = Counter()

    for (
        _job_id,
        cluster_title,
        org_name,
        role_family_value,
        seniority_value,
        county_value,
        sector_value,
    ) in facet_rows:
        if cluster_title:
            clusters[cluster_title] += 1
        if cluster_title and org_name:
            companies[(cluster_title, org_name)] += 1
        if role_family_value:
            role_families[role_family_value] += 1
        if seniority_value:
            seniority_buckets[seniority_value] += 1
        if county_value:
            counties_hiring[county_value] += 1
        if sector_value:
            sectors_hiring[sector_value] += 1

    # Apply selected refinements for the job list.
    if title:
        stmt_jobs = stmt_jobs.where(cluster_title_expr == title)
    if company:
        stmt_jobs = stmt_jobs.where(Organization.name.ilike(f"%{company}%"))

    # Pagination: fetch limit+1 to compute has_more without an extra COUNT.
    page_rows = db.execute(
        stmt_jobs.order_by(JobPost.first_seen.desc())
        .limit(int(limit) + 1)
        .offset(int(offset))
    ).all()
    has_more = len(page_rows) > int(limit)
    rows = page_rows[: int(limit)]

    if is_postgres and q:
        # COUNT(*) over a broad ILIKE set can be extremely expensive. Use a cheap
        # lower bound and let the UI rely on `has_more` for pagination.
        total_jobs = int(offset) + len(rows) + (1 if has_more else 0)
    else:
        total_jobs = (
            db.execute(select(func.count()).select_from(stmt_jobs.subquery())).scalar()
            or 0
        )

    # Process results with explanations
    results = []
    # If transformers are disabled (common in multi-worker API deployments),
    # `embed_text()` falls back to hash vectors which are not semantically meaningful.
    # In that mode, disable semantic scoring to avoid randomizing ranking.
    transformers_enabled = os.getenv("NEXTSTEP_DISABLE_TRANSFORMERS") != "1"
    query_embedding = (
        embed_text(f"query: {q}") if (q and transformers_enabled) else None
    )
    embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "e5-small-v2")

    from ..db.models import JobEmbedding, JobEntities

    job_ids = [jp.id for jp, _org, _loc, _title_norm in rows]
    entities_by_job_id = {}
    if job_ids:
        entities_by_job_id = {
            e.job_id: e
            for e in db.execute(
                select(JobEntities).where(JobEntities.job_id.in_(job_ids))
            )
            .scalars()
            .all()
        }

    embeddings_by_job_id = {}
    if job_ids and query_embedding is not None:
        # Fetch embeddings in one query and keep the most recent per job_id.
        emb_rows = (
            db.execute(
                select(JobEmbedding)
                .where(JobEmbedding.job_id.in_(job_ids))
                .where(JobEmbedding.model_name == embedding_model)
                .order_by(JobEmbedding.job_id, JobEmbedding.id.desc())
            )
            .scalars()
            .all()
        )
        for emb in emb_rows:
            embeddings_by_job_id.setdefault(emb.job_id, emb)

    for jp, org, loc, title_norm in rows:
        # Calculate semantic similarity
        similarity_score = 0.0

        emb_record = embeddings_by_job_id.get(jp.id)
        if query_embedding and emb_record and emb_record.vector_json:
            try:
                # In Postgres this would be a real vector;
                # in SQLite it's JSON
                job_vec = emb_record.vector_json
                if isinstance(job_vec, str):
                    # Back-compat: older data stored the vector
                    # as a JSON string.
                    import json

                    job_vec = json.loads(job_vec)
                similarity_score = cosine_similarity(query_embedding, job_vec)
            except Exception:
                similarity_score = 0.0

        # Fetch entities for better explanation
        entities = entities_by_job_id.get(jp.id)

        # Generate explanation
        why_match = generate_match_explanation(
            q, jp, title_norm, similarity_score, entities
        )
        top_skills = extract_entity_skill_values(entities.skills if entities else None)
        quality_value = (
            float(jp.quality_score) if jp.quality_score is not None else None
        )
        is_high_confidence = bool(quality_value is not None and quality_value >= 0.7)
        posted_at = (
            jp.first_seen.isoformat() if getattr(jp, "first_seen", None) else None
        )
        county_value = None
        if loc:
            county_value = loc.region or loc.city or loc.raw

        results.append(
            {
                "id": jp.id,
                "title": jp.title_raw,
                "organization": org.name if org else "Unknown Company",
                "sector": org.sector if org else None,
                "location": format_location(loc),
                "county": county_value,
                "url": jp.url,
                "source_url": getattr(jp, "source_url", None) or jp.url,
                "application_url": (getattr(jp, "application_url", None) or jp.url),
                "first_seen": jp.first_seen.isoformat()
                if getattr(jp, "first_seen", None)
                else None,
                "posted_at": posted_at,
                "apply_url": f"/r/apply/{jp.id}",
                **build_salary_fields(jp, loc),
                "tenure": jp.tenure,
                "contract_type": jp.tenure,
                "seniority": jp.seniority,
                "role_family": title_norm.family if title_norm else None,
                "why_match": why_match,
                "top_skills": top_skills[:3],
                "quality_score": quality_value,
                "high_confidence": is_high_confidence,
                "quality_tag": "High confidence" if is_high_confidence else "Medium",
                "similarity_score": round(similarity_score * 100, 1)
                if similarity_score > 0
                else None,
                "skills_found": entities.skills if entities else [],
            }
        )

    # Apply learned ranking with fallback to similarity sort
    user_context = {}
    if location:
        user_context["location"] = location
    if seniority:
        user_context["seniority"] = seniority
    results = rank_results(results, q, user_context)

    # If no results, provide suggestions
    if not results and q:
        return suggest_alternatives(db, q, location, seniority)

    return {
        # Back-compat: older clients expect `results` to be a list of jobs.
        "results": results,
        "jobs": results,
        "total": int(total_jobs),
        "limit": int(limit),
        "offset": int(offset),
        "has_more": bool(has_more),
        "title_clusters": [
            {"title": title_value, "count_ads": int(count)}
            for title_value, count in clusters.most_common(50)
        ],
        "companies_hiring": [
            {
                "title": title_value,
                "company": company_name,
                "count_ads": int(count),
            }
            for (title_value, company_name), count in companies.most_common(200)
        ],
        "selected": {
            "title": title,
            "company": company,
            "role_family": role_family,
            "county": county,
            "sector": sector,
            "high_confidence_only": bool(high_confidence_only),
        },
        "role_families": [
            {"role_family": value, "count_ads": int(count)}
            for value, count in role_families.most_common(40)
        ],
        "seniority_buckets": [
            {"seniority": value, "count_ads": int(count)}
            for value, count in seniority_buckets.most_common(20)
        ],
        "counties_hiring": [
            {"county": value, "count_ads": int(count)}
            for value, count in counties_hiring.most_common(30)
        ],
        "sectors_hiring": [
            {"sector": value, "count_ads": int(count)}
            for value, count in sectors_hiring.most_common(30)
        ],
    }


def search_by_degree(
    db: Session,
    degree: str,
    location: str | None = None,
    seniority: str | None = None,
):
    """Search jobs based on degree/field of study"""

    # Get relevant career paths for the degree
    career_suggestions = get_careers_for_degree(degree)

    # Search for jobs matching these career paths
    stmt = (
        select(JobPost, Organization, Location, TitleNorm)
        .join(Organization, Organization.id == JobPost.org_id, isouter=True)
        .join(Location, Location.id == JobPost.location_id, isouter=True)
        .join(TitleNorm, TitleNorm.id == JobPost.title_norm_id, isouter=True)
        .where(JobPost.is_active.is_(True))
    )

    # Build conditions for career-relevant jobs
    title_conditions = []
    for career in career_suggestions:
        title_conditions.append(JobPost.title_raw.ilike(f"%{career}%"))
        title_conditions.append(TitleNorm.canonical_title.ilike(f"%{career}%"))

    conditions = [or_(*title_conditions)]

    # Apply location filter
    if location:
        like_loc = f"%{location.lower()}%"
        conditions.append(
            or_(
                Location.city.ilike(like_loc),
                Location.region.ilike(like_loc),
                Location.country.ilike(like_loc),
                Location.raw.ilike(like_loc),
            )
        )

    # Apply seniority filter (default to entry level for degree searches)
    if seniority:
        conditions.append(JobPost.seniority.ilike(f"%{seniority.lower()}%"))
    else:
        conditions.append(
            or_(
                JobPost.seniority.ilike("%entry%"),
                JobPost.seniority.ilike("%junior%"),
                JobPost.seniority.ilike("%graduate%"),
                JobPost.seniority.is_(None),
            )
        )

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

        results.append(
            {
                "id": jp.id,
                "title": jp.title_raw,
                "organization": org.name if org else "Unknown Company",
                "location": format_location(loc),
                "url": jp.url,
                "first_seen": jp.first_seen.isoformat()
                if getattr(jp, "first_seen", None)
                else None,
                **build_salary_fields(jp, loc),
                "tenure": jp.tenure,
                "seniority": jp.seniority,
                "why_match": why_match,
                "career_path": matched_career,
            }
        )

    return results


def suggest_alternatives(
    db: Session,
    original_query: str,
    location: str | None = None,
    seniority: str | None = None,
):
    """Suggest alternative searches when no results found"""

    # Try broader search terms
    normalized_family, normalized_title = normalize_title(original_query)

    # Search by family instead of specific title
    if normalized_family != "other":
        stmt = (
            select(JobPost, Organization, Location, TitleNorm)
            .join(
                Organization,
                Organization.id == JobPost.org_id,
                isouter=True,
            )
            .join(Location, Location.id == JobPost.location_id, isouter=True)
            .join(
                TitleNorm,
                TitleNorm.id == JobPost.title_norm_id,
                isouter=True,
            )
            .where(JobPost.is_active.is_(True))
        )

        conditions = [TitleNorm.family.ilike(f"%{normalized_family}%")]

        if location:
            like_loc = f"%{location.lower()}%"
            conditions.append(
                or_(
                    Location.city.ilike(like_loc),
                    Location.region.ilike(like_loc),
                    Location.raw.ilike(like_loc),
                )
            )

        stmt = stmt.where(*conditions)
        rows = db.execute(stmt.limit(10)).all()

        if rows:
            results = []
            for jp, org, loc, title_norm in rows:
                results.append(
                    {
                        "id": jp.id,
                        "title": jp.title_raw,
                        "organization": org.name if org else "Unknown Company",
                        "location": format_location(loc),
                        "url": jp.url,
                        **build_salary_fields(jp, loc),
                        "why_match": (
                            f"Broader match in "
                            f"{normalized_family.replace('_', ' ')} field"
                        ),
                        "is_suggestion": True,
                    }
                )
            return results

    # Return empty with helpful message
    return [
        {
            "id": 0,
            "title": "No exact matches found",
            "organization": None,
            "location": None,
            "url": None,
            "why_match": (
                f"Try broader terms like "
                f"'{normalized_family.replace('_', ' ')}' or check spelling"
            ),
            "is_suggestion": True,
        }
    ]


def generate_match_explanation(
    query: str,
    job_post: JobPost,
    title_norm: TitleNorm | None,
    similarity_score: float,
    entities: any = None,
) -> str:
    """Generate explanation for why a job matches the search"""

    explanations = []
    q = (query or "").lower()

    def _skill_values(raw_skills: object) -> list[str]:
        """Best-effort extraction of skill strings from JobEntities.skills.

        In production this is typically a list[dict] like:
        {"value": "python", "confidence": 0.8, ...}
        but older rows or other processors may store strings or dicts.
        """

        if not raw_skills:
            return []
        if isinstance(raw_skills, list):
            out: list[str] = []
            for item in raw_skills:
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s)
                    continue
                if isinstance(item, dict):
                    v = (
                        item.get("value")
                        or item.get("name")
                        or item.get("skill")
                        or item.get("text")
                    )
                    if isinstance(v, str):
                        s = v.strip()
                        if s:
                            out.append(s)
            return out
        if isinstance(raw_skills, dict):
            # Handle rare cases like {"python": 0.8, "sql": 0.7}
            return [str(k).strip() for k in raw_skills.keys() if str(k).strip()]
        return []

    # Title match
    if q and q in (job_post.title_raw or "").lower():
        explanations.append("title matches search")

    # Entity/Skill match
    raw_skills = None
    if entities:
        if isinstance(entities, dict):
            raw_skills = entities.get("skills")
        else:
            raw_skills = getattr(entities, "skills", None)
    skills_lc = {s.lower() for s in _skill_values(raw_skills)}
    if q and skills_lc and q in skills_lc:
        explanations.append(f"requires {query} skill")

    # Normalized title match
    if title_norm and q and q in (title_norm.canonical_title or "").lower():
        explanations.append(f"major {title_norm.canonical_title} role")

    # Semantic similarity
    if similarity_score > 0.7:
        explanations.append(f"high semantic match ({similarity_score * 100:.0f}%)")
    elif similarity_score > 0.5:
        explanations.append(f"related concept ({similarity_score * 100:.0f}%)")

    if not explanations:
        explanations.append("general match")

    return "; ".join(explanations[:3])  # Limit to top 3 explanations


def extract_entity_skill_values(raw_skills: object) -> list[str]:
    """Extract normalized skill strings from JobEntities.skills payload."""
    if not raw_skills:
        return []
    if isinstance(raw_skills, list):
        out: list[str] = []
        for item in raw_skills:
            if isinstance(item, str):
                value = item.strip()
                if value:
                    out.append(value)
                continue
            if isinstance(item, dict):
                value = (
                    item.get("value")
                    or item.get("name")
                    or item.get("skill")
                    or item.get("text")
                )
                if isinstance(value, str):
                    normalized = value.strip()
                    if normalized:
                        out.append(normalized)
        return out
    if isinstance(raw_skills, dict):
        return [str(key).strip() for key in raw_skills.keys() if str(key).strip()]
    return []


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


def format_salary(
    min_sal: float | None, max_sal: float | None, currency: str | None
) -> str | None:
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


def build_salary_fields(job_post: JobPost, location: Location | None) -> dict:
    salary_range = format_salary(
        job_post.salary_min,
        job_post.salary_max,
        job_post.currency,
    )
    if salary_range:
        return {
            "salary_range": salary_range,
            "salary_estimated": False,
            "salary_confidence": None,
        }

    estimate = salary_service.estimate_salary_range(
        title=job_post.title_raw,
        seniority=job_post.seniority,
        location_text=format_location(location),
        currency=job_post.currency or "KES",
    )
    return {
        "salary_range": salary_service.format_salary_range(
            estimate["min"],
            estimate["max"],
            estimate["currency"],
        ),
        "salary_estimated": bool(estimate["estimated"]),
        "salary_confidence": float(estimate["confidence"]),
    }
