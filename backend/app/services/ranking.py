"""Learned ranking module for job search results.

This is an optional enhancement: production search must continue to work even
when the learned model or training dependencies are unavailable.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np

try:
    # Optional dependency: allow the app to run without scikit-learn installed.
    from sklearn.linear_model import LogisticRegression  # type: ignore
except (
    Exception
):  # pragma: no cover - exercised implicitly in environments without sklearn
    LogisticRegression = None  # type: ignore[assignment]

# Model persistence path
# Keep artifacts out of the package tree: store in backend/var/.
MODEL_PATH = Path(__file__).resolve().parents[2] / "var" / "ranking_model.pkl"


class RankingModel:
    """Lightweight learned-to-rank model using logistic regression."""

    def __init__(self):
        # Stored model may come from sklearn; keep type flexible for optional dependency.
        self.model: Any | None = None
        self.features_dim = 8  # Number of features per result

    def load(self) -> bool:
        """Load trained model from disk. Returns True if loaded."""
        if not MODEL_PATH.exists():
            return False
        try:
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            return True
        except Exception:
            self.model = None
            return False

    def save(self) -> None:
        """Save trained model to disk."""
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)

    def train(self, features: np.ndarray, labels: np.ndarray) -> None:
        """Train the ranking model.

        Args:
            features: (N, features_dim) array of feature vectors
            labels: (N,) binary array (1=clicked/applied, 0=shown)
        """
        if LogisticRegression is None:
            raise RuntimeError(
                "scikit-learn is not installed; cannot train ranking model"
            )
        self.model = LogisticRegression(
            max_iter=1000, random_state=42, class_weight="balanced"
        )
        self.model.fit(features, labels)
        self.save()

    def score(self, features: np.ndarray) -> np.ndarray:
        """Score results using the trained model.

        Args:
            features: (N, features_dim) array

        Returns:
            (N,) array of relevance scores (probabilities)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() or train() first.")
        return self.model.predict_proba(features)[:, 1]


def extract_ranking_features(
    result: dict[str, Any],
    query: str,
    user_context: dict[str, Any] | None = None,
) -> np.ndarray:
    """Extract feature vector for a single search result.

    Features (8-dim):
    - semantic_similarity (from result)
    - title_keyword_match (binary)
    - desc_keyword_match (binary, not available here - placeholder)
    - recency_days (normalized)
    - seniority_match (binary)
    - location_match (binary)
    - has_salary (binary)
    - skill_overlap_count (placeholder for future entity match)
    """
    q_lower = (query or "").lower()
    title_lower = (result.get("title") or "").lower()
    seniority = (result.get("seniority") or "").lower()
    location = (result.get("location") or "").lower()

    # Feature 0: semantic similarity
    sim_raw = result.get("similarity_score") or 0.0
    sim = float(sim_raw) / 100.0  # Normalize to [0,1]

    # Feature 1: title keyword match
    title_match = 1.0 if q_lower and q_lower in title_lower else 0.0

    # Feature 2: description match (placeholder - not in result dict)
    desc_match = 0.0

    # Feature 3: recency (placeholder - first_seen not in result)
    recency = 0.5  # Neutral value

    # Feature 4: seniority match
    user_seniority = user_context.get("seniority", "").lower() if user_context else ""
    seniority_match = 1.0 if user_seniority and user_seniority in seniority else 0.0

    # Feature 5: location match
    user_location = user_context.get("location", "").lower() if user_context else ""
    location_match = 1.0 if user_location and user_location in location else 0.0

    # Feature 6: has salary
    has_salary = 1.0 if result.get("salary_range") else 0.0

    # Feature 7: skill overlap (placeholder)
    skill_overlap = 0.0

    return np.array(
        [
            sim,
            title_match,
            desc_match,
            recency,
            seniority_match,
            location_match,
            has_salary,
            skill_overlap,
        ],
        dtype=np.float32,
    )


def rank_results(
    results: list[dict[str, Any]],
    query: str,
    user_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Re-rank search results using learned model with heuristic fallback.

    Args:
        results: List of job result dicts
        query: User search query
        user_context: Optional user preferences (seniority, location)

    Returns:
        Re-ordered list of results
    """
    if not results:
        return results

    # Extract features for all results
    features = np.array(
        [extract_ranking_features(r, query, user_context) for r in results]
    )

    # Try learned ranking
    ranker = RankingModel()
    if ranker.load():
        try:
            scores = ranker.score(features)
            # Sort by score descending
            ranked_indices = np.argsort(-scores)
            return [results[int(i)] for i in ranked_indices]
        except Exception:
            pass  # Fall through to heuristic

    # Fallback: heuristic sort by similarity
    return sorted(
        results,
        key=lambda x: float(x.get("similarity_score") or 0.0),
        reverse=True,
    )
