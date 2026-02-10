from types import SimpleNamespace

from app.services.search import generate_match_explanation


class _Job:
    def __init__(self, title_raw: str) -> None:
        self.title_raw = title_raw


def test_generate_match_explanation_handles_skill_dicts() -> None:
    job = _Job("Backend Engineer")
    entities = SimpleNamespace(skills=[{"value": "Python", "confidence": 0.9}])
    msg = generate_match_explanation(
        "python",
        job,  # type: ignore[arg-type]
        title_norm=None,
        similarity_score=0.0,
        entities=entities,
    )
    assert "requires python skill" in msg


def test_generate_match_explanation_handles_skill_strings() -> None:
    job = _Job("Backend Engineer")
    entities = SimpleNamespace(skills=["SQL", "Docker"])
    msg = generate_match_explanation(
        "sql",
        job,  # type: ignore[arg-type]
        title_norm=None,
        similarity_score=0.0,
        entities=entities,
    )
    assert "requires sql skill" in msg
