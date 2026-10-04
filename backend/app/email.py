"""Transactional email sender (OTP verification codes). Never raises to the caller."""
import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _send(to_email: str, subject: str, body: str) -> bool:
    """Low-level send. Never raises; returns False on any failure."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured — email not sent (dev fallback)")
        return True
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_otp_email(to_email: str, otp: str, name: str) -> bool:
    """Send a 6-digit verification code. Returns True on success.

    If SMTP is not configured, logs the OTP at INFO for local development and
    returns True. Any SMTP failure is logged and returns False — the caller
    must still return a generic success to avoid user enumeration.
    """
    if not settings.smtp_host:
        logger.info("DEV OTP for %s: %s", to_email, otp)
    return _send(
        to_email,
        "Your CreatorGrowth verification code",
        f"Hi {name or 'there'},\n\n"
        f"Your CreatorGrowth verification code is:\n\n    {otp}\n\n"
        f"This code expires in {settings.otp_ttl_minutes} minutes. "
        "If you did not request this, you can safely ignore this email.\n\n"
        "— The CreatorGrowth team",
    )


def send_account_exists_email(to_email: str, name: str) -> bool:
    """Tell an already-registered user to log in instead.

    Used by the enumeration-safe register flow: the API response is identical
    whether the email is new or taken, and the real owner learns via email.
    """
    return _send(
        to_email,
        "You already have a CreatorGrowth account",
        f"Hi {name or 'there'},\n\n"
        "Someone tried to create a new CreatorGrowth account with this email, "
        "but it is already registered. Just log in with your existing password — "
        "no action needed.\n\n"
        "If this wasn't you, you can safely ignore this email.\n\n"
        "— The CreatorGrowth team",
    )
