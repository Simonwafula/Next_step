from app.services.search import search_jobs


def test_search_jobs_no_match_fallback_returns_canonical_results_payload(
    db_session_factory,
):
    db = db_session_factory()

    payload = search_jobs(db, q="zzzxxyy-unmatched-query", limit=5, offset=0)

    assert payload["results"] == payload["jobs"]
    assert len(payload["results"]) == 1
    assert payload["results"][0]["is_suggestion"] is True
    assert payload["results"][0]["title"] == "No exact matches found"
    assert payload["total"] == 1
    assert payload["has_more"] is False
    assert payload["title_clusters"] == []
    assert payload["companies_hiring"] == []
    assert payload["meta"]["suggestion"] is True

    db.close()
