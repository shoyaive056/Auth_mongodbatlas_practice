"""Sending email.

- SMTP configured  -> real email through your SMTP server.
- SMTP not configured (development only) -> the email is printed to the
  backend console, so you can click the link without any email account.
  This is the ONLY place a token is ever logged, and only in that dev mode.

Sending never raises: callers run it as a background task, and a mail-server
problem must not break registration or reveal whether an account exists.
"""
import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings
from app.utils.email_templates import password_reset_email, verification_email

logger = logging.getLogger("app.email")

# Development-mode mailbox (also used by the tests to read links). Capped in size.
dev_outbox: list[dict] = []


def _build_message(to_email: str, subject: str, text: str, html: str) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email or 'no-reply@localhost'}>"
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _send_via_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    port = int(settings.smtp_port)
    if port == 465:
        server = smtplib.SMTP_SSL(settings.smtp_host, port, timeout=15)
    else:
        server = smtplib.SMTP(settings.smtp_host, port, timeout=15)
        server.starttls()
    with server:
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def _deliver(to_email: str, subject: str, text: str, html: str, link: str) -> None:
    settings = get_settings()
    try:
        if settings.smtp_configured:
            _send_via_smtp(_build_message(to_email, subject, text, html))
            logger.info("Email '%s' sent to %s", subject, to_email)
        elif settings.is_production:
            logger.error("SMTP is not configured; email '%s' to %s was NOT sent", subject, to_email)
        else:
            dev_outbox.append({"to": to_email, "subject": subject, "link": link})
            del dev_outbox[:-50]
            logger.warning("DEV EMAIL (SMTP not configured) to=%s subject=%s\n  link: %s", to_email, subject, link)
    except Exception:  # noqa: BLE001 - never let email problems crash the request
        logger.exception("Failed to send email '%s' to %s", subject, to_email)


def send_verification_email(to_email: str, first_name: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={quote(token)}"
    subject, text, html = verification_email(first_name, link, settings.email_verification_expire_minutes)
    _deliver(to_email, subject, text, html, link)


def send_password_reset_email(to_email: str, first_name: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={quote(token)}"
    subject, text, html = password_reset_email(first_name, link, settings.password_reset_expire_minutes)
    _deliver(to_email, subject, text, html, link)
