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
