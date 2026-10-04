"""Transactional email sender (OTP verification codes). Never raises to the caller."""
import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_otp_email(to_email: str, otp: str, name: str) -> bool:
    """Send a 6-digit verification code. Returns True on success.

    If SMTP is not configured, logs the OTP at INFO for local development and
    returns True. Any SMTP failure is logged and returns False — the caller
    must still return a generic success to avoid user enumeration.
    """
    if not settings.smtp_host:
        logger.warning("SMTP not configured — OTP email not sent (dev fallback)")
        logger.info("DEV OTP for %s: %s", to_email, otp)
        return True

    msg = EmailMessage()
    msg["Subject"] = "Your CreatorGrowth verification code"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.set_content(
        f"Hi {name or 'there'},\n\n"
        f"Your CreatorGrowth verification code is:\n\n    {otp}\n\n"
        f"This code expires in {settings.otp_ttl_minutes} minutes. "
        "If you did not request this, you can safely ignore this email.\n\n"
        "— The CreatorGrowth team"
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send OTP email to %s", to_email)
        return False
