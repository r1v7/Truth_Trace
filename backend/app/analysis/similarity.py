"""Pluggable claim-similarity backends.

`lexical` needs no model download and keeps the stack runnable offline; `embedding`
loads a local sentence-transformers model. Both expose the same interface so the
rest of the engine never knows which one is active.
"""

import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings

_TOKEN_RE = re.compile(r"\b[\w']+\b")
_FILLER = {"the", "a", "an", "i", "was", "were", "is", "are", "to", "at", "in", "of", "and", "my"}


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _FILLER]


class SimilarityBackend(ABC):
    name: str
    version: str

    @abstractmethod
    def similarity_matrix(self, texts_a: list[str], texts_b: list[str]) -> list[list[float]]:
        """Return an len(a) x len(b) matrix of scores in [0, 1]."""


class LexicalBackend(SimilarityBackend):
    name = "lexical"
    version = "1.0"

    def _pair(self, a: str, b: str) -> float:
        ta, tb = set(_tokens(a)), set(_tokens(b))
        if not ta or not tb:
            return 0.0
        overlap = len(ta & tb)
        # Dice coefficient: less harsh than Jaccard when lengths differ.
        return 2 * overlap / (len(ta) + len(tb))

    def similarity_matrix(self, texts_a: list[str], texts_b: list[str]) -> list[list[float]]:
        return [[self._pair(a, b) for b in texts_b] for a in texts_a]


class EmbeddingBackend(SimilarityBackend):
    name = "embedding"

    def __init__(self) -> None:
        self.version = settings.embedding_model.split("/")[-1]
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                settings.embedding_model, cache_folder=settings.model_cache_dir
            )
        return self._model

    def similarity_matrix(self, texts_a: list[str], texts_b: list[str]) -> list[list[float]]:
        if not texts_a or not texts_b:
            return [[] for _ in texts_a]
        model = self._load()
        emb_a = model.encode(texts_a, normalize_embeddings=True)
        emb_b = model.encode(texts_b, normalize_embeddings=True)
        return [
            [
                max(0.0, min(1.0, float(sum(x * y for x, y in zip(va, vb, strict=True)))))
                for vb in emb_b
            ]
            for va in emb_a
        ]


@lru_cache
def get_backend() -> SimilarityBackend:
    if settings.analyzer_backend == "embedding":
        return EmbeddingBackend()
    return LexicalBackend()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0
