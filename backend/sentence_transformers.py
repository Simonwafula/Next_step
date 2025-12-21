import os
from typing import Iterable, List

def _embedding_dim() -> int:
    try:
        return int(os.getenv("EMBEDDING_DIM", "384"))
    except Exception:
        return 384

class SentenceTransformer:
    """Minimal local stub for sentence_transformers.SentenceTransformer

    This avoids importing torch/transformers during local test runs.
    It returns deterministic zero vectors of the configured embedding dim.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dim = _embedding_dim()

    def encode(self, texts: Iterable[str], convert_to_tensor: bool = False):
        # Support single string or list
        if isinstance(texts, str):
            return [0.0] * self.dim
        # Return list of vectors
        return [[0.0] * self.dim for _ in texts]
