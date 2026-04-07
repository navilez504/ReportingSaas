"""Outbound email: uses SMTP when configured; otherwise logs (dev)."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import Settings

logger = logging.getLogger(__name__)


def send_email(settings: Settings, to_email: str, subject: str, body_text: str) -> bool:
    """Send plain-text email. Returns True if sent (or log-only when SMTP is not fully configured)."""
    body_text = body_text.strip()
    if not to_email or not subject:
        return False
    if not settings.smtp_ready:
        logger.warning(
            "Email not sent (SMTP not configured). Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD "
            "(and usually SMTP_FROM) in the environment or project root .env. Preview to=%s subject=%s",
            to_email,
            subject,
        )
        logger.debug("Email body preview:\n%s", body_text)
        return True

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    mail_from = msg["From"]

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(mail_from, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(mail_from, [to_email], msg.as_string())
        logger.info("Email sent to %s subject=%s", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
