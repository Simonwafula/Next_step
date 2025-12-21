import numpy as np
import hashlib
from ..core.config import settings

def _hash_to_vec(text: str, dim: int) -> np.ndarray:
    # Deterministic "embedding": hash chunks mapped to [-1, 1]
    h = hashlib.sha256((text or '').encode('utf-8')).digest()
    # Repeat to fill dim
    needed = (dim + len(h) - 1) // len(h)
    buf = (h * needed)[:dim]
    arr = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
    arr = (arr - 127.5) / 127.5
    return arr

def embed_text(text: str) -> list[float]:
    dim = settings.EMBEDDING_DIM
    vec = _hash_to_vec(text, dim)
    return vec.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the hash-based embedder."""
    return [embed_text(t) for t in texts]


def update_embeddings_model(db=None) -> dict:
    """Placeholder for updating embedding model; no-op for tests.

    Returns a simple dict indicating success to satisfy callers in workflows.
    """
    return {"success": True, "message": "no-op in test environment"}
