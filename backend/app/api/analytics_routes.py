from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.analytics import (
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
