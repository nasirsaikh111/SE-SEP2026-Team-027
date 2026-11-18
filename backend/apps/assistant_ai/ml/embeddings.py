"""Sentence-embedding backends with caching and a hard timeout.

Backends: "minilm" (sentence-transformers all-MiniLM-L6-v2, local), "gemini" (cloud, optional),
"none" (disabled -> rule-based fallback), or any object with .encode(list[str]) -> np.ndarray (tests).
"""
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

import numpy as np

logger = logging.getLogger(__name__)


# Raised whenever the model cannot help; callers then fall back to rules
class EmbeddingUnavailable(Exception):
    pass


# Unit-length vectors, so a dot product is the cosine similarity
def _normalise(m):
    m = np.asarray(m, dtype=np.float32)
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


# Small local model (about 90 MB), runs on CPU, no data leaves the server
class MiniLMEmbedder:
    name = 'all-MiniLM-L6-v2'

    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2', timeout=10.0):
        self.model_name, self.timeout = model_name, timeout
        self._model, self._lock, self._failed = None, threading.Lock(), False
        self._pool = ThreadPoolExecutor(max_workers=1)

    # Load lazily on first use, and only once even with many threads
    def _load(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device='cpu')
        return self._model

    def encode(self, texts):
        if self._failed:
            raise EmbeddingUnavailable('model failed to load earlier')
        # Run in a worker thread so a slow model cannot block the request forever
        fut = self._pool.submit(lambda: self._load().encode(list(texts), batch_size=32, show_progress_bar=False))
        try:
            return _normalise(fut.result(timeout=self.timeout))
        except FutTimeout:
            raise EmbeddingUnavailable('embedding timed out')
        except Exception as exc:  # import error, missing weights, ...
            # Remember the failure so later requests skip straight to the fallback
            self._failed = True
            logger.warning('Embedding model unavailable: %s', type(exc).__name__)
            raise EmbeddingUnavailable(type(exc).__name__)

    def available(self):
        try:
            self.encode(['health check'])
            return True
        except EmbeddingUnavailable:
            return False


class CallableEmbedder:
    """Wrap a function texts -> vectors (used for Gemini embeddings)."""

    def __init__(self, fn, name):
        self.fn, self.name = fn, name

    def encode(self, texts):
        vecs = self.fn(list(texts))
        if vecs is None:
            raise EmbeddingUnavailable(self.name + ' returned nothing')
        return _normalise(vecs)


# Fake but stable vectors for tests, so CI never downloads a model
class HashingEmbedder:
    """Deterministic bag-of-words hashing vectors. Used as a mock in tests (no model download)."""
    name = 'hashing-mock'

    def __init__(self, dim=256):
        self.dim = dim

    def encode(self, texts):
        from .text import tokens
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in tokens(t):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0
        return _normalise(out)


# Mentor profiles rarely change, so we embed each one once and reuse it
class VectorCache:
    """Cache mentor vectors keyed by (id, hash of profile text) so edits refresh automatically."""

    def __init__(self):
        self._store, self._lock = {}, threading.Lock()

    def get_many(self, embedder, items):
        """items: list of (key, text). Returns np.ndarray in the same order."""
        name = getattr(embedder, 'name', type(embedder).__name__)
        # The text hash in the key means an edited profile gets a fresh vector
        keys = [(name, k, hashlib.sha1(t.encode('utf8')).hexdigest()) for k, t in items]
        missing = [(i, items[i][1]) for i, key in enumerate(keys) if key not in self._store]
        if missing:
            vecs = embedder.encode([t for _, t in missing])
            with self._lock:
                for (i, _), v in zip(missing, vecs):
                    self._store[keys[i]] = v
        return np.stack([self._store[k] for k in keys]) if keys else np.zeros((0, 1))

    def clear(self):
        self._store.clear()


MENTOR_CACHE = VectorCache()
