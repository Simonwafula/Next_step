from app.normalization.extractors import extract_task_statements


def test_extract_task_statements_returns_evidence():
    text = """
    - Analyze data to produce weekly reports
    - Manage stakeholder expectations across teams
    """
    tasks = extract_task_statements(text)
    assert tasks
    for task in tasks:
        assert "value" in task
        assert "confidence" in task
        assert "evidence" in task
        assert task["confidence"] >= 0.2
