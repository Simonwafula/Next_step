# Very lightweight patterns; extend with NLP later
import re

SKILL_PATTERNS = {
    "sql": [" sql", "postgres", "mysql", "sqlserver", "tsql", "sqlite"],
    "python": [" python", "pandas", "numpy", "scikit-learn", "sklearn"],
    "r": [" r ", "rstudio", "tidyverse", "ggplot"],
    "stata": [" stata", "spss"],
    "excel": [" excel", "vlookup", "pivot", "powerpivot"],
    "power bi": [" power bi", "dax", "power query"],
    "tableau": [" tableau"],
    "data analysis": [" data analysis", "data analytics", "statistical analysis"],
    "machine learning": [" machine learning", "ml ", "ml,", "ml."],
    "data visualization": [" data visualization", "dashboards"],
    "java": [" java", "spring"],
    "javascript": [" javascript", "node.js", "nodejs", "react", "vue", "angular"],
    "c#": [" c#", ".net", "dotnet"],
    "php": [" php", "laravel"],
    "html/css": [" html", " css", "bootstrap"],
    "aws": [" aws", "amazon web services"],
    "azure": [" azure"],
    "gcp": [" gcp", "google cloud"],
    "docker": [" docker", "containers"],
    "kubernetes": [" kubernetes", "k8s"],
    "project management": [" project management", "pmp", "prince2"],
    "agile": [" agile", "scrum", "kanban"],
    "sales": [" sales", "business development", "account management"],
    "marketing": [" marketing", "digital marketing", "seo", "content marketing"],
    "customer service": [" customer service", "client service", "call center"],
    "accounting": [" accounting", "bookkeeping", "ifrs"],
    "finance": [" finance", "financial analysis", "budgeting"],
    "hr": [" human resources", "hr", "talent acquisition", "recruitment"],
    "monitoring & evaluation": [
        " m&e",
        " monitoring and evaluation",
        " results framework",
        " logframe",
    ],
    "procurement": [" procurement", "supply chain", "tendering"],
    "logistics": [" logistics", "inventory", "warehouse"],
    "healthcare": [" nursing", "clinical", "public health"],
    "teaching": [" teaching", "lesson planning", "curriculum"],
    "communication": [" communication", "report writing", "presentation skills"],
}

SECTION_MARKERS = [
    "skills",
    "requirements",
    "qualifications",
    "competencies",
]


def extract_skill_phrases(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    found = []
    for marker in SECTION_MARKERS:
        if marker in lowered:
            pattern = rf"{marker}\s*[:\-]\s*(.+?)(?=responsibilities|duties|how to apply|application|$)"
            match = re.search(pattern, lowered, re.IGNORECASE)
            if not match:
                continue
            chunk = match.group(1)
            parts = re.split(r"[;•\n,/]", chunk)
            for part in parts:
                cleaned = re.sub(r"[^a-z0-9\+\#\&\s\-]", "", part).strip()
                if 2 < len(cleaned) <= 40 and cleaned not in found:
                    found.append(cleaned)
    return found


def extract_skills(text: str) -> list[str]:
    t = (text or "").lower()
    found = []
    for skill, needles in SKILL_PATTERNS.items():
        if any(n in t for n in needles):
            found.append(skill)

    found.extend(s for s in extract_skill_phrases(text) if s not in found)
    return found


def extract_and_normalize_skills(text: str) -> dict:
    """Return a mapping of skill -> confidence for given text."""
    skills = extract_skills(text)
    return {s: 0.9 for s in skills}


def update_skill_mappings(new_mappings: dict) -> None:
    """Merge new skill patterns into SKILL_PATTERNS."""
    for k, needles in (new_mappings or {}).items():
        if k in SKILL_PATTERNS:
            existing = set(SKILL_PATTERNS[k])
            existing.update(
                needles if isinstance(needles, (list, tuple)) else [needles]
            )
            SKILL_PATTERNS[k] = list(existing)
        else:
            SKILL_PATTERNS[k] = (
                list(needles) if isinstance(needles, (list, tuple)) else [needles]
            )
