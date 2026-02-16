"""Admin endpoints for audit log and system events."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import ProcessingLog, User
from ..services.auth_service import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin-audit"])

# Process types that represent admin actions (vs. automated system events)
ADMIN_ACTION_TYPES = frozenset(
    {
        "monitoring",
        "admin_conversion_alert_settings",
    }
)

SYSTEM_EVENT_TYPES = frozenset(
    {
        "post_processing",
        "government_processing",
        "ingestion",
        "deduplication",
        "embedding",
        "normalization",
    }
)


@router.get("/audit-log")
def audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action_filter: str | None = Query(
        None, description="Filter by process_type prefix"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Admin audit log — shows admin-triggered and monitoring events."""
    del current_user

    stmt = select(ProcessingLog)

    if action_filter:
        stmt = stmt.where(ProcessingLog.process_type.ilike(f"%{action_filter}%"))

    total = (
        db.execute(
            select(func.count(ProcessingLog.id)).where(
                ProcessingLog.process_type.ilike(f"%{action_filter}%")
                if action_filter
                else True
            )
        ).scalar()
        or 0
    )

    stmt = stmt.order_by(desc(ProcessingLog.processed_at)).limit(limit).offset(offset)
    logs = db.execute(stmt).scalars().all()

    return {
        "entries": [_format_audit_entry(log) for log in logs],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.get("/system-events")
def system_events(
    limit: int = Query(30, ge=1, le=100),
    level: str | None = Query(
        None,
        description="Filter by event level: error, warning, success",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Recent system events — processing runs, errors, automated tasks."""
    del current_user

    stmt = select(ProcessingLog)

    if level:
        # Filter by status stored inside results JSONB
        stmt = stmt.where(ProcessingLog.results["status"].as_string() == level)

    stmt = stmt.order_by(desc(ProcessingLog.processed_at)).limit(limit)
    logs = db.execute(stmt).scalars().all()

    return {
        "events": [_format_system_event(log) for log in logs],
        "total": len(logs),
    }


def _format_audit_entry(log: ProcessingLog) -> dict:
    """Format a ProcessingLog row as an audit log entry."""
    results = log.results or {}
    details_data = results.get("details", {})
    admin_email = (
        details_data.get("triggered_by") if isinstance(details_data, dict) else None
    )

    return {
        "id": log.id,
        "timestamp": log.processed_at.isoformat() if log.processed_at else None,
        "admin": admin_email or "system",
        "action": log.process_type,
        "target": results.get("message", ""),
        "details": _summarise_details(details_data),
    }


def _format_system_event(log: ProcessingLog) -> dict:
    """Format a ProcessingLog row as a system event."""
    results = log.results or {}
    return {
        "id": log.id,
        "timestamp": log.processed_at.isoformat() if log.processed_at else None,
        "event": log.process_type,
        "level": results.get("status", "info"),
        "message": results.get("message", ""),
    }


def _summarise_details(details: dict | list | str | None) -> str:
    """Produce a short human-readable summary of event details."""
    if not details:
        return ""
    if isinstance(details, str):
        return details[:120]
    if isinstance(details, list):
        return f"{len(details)} items"
    if isinstance(details, dict):
        parts = []
        for key in ("result", "count", "processed", "status"):
            if key in details:
                parts.append(f"{key}={details[key]}")
        return ", ".join(parts) if parts else str(details)[:120]
    return str(details)[:120]
