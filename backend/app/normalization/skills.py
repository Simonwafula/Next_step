# Very lightweight patterns; extend with NLP later
SKILL_PATTERNS = {
    "sql": [" sql", "postgres", "mysql", "sqlserver", "tsql"],
    "python": [" python", "pandas", "numpy", "scikit-learn"],
    "r": [" r ", "rstudio", "tidyverse", "ggplot"],
    "stata": [" stata"],
    "excel": [" excel", "vlookup", "pivot"],
    "power bi": [" power bi", "dax", "power query"],
    "tableau": [" tableau"],
    "monitoring & evaluation": [" m&e", " monitoring and evaluation", " results framework", " logframe"],
}

def extract_skills(text: str) -> list[str]:
    t = (text or "").lower()
    found = []
    for skill, needles in SKILL_PATTERNS.items():
        if any(n in t for n in needles):
            found.append(skill)
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
            existing.update(needles if isinstance(needles, (list, tuple)) else [needles])
            SKILL_PATTERNS[k] = list(existing)
        else:
            SKILL_PATTERNS[k] = list(needles) if isinstance(needles, (list, tuple)) else [needles]
