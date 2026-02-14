"""Tests for learned ranking module."""

import numpy as np
import pytest

from app.services.ranking import (
    RankingModel,
    extract_ranking_features,
    rank_results,
)


def test_extract_ranking_features_returns_8dim_vector():
    """Feature extraction produces correct dimensionality."""
    result = {
        "title": "Backend Engineer",
        "similarity_score": 85.3,
        "seniority": "mid-level",
        "location": "Nairobi",
        "salary_range": "KES 100,000 - 150,000",
    }
    query = "backend"
    user_context = {"seniority": "mid", "location": "nairobi"}

    features = extract_ranking_features(result, query, user_context)
    assert features.shape == (8,)
    assert features.dtype == np.float32


def test_extract_ranking_features_title_match():
    """Title keyword match feature is set correctly."""
    result = {
        "title": "Python Developer",
        "similarity_score": 50.0,
    }
    query = "python"

    features = extract_ranking_features(result, query)
    # Feature 1: title_keyword_match
    assert features[1] == 1.0


def test_extract_ranking_features_no_title_match():
    """Title keyword match is zero when query not in title."""
    result = {
        "title": "Backend Engineer",
        "similarity_score": 50.0,
    }
    query = "frontend"

    features = extract_ranking_features(result, query)
    assert features[1] == 0.0


def test_ranking_model_train_and_score():
    """Ranking model can be trained and score new data."""
    pytest.importorskip("sklearn", reason="scikit-learn not installed")

    X = np.array(
        [
            [0.8, 1.0, 0.0, 0.5, 1.0, 1.0, 1.0, 0.0],
            [0.3, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0],
            [0.9, 1.0, 1.0, 0.8, 1.0, 1.0, 1.0, 1.0],
        ],
        dtype=np.float32,
    )
    y = np.array([1, 0, 1])  # First and third are relevant

    model = RankingModel()
    model.train(X, y)

    # Score the training data
    scores = model.score(X)
    assert scores.shape == (3,)
    # Expect third (all features high) to score highest
    assert scores[2] > scores[0] > scores[1]


def test_rank_results_without_model_falls_back_to_similarity():
    """Ranking without trained model uses similarity_score heuristic."""
    results = [
        {"id": 1, "title": "Job A", "similarity_score": 50.0},
        {"id": 2, "title": "Job B", "similarity_score": 80.0},
        {"id": 3, "title": "Job C", "similarity_score": 40.0},
    ]
    query = "test"

    ranked = rank_results(results, query)
    assert [r["id"] for r in ranked] == [2, 1, 3]


def test_rank_results_empty_list():
    """Ranking empty list returns empty."""
    ranked = rank_results([], "query")
    assert ranked == []


def test_ranking_model_load_fails_gracefully():
    """Loading nonexistent model returns False."""
    model = RankingModel()
    # Delete model file if it exists
    from app.services.ranking import MODEL_PATH

    if MODEL_PATH.exists():
        MODEL_PATH.unlink()

    loaded = model.load()
    assert loaded is False
    assert model.model is None


def test_extract_ranking_features_location_match():
    """Location match feature is set when user location in result."""
    result = {
        "title": "Engineer",
        "location": "Nairobi, Kenya",
        "similarity_score": 60.0,
    }
    user_context = {"location": "nairobi"}

    features = extract_ranking_features(result, "", user_context)
    # Feature 5: location_match
    assert features[5] == 1.0


def test_extract_ranking_features_seniority_match():
    """Seniority match feature is set when user seniority in result."""
    result = {
        "title": "Engineer",
        "seniority": "mid-level",
        "similarity_score": 60.0,
    }
    user_context = {"seniority": "mid"}

    features = extract_ranking_features(result, "", user_context)
    # Feature 4: seniority_match
    assert features[4] == 1.0


def test_extract_ranking_features_has_salary():
    """Salary feature is set when salary_range present."""
    result = {
        "title": "Engineer",
        "salary_range": "KES 100,000",
        "similarity_score": 60.0,
    }

    features = extract_ranking_features(result, "")
    # Feature 6: has_salary
    assert features[6] == 1.0


def test_extract_ranking_features_no_salary():
    """Salary feature is zero when salary_range absent."""
    result = {
        "title": "Engineer",
        "similarity_score": 60.0,
    }

    features = extract_ranking_features(result, "")
    assert features[6] == 0.0
