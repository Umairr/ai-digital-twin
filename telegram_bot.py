"""Telegram owner console (optional). Runs a background long-polling thread.

Only messages from TELEGRAM_CHAT_ID (you) are accepted. Commands:
  /pending                 list unanswered questions
  /answer <id> <text>      answer a question -> it becomes an FAQ the twin can use
  /faq <question> | <ans>  add a new FAQ directly
  /contacts                last 5 captured contacts
  /stats                   counts

Setup: talk to @BotFather -> /newbot -> copy token into TELEGRAM_BOT_TOKEN.
Then message your bot once and open https://api.telegram.org/bot<TOKEN>/getUpdates
to find your chat id -> TELEGRAM_CHAT_ID.
"""

import os
import threading
import time

import requests

import database as db

HELP = (
    "/pending - unanswered questions\n"
    "/answer <id> <text> - answer one\n"
    "/faq <question> | <answer> - add FAQ\n"
    "/contacts - recent leads\n"
    "/stats - counts"
)


def _api(method: str, **params):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=40)
    return r.json()


def _reply(chat_id, text: str) -> None:
    _api("sendMessage", chat_id=chat_id, text=text[:4000])


def handle_command(text: str) -> str:
    text = text.strip()
    if text.startswith("/pending"):
        rows = db.list_unanswered()
        if not rows:
            return "No pending questions 🎉"
        return "\n".join(f"#{r['id']} (x{r['times_asked']}): {r['question']}" for r in rows[:20])

    if text.startswith("/answer"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            return "Usage: /answer <id> <answer text>"
        ok = db.answer_question(int(parts[1]), parts[2])
        return f"Saved answer for #{parts[1]} ✅" if ok else f"No question with id {parts[1]}"

    if text.startswith("/faq"):
        body = text[len("/faq"):].strip()
        if "|" not in body:
            return "Usage: /faq <question> | <answer>"
        q, a = (s.strip() for s in body.split("|", 1))
        return f"FAQ #{db.add_faq(q, a)} added ✅"

    if text.startswith("/contacts"):
        rows = db.list_contacts()[:5]
        if not rows:
            return "No contacts yet"
        return "\n\n".join(f"{r['name']} <{r['email']}>\n{r['notes']}\n{r['created_at']}" for r in rows)

    if text.startswith("/stats"):
        return "\n".join(f"{k}: {v}" for k, v in db.stats().items())

    return HELP


def _poll_forever() -> None:
    owner = str(os.getenv("TELEGRAM_CHAT_ID"))
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            data = _api("getUpdates", **params)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or {}
                chat_id = str(msg.get("chat", {}).get("id"))
                if chat_id != owner or "text" not in msg:
                    continue  # ignore everyone except the owner
                _reply(chat_id, handle_command(msg["text"]))
        except Exception as e:
            print(f"Telegram polling error: {e}")
            time.sleep(5)


def start_telegram_bot() -> bool:
    if not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        print("Telegram not configured - skipping bot")
        return False
    db.init_db()
    threading.Thread(target=_poll_forever, daemon=True).start()
    print("Telegram owner bot started")
    return True
