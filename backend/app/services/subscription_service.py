from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import User, UserNotification


class SubscriptionService:
    def __init__(self) -> None:
        self._plans = {
            "professional_monthly": {
                "code": "professional_monthly",
                "tier": "professional",
                "name": "Professional Monthly",
                "currency": "KES",
                "amount": 300,
                "duration_days": 30,
                "features": [
                    "Skills gap scan",
                    "Career pathways",
                    "Advanced salary intelligence",
                ],
            },
            "enterprise_monthly": {
                "code": "enterprise_monthly",
                "tier": "enterprise",
                "name": "Enterprise Monthly",
                "currency": "KES",
                "amount": 5000,
                "duration_days": 30,
                "features": [
                    "Everything in Professional",
                    "Admin intelligence dashboard",
                    "Priority support",
                ],
            },
        }
        self._providers = {"stripe", "mpesa"}

    def list_plans(self) -> list[dict]:
        return list(self._plans.values())

    def create_checkout(
        self,
        user: User,
        plan_code: str,
        provider: str,
    ) -> dict:
        plan = self._plans.get(plan_code)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported subscription plan",
            )

        if provider not in self._providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported payment provider",
            )

        checkout_id = uuid4().hex

        if provider == "stripe":
            checkout_url = f"https://checkout.stripe.com/pay/{checkout_id}"
        else:
            checkout_url = (
                "https://payments.nextstep.co.ke/mpesa"
                f"?checkout_id={checkout_id}&plan={plan_code}"
            )

        return {
            "checkout_id": checkout_id,
            "status": "pending",
            "provider": provider,
            "plan_code": plan_code,
            "amount": plan["amount"],
            "currency": plan["currency"],
            "checkout_url": checkout_url,
            "user_id": user.id,
        }

    def activate_plan(self, db: Session, user: User, plan_code: str) -> dict:
        return self.activate_plan_by_user_id(db, user.id, plan_code)

    def activate_plan_by_user_id(
        self,
        db: Session,
        user_id: int,
        plan_code: str,
    ) -> dict:
        plan = self._plans.get(plan_code)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported subscription plan",
            )

        managed_user = db.get(User, user_id)
        if managed_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        now = datetime.utcnow()
        current_expiry = managed_user.subscription_expires or now
        effective_start = current_expiry if current_expiry > now else now
        new_expiry = effective_start + timedelta(days=plan["duration_days"])

        managed_user.subscription_tier = plan["tier"]
        managed_user.subscription_expires = new_expiry

        db.add(
            UserNotification(
                user_id=managed_user.id,
                type="subscription_upgrade",
                title="Subscription upgraded",
                message=(
                    f"Your {plan['name']} plan is now active until "
                    f"{new_expiry.date().isoformat()}."
                ),
                data={
                    "plan_code": plan_code,
                    "subscription_tier": managed_user.subscription_tier,
                    "source": "payment",
                },
                delivered_via=["in_app"],
                delivery_status={"in_app": "delivered"},
            )
        )

        db.commit()
        db.refresh(managed_user)

        return {
            "message": "Subscription activated successfully",
            "plan_code": plan_code,
            "subscription_tier": managed_user.subscription_tier,
            "subscription_expires": (managed_user.subscription_expires.isoformat()),
        }


subscription_service = SubscriptionService()
