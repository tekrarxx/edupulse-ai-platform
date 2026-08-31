"""Outbound email (§54 notifications boundary). SMTP-only and provider-
agnostic on purpose: local development points it at Mailpit (docker-compose,
§9-11 local-first — no external API key), and nothing here is Mailpit-
specific, so pointing `SMTP_HOST`/`SMTP_PORT` at a real provider's SMTP
endpoint later is a configuration change, not a code change (§119).

Deliberately narrow: password-reset is the only email the product sends
today. A second kind of email should still come through a function here,
not a second ad-hoc smtplib call elsewhere.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """The SMTP server rejected or could not be reached for this send."""


def send_password_reset_email(*, to_email: str, reset_link: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = "EduPulse AI - Şifre sıfırlama"
    message["From"] = settings.smtp_from_address
    message["To"] = to_email
    message.set_content(
        "Şifreni sıfırlamak için bu bağlantıyı kullan:\n\n"
        f"{reset_link}\n\n"
        "Bu bağlantı 1 saat içinde geçerliliğini yitirir. Bu isteği sen yapmadıysan "
        "bu e-postayı yok sayabilirsin — şifren değişmeyecek."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        # §43-style honest failure: a real, sometimes-unavailable dependency,
        # not silently retried or hidden. The caller (auth_service) still
        # returns its generic anti-enumeration response either way (§90) —
        # this is logged so the failure is operationally visible instead.
        logger.error("Password reset email delivery failed: %s", exc.__class__.__name__)
        raise EmailDeliveryError(str(exc)) from exc
