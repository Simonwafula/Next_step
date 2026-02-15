from app.services.salary_service import salary_service


def test_estimate_salary_range_boosts_for_senior_data_roles_in_nairobi():
    estimate = salary_service.estimate_salary_range(
        title="Senior Data Scientist",
        seniority="senior",
        location_text="Nairobi, Kenya",
    )

    assert estimate["currency"] == "KES"
    assert estimate["min"] >= 200000
    assert estimate["max"] > estimate["min"]
    assert estimate["estimated"] is True
    assert estimate["confidence"] >= 0.7


def test_estimate_salary_range_defaults_for_unknown_role_without_context():
    estimate = salary_service.estimate_salary_range(
        title="Operations Associate",
        seniority=None,
        location_text=None,
    )

    assert estimate["min"] > 0
    assert estimate["max"] >= estimate["min"]
    assert estimate["confidence"] >= 0.4


def test_format_salary_range_produces_kes_display_string():
    formatted = salary_service.format_salary_range(80000, 120000, "KES")
    assert formatted == "KES 80,000 - 120,000"
