"""
Career Insight Service

Analyzes job descriptions to generate career guides for students and job seekers.
Shows what a career entails by aggregating real job postings.

Pipeline:
1. COLLECT: Fetch all jobs for a given normalized title
2. COLLATE: Extract patterns (responsibilities, skills, tools, education)
3. SUMMARIZE: Generate a structured career guide
"""

import logging
import re
from collections import Counter
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import JobPost, Organization, TitleNorm

logger = logging.getLogger(__name__)


class CareerInsightService:
    def __init__(self, db: Session):
        self.db = db

        self.responsibility_patterns = [
            r"(?:responsibilities|duties|what you.{0,5}ll do|key tasks)(?:\s*:|\n)(.*?)(?=\n\n|\n[a-z]+:|requirements|qualifications|$)",
            r"(?:main duties|key responsibilities|role summary)(?:\s*:|\n)(.*?)(?=\n\n|\n[a-z]+:|requirements|qualifications|$)",
        ]

        self.requirement_patterns = [
            r"(?:requirements|qualifications|what you need|skills required)(?:\s*:|\n)(.*?)(?=\n\n|\n[a-z]+:|responsibilities|benefits|$)",
            r"(?:education|experience required|minimum requirements)(?:\s*:|\n)(.*?)(?=\n\n|\n[a-z]+:|responsibilities|benefits|$)",
        ]

        self.skill_keywords = {
            "programming": [
                "python",
                "java",
                "javascript",
                "typescript",
                "c++",
                "c#",
                "php",
                "ruby",
                "go",
                "rust",
                "swift",
                "kotlin",
            ],
            "data_analysis": [
                "sql",
                "excel",
                "tableau",
                "power bi",
                "pandas",
                "numpy",
                "r",
                "stata",
                "spss",
                "sas",
            ],
            "machine_learning": [
                "tensorflow",
                "pytorch",
                "scikit-learn",
                "ml",
                "ai",
                "deep learning",
                "nlp",
            ],
            "cloud": [
                "aws",
                "azure",
                "gcp",
                "docker",
                "kubernetes",
                "terraform",
                "cloud",
            ],
            "databases": [
                "mysql",
                "postgresql",
                "mongodb",
                "redis",
                "elasticsearch",
                "oracle",
                "sql server",
            ],
            "web_dev": [
                "react",
                "angular",
                "vue",
                "node.js",
                "django",
                "flask",
                "html",
                "css",
                "api",
            ],
            "project_management": [
                "agile",
                "scrum",
                "project management",
                "jira",
                "ms project",
                "pmp",
            ],
            "communication": [
                "communication",
                "presentation",
                "writing",
                "reporting",
                "stakeholder",
            ],
            "leadership": [
                "leadership",
                "team management",
                "mentoring",
                "supervision",
                "coaching",
            ],
            "finance": [
                "accounting",
                "financial analysis",
                "budgeting",
                "audit",
                "taxation",
                "quickbooks",
            ],
            "marketing": [
                "digital marketing",
                "seo",
                "social media",
                "content",
                "branding",
                "analytics",
            ],
            "design": [
                "photoshop",
                "illustrator",
                "figma",
                "ui/ux",
                "graphic design",
                "canva",
            ],
        }

        self.tool_patterns = [
            r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b",
        ]

        self.experience_patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|relevant)",
            r"(?:minimum|at least)\s*(\d+)\+?\s*(?:years?|yrs?)",
            r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience)?",
        ]

        self.education_keywords = [
            "bachelor",
            "master",
            "phd",
            "degree",
            "diploma",
            "certificate",
            "mba",
            "bsc",
            "ba",
            "msc",
            "ma",
            "undergraduate",
            "graduate",
        ]

    def collect_jobs_for_title(
        self, title: str, limit: int = 100, min_description_length: int = 200
    ) -> list[dict[str, Any]]:
        """
        Phase 1: COLLECT

        Fetch all jobs matching a normalized title.
        Returns raw job data for analysis.
        """
        normalized_title = self._normalize_search_title(title)

        query = (
            select(JobPost, TitleNorm, Organization)
            .outerjoin(TitleNorm, TitleNorm.id == JobPost.title_norm_id)
            .outerjoin(Organization, Organization.id == JobPost.org_id)
            .where(JobPost.is_active.is_(True))
            .where(
                (JobPost.description_raw.is_not(None))
                | (JobPost.description_clean.is_not(None))
            )
        )

        if normalized_title:
            query = query.where(
                (TitleNorm.canonical_title.ilike(f"%{normalized_title}%"))
                | (JobPost.title_raw.ilike(f"%{normalized_title}%"))
            )

        query = query.limit(limit)

        results = self.db.execute(query).all()

        jobs = []
        for jp, tn, org in results:
            description = jp.description_clean or jp.description_raw or ""
            if len(description) < min_description_length:
                continue

            jobs.append(
                {
                    "id": jp.id,
                    "title_raw": jp.title_raw,
                    "title_normalized": tn.canonical_title if tn else None,
                    "title_family": tn.family if tn else None,
                    "description": description,
                    "requirements": jp.requirements_raw or "",
                    "organization": org.name if org else None,
                    "seniority": jp.seniority,
                    "salary_min": jp.salary_min,
                    "salary_max": jp.salary_max,
                    "education": jp.education,
                }
            )

        logger.info(f"Collected {len(jobs)} jobs for title: {title}")
        return jobs

    def collate_insights(self, jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Phase 2: COLLATE

        Extract patterns from collected job descriptions.
        Aggregates responsibilities, skills, tools, experience, education.
        """
        if not jobs:
            return self._empty_collation()

        all_text = " ".join(
            j.get("description", "") + " " + j.get("requirements", "") for j in jobs
        )

        responsibilities = self._extract_responsibilities(jobs)
        skills = self._extract_skills(all_text)
        tools = self._extract_tools(all_text)
        experience = self._extract_experience_requirements(jobs)
        education = self._extract_education_requirements(jobs, all_text)
        salary = self._extract_salary_data(jobs)
        locations = self._extract_location_data(jobs)
        companies = self._extract_company_data(jobs)

        return {
            "job_count": len(jobs),
            "titles_found": list(
                set(j.get("title_raw") for j in jobs if j.get("title_raw"))
            )[:10],
            "responsibilities": responsibilities,
            "skills": skills,
            "tools": tools,
            "experience": experience,
            "education": education,
            "salary": salary,
            "locations": locations,
            "companies": companies,
        }

    def summarize_career(self, collated: dict[str, Any], title: str) -> dict[str, Any]:
        """
        Phase 3: SUMMARIZE

        Generate a structured career guide from collated insights.
        Human-readable summary for students.
        """
        responsibilities = collated.get("responsibilities", {})
        skills = collated.get("skills", {})
        tools = collated.get("tools", {})
        experience = collated.get("experience", {})
        education = collated.get("education", {})
        salary = collated.get("salary", {})

        summary = {
            "title": title.title(),
            "what_you_do": self._generate_what_you_do(responsibilities),
            "daily_tasks": self._extract_top_tasks(responsibilities),
            "skills_needed": self._format_skills_needed(skills),
            "tools_used": self._format_tools_used(tools),
            "education_required": self._summarize_education(education),
            "experience_needed": self._summarize_experience(experience),
            "salary_range": self._format_salary(salary),
            "career_outlook": self._generate_outlook(collated),
            "top_employers": collated.get("companies", {}).get("top_employers", [])[:5],
            "common_locations": collated.get("locations", {}).get("cities", [])[:5],
            "data_source": {
                "jobs_analyzed": collated.get("job_count", 0),
                "titles_found": collated.get("titles_found", []),
            },
        }

        return summary

    def get_full_career_insight(
        self, title: str, job_limit: int = 100
    ) -> dict[str, Any]:
        """
        Complete pipeline: Collect -> Collate -> Summarize
        """
        jobs = self.collect_jobs_for_title(title, limit=job_limit)

        if not jobs:
            return {
                "success": False,
                "error": f"No jobs found for title: {title}",
                "title": title,
                "summary": None,
                "raw_data": None,
            }

        collated = self.collate_insights(jobs)
        summary = self.summarize_career(collated, title)

        return {
            "success": True,
            "title": title,
            "summary": summary,
            "detailed_breakdown": collated,
        }

    def _normalize_search_title(self, title: str) -> str:
        """Normalize title for search"""
        title = title.lower().strip()

        stop_words = ["junior", "senior", "lead", "principal", "associate", "assistant"]
        for word in stop_words:
            title = re.sub(rf"\b{word}\b", "", title)

        return title.strip()

    def _extract_responsibilities(self, jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract and aggregate responsibilities across jobs"""
        responsibility_sentences = []

        for job in jobs:
            desc = job.get("description", "")

            for pattern in self.responsibility_patterns:
                matches = re.findall(pattern, desc, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    lines = re.split(r"[\n•\-\*]+", match)
                    for line in lines:
                        line = line.strip()
                        if len(line) > 20 and len(line) < 300:
                            responsibility_sentences.append(line)

        task_keywords = Counter()
        for sentence in responsibility_sentences:
            sentence_lower = sentence.lower()

            action_verbs = [
                "manage",
                "lead",
                "develop",
                "analyze",
                "create",
                "design",
                "implement",
                "coordinate",
                "monitor",
                "prepare",
                "review",
                "support",
                "conduct",
                "maintain",
                "ensure",
                "oversee",
                "build",
                "train",
                "collaborate",
                "research",
                "evaluate",
                "communicate",
                "plan",
                "execute",
                "optimize",
                "report",
            ]

            for verb in action_verbs:
                if verb in sentence_lower:
                    task_keywords[verb] += 1

        top_tasks = []
        for sentence in responsibility_sentences[:50]:
            sentence_lower = sentence.lower()
            if any(verb in sentence_lower for verb in list(task_keywords.keys())[:10]):
                clean_sentence = re.sub(r"^\s*[\-\*\•]\s*", "", sentence)
                clean_sentence = clean_sentence.strip()
                if clean_sentence and len(clean_sentence) > 30:
                    top_tasks.append(clean_sentence)

        unique_tasks = list(dict.fromkeys(top_tasks))[:20]

        return {
            "common_verbs": dict(task_keywords.most_common(10)),
            "example_tasks": unique_tasks,
            "total_extracted": len(responsibility_sentences),
        }

    def _extract_skills(self, text: str) -> dict[str, Any]:
        """Extract skills from text"""
        text_lower = text.lower()

        found_skills = {}
        for category, keywords in self.skill_keywords.items():
            category_skills = []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    count = text_lower.count(keyword.lower())
                    category_skills.append(
                        {
                            "skill": keyword,
                            "frequency": count,
                        }
                    )

            if category_skills:
                category_skills.sort(key=lambda x: x["frequency"], reverse=True)
                found_skills[category] = category_skills

        all_skills_flat = []
        for category, skills in found_skills.items():
            for skill in skills:
                all_skills_flat.append((skill["skill"], skill["frequency"], category))

        all_skills_flat.sort(key=lambda x: x[1], reverse=True)

        return {
            "by_category": found_skills,
            "top_10": [
                {"skill": s, "frequency": f, "category": c}
                for s, f, c in all_skills_flat[:10]
            ],
            "total_unique": len(all_skills_flat),
        }

    def _extract_tools(self, text: str) -> dict[str, Any]:
        """Extract tools/software mentioned"""
        known_tools = [
            "excel",
            "word",
            "powerpoint",
            "outlook",
            "teams",
            "zoom",
            "slack",
            "jira",
            "trello",
            "asana",
            "notion",
            "figma",
            "canva",
            "salesforce",
            "hubspot",
            "mailchimp",
            "google analytics",
            "tableau",
            "power bi",
            "looker",
            "metabase",
            "git",
            "github",
            "gitlab",
            "bitbucket",
            "vscode",
            "intellij",
            "photoshop",
            "illustrator",
            "premiere",
            "after effects",
            "sap",
            "oracle",
            "quickbooks",
            "xero",
            "sage",
        ]

        text_lower = text.lower()
        found_tools = []

        for tool in known_tools:
            if tool in text_lower:
                count = text_lower.count(tool)
                found_tools.append({"tool": tool.title(), "frequency": count})

        found_tools.sort(key=lambda x: x["frequency"], reverse=True)

        return {
            "software": found_tools[:15],
            "total": len(found_tools),
        }

    def _extract_experience_requirements(
        self, jobs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract experience requirements"""
        years_required = []

        for job in jobs:
            text = job.get("description", "") + " " + job.get("requirements", "")

            for pattern in self.experience_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        if match[0] and match[1]:
                            years_required.append(int(match[0]))
                            years_required.append(int(match[1]))
                        elif match[0]:
                            years_required.append(int(match[0]))
                    else:
                        years_required.append(int(match))

        if not years_required:
            return {
                "min_years": None,
                "max_years": None,
                "average": None,
                "distribution": {},
            }

        distribution = Counter(years_required)

        return {
            "min_years": min(years_required),
            "max_years": max(years_required),
            "average": round(sum(years_required) / len(years_required), 1),
            "distribution": dict(distribution.most_common(10)),
            "most_common": distribution.most_common(1)[0][0] if distribution else None,
        }

    def _extract_education_requirements(
        self, jobs: list[dict[str, Any]], text: str
    ) -> dict[str, Any]:
        """Extract education requirements"""
        text_lower = text.lower()

        education_found = {}

        education_levels = {
            "phd": ["phd", "doctorate", "doctoral"],
            "masters": ["master", "msc", "ma", "mba", "postgraduate"],
            "bachelors": ["bachelor", "bsc", "ba", "undergraduate", "degree"],
            "diploma": ["diploma", "higher national diploma", "hnd"],
            "certificate": [
                "certificate",
                "certification",
                "professional qualification",
            ],
        }

        for level, keywords in education_levels.items():
            for keyword in keywords:
                if keyword in text_lower:
                    education_found[level] = education_found.get(
                        level, 0
                    ) + text_lower.count(keyword)

        fields = []
        field_patterns = [
            r"bachelor[^.]*?(?:in|of)\s+([^.,]+)",
            r"degree\s+in\s+([^.,]+)",
            r"master[^.]*?(?:in|of)\s+([^.,]+)",
        ]

        for pattern in field_patterns:
            matches = re.findall(pattern, text_lower)
            fields.extend(matches)

        field_counter = Counter(f.strip() for f in fields if len(f.strip()) > 3)

        return {
            "levels": education_found,
            "common_fields": dict(field_counter.most_common(10)),
        }

    def _extract_salary_data(self, jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract salary information"""
        salaries = []

        for job in jobs:
            salary_min = job.get("salary_min")
            if salary_min and salary_min > 0:
                salaries.append(
                    {
                        "min": job["salary_min"],
                        "max": job.get("salary_max") or job["salary_min"],
                    }
                )

        if not salaries:
            return {"available": False, "min": None, "max": None, "median": None}

        all_mins = [s["min"] for s in salaries]
        all_maxs = [s["max"] for s in salaries]

        return {
            "available": True,
            "min": min(all_mins),
            "max": max(all_maxs),
            "median": sorted(all_mins)[len(all_mins) // 2],
            "sample_size": len(salaries),
        }

    def _extract_location_data(self, jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract location data - placeholder for now"""
        return {
            "cities": ["Nairobi", "Mombasa", "Kisumu"],
            "remote_available": True,
        }

    def _extract_company_data(self, jobs: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract company/employer data"""
        companies = [j.get("organization") for j in jobs if j.get("organization")]
        company_counter = Counter(companies)

        return {
            "unique_employers": len(set(companies)),
            "top_employers": [c for c, _ in company_counter.most_common(10)],
            "total_postings": len(companies),
        }

    def _generate_what_you_do(self, responsibilities: dict) -> str:
        """Generate 'What You Do' summary"""
        verbs = responsibilities.get("common_verbs", {})
        tasks = responsibilities.get("example_tasks", [])

        if not verbs and not tasks:
            return "Information not available from current job postings."

        top_verbs = list(verbs.keys())[:5]

        summaries = {
            "manage": "managing teams and projects",
            "lead": "leading initiatives and teams",
            "develop": "developing solutions and products",
            "analyze": "analyzing data and trends",
            "create": "creating content and materials",
            "design": "designing systems and processes",
            "implement": "implementing strategies and solutions",
            "coordinate": "coordinating activities and resources",
            "monitor": "monitoring performance and progress",
            "prepare": "preparing reports and documentation",
            "review": "reviewing processes and outputs",
            "support": "supporting teams and stakeholders",
            "conduct": "conducting research and analysis",
            "maintain": "maintaining systems and relationships",
            "ensure": "ensuring quality and compliance",
            "oversee": "overseeing operations and teams",
            "build": "building products and relationships",
            "train": "training teams and users",
            "collaborate": "collaborating with cross-functional teams",
            "research": "researching markets and solutions",
        }

        activities = []
        for verb in top_verbs:
            if verb in summaries:
                activities.append(summaries[verb])

        if activities:
            return f"As a {self._title_placeholder}, you will be responsible for {', '.join(activities[:-1])}{' and ' if len(activities) > 1 else ''}{activities[-1] if activities else 'various tasks'}."

        return "Information not available from current job postings."

    _title_placeholder = "[this role]"

    def _extract_top_tasks(self, responsibilities: dict) -> list[str]:
        """Extract top daily tasks"""
        tasks = responsibilities.get("example_tasks", [])
        return tasks[:8]

    def _format_skills_needed(self, skills: dict) -> dict[str, Any]:
        """Format skills section"""
        return {
            "top_skills": [s["skill"] for s in skills.get("top_10", [])[:5]],
            "by_category": {
                cat: [s["skill"] for s in skils[:3]]
                for cat, skils in skills.get("by_category", {}).items()
            },
            "total_found": skills.get("total_unique", 0),
        }

    def _format_tools_used(self, tools: dict) -> list[str]:
        """Format tools section"""
        return [t["tool"] for t in tools.get("software", [])[:10]]

    def _summarize_education(self, education: dict) -> dict[str, Any]:
        """Summarize education requirements"""
        levels = education.get("levels", {})
        fields = education.get("common_fields", {})

        if not levels:
            return {
                "minimum": "Not specified",
                "preferred": [],
                "fields": [],
            }

        sorted_levels = sorted(levels.items(), key=lambda x: x[1], reverse=True)

        level_names = {
            "phd": "PhD/Doctorate",
            "masters": "Master's Degree",
            "bachelors": "Bachelor's Degree",
            "diploma": "Diploma",
            "certificate": "Certificate",
        }

        return {
            "minimum": level_names.get(sorted_levels[-1][0], "Not specified")
            if sorted_levels
            else "Not specified",
            "preferred": [
                level_names.get(item[0], item[0]) for item in sorted_levels[:2]
            ],
            "fields": list(fields.keys())[:5],
        }

    def _summarize_experience(self, experience: dict) -> dict[str, Any]:
        """Summarize experience requirements"""
        if not experience.get("average"):
            return {
                "years_required": "Not specified",
                "level": "Entry level to Experienced",
            }

        avg = experience["average"]
        most_common = experience.get("most_common", avg)

        if most_common <= 1:
            level = "Entry level (0-1 years)"
        elif most_common <= 3:
            level = "Junior (1-3 years)"
        elif most_common <= 5:
            level = "Mid-level (3-5 years)"
        elif most_common <= 8:
            level = "Senior (5-8 years)"
        else:
            level = "Expert (8+ years)"

        return {
            "years_required": f"{experience.get('min_years', 0)}-{experience.get('max_years', 'many')} years",
            "average": f"{avg} years",
            "most_common": f"{most_common} years",
            "level": level,
        }

    def _format_salary(self, salary: dict) -> dict[str, Any]:
        """Format salary information"""
        if not salary.get("available"):
            return {
                "available": False,
                "range": "Not specified",
                "note": "Salary data not commonly posted in job listings",
            }

        def format_kes(amount):
            if amount >= 1000000:
                return f"KES {amount / 1000000:.1f}M"
            elif amount >= 1000:
                return f"KES {amount / 1000:.0f}K"
            return f"KES {amount}"

        return {
            "available": True,
            "range": f"{format_kes(salary['min'])} - {format_kes(salary['max'])}",
            "median": format_kes(salary.get("median", salary["min"])),
            "sample_size": salary.get("sample_size", 0),
        }

    def _generate_outlook(self, collated: dict) -> str:
        """Generate career outlook summary"""
        job_count = collated.get("job_count", 0)
        companies = collated.get("companies", {}).get("unique_employers", 0)

        if job_count > 50:
            demand = "high"
        elif job_count > 20:
            demand = "moderate"
        else:
            demand = "specialized"

        outlooks = {
            "high": f"This role shows strong demand with {job_count} active postings from {companies} employers. Good opportunities for growth.",
            "moderate": f"Moderate demand with {job_count} active postings. Opportunities exist across {companies} employers.",
            "specialized": f"Specialized role with {job_count} postings. May require specific skills or experience.",
        }

        return outlooks.get(demand, "Career outlook not available.")

    def _empty_collation(self) -> dict[str, Any]:
        """Return empty collation structure"""
        return {
            "job_count": 0,
            "titles_found": [],
            "responsibilities": {
                "common_verbs": {},
                "example_tasks": [],
                "total_extracted": 0,
            },
            "skills": {"by_category": {}, "top_10": [], "total_unique": 0},
            "tools": {"software": [], "total": 0},
            "experience": {
                "min_years": None,
                "max_years": None,
                "average": None,
                "distribution": {},
            },
            "education": {"levels": {}, "common_fields": {}},
            "salary": {"available": False, "min": None, "max": None, "median": None},
            "locations": {"cities": [], "remote_available": False},
            "companies": {
                "unique_employers": 0,
                "top_employers": [],
                "total_postings": 0,
            },
        }
