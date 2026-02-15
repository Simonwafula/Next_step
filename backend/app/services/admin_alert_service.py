from datetime import datetime, timedelta
import asyncio
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import User, UserNotification
from ..services.email_service import send_email
from ..webhooks.whatsapp import send_whatsapp_message


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


class AdminAlertService:
    def __init__(self, cooldown_hours: int = 6) -> None:
        self.cooldown_hours = cooldown_hours

    def _admin_emails(self) -> list[str]:
        return [
            email.strip().lower()
            for email in settings.ADMIN_EMAILS.split(",")
            if email.strip()
        ]

    def _build_subject(
        self,
        avg_conversion_7d: float,
        threshold: float,
    ) -> str:
        return (
            "⚠️ NextStep conversion alert: "
            f"{avg_conversion_7d:.1f}% (target {threshold:.1f}%)"
        )

    def _build_message(
        self,
        avg_conversion_7d: float,
        threshold: float,
        conversion_rate_30d: float,
    ) -> str:
        return (
            "Conversion performance is below target.\n\n"
            f"- 7-day average conversion: {avg_conversion_7d:.1f}%\n"
            f"- Alert threshold: {threshold:.1f}%\n"
            f"- 30-day conversion: {conversion_rate_30d:.1f}%\n\n"
            "Action: review pricing flow, payment completion funnel, and"
            " recent traffic quality in the admin dashboard."
        )

    def dispatch_conversion_dropoff_alert(
        self,
        db: Session,
        *,
        avg_conversion_7d: float,
        threshold: float,
        conversion_rate_30d: float,
    ) -> dict[str, Any]:
        admin_emails = self._admin_emails()
        if not admin_emails:
            return {
                "status": "skipped",
                "reason": "no_admin_emails_configured",
                "notifications_created": 0,
            }

        cutoff = datetime.utcnow() - timedelta(hours=self.cooldown_hours)
        admin_users = (
            db.execute(
                select(User).where(
                    func.lower(User.email).in_(admin_emails),
                    User.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )

        if not admin_users:
            return {
                "status": "skipped",
                "reason": "no_admin_users_found",
                "notifications_created": 0,
            }

        subject = self._build_subject(avg_conversion_7d, threshold)
        message = self._build_message(
            avg_conversion_7d,
            threshold,
            conversion_rate_30d,
        )

        notifications_created = 0
        emailed = 0
        whatsapp_sent = 0

        for admin in admin_users:
            already_notified_recently = (
                db.execute(
                    select(func.count(UserNotification.id)).where(
                        UserNotification.user_id == admin.id,
                        UserNotification.type
                        == "admin_conversion_dropoff_alert",
                        UserNotification.created_at >= cutoff,
                    )
                ).scalar()
                or 0
            )
            if already_notified_recently:
                continue

            delivered_via = ["in_app"]
            delivery_status = {"in_app": "sent"}

            email_ok = False
            try:
                email_ok = send_email(admin.email, subject, message)
            except Exception:
                email_ok = False
            if email_ok:
                delivered_via.append("email")
                delivery_status["email"] = "sent"
                emailed += 1
            else:
                delivery_status["email"] = "failed"

            recipient_number = admin.whatsapp_number or admin.phone
            if recipient_number:
                try:
                    whatsapp_ok = bool(
                        _run_async(
                            send_whatsapp_message(recipient_number, message)
                        )
                    )
                except Exception:
                    whatsapp_ok = False
                if whatsapp_ok:
                    delivered_via.append("whatsapp")
                    delivery_status["whatsapp"] = "sent"
                    whatsapp_sent += 1
                else:
                    delivery_status["whatsapp"] = "failed"
            else:
                delivery_status["whatsapp"] = "skipped_no_number"

            db.add(
                UserNotification(
                    user_id=admin.id,
                    type="admin_conversion_dropoff_alert",
                    title=subject,
                    message=message,
                    data={
                        "avg_conversion_7d": avg_conversion_7d,
                        "threshold": threshold,
                        "conversion_rate_30d": conversion_rate_30d,
                    },
                    delivered_via=delivered_via,
                    delivery_status=delivery_status,
                )
            )
            notifications_created += 1

        if notifications_created:
            db.commit()

        return {
            "status": "processed",
            "notifications_created": notifications_created,
            "emailed": emailed,
            "whatsapp_sent": whatsapp_sent,
        }


admin_alert_service = AdminAlertService()
