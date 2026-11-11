"""AI Digital Twin - Gradio app.

Agentic patterns used:
- Tool use: RAG search, SQLite FAQ lookup, lead capture, unknown-question capture
- Agentic RAG: the model decides when/what to search
- Evaluator-optimizer: every reply is checked by a second LLM and regenerated if it fails
- Human in the loop: you answer unknown questions from Telegram; the twin learns them
"""

import os

from dotenv import load_dotenv

load_dotenv(override=True)

import context  # noqa: E402
from evaluator import evaluate  # noqa: E402
from knowledge import KnowledgeBase  # noqa: E402
from llm import LLM, Embedder  # noqa: E402
from telegram_bot import start_telegram_bot  # noqa: E402
from tools import TOOLS, execute_tool, init_tools  # noqa: E402

MAX_TOOL_ROUNDS = 6
MAX_RETRIES = 2

# LLM_PROVIDER / LLM_MODEL pick the chat model (OpenAI, Claude, OpenRouter, Grok, Gemini, Ollama).
# TWIN_MODEL is still honoured for backwards compatibility.
llm = LLM(model=os.getenv("LLM_MODEL") or os.getenv("TWIN_MODEL"))
evaluator_llm = LLM(
    provider=os.getenv("EVALUATOR_PROVIDER") or llm.provider.name,
    model=os.getenv("EVALUATOR_MODEL") or (llm.model if not os.getenv("EVALUATOR_PROVIDER") else None),
)
print(f"Chat model: {llm}  |  Evaluator: {evaluator_llm}")

kb = KnowledgeBase(
    Embedder(llm.provider.name),
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


def _run_agent(history: list[dict], message: str, extra: list[dict] | None = None) -> tuple[str, str]:
    """Run the tool loop. Returns (reply, retrieved_context) so the evaluator sees what the twin saw."""
    reply, outputs = llm.run_tools(
        context.system_prompt, history, message, TOOLS, execute_tool,
        max_rounds=MAX_TOOL_ROUNDS, extra_messages=extra,
    )
    return reply, "\n\n".join(outputs)


def chat(message: str, history: list) -> str:
    history = _clean_history(history)
    reply, retrieved = _run_agent(history, message)

    for attempt in range(MAX_RETRIES):
        evaluation = evaluate(
            evaluator_llm, context.NAME, context.base_context + "\n\n## Retrieved this turn\n" + retrieved,
            reply, message, history,
        )
        if evaluation.is_acceptable:
            break
        print(f"Evaluator rejected (attempt {attempt + 1}): {evaluation.feedback}", flush=True)
        retry = [
            {"role": "assistant", "content": reply},
            {
                "role": "system",
                "content": "Your previous reply was rejected by quality control.\n"
                f"Feedback: {evaluation.feedback}\nWrite an improved reply to the visitor's last message.",
            },
        ]
        reply, more = _run_agent(history, message, retry)
        retrieved += "\n\n" + more
    return reply


from ui import CSS, HEAD, JS, THEME, build_ui  # noqa: E402

demo = build_ui(chat)

if __name__ == "__main__":
    demo.launch(
        css=CSS,
        js=JS,
        head=HEAD,
        theme=THEME,
        server_name="0.0.0.0",
        server_port=int(os.environ["PORT"]) if os.environ.get("PORT") else None,  # None = Gradio picks a free port
    )
