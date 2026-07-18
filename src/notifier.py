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


def send_notification(title: str, message: str) -> None:
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        send_telegram(title, message)
        return

    if os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and os.getenv("EMAIL_TO"):
        send_email(title, message)
        return

    webhook_url = os.getenv("NOTIFY_WEBHOOK_URL")
    if webhook_url:
        send_webhook(webhook_url, title, message)


def send_telegram(title: str, message: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{title}\n\n{message}",
        "disable_web_page_preview": True,
    }
    post(url, json=payload)


def send_webhook(webhook_url: str, title: str, message: str) -> None:
    payload = {"text": f"{title}\n\n{message}", "content": f"{title}\n\n{message}"}
    post(webhook_url, json=payload)


def send_email(title: str, message: str) -> None:
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
    except Exception as e:
        print(f"email notification failed: {e}")


def post(url: str, **kwargs: Any) -> None:
    try:
        resp = requests.post(url, timeout=15, **kwargs)
        resp.raise_for_status()
    except Exception as e:
        print(f"notification failed: {e}")
