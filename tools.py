"""Tools the twin can call, their JSON schemas, and a safe dispatcher (explicit allow-list
instead of globals())."""

import json

import database as db
from notifier import push

_kb = None  # set by init_tools()


def init_tools(knowledge_base) -> None:
    global _kb
    _kb = knowledge_base
    db.init_db()


# ---------- tool functions ----------

def search_knowledge_base(query: str) -> dict:
    if _kb is None:
        return {"results": [], "note": "Knowledge base not loaded"}
    hits = _kb.search(query)
    return {"results": [{"source": h["source"], "text": h["text"]} for h in hits]}


def lookup_faq(question: str) -> dict:
    hits = db.search_faq(question)
    return {"matches": [{"question": h["question"], "answer": h["answer"]} for h in hits]}


def record_user_details(email: str, name: str = "Name not provided", notes: str = "not provided") -> dict:
    db.add_contact(email, name, notes)
    push(f"New contact: {name} <{email}>\nNotes: {notes}")
    return {"status": "recorded"}


def record_unknown_question(question: str) -> dict:
    faq_id = db.add_unanswered(question)
    push(f"Unanswered question #{faq_id}: {question}\nReply in Telegram: /answer {faq_id} <your answer>")
    return {"status": "recorded", "id": faq_id}


TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "lookup_faq": lookup_faq,
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
}


# ---------- schemas ----------

def _fn(name, description, properties, required):
    """Provider-neutral tool schema; llm.py adapts it for OpenAI-style APIs and Claude."""
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    _fn(
        "search_knowledge_base",
        "Search the knowledge base of documents about the person (projects, experience, skills, "
        "case studies). Use this whenever a question needs specific details not already in the system prompt.",
        {"query": {"type": "string", "description": "A focused search query, e.g. 'Shopify gift card integration'"}},
        ["query"],
    ),
    _fn(
        "lookup_faq",
        "Look up previously answered common questions. Use this BEFORE saying you don't know something.",
        {"question": {"type": "string", "description": "The visitor's question"}},
        ["question"],
    ),
    _fn(
        "record_user_details",
        "Record that a user wants to be in touch and has provided an email address.",
        {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {"type": "string", "description": "Context worth recording, e.g. role they are hiring for"},
        },
        ["email"],
    ),
    _fn(
        "record_unknown_question",
        "Record a question you could not answer after checking the knowledge base and FAQ.",
        {"question": {"type": "string", "description": "The question that couldn't be answered"}},
        ["question"],
    ),
]


def execute_tool(name: str, args: dict) -> str:
    """Run one tool by name (explicit allow-list) and return its JSON result as a string."""
    try:
        fn = TOOL_FUNCTIONS.get(name)
        result = fn(**args) if fn else {"error": f"Unknown tool {name}"}
    except Exception as e:  # never crash the chat because of a tool
        result = {"error": str(e)}
    print(f"Tool called: {name} -> {str(result)[:200]}", flush=True)
    return json.dumps(result)
