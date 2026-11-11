"""Notifications to the owner: Pushover and/or Telegram (whichever is configured)."""

import os
import requests

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def _pushover(message: str) -> None:
    user, token = os.getenv("PUSHOVER_USER"), os.getenv("PUSHOVER_TOKEN")
    if not (user and token):
        return
    try:
        requests.post(PUSHOVER_URL, data={"user": user, "token": token, "message": message}, timeout=10)
    except requests.RequestException as e:
        print(f"Pushover failed: {e}")


def _telegram(message: str) -> None:
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000]},
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"Telegram failed: {e}")


def push(message: str) -> None:
    print(f"Push: {message}", flush=True)
    _pushover(message)
    _telegram(message)
