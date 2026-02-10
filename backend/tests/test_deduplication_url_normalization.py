from app.services.deduplication_service import DeduplicationService


def test_normalize_url_strips_tracking_and_www_and_trailing_slash():
    svc = DeduplicationService()
    raw = "https://www.Example.com/path/to/job/?utm_source=x&ref=abc#frag"
    assert svc.normalize_url(raw) == "https://example.com/path/to/job"


def test_generate_url_hash_is_stable_for_www_variants():
    svc = DeduplicationService()
    a = "https://example.com/jobs/role?id=123&utm_medium=y"
    b = "https://www.example.com/jobs/role?id=123"
    assert svc.generate_url_hash(a) == svc.generate_url_hash(b)
