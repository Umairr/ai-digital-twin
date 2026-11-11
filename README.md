# AI Digital Twin

**An agentic AI assistant that represents you on your website, answering recruiters, hiring managers and clients in your voice, around the clock.**

AI Digital Twin is a production-ready chat agent grounded in your own career data: résumé, LinkedIn profile and knowledge notes. It retrieves facts on demand, checks every answer with a second model before the visitor sees it, captures leads, and learns from you. When it gets a question it can't answer, it notifies you, and your reply on Telegram becomes knowledge it can use from then on.

![Python](https://img.shields.io/badge/python-3.12-blue)
![LLM](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Claude%20%7C%20OpenRouter%20%7C%20Grok%20%7C%20Gemini%20%7C%20Ollama-412991)
![Gradio](https://img.shields.io/badge/Gradio-6-ff7c00)
![Deploy](https://img.shields.io/badge/deploy-Render-46e3b7)
![License](https://img.shields.io/badge/license-MIT-green)

![AI Digital Twin answering a recruiter's question](docs/screenshots/chat-light.png)

---

## Screenshots

| Welcome screen | On mobile |
|---|---|
| ![Welcome screen with profile sidebar and suggested questions](docs/screenshots/home.png) | <img src="docs/screenshots/mobile.png" alt="Mobile layout" width="280"> |

The layout is a profile sidebar (name, title, stats, core stack, contact button) next to a chat panel with suggested questions. On phones the chat moves to the top and the profile becomes compact below it. The interface always renders in its light design, even for visitors whose device is set to dark mode.

---

## Features

- **Bring your own LLM.** Run on OpenAI, Claude, OpenRouter (hundreds of models), Grok, Gemini or a local Ollama model by changing one setting.
- **Agentic RAG.** The model decides when and what to search. A lightweight vector search over Markdown, text and PDF sources (embeddings with NumPy cosine similarity) means no vector database to run. Without an embeddings provider it falls back to BM25-style keyword search.
- **Self-evaluating replies.** Every answer goes through an evaluator–optimizer loop. A second LLM rejects hallucinated, off-brand or unhelpful replies, and the twin regenerates them using that feedback.
- **Lead capture.** When a visitor shares contact details, the twin stores them and notifies you instantly.
- **Human-in-the-loop learning.** Unanswered questions are logged and pushed to you. Answer one from Telegram and it becomes an FAQ the twin uses in future conversations.
- **Telegram owner console.** Review pending questions, answer them, add FAQs, see recent contacts and usage stats from your phone.
- **Real-time notifications** through Pushover and/or Telegram.
- **Polished, responsive UI.** A profile sidebar, a chat panel, suggested questions, and light and dark themes.
- **One-click deployment** to Render, with a ready-made `render.yaml`.

---

## Architecture

```mermaid
flowchart LR
    V[Visitor] --> UI[Gradio chat UI]
    UI --> A[Twin agent<br/>tool loop]
    A -->|search_knowledge_base| KB[(RAG index<br/>résumé · LinkedIn · notes)]
    A -->|lookup_faq| DB[(SQLite<br/>FAQs · contacts · questions)]
    A -->|record_user_details| DB
    A -->|record_unknown_question| DB
    A --> E{Evaluator LLM}
    E -->|rejected + feedback| A
    E -->|approved| UI
    DB --> N[Pushover / Telegram<br/>notifications]
    O[Owner on Telegram] -->|/answer · /faq| DB
```

### Agent tools

| Tool | Purpose |
|---|---|
| `search_knowledge_base` | Semantic search over your résumé, LinkedIn profile and knowledge notes |
| `lookup_faq` | Finds answers you have already given to similar questions |
| `record_user_details` | Saves a visitor's contact details and notifies you |
| `record_unknown_question` | Logs a question the twin couldn't answer so you can teach it |

### Telegram commands

| Command | Action |
|---|---|
| `/pending` | List unanswered questions |
| `/answer <id> <text>` | Answer a question; it becomes an FAQ |
| `/faq <question> \| <answer>` | Add an FAQ directly |
| `/contacts` | Show the five most recent leads |
| `/stats` | Usage counts |

Only messages from your own `TELEGRAM_CHAT_ID` are accepted.

---

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (or pip)
- An API key for any supported LLM provider (or a local Ollama install)
- Optional: a [Pushover](https://pushover.net) account and/or a Telegram bot

### Installation

```bash
git clone https://github.com/<your-username>/ai-digital-twin.git
cd ai-digital-twin
cp .env.example .env    # add your keys
uv sync
uv run app.py
```

With pip:

```bash
pip install -r requirements.txt
python app.py
```

### Make it yours

| File | What to change |
|---|---|
| `linkedin.pdf` | Export your LinkedIn profile as a PDF |
| `summary.txt` | A short professional summary in your own words |
| `knowledge/*.md` | Extra detail the twin can search: projects, skills, experience |
| `ui.py` → `PROFILE` | Name, title, location, bio, stats, skills and links shown in the sidebar |
| `.env` → `TWIN_NAME` | The name the twin speaks for |

The embeddings cache is rebuilt automatically whenever your source files change.

### Setting up the Telegram console (optional)

1. Message [@BotFather](https://t.me/BotFather), run `/newbot`, and copy the token into `TELEGRAM_BOT_TOKEN`.
2. Send your new bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat ID.
3. Put that ID into `TELEGRAM_CHAT_ID`.

---

## Choose your LLM provider

Set `LLM_PROVIDER` in `.env` and add that provider's key. Nothing else changes.

| Provider | `LLM_PROVIDER` | Key | Default model | Embeddings for RAG |
|---|---|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-5.4-mini` | ✅ built in |
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | `claude-opus-5-5` | via OpenAI/OpenRouter key, else keyword search |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-5.4-mini` | ✅ built in |
| xAI Grok | `grok` | `XAI_API_KEY` | `grok-4.7` | via OpenAI/OpenRouter key, else keyword search |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | `gemini-2.5-flash` | ✅ built in |
| Ollama (local) | `ollama` | none | `llama3.2` | ✅ `nomic-embed-text` |

**Examples**

```bash
# Claude, directly through Anthropic's official SDK
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-5-5        # optional: faster, lower-cost Claude

# Any model through one OpenRouter key: Claude, GPT, Grok, Llama, Mistral...
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-sonnet-5.5

# Grok
LLM_PROVIDER=grok
XAI_API_KEY=xai-...
```

Under the hood, `llm.py` calls Claude with the official `anthropic` SDK and every other provider through its OpenAI-compatible API. You can also pair models, for example a cheaper model as the quality-control evaluator via `EVALUATOR_PROVIDER` / `EVALUATOR_MODEL`.

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | | `openai` (default), `anthropic`, `openrouter`, `grok`, `gemini`, `ollama` |
| `LLM_MODEL` | | Override the provider's default model |
| Provider key | ✅ | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY` or `GEMINI_API_KEY` |
| `EVALUATOR_PROVIDER`, `EVALUATOR_MODEL` | | Use a different model for quality control |
| `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL` | | Override the embeddings used for RAG |
| `TWIN_NAME` | | Name the twin represents |
| `PUSHOVER_USER`, `PUSHOVER_TOKEN` | | Push notifications |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | Telegram notifications and owner console |
| `TWIN_DB_PATH` | | Custom location for the SQLite database |
| `PORT` | | Server port (set automatically on Render) |

---

## Deployment

### Render

The repository includes a `render.yaml` blueprint:

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository.
3. Fill in the secret environment variables when prompted.

On Render's free plan the filesystem is ephemeral, so the SQLite database resets on redeploy. Point `TWIN_DB_PATH` at a persistent disk to keep FAQs and leads.

---

## Project structure

```
├── app.py            # entry point: agent loop + evaluator-optimizer
├── llm.py            # provider layer: OpenAI, Claude, OpenRouter, Grok, Gemini, Ollama
├── context.py        # loads profile sources and builds the system prompt
├── knowledge.py      # chunking, embeddings (or keyword fallback), cached search
├── tools.py          # tool functions, JSON schemas, safe dispatcher
├── evaluator.py      # quality-control LLM with structured output
├── database.py       # SQLite: FAQs, unknown questions, contacts
├── notifier.py       # Pushover + Telegram notifications
├── telegram_bot.py   # owner console (long-polling, owner-only)
├── ui.py             # profile sidebar + chat layout
├── styles.py         # theme, CSS and JS
├── knowledge/        # Markdown knowledge notes
├── summary.txt       # professional summary
├── linkedin.pdf      # LinkedIn profile export
├── docs/screenshots/ # images used in this README
└── render.yaml       # Render deployment blueprint
```

---

## Tech stack

**OpenAI SDK** and **Anthropic SDK** (chat, tool use, structured outputs, embeddings) · **OpenRouter / xAI / Gemini / Ollama** · **Gradio 6** · **NumPy** · **SQLite** · **pypdf** · **Pydantic** · **Telegram Bot API** · **Pushover** · **Render**

---

## License

Released under the MIT License.
