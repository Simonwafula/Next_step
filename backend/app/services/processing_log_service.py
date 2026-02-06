from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..db.models import ProcessingLog


def _build_payload(
    status: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": status}
    if message:
        payload["message"] = message
    if details:
        payload["details"] = details
    payload["recorded_at"] = datetime.utcnow().isoformat()
    return payload


def log_processing_event(
    db: Session,
    process_type: str,
    status: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ProcessingLog:
    log = ProcessingLog(
        process_type=process_type,
        results=_build_payload(status, message, details),
        processed_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_processing_event(
    db: Session,
    log_id: int,
    status: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[ProcessingLog]:
    log = db.get(ProcessingLog, log_id)
    if not log:
        return None
    log.results = _build_payload(status, message, details)
    log.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


async def log_processing_event_async(
    db: AsyncSession,
    process_type: str,
    status: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ProcessingLog:
    log = ProcessingLog(
        process_type=process_type,
        results=_build_payload(status, message, details),
        processed_at=datetime.utcnow(),
    )
    db.add(log)
    await _maybe_await(db.commit())
    await _maybe_await(db.refresh(log))
    return log


async def update_processing_event_async(
    db: AsyncSession,
    log_id: int,
    status: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[ProcessingLog]:
    log = await db.get(ProcessingLog, log_id)
    if not log:
        return None
    log.results = _build_payload(status, message, details)
    log.processed_at = datetime.utcnow()
    await _maybe_await(db.commit())
    await _maybe_await(db.refresh(log))
    return log


async def _maybe_await(result: Any) -> Any:
    if hasattr(result, "__await__"):
        return await result
    return result
