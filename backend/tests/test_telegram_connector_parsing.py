from app.ingestion.connectors.telegram import (
    extract_urls,
    guess_title_from_text,
    normalize_channel,
    pick_application_url,
    should_keep_message,
)


def test_normalize_channel_handles_urls_and_mentions():
    assert normalize_channel("https://t.me/job_vacancy_kenya") == "job_vacancy_kenya"
    assert normalize_channel("t.me/job_vacancy_kenya/123") == "job_vacancy_kenya"
    assert normalize_channel("@job_vacancy_kenya") == "job_vacancy_kenya"


def test_extract_urls_strips_trailing_punctuation_and_dedupes():
    text = "Apply here: https://example.com/job) and https://example.com/job."
    assert extract_urls(text) == ["https://example.com/job"]


def test_pick_application_url_skips_telegram_links():
    urls = [
        "https://t.me/job_vacancy_kenya/123",
        "https://example.com/apply",
    ]
    assert pick_application_url(urls) == "https://example.com/apply"


def test_guess_title_from_text_prefers_explicit_patterns():
    text = "Position: Data Analyst\nLocation: Nairobi\nApply: https://example.com"
    assert guess_title_from_text(text) == "Data Analyst"


def test_guess_title_from_text_falls_back_to_first_text_line():
    text = "Senior Backend Engineer\nApply: https://example.com/apply"
    assert guess_title_from_text(text) == "Senior Backend Engineer"


def test_guess_title_from_text_skips_url_lines():
    text = "https://example.com/apply\nData Engineer\nDeadline: tomorrow"
    assert guess_title_from_text(text) == "Data Engineer"


def test_should_keep_message_filters_short_and_promo_messages():
    assert should_keep_message("short", min_text_len=10) is False

    promo = "Subscribe to our channel for updates and promotions. Thanks."
    assert should_keep_message(promo, min_text_len=10) is False

    promo_with_job = "Subscribe for updates. New job vacancy: Data Analyst."
    assert should_keep_message(promo_with_job, min_text_len=10) is True


def test_should_keep_message_supports_require_and_exclude_keywords():
    msg = "We are hiring a Data Analyst. Apply by Friday."
    assert (
        should_keep_message(msg, min_text_len=10, require_keywords=["vacancy"]) is False
    )
    assert (
        should_keep_message(msg, min_text_len=10, require_keywords=["hiring"]) is True
    )

    msg2 = "Promo: apply now for job vacancies."
    assert (
        should_keep_message(msg2, min_text_len=10, exclude_keywords=["promo"]) is False
    )
