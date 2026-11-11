"""Tiny RAG knowledge base: chunks every .md/.txt/.pdf in a folder, embeds with OpenAI,
caches embeddings to disk, and does cosine-similarity search with numpy.
No vector DB needed, so it deploys anywhere (HF Spaces, Render, fly.io)."""

import hashlib
import json
import os

import numpy as np
from pypdf import PdfReader

EMBED_MODEL = "text-embedding-3-small"


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
    def __init__(self, client, sources: list[str], cache_path: str, model: str = EMBED_MODEL):
        """sources: list of files and/or folders."""
        self.client = client
        self.model = model
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
        out = []
        for i in range(0, len(texts), 100):
            resp = self.client.embeddings.create(model=self.model, input=texts[i:i + 100])
            out.extend(d.embedding for d in resp.data)
        return out

    def _load(self, sources: list[str]) -> None:
        for path in self._files(sources):
            for i, chunk in enumerate(chunk_text(_read_file(path))):
                self.chunks.append({"source": os.path.basename(path), "index": i, "text": chunk})
        if not self.chunks:
            print("Knowledge base: no documents found")
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

    def search(self, query: str, k: int = 4, min_score: float = 0.25) -> list[dict]:
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
