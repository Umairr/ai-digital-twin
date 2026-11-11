"""AI Digital Twin - Gradio app.

Agentic patterns used:
- Tool use: RAG search, SQLite FAQ lookup, lead capture, unknown-question capture
- Agentic RAG: the model decides when/what to search
- Evaluator-optimizer: every reply is checked by a second LLM and regenerated if it fails
- Human in the loop: you answer unknown questions from Telegram; the twin learns them
"""

import os

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

import context  # noqa: E402
from evaluator import evaluate  # noqa: E402
from knowledge import KnowledgeBase  # noqa: E402
from telegram_bot import start_telegram_bot  # noqa: E402
from tools import TOOLS, handle_tool_calls, init_tools  # noqa: E402

MODEL = os.getenv("TWIN_MODEL", "gpt-5.4-mini")
MAX_TOOL_ROUNDS = 6
MAX_RETRIES = 2

openai = OpenAI()

kb = KnowledgeBase(
    openai,
    sources=[context.KNOWLEDGE_DIR, context.SUMMARY_PATH, context.LINKEDIN_PATH],
    cache_path=os.path.join(context.BASE, "embeddings_cache.json"),
)
init_tools(kb)
start_telegram_bot()


def _clean_history(history: list) -> list[dict]:
    """Gradio may send extra keys or list-style content; keep only role + text."""
    cleaned = []
    for m in history or []:
        content = m.get("content")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if isinstance(content, str) and m.get("role") in ("user", "assistant"):
            cleaned.append({"role": m["role"], "content": content})
    return cleaned


def _run_agent(messages: list) -> tuple[str, str]:
    """Run the tool loop. Returns (reply, retrieved_context) so the evaluator sees what the twin saw."""
    retrieved = []
    for _ in range(MAX_TOOL_ROUNDS):
        response = openai.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        choice = response.choices[0]
        if choice.finish_reason != "tool_calls":
            return choice.message.content or "", "\n\n".join(retrieved)
        results = handle_tool_calls(choice.message.tool_calls)
        messages.append(choice.message)
        messages.extend(results)
        retrieved.extend(r["content"] for r in results)
    return "Sorry, I got a bit tangled up there - could you rephrase that?", "\n\n".join(retrieved)


def chat(message: str, history: list) -> str:
    history = _clean_history(history)
    messages = [{"role": "system", "content": context.system_prompt}] + history + [
        {"role": "user", "content": message}
    ]
    reply, retrieved = _run_agent(list(messages))

    for attempt in range(MAX_RETRIES):
        evaluation = evaluate(
            openai, context.NAME, context.base_context + "\n\n## Retrieved this turn\n" + retrieved,
            reply, message, history,
        )
        if evaluation.is_acceptable:
            break
        print(f"Evaluator rejected (attempt {attempt + 1}): {evaluation.feedback}", flush=True)
        retry_messages = messages + [
            {"role": "assistant", "content": reply},
            {
                "role": "system",
                "content": "Your previous reply was rejected by quality control.\n"
                f"Feedback: {evaluation.feedback}\nWrite an improved reply to the visitor's last message.",
            },
        ]
        reply, more = _run_agent(retry_messages)
        retrieved += "\n\n" + more
    return reply


from ui import CSS, JS, THEME, build_ui  # noqa: E402

demo = build_ui(chat)

if __name__ == "__main__":
    demo.launch(
        css=CSS,
        js=JS,
        theme=THEME,
        server_name="0.0.0.0",
        server_port=int(os.environ["PORT"]) if os.environ.get("PORT") else None,  # None = Gradio picks a free port
    )
