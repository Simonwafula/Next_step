"""Tests for T-DS-980: Model stack consolidation."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.intelligence_routes import router as intelligence_router
from app.db.database import get_db
from app.ml.model_registry import (  # noqa: E402
    CANONICAL_EMBEDDING_DIM,
    CANONICAL_EMBEDDING_MODEL_HF,
    CANONICAL_EMBEDDING_MODEL_SHORT,
    FEATURE_CONTRACT,
    FEATURE_CONTRACT_VERSION,
    FEATURE_DIM,
    get_feature_contract_dict,
    get_metric_registry,
    is_hash_fallback_active,
    load_algorithm_registry,
    set_hash_fallback_active,
    update_algorithm_registry,
)


def _build_app(db_session_factory):
    app = FastAPI()
    app.include_router(intelligence_router)

    def override_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return app


# ---------------------------------------------------------------------------
# T-DS-981: Canonical embedding constants
# ---------------------------------------------------------------------------


def test_canonical_embedding_model_name():
    assert CANONICAL_EMBEDDING_MODEL_SHORT == "e5-small-v2"
    assert "e5-small-v2" in CANONICAL_EMBEDDING_MODEL_HF


def test_canonical_embedding_dim():
    assert CANONICAL_EMBEDDING_DIM == 384


# ---------------------------------------------------------------------------
# T-DS-982: Feature contract
# ---------------------------------------------------------------------------


def test_feature_contract_length():
    assert FEATURE_DIM == 8
    assert len(FEATURE_CONTRACT) == FEATURE_DIM


def test_feature_contract_indices_sequential():
    for spec in FEATURE_CONTRACT:
        assert spec.index == FEATURE_CONTRACT.index(spec)


def test_feature_contract_dict():
    d = get_feature_contract_dict()
    assert d["version"] == FEATURE_CONTRACT_VERSION
    assert d["dimension"] == FEATURE_DIM
    assert len(d["features"]) == FEATURE_DIM


def test_ranking_model_uses_feature_dim():
    # Import here to avoid numpy at collection time in lean test venv
    import sys
    import types
    # Stub numpy so ranking.py can be imported without the real package
    if "numpy" not in sys.modules:
        np_stub = types.ModuleType("numpy")
        np_stub.ndarray = list
        np_stub.float32 = float
        np_stub.array = lambda x, **kw: x
        np_stub.argsort = sorted
        sys.modules["numpy"] = np_stub
    from app.services.ranking import RankingModel  # noqa: PLC0415
    model = RankingModel()
    assert model.features_dim == FEATURE_DIM


# ---------------------------------------------------------------------------
# T-DS-983: Algorithm registry
# ---------------------------------------------------------------------------


def test_load_algorithm_registry_returns_dict():
    registry = load_algorithm_registry()
    assert "algorithms" in registry
    assert "ranking" in registry["algorithms"]
    assert "embeddings" in registry["algorithms"]


def test_algorithm_registry_embedding_model_matches_canonical():
    registry = load_algorithm_registry()
    emb = registry["algorithms"]["embeddings"]
    assert emb["name"] == CANONICAL_EMBEDDING_MODEL_SHORT
    assert emb["dimension"] == CANONICAL_EMBEDDING_DIM


def test_update_algorithm_registry(tmp_path, monkeypatch):
    import app.ml.model_registry as reg_module

    monkeypatch.setattr(
        reg_module, "_REGISTRY_PATH", tmp_path / "algorithm_registry.json"
    )
    result = update_algorithm_registry("ranking", {"eval_metrics": {"auc": 0.75}})
    assert result["algorithms"]["ranking"]["eval_metrics"]["auc"] == 0.75


# ---------------------------------------------------------------------------
# T-DS-984: Metric registry
# ---------------------------------------------------------------------------


def test_get_metric_registry_no_db():
    result = get_metric_registry(db=None)
    assert "embedding" in result
    assert "feature_contract" in result
    assert "algorithms" in result


def test_get_metric_registry_with_db(db_session_factory):
    db = db_session_factory()
    result = get_metric_registry(db=db)
    db.close()
    assert "baseline_health" in result
    assert "embedding" in result


# ---------------------------------------------------------------------------
# T-DS-985: Hash-fallback gate
# ---------------------------------------------------------------------------


def test_set_hash_fallback_active_false():
    set_hash_fallback_active(False)
    assert not is_hash_fallback_active()


def test_set_hash_fallback_active_true():
    set_hash_fallback_active(True)
    assert is_hash_fallback_active()
    set_hash_fallback_active(False)  # reset


def test_hash_fallback_via_env(monkeypatch):
    monkeypatch.setenv("NEXTSTEP_DISABLE_TRANSFORMERS", "1")
    assert is_hash_fallback_active()
    monkeypatch.delenv("NEXTSTEP_DISABLE_TRANSFORMERS")


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


def test_algorithm_registry_endpoint(db_session_factory):
    client = TestClient(_build_app(db_session_factory))
    resp = client.get("/api/intelligence/algorithm-registry")
    assert resp.status_code == 200
    assert "algorithms" in resp.json()


def test_feature_contract_endpoint(db_session_factory):
    client = TestClient(_build_app(db_session_factory))
    resp = client.get("/api/intelligence/feature-contract")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimension"] == 8


def test_metric_registry_endpoint(db_session_factory):
    client = TestClient(_build_app(db_session_factory))
    resp = client.get("/api/intelligence/metric-registry")
    assert resp.status_code == 200
    data = resp.json()
    assert "embedding" in data


def test_embedding_mode_endpoint(db_session_factory):
    set_hash_fallback_active(False)
    client = TestClient(_build_app(db_session_factory))
    resp = client.get("/api/intelligence/embedding-mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] in ("semantic", "hash_fallback")
    assert "degraded" in data
