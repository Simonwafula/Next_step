import numpy as np
import hashlib
import logging
from functools import lru_cache
from ..core.config import settings

logger = logging.getLogger(__name__)

# Global model instances (lazy loaded)
_tokenizer = None
_transformer_model = None
_use_transformers = True


def _get_model():
    """Lazy load transformer model for embeddings."""
    global _tokenizer, _transformer_model, _use_transformers
    if _tokenizer is None and _use_transformers:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel

            model_name = "intfloat/e5-small-v2"
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _transformer_model = AutoModel.from_pretrained(model_name)
            _transformer_model.eval()  # Set to evaluation mode
            logger.info(f"Loaded transformer model: {model_name}")
        except Exception as e:
            logger.warning(
                f"Failed to load transformer model: {e}. Falling back to hash-based embeddings."
            )
            _use_transformers = False
    return _tokenizer, _transformer_model


def _hash_to_vec(text: str, dim: int) -> np.ndarray:
    """Fallback: Deterministic embedding using hash (not semantically meaningful)."""
    h = hashlib.sha256((text or "").encode("utf-8")).digest()
    needed = (dim + len(h) - 1) // len(h)
    buf = (h * needed)[:dim]
    arr = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
    arr = (arr - 127.5) / 127.5
    return arr


def _mean_pooling(model_output, attention_mask):
    """Mean pooling for transformer outputs."""
    import torch

    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = (
        attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    )
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


@lru_cache(maxsize=1000)
def embed_text(text: str) -> list[float]:
    """Generate embedding for text using transformers or hash fallback."""
    if not text:
        text = ""

    tokenizer, model = _get_model()
    if tokenizer is not None and model is not None:
        try:
            import torch

            # Tokenize
            inputs = tokenizer(
                text, return_tensors="pt", padding=True, truncation=True, max_length=512
            )

            # Generate embeddings
            with torch.no_grad():
                outputs = model(**inputs)
                embeddings = _mean_pooling(outputs, inputs["attention_mask"])

                # Normalize embeddings
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            return embeddings[0].tolist()
        except Exception as e:
            logger.warning(f"Transformer encoding failed: {e}")

    # Fallback to hash-based
    dim = settings.EMBEDDING_DIM
    vec = _hash_to_vec(text, dim)
    return vec.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    tokenizer, model = _get_model()
    if tokenizer is not None and model is not None:
        try:
            import torch

            # Tokenize batch
            inputs = tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )

            # Generate embeddings
            with torch.no_grad():
                outputs = model(**inputs)
                embeddings = _mean_pooling(outputs, inputs["attention_mask"])

                # Normalize embeddings
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            return embeddings.tolist()
        except Exception as e:
            logger.warning(f"Batch encoding failed: {e}")

    # Fallback to hash-based
    return [embed_text(t) for t in texts]


def update_embeddings_model(db=None) -> dict:
    """Placeholder for updating embedding model; no-op for now.

    Returns a simple dict indicating success to satisfy callers in workflows.
    """
    return {"success": True, "message": "no-op in test environment"}
