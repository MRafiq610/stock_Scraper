from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests


def enabled() -> bool:
    return (
        bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
        or bool(os.getenv("NOTIFY_WEBHOOK_URL"))
        or bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and os.getenv("EMAIL_TO"))
    )


def send_notification(title: str, message: str, strict: bool = False) -> bool:
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        return send_telegram(title, message, strict=strict)

    if os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and os.getenv("EMAIL_TO"):
        return send_email(title, message, strict=strict)

    webhook_url = os.getenv("NOTIFY_WEBHOOK_URL")
    if webhook_url:
        return send_webhook(webhook_url, title, message, strict=strict)

    warning = "notification skipped: no notification secrets configured"
    if strict:
        raise RuntimeError(warning)
    print(warning)
    return False


def send_telegram(title: str, message: str, strict: bool = False) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{title}\n\n{message}",
        "disable_web_page_preview": True,
    }
    return post(url, strict=strict, json=payload)


def send_webhook(webhook_url: str, title: str, message: str, strict: bool = False) -> bool:
    payload = {"text": f"{title}\n\n{message}", "content": f"{title}\n\n{message}"}
    return post(webhook_url, strict=strict, json=payload)


def send_email(title: str, message: str, strict: bool = False) -> bool:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    email_from = os.getenv("EMAIL_FROM", smtp_user)
    email_to = os.environ["EMAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(message)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
        print(f"email notification sent to {email_to}")
        return True
    except Exception as e:
        error = f"email notification failed: {e}"
        if strict:
            raise RuntimeError(error) from e
        print(error)
        return False


def post(url: str, strict: bool = False, **kwargs: Any) -> bool:
    try:
        resp = requests.post(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return True
    except Exception as e:
        error = f"notification failed: {e}"
        if strict:
            raise RuntimeError(error) from e
        print(error)
        return False
