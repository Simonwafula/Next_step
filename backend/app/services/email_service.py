import logging
import smtplib
from email.mime.text import MIMEText

from ..core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_address: str, subject: str, body: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info("SMTP not configured; skipping email send.")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_address

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_address], msg.as_string())
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


def send_password_reset_email(to_address: str, reset_url: str, expires_minutes: int) -> bool:
    subject = "Reset your password"
    body = (
        "We received a request to reset your password.\\n\\n"
        f"Reset your password using this link (valid for {expires_minutes} minutes):\\n"
        f"{reset_url}\\n\\n"
        "If you did not request this, you can ignore this email."
    )
    return send_email(to_address, subject, body)
