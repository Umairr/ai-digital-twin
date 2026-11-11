"""Tiny RAG knowledge base: chunks every .md/.txt/.pdf in a folder, embeds the chunks,
caches embeddings to disk, and does cosine-similarity search with numpy.
No vector DB needed, so it deploys anywhere (HF Spaces, Render, fly.io).

Embeddings come from any provider with an embeddings API (see llm.Embedder). When none is
configured (e.g. Claude or Grok only), it falls back to keyword (BM25-style) search."""

import hashlib
import json
import math
import os
import re
from collections import Counter

import numpy as np
from pypdf import PdfReader

_WORD = re.compile(r"[a-z0-9+#.]{2,}")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _read_file(path: str) -> str:
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, max_chars: int = 900, overlap: int = 150) -> list[str]:
    """Paragraph-aware chunking with a small overlap between chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        while len(p) > max_chars:  # very long paragraph -> hard split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(p[:max_chars])
            p = p[max_chars - overlap:]
        if len(current) + len(p) + 2 <= max_chars:
            current = f"{current}\n\n{p}" if current else p
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if current else ""
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail  # start at a word boundary
            current = f"{tail}\n\n{p}" if tail else p
    if current:
        chunks.append(current)
    return chunks


class KnowledgeBase:
    def __init__(self, embedder, sources: list[str], cache_path: str):
        """sources: list of files and/or folders. embedder: llm.Embedder."""
        self.embedder = embedder
        self.model = embedder.cache_key
        self.cache_path = cache_path
        self.chunks: list[dict] = []
        self.matrix: np.ndarray | None = None
        self._load(sources)

    def _files(self, sources: list[str]) -> list[str]:
        files = []
        for s in sources:
            if os.path.isdir(s):
                for name in sorted(os.listdir(s)):
                    if name.lower().endswith((".md", ".txt", ".pdf")):
                        files.append(os.path.join(s, name))
            elif os.path.isfile(s):
                files.append(s)
        return files

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed(texts)

    def _load(self, sources: list[str]) -> None:
        for path in self._files(sources):
            for i, chunk in enumerate(chunk_text(_read_file(path))):
                self.chunks.append({"source": os.path.basename(path), "index": i, "text": chunk})
        if not self.chunks:
            print("Knowledge base: no documents found")
            return
        if not self.embedder.available:
            self._build_keyword_index()
            print(f"Knowledge base: {len(self.chunks)} chunks (keyword search - no embeddings provider)")
            return

        cache = {}
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("model") != self.model:
                cache = {}
        vectors = cache.get("vectors", {})

        keys = [hashlib.sha256(c["text"].encode()).hexdigest() for c in self.chunks]
        missing = [k for k in dict.fromkeys(keys) if k not in vectors]
        if missing:
            texts = {k: c["text"] for k, c in zip(keys, self.chunks)}
            for k, v in zip(missing, self._embed([texts[k] for k in missing])):
                vectors[k] = v
            # keep only vectors still in use
            vectors = {k: vectors[k] for k in set(keys)}
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"model": self.model, "vectors": vectors}, f)

        m = np.array([vectors[k] for k in keys], dtype=np.float32)
        self.matrix = m / np.linalg.norm(m, axis=1, keepdims=True)
        print(f"Knowledge base: {len(self.chunks)} chunks ({len(missing)} newly embedded)")

    def _build_keyword_index(self) -> None:
        self._doc_tokens = [Counter(_tokens(c["text"])) for c in self.chunks]
        self._doc_len = [sum(t.values()) for t in self._doc_tokens]
        self._avg_len = sum(self._doc_len) / max(len(self._doc_len), 1)
        df = Counter(term for toks in self._doc_tokens for term in toks)
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _keyword_search(self, query: str, k: int) -> list[dict]:
        terms = _tokens(query)
        scored = []
        for i, toks in enumerate(self._doc_tokens):
            score = 0.0
            for t in terms:
                tf = toks.get(t, 0)
                if tf:
                    score += self._idf.get(t, 0) * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * self._doc_len[i] / self._avg_len))
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [{**self.chunks[i], "score": round(s, 3)} for s, i in scored[:k]]

    def search(self, query: str, k: int = 4, min_score: float = 0.25) -> list[dict]:
        if not self.chunks:
            return []
        if not self.embedder.available:
            return self._keyword_search(query, k)
        if self.matrix is None:
            return []
        q = np.array(self._embed([query])[0], dtype=np.float32)
        q /= np.linalg.norm(q)
        scores = self.matrix @ q
        top = np.argsort(-scores)[:k]
        return [
            {**self.chunks[i], "score": round(float(scores[i]), 3)}
            for i in top
            if scores[i] >= min_score
        ]
