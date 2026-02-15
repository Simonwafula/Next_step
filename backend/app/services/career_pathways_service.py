from dataclasses import dataclass

from .salary_service import salary_service


class CareerPathwayNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CareerPathway:
    role_slug: str
    title: str
    required_skills: tuple[str, ...]
    certifications: tuple[str, ...]
    employers_hiring: tuple[str, ...]
    learning_resources: tuple[str, ...]
    project_ideas: tuple[str, ...]


class CareerPathwaysService:
    def __init__(self) -> None:
        self._pathways = {
            "data-analyst": CareerPathway(
                role_slug="data-analyst",
                title="Data Analyst in Kenya (2026)",
                required_skills=(
                    "SQL",
                    "Excel",
                    "Power BI",
                    "Python",
                    "Business storytelling",
                ),
                certifications=(
                    "Google Data Analytics",
                    "Microsoft Power BI Data Analyst",
                    "SQL for Data Analysis",
                ),
                employers_hiring=(
                    "Safaricom",
                    "KCB Group",
                    "NCBA Bank",
                    "Jumia",
                    "Andela",
                ),
                learning_resources=(
                    "Practice SQL daily on real datasets.",
                    "Build dashboards from local market datasets.",
                    "Publish portfolio writeups with insights and decisions.",
                ),
                project_ideas=(
                    "Customer churn dashboard for telecom data.",
                    "E-commerce cohort retention analysis.",
                    "County-level labor demand tracker.",
                ),
            ),
            "software-engineer": CareerPathway(
                role_slug="software-engineer",
                title="Software Engineer in Kenya (2026)",
                required_skills=(
                    "Python or JavaScript",
                    "REST API design",
                    "Testing",
                    "Version control",
                    "System design basics",
                ),
                certifications=(
                    "AWS Cloud Practitioner",
                    "Meta Backend Developer",
                    "Docker Essentials",
                ),
                employers_hiring=(
                    "M-KOPA",
                    "Cellulant",
                    "Twiga Foods",
                    "PesaPal",
                    "Airtel Africa",
                ),
                learning_resources=(
                    "Ship one production-grade API with tests.",
                    "Learn deployment and monitoring basics.",
                    "Contribute to open-source projects.",
                ),
                project_ideas=(
                    "Job application tracker backend + frontend.",
                    "Authentication service with role-based access.",
                    "Search API with ranking and filtering.",
                ),
            ),
        }

    def get_pathway(self, role_slug: str) -> dict:
        normalized_slug = (role_slug or "").strip().lower()
        pathway = self._pathways.get(normalized_slug)
        if not pathway:
            raise CareerPathwayNotFoundError("Career pathway not found")

        salary_band = salary_service.estimate_salary_range(
            title=pathway.title,
            seniority="mid",
            location_text="Nairobi",
        )

        experience_ladder = [
            {
                "level": "Entry",
                "salary_range": salary_service.format_salary_range(
                    int(salary_band["min"] * 0.7),
                    int(salary_band["max"] * 0.75),
                    salary_band["currency"],
                ),
            },
            {
                "level": "Mid",
                "salary_range": salary_service.format_salary_range(
                    salary_band["min"],
                    salary_band["max"],
                    salary_band["currency"],
                ),
            },
            {
                "level": "Senior",
                "salary_range": salary_service.format_salary_range(
                    int(salary_band["min"] * 1.4),
                    int(salary_band["max"] * 1.5),
                    salary_band["currency"],
                ),
            },
        ]

        return {
            "role_slug": pathway.role_slug,
            "title": pathway.title,
            "required_skills": list(pathway.required_skills),
            "certifications": list(pathway.certifications),
            "experience_ladder": experience_ladder,
            "employers_hiring": list(pathway.employers_hiring),
            "learning_resources": list(pathway.learning_resources),
            "project_ideas": list(pathway.project_ideas),
        }


career_pathways_service = CareerPathwaysService()
