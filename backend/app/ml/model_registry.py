"""Model stack registry — single source of truth for all ML/algorithm metadata.

Covers T-DS-981 through T-DS-985:
- T-DS-981: Canonical embedding model name + dimension
- T-DS-982: Canonical feature contract for ranking / matching
- T-DS-983: Algorithm registry with evaluation-linked versioning
- T-DS-984: Intelligence metric registry
- T-DS-985: Hash-fallback detection + degraded-mode flag
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# T-DS-981: Canonical embedding model + dimension
# ---------------------------------------------------------------------------

# Single source of truth for the embedding model used across all services.
# search.py used os.getenv("EMBEDDING_MODEL_NAME", "e5-small-v2") directly;
# embeddings.py hardcoded the HuggingFace path inline.
# All callers should import from here.
CANONICAL_EMBEDDING_MODEL_SHORT = "e5-small-v2"
CANONICAL_EMBEDDING_MODEL_HF = "intfloat/e5-small-v2"
CANONICAL_EMBEDDING_DIM = 384  # e5-small-v2 output dimension

# ---------------------------------------------------------------------------
# T-DS-985: Hash-fallback detection
# ---------------------------------------------------------------------------

# Env var that disables transformer loading (used in CI / constrained envoys).
_DISABLE_TRANSFORMERS_ENV = "NEXTSTEP_DISABLE_TRANSFORMERS"

# Runtime flag: set to True by embeddings.py when transformers fail to load.
_hash_fallback_active: bool = False


def set_hash_fallback_active(value: bool) -> None:
    """Called by embeddings.py to signal that hash fallback is in use."""
    global _hash_fallback_active
    _hash_fallback_active = value
    if value:
        logger.warning(
            "Embedding model unavailable — hash-vector fallback is ACTIVE. "
            "Semantic search and ranking are DEGRADED."
        )


def is_hash_fallback_active() -> bool:
    """Return True if the hash-vector fallback is in use (degraded mode)."""
    if os.getenv(_DISABLE_TRANSFORMERS_ENV) == "1":
        return True
    return _hash_fallback_active


def embedding_mode() -> str:
    """Return 'semantic' or 'hash_fallback' for health/monitoring surfaces."""
    return "hash_fallback" if is_hash_fallback_active() else "semantic"


# ---------------------------------------------------------------------------
# T-DS-982: Canonical feature contract for ranking / matching
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    index: int
    description: str
    range: str  # e.g. "[0, 1]"


FEATURE_CONTRACT: list[FeatureSpec] = [
    FeatureSpec(
        0, 0, "Normalised semantic similarity from retrieval (score/100)", "[0, 1]"
    ),
    FeatureSpec(1, 1, "Jaccard token overlap between query and job title", "[0, 1]"),
    FeatureSpec(
        2, 2, "Jaccard token overlap between query and job description", "[0, 1]"
    ),
    FeatureSpec(3, 3, "Normalised posting recency (1.0=today, 0.0=180d+)", "[0, 1]"),
    FeatureSpec(
        4, 4, "Seniority match (1 if user seniority matches job band)", "{0, 1}"
    ),
    FeatureSpec(
        5, 5, "Location match (1 if user preferred location in job location)", "{0, 1}"
    ),
    FeatureSpec(6, 6, "Has salary (1 if salary information is present)", "{0, 1}"),
    FeatureSpec(
        7, 7, "Jaccard skill overlap between user skills and job skills", "[0, 1]"
    ),
]

FEATURE_CONTRACT_VERSION = "v1"
FEATURE_DIM = len(FEATURE_CONTRACT)  # 8 — use this instead of magic number


def get_feature_contract_dict() -> dict[str, Any]:
    return {
        "version": FEATURE_CONTRACT_VERSION,
        "dimension": FEATURE_DIM,
        "features": [asdict(f) for f in FEATURE_CONTRACT],
    }


# ---------------------------------------------------------------------------
# T-DS-983: Algorithm registry + evaluation-linked versioning
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "var" / "algorithm_registry.json"

_DEFAULT_REGISTRY: dict[str, Any] = {
    "algorithms": {
        "ranking": {
            "name": "logistic_regression_ranker",
            "version": "v1",
            "feature_contract_version": FEATURE_CONTRACT_VERSION,
            "model_path": str(
                Path(__file__).resolve().parents[2] / "var" / "ranking_model.pkl"
            ),
            "trained_at": None,
            "eval_metrics": {},
            "notes": "LogisticRegression on 8 serve-time features. Falls back to similarity sort when model file absent.",
        },
        "embeddings": {
            "name": CANONICAL_EMBEDDING_MODEL_SHORT,
            "hf_model_id": CANONICAL_EMBEDDING_MODEL_HF,
            "version": "v1",
            "dimension": CANONICAL_EMBEDDING_DIM,
            "notes": "intfloat/e5-small-v2 via HuggingFace transformers. Hash-vector fallback when unavailable.",
        },
    },
    "registry_version": "1",
    "last_updated": None,
}


def load_algorithm_registry() -> dict[str, Any]:
    """T-DS-983: Load algorithm registry from disk, or return default."""
    if _REGISTRY_PATH.exists():
        try:
            with open(_REGISTRY_PATH) as f:
                data = json.load(f)
            # Merge: ensure any new default keys are present
            for algo, defaults in _DEFAULT_REGISTRY["algorithms"].items():
                data.setdefault("algorithms", {}).setdefault(algo, defaults)
            return data
        except Exception as exc:
            logger.warning("Could not load algorithm registry: %s", exc)
    return dict(_DEFAULT_REGISTRY)


def update_algorithm_registry(
    algorithm: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """T-DS-983: Persist updated metadata for an algorithm entry."""
    registry = load_algorithm_registry()
    registry.setdefault("algorithms", {}).setdefault(algorithm, {}).update(updates)
    registry["last_updated"] = datetime.utcnow().isoformat()
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not persist algorithm registry: %s", exc)
    return registry


def record_ranking_train(trained_at: datetime, eval_metrics: dict[str, Any]) -> None:
    """T-DS-983: Record a completed ranking model training run."""
    update_algorithm_registry(
        "ranking",
        {
            "trained_at": trained_at.isoformat(),
            "eval_metrics": eval_metrics,
        },
    )


# ---------------------------------------------------------------------------
# T-DS-984: Intelligence metric registry
# ---------------------------------------------------------------------------


@dataclass
class IntelligenceMetricSnapshot:
    """Point-in-time snapshot of key intelligence system health metrics."""

    captured_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    embedding_mode: str = "unknown"
    ranking_model_loaded: bool = False
    baseline_health_status: str = "unknown"
    salary_coverage_pct: float = 0.0
    role_families_with_baseline: int = 0
    # Free-form dict for additional platform-specific metrics
    extra: dict[str, Any] = field(default_factory=dict)


_current_metric_snapshot: IntelligenceMetricSnapshot | None = None


def update_metric_snapshot(**kwargs: Any) -> IntelligenceMetricSnapshot:
    """T-DS-984: Update the in-process intelligence metric snapshot."""
    global _current_metric_snapshot
    if _current_metric_snapshot is None:
        _current_metric_snapshot = IntelligenceMetricSnapshot()
    for k, v in kwargs.items():
        if hasattr(_current_metric_snapshot, k):
            object.__setattr__(_current_metric_snapshot, k, v)
        else:
            _current_metric_snapshot.extra[k] = v
    _current_metric_snapshot.captured_at = datetime.utcnow().isoformat()
    return _current_metric_snapshot


def get_metric_registry(db=None) -> dict[str, Any]:
    """T-DS-984: Return full intelligence metric registry snapshot.

    Combines: embedding mode, algorithm registry, baseline health summary.
    Optionally accepts a db session to pull live baseline health.
    """
    registry = load_algorithm_registry()
    snapshot = _current_metric_snapshot

    baseline_summary: dict[str, Any] = {}
    if db is not None:
        try:
            from ..services.intelligence_products import get_baseline_health

            health = get_baseline_health(db)
            baseline_summary = {
                "overall_status": health.get("overall_status"),
                "role_families_covered": len(health.get("role_families_covered", [])),
                "stale_tables": [
                    name
                    for name, info in health.get("tables", {}).items()
                    if info.get("stale")
                ],
            }
        except Exception:
            pass

    return {
        "captured_at": datetime.utcnow().isoformat(),
        "embedding": {
            "mode": embedding_mode(),
            "model": CANONICAL_EMBEDDING_MODEL_SHORT,
            "dimension": CANONICAL_EMBEDDING_DIM,
            "degraded": is_hash_fallback_active(),
        },
        "feature_contract": get_feature_contract_dict(),
        "algorithms": registry.get("algorithms", {}),
        "baseline_health": baseline_summary
        or ({"status": snapshot.baseline_health_status} if snapshot else {}),
        "salary_coverage_pct": snapshot.salary_coverage_pct if snapshot else 0.0,
        "role_families_with_baseline": snapshot.role_families_with_baseline
        if snapshot
        else 0,
        "extra": snapshot.extra if snapshot else {},
    }
