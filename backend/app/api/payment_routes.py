import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.database import get_db
from ..services.subscription_service import subscription_service

router = APIRouter()


def _verify_webhook_signature(
    secret: str | None,
    payload: bytes,
    provided_signature: str | None,
) -> None:
    if not provided_signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    normalized_signature = provided_signature.strip()
    if "=" in normalized_signature:
        normalized_signature = normalized_signature.split("=", 1)[1]

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(normalized_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _parse_json_payload(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc


def _parse_user_id(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id in payment reference",
        ) from exc


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    _verify_webhook_signature(
        settings.STRIPE_WEBHOOK_SECRET,
        payload,
        request.headers.get("Stripe-Signature"),
    )

    event = _parse_json_payload(payload)
    if event.get("type") != "checkout.session.completed":
        return {"status": "ignored"}

    metadata = ((event.get("data") or {}).get("object") or {}).get("metadata") or {}
    user_id = _parse_user_id(metadata.get("user_id"))
    plan_code = metadata.get("plan_code") or "professional_monthly"

    result = subscription_service.activate_plan_by_user_id(
        db,
        user_id,
        plan_code,
    )
    return {"status": "processed", **result}


@router.post("/webhooks/mpesa")
async def mpesa_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    _verify_webhook_signature(
        settings.MPESA_WEBHOOK_SECRET,
        payload,
        request.headers.get("X-Mpesa-Signature"),
    )

    event = _parse_json_payload(payload)
    if str(event.get("status", "")).upper() != "SUCCESS":
        return {"status": "ignored"}

    reference = event.get("reference") or {}
    user_id = _parse_user_id(reference.get("user_id"))
    plan_code = reference.get("plan_code") or "professional_monthly"

    result = subscription_service.activate_plan_by_user_id(
        db,
        user_id,
        plan_code,
    )
    return {"status": "processed", **result}
