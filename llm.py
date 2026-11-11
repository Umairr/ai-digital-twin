"""Provider-agnostic LLM layer.

Pick a provider with LLM_PROVIDER (and optionally LLM_MODEL):

    openai      OpenAI                       OPENAI_API_KEY
    anthropic   Claude (official SDK)        ANTHROPIC_API_KEY
    openrouter  OpenRouter (any model)       OPENROUTER_API_KEY
    grok        xAI Grok                     XAI_API_KEY (or GROK_API_KEY)
    gemini      Google Gemini                GEMINI_API_KEY (or GOOGLE_API_KEY)
    ollama      Local models via Ollama      (no key)

Claude is called through the official `anthropic` SDK. Every other provider exposes an
OpenAI-compatible API and is called through the `openai` SDK with its own base URL.

The rest of the app only uses three operations:
    llm.run_tools(system, history, user_message, tools, execute)   -> (reply, tool_outputs)
    llm.structured(system, user, PydanticModel)                    -> model instance
    embedder.embed(texts) / embedder.available                     -> vectors for RAG
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel


@dataclass(frozen=True)
class Provider:
    name: str
    key_envs: tuple[str, ...]
    default_model: str
    base_url: str | None = None
    embed_model: str | None = None  # None = provider has no embeddings endpoint
    native_anthropic: bool = False


PROVIDERS: dict[str, Provider] = {
    "openai": Provider("openai", ("OPENAI_API_KEY",), "gpt-5.4-mini", embed_model="text-embedding-3-small"),
    "anthropic": Provider("anthropic", ("ANTHROPIC_API_KEY",), "claude-opus-5-5", native_anthropic=True),
    "openrouter": Provider(
        "openrouter", ("OPENROUTER_API_KEY",), "openai/gpt-5.4-mini",
        base_url="https://openrouter.ai/api/v1", embed_model="openai/text-embedding-3-small",
    ),
    "grok": Provider("grok", ("XAI_API_KEY", "GROK_API_KEY"), "grok-4.7", base_url="https://api.x.ai/v1"),
    "gemini": Provider(
        "gemini", ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/", embed_model="text-embedding-004",
    ),
    "ollama": Provider(
        "ollama", (), "llama3.2", base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        embed_model="nomic-embed-text",
    ),
}


def _key(p: Provider) -> str | None:
    if not p.key_envs:
        return "ollama"
    return next((os.getenv(k) for k in p.key_envs if os.getenv(k)), None)


def _openai_client(p: Provider):
    from openai import OpenAI

    headers = {"X-Title": "AI Digital Twin"} if p.name == "openrouter" else None
    return OpenAI(api_key=_key(p), base_url=p.base_url, default_headers=headers)


# --------------------------------------------------------------------------- chat
class LLM:
    def __init__(self, provider: str | None = None, model: str | None = None):
        name = (provider or os.getenv("LLM_PROVIDER") or "openai").lower()
        if name not in PROVIDERS:
            raise ValueError(f"Unknown LLM_PROVIDER '{name}'. Choose one of: {', '.join(PROVIDERS)}")
        self.provider = PROVIDERS[name]
        if self.provider.key_envs and not _key(self.provider):
            raise RuntimeError(f"LLM_PROVIDER={name} needs one of: {', '.join(self.provider.key_envs)}")
        self.model = model or os.getenv("LLM_MODEL") or self.provider.default_model
        if self.provider.native_anthropic:
            import anthropic

            self.client = anthropic.Anthropic(api_key=_key(self.provider))
        else:
            self.client = _openai_client(self.provider)

    def __repr__(self) -> str:
        return f"{self.provider.name}:{self.model}"

    @property
    def _limits(self) -> dict:
        # OpenRouter & co. reserve the model's full output window when max_tokens is unset,
        # which fails on low-credit keys. OpenAI's own API manages this itself.
        return {} if self.provider.name == "openai" else {"max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096"))}

    # ---- agent loop with tools -------------------------------------------------
    def run_tools(
        self,
        system: str,
        history: list[dict],
        user_message: str,
        tools: list[dict],
        execute: Callable[[str, dict], str],
        max_rounds: int = 6,
        extra_messages: list[dict] | None = None,
    ) -> tuple[str, list[str]]:
        """Chat with tool use. `tools` use a neutral schema: {name, description, parameters}.
        `execute(name, args) -> str` runs one tool. Returns (reply, tool outputs seen)."""
        runner = self._run_anthropic if self.provider.native_anthropic else self._run_openai
        return runner(system, history, user_message, tools, execute, max_rounds, extra_messages or [])

    def _run_openai(self, system, history, user_message, tools, execute, max_rounds, extra):
        messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": user_message}, *extra]
        oa_tools = [{"type": "function", "function": t} for t in tools]
        outputs: list[str] = []
        for _ in range(max_rounds):
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=oa_tools, **self._limits
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                return msg.content or "", outputs
            messages.append(msg)
            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute(call.function.name, args)
                outputs.append(result)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        return "Sorry, I got a bit tangled up there - could you rephrase that?", outputs

    def _run_anthropic(self, system, history, user_message, tools, execute, max_rounds, extra):
        # Claude takes the system prompt separately; extra "system" notes become user turns.
        messages = [*history, {"role": "user", "content": user_message}]
        for m in extra:
            role = "user" if m["role"] == "system" else m["role"]
            if messages and messages[-1]["role"] == role:
                messages[-1] = {"role": role, "content": f"{messages[-1]['content']}\n\n{m['content']}"}
            else:
                messages.append({"role": role, "content": m["content"]})
        an_tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        outputs: list[str] = []
        for _ in range(max_rounds):
            response = self.client.messages.create(
                model=self.model, max_tokens=16000, system=system, tools=an_tools, messages=messages,
            )
            if response.stop_reason == "refusal":
                return "Sorry, I can't help with that one - is there anything else about my work you'd like to know?", outputs
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                text = "".join(b.text for b in response.content if b.type == "text")
                return text, outputs
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in tool_uses:
                result = execute(block.name, block.input or {})
                outputs.append(result)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": results})  # all results in ONE user message
        return "Sorry, I got a bit tangled up there - could you rephrase that?", outputs

    # ---- structured output -------------------------------------------------------
    def structured(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        if self.provider.native_anthropic:
            response = self.client.messages.parse(
                model=self.model, max_tokens=16000, system=system,
                messages=[{"role": "user", "content": user}], output_format=schema,
            )
            return response.parsed_output
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            resp = self.client.chat.completions.parse(
                model=self.model, messages=messages, response_format=schema, **self._limits
            )
            parsed = resp.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except Exception as exc:  # some OpenAI-compatible providers lack json_schema support
            print(f"Structured output not supported by {self} ({exc}); falling back to JSON prompt")
        hint = f"\n\nRespond ONLY with a JSON object matching this schema:\n{json.dumps(schema.model_json_schema())}"
        resp = self.client.chat.completions.create(
            model=self.model, messages=[messages[0], {"role": "user", "content": user + hint}], **self._limits,
        )
        text = (resp.choices[0].message.content or "").strip().removeprefix("```json").removesuffix("```").strip()
        return schema.model_validate_json(text)


# ---------------------------------------------------------------------- embeddings
class Embedder:
    """Embeddings for RAG. Uses EMBEDDINGS_PROVIDER, else the chat provider if it has
    embeddings, else OpenAI/OpenRouter if a key exists. `available` is False when none
    is configured; the knowledge base then falls back to keyword search."""

    def __init__(self, chat_provider: str):
        choice = os.getenv("EMBEDDINGS_PROVIDER")
        candidates = [choice] if choice else [chat_provider, "openai", "openrouter", "gemini"]
        self.provider: Provider | None = None
        for name in candidates:
            p = PROVIDERS.get((name or "").lower())
            if p and p.embed_model and _key(p) and (p.name != "ollama" or name == choice or name == chat_provider):
                self.provider = p
                break
        self.model = os.getenv("EMBEDDINGS_MODEL") or (self.provider.embed_model if self.provider else None)
        self.client = _openai_client(self.provider) if self.provider else None

    @property
    def available(self) -> bool:
        return self.client is not None

    @property
    def cache_key(self) -> str:
        return f"{self.provider.name}:{self.model}" if self.provider else "keyword"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 100):
            resp = self.client.embeddings.create(model=self.model, input=texts[i:i + 100])
            out.extend(d.embedding for d in resp.data)
        return out
