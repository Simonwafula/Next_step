"""
Tests for Career Insight Service

Tests the three-phase pipeline:
1. Collection - fetching jobs by title
2. Collation - extracting patterns
3. Summarization - generating career guide
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.services.career_insight_service import CareerInsightService


class MockJob:
    """Mock job for testing"""

    def __init__(
        self,
        id=1,
        title_raw="Data Analyst",
        description_raw="Analyze data using Python and SQL. Create reports.",
        description_clean=None,
        requirements_raw="3 years experience. Bachelor's degree.",
        organization="Test Company",
        seniority="mid",
        salary_min=100000,
        salary_max=200000,
        education="Bachelor's Degree",
        is_active=True,
        title_norm_id=1,
        org_id=1,
    ):
        self.id = id
        self.title_raw = title_raw
        self.description_raw = description_raw
        self.description_clean = description_clean
        self.requirements_raw = requirements_raw
        self.organization = organization
        self.seniority = seniority
        self.salary_min = salary_min
        self.salary_max = salary_max
        self.education = education
        self.is_active = is_active
        self.title_norm_id = title_norm_id
        self.org_id = org_id


class MockTitleNorm:
    """Mock title normalization"""

    def __init__(self, canonical_title="data analyst", family="data_analytics"):
        self.canonical_title = canonical_title
        self.family = family


class MockOrg:
    """Mock organization"""

    def __init__(self, name="Test Company"):
        self.name = name


class TestCareerInsightService:
    """Test career insight extraction"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance"""
        return CareerInsightService(mock_db)

    def test_normalize_search_title(self, service):
        """Test title normalization for search"""
        assert service._normalize_search_title("Senior Data Analyst") == "data analyst"
        assert (
            service._normalize_search_title("JUNIOR SOFTWARE ENGINEER")
            == "software engineer"
        )
        assert (
            service._normalize_search_title("Lead Project Manager") == "project manager"
        )

    def test_extract_skills_basic(self, service):
        """Test basic skill extraction"""
        text = "We need someone with Python, SQL, and Excel skills."
        skills = service._extract_skills(text)

        assert skills["total_unique"] > 0
        assert any(s["skill"] == "python" for s in skills["top_10"])
        assert any(s["skill"] == "sql" for s in skills["top_10"])

    def test_extract_skills_categorized(self, service):
        """Test skill categorization"""
        text = "Python, JavaScript, React, AWS, Docker, and SQL required."
        skills = service._extract_skills(text)

        assert "programming" in skills["by_category"]
        assert "web_dev" in skills["by_category"]
        assert "cloud" in skills["by_category"]

    def test_extract_experience_requirements(self, service):
        """Test experience extraction"""
        jobs = [
            {"description": "Minimum 3 years experience required", "requirements": ""},
            {"description": "5-7 years of relevant experience", "requirements": ""},
            {
                "description": "At least 2 years experience in similar role",
                "requirements": "",
            },
        ]

        experience = service._extract_experience_requirements(jobs)

        assert experience["min_years"] is not None
        assert experience["average"] is not None
        assert "distribution" in experience

    def test_extract_education_requirements(self, service):
        """Test education extraction"""
        jobs = [{"description": "", "requirements": ""}]
        text = "Bachelor's degree in Computer Science required. Master's preferred."

        education = service._extract_education_requirements(jobs, text)

        assert "bachelors" in education["levels"]
        assert "masters" in education["levels"]

    def test_extract_salary_data(self, service):
        """Test salary extraction"""
        jobs = [
            {"salary_min": 100000, "salary_max": 150000},
            {"salary_min": 120000, "salary_max": 180000},
            {"salary_min": 80000, "salary_max": 120000},
        ]

        salary = service._extract_salary_data(jobs)

        assert salary["available"] is True
        assert salary["min"] == 80000
        assert salary["max"] == 180000
        assert salary["sample_size"] == 3

    def test_extract_salary_data_empty(self, service):
        """Test salary extraction with no data"""
        jobs = [{"salary_min": None, "salary_max": None}]

        salary = service._extract_salary_data(jobs)

        assert salary["available"] is False

    def test_empty_collation(self, service):
        """Test empty collation structure"""
        collation = service._empty_collation()

        assert collation["job_count"] == 0
        assert collation["skills"]["total_unique"] == 0
        assert collation["responsibilities"]["total_extracted"] == 0

    def test_collate_insights(self, service):
        """Test full collation pipeline"""
        jobs = [
            {
                "description": "Analyze data using Python and SQL. Create reports and dashboards.",
                "requirements": "Bachelor's degree. 3 years experience.",
                "organization": "Tech Corp",
                "seniority": "mid",
                "salary_min": 100000,
                "salary_max": 150000,
            },
            {
                "description": "Work with large datasets. Use Excel and Tableau for visualization.",
                "requirements": "Degree in Statistics or related field.",
                "organization": "Data Inc",
                "seniority": "senior",
                "salary_min": 120000,
                "salary_max": 180000,
            },
        ]

        collated = service.collate_insights(jobs)

        assert collated["job_count"] == 2
        assert collated["skills"]["total_unique"] > 0
        assert len(collated["companies"]["top_employers"]) > 0

    def test_summarize_career(self, service):
        """Test career summary generation"""
        collated = {
            "job_count": 50,
            "titles_found": ["Data Analyst", "Junior Data Analyst"],
            "responsibilities": {
                "common_verbs": {"analyze": 30, "report": 25},
                "example_tasks": ["Analyze data trends", "Create monthly reports"],
                "total_extracted": 100,
            },
            "skills": {
                "by_category": {"data_analysis": [{"skill": "sql", "frequency": 40}]},
                "top_10": [
                    {"skill": "sql", "frequency": 40, "category": "data_analysis"}
                ],
                "total_unique": 15,
            },
            "tools": {"software": [{"tool": "Excel", "frequency": 30}], "total": 5},
            "experience": {
                "min_years": 1,
                "max_years": 5,
                "average": 3.0,
                "distribution": {"2": 10, "3": 15},
            },
            "education": {
                "levels": {"bachelors": 40, "masters": 10},
                "common_fields": {"statistics": 15, "computer science": 12},
            },
            "salary": {
                "available": True,
                "min": 80000,
                "max": 200000,
                "median": 120000,
            },
            "locations": {"cities": ["Nairobi"], "remote_available": True},
            "companies": {
                "unique_employers": 20,
                "top_employers": ["Safaricom"],
                "total_postings": 50,
            },
        }

        summary = service.summarize_career(collated, "data analyst")

        assert summary["title"] == "Data Analyst"
        assert "what_you_do" in summary
        assert len(summary["skills_needed"]["top_skills"]) > 0
        assert summary["education_required"]["minimum"] is not None
        assert summary["data_source"]["jobs_analyzed"] == 50

    def test_generate_outlook(self, service):
        """Test career outlook generation"""
        high_demand = {"job_count": 100, "companies": {"unique_employers": 30}}
        assert "strong demand" in service._generate_outlook(high_demand).lower()

        moderate_demand = {"job_count": 30, "companies": {"unique_employers": 15}}
        assert "moderate" in service._generate_outlook(moderate_demand).lower()

        specialized = {"job_count": 5, "companies": {"unique_employers": 3}}
        assert "specialized" in service._generate_outlook(specialized).lower()

    def test_format_salary(self, service):
        """Test salary formatting"""
        salary_data = {
            "available": True,
            "min": 100000,
            "max": 250000,
            "median": 150000,
        }
        formatted = service._format_salary(salary_data)

        assert "KES" in formatted["range"]
        assert formatted["available"] is True

    @patch.object(CareerInsightService, "collect_jobs_for_title")
    def test_get_full_career_insight_no_jobs(self, mock_collect, service):
        """Test handling when no jobs found"""
        mock_collect.return_value = []

        result = service.get_full_career_insight("nonexistent role")

        assert result["success"] is False
        assert "error" in result

    @patch.object(CareerInsightService, "collect_jobs_for_title")
    def test_get_full_career_insight_with_jobs(self, mock_collect, service):
        """Test full pipeline with mock data"""
        mock_collect.return_value = [
            {
                "id": 1,
                "title_raw": "Data Analyst",
                "description": "Analyze data using Python and SQL",
                "requirements": "Bachelor's degree, 3 years experience",
                "organization": "Tech Corp",
                "seniority": "mid",
                "salary_min": 100000,
                "salary_max": 150000,
                "education": "Bachelor's Degree",
            }
        ]

        result = service.get_full_career_insight("data analyst")

        assert result["success"] is True
        assert "summary" in result
        assert "detailed_breakdown" in result
