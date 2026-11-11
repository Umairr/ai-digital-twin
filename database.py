"""SQLite store for FAQ (common Q&A) and captured contacts.

Flow:
- The twin looks up answered FAQs before saying "I don't know".
- Unknown questions are saved with answer = NULL.
- You (the owner) answer them later (Telegram /answer, or database.answer_question()),
  and from then on the twin can answer that question itself.
"""

import os
import re
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("TWIN_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "twin.db"))

STOPWORDS = {
    "the", "and", "for", "are", "you", "your", "what", "how", "does", "did", "can", "with",
    "have", "has", "who", "why", "when", "where", "which", "about", "this", "that", "his",
    "him", "agha", "any", "was", "were", "will", "would", "could", "tell",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT,
                times_asked INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                name TEXT,
                notes TEXT,
                created_at TEXT
            );
            """
        )


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9+#.]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def search_faq(query: str, limit: int = 3) -> list[dict]:
    """Keyword-overlap search over ANSWERED FAQs."""
    keys = set(_keywords(query))
    if not keys:
        return []
    with _conn() as c:
        rows = c.execute("SELECT id, question, answer FROM faq WHERE answer IS NOT NULL").fetchall()
    scored = []
    for r in rows:
        overlap = len(keys & set(_keywords(r["question"])))
        if overlap:
            scored.append((overlap / len(keys), dict(r)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for score, r in scored[:limit] if score >= 0.3]


def add_unanswered(question: str) -> int:
    """Save an unknown question (or bump its counter if already pending). Returns the row id."""
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM faq WHERE answer IS NULL AND lower(question) = lower(?)", (question,)
        ).fetchone()
        if row:
            c.execute("UPDATE faq SET times_asked = times_asked + 1, updated_at = ? WHERE id = ?", (_now(), row["id"]))
            return row["id"]
        cur = c.execute(
            "INSERT INTO faq (question, answer, created_at, updated_at) VALUES (?, NULL, ?, ?)",
            (question, _now(), _now()),
        )
        return cur.lastrowid


def answer_question(faq_id: int, answer: str) -> bool:
    with _conn() as c:
        cur = c.execute("UPDATE faq SET answer = ?, updated_at = ? WHERE id = ?", (answer, _now(), faq_id))
        return cur.rowcount > 0


def add_faq(question: str, answer: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO faq (question, answer, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (question, answer, _now(), _now()),
        )
        return cur.lastrowid


def list_unanswered() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, question, times_asked FROM faq WHERE answer IS NULL ORDER BY times_asked DESC, id"
        ).fetchall()
    return [dict(r) for r in rows]


def list_faq() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM faq ORDER BY id").fetchall()]


def add_contact(email: str, name: str | None = None, notes: str | None = None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO contacts (email, name, notes, created_at) VALUES (?, ?, ?, ?)",
            (email, name, notes, _now()),
        )
        return cur.lastrowid


def list_contacts() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()]


def stats() -> dict:
    with _conn() as c:
        return {
            "answered_faq": c.execute("SELECT COUNT(*) FROM faq WHERE answer IS NOT NULL").fetchone()[0],
            "pending_questions": c.execute("SELECT COUNT(*) FROM faq WHERE answer IS NULL").fetchone()[0],
            "contacts": c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        }
