import pytest

pytest.importorskip("bs4")

from app.ingestion.connectors import gov_careers


def test_job_page_filter_rejects_generic_opportunities_pages():
    assert (
        gov_careers._looks_like_job_page(
            "https://meru.go.ke/opportunities/news-updates/",
            "News Updates",
            "Latest county updates and notices.",
            is_doc=False,
        )
        is False
    )


def test_job_page_filter_accepts_vacancy_like_pages():
    assert (
        gov_careers._looks_like_job_page(
            "https://example.go.ke/vacancies/",
            "Vacancies",
            "View current vacancies and how to apply. Closing date 2026-03-01.",
            is_doc=False,
        )
        is True
    )
