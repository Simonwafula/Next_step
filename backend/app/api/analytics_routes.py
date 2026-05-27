from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.analytics import (
    get_operations_intelligence_rollup,
    get_skill_trends,
    get_role_evolution,
    get_title_adjacency,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/skill-trends")
def skill_trends(
    role_family: str | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return get_skill_trends(db, role_family=role_family, months=months, limit=limit)


@router.get("/role-evolution")
def role_evolution(
    role_family: str | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    limit: int = Query(24, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return get_role_evolution(db, role_family=role_family, months=months, limit=limit)


@router.get("/title-adjacency")
def title_adjacency(
    title: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_title_adjacency(db, title=title, limit=limit)


@router.get("/market-pulse")
def market_pulse(
    query: str | None = Query(None, min_length=1, max_length=80),
    period: str = Query("monthly", pattern="^(daily|monthly|quarterly|annual)$"),
    window_days: int = Query(180, ge=30, le=365),
    limit: int = Query(5, ge=1, le=8),
    db: Session = Depends(get_db),
):
    rollup = get_operations_intelligence_rollup(
        db,
        query=query,
        period=period,
        window_days=window_days,
        limit=limit,
    )
    return {
        "query": rollup["query"],
        "period": rollup["period"],
        "window_days": rollup["window_days"],
        "sample": rollup["sample"],
        "series": rollup["series"][-6:],
        "top_skills": rollup["top_skills"][:limit],
        "top_companies": rollup["top_companies"][:limit],
        "top_sectors": rollup["top_sectors"][:limit],
    }
