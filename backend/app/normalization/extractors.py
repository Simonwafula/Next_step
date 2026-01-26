import re


def extract_education_level(text: str) -> str | None:
    """
    Detects the highest education level required in the job description.
    Returns: 'PhD', 'Master', 'Bachelor', 'Diploma', 'High School', or None.
    """
    if not text:
        return None

    t = text.lower()

    # Priority order: PhD -> Master -> Bachelor -> Diploma -> High School
    if any(p in t for p in ["phd", "doctorate", "ph.d"]):
        return "PhD"
    if any(m in t for m in ["master's", "masters", "msc", "mba", "ma degree"]):
        return "Master"
    if any(
        b in t
        for b in [
            "bachelor's",
            "bachelors",
            "degree",
            "university graduate",
            "bsc",
            "ba degree",
        ]
    ):
        return "Bachelor"
    if any(d in t for d in ["diploma", "higher national diploma", "hnd"]):
        return "Diploma"
    if any(h in t for h in ["high school", "kcse", "school leaver"]):
        return "High School"

    return None


def extract_experience_years(text: str) -> int | None:
    """
    Extracts required years of experience using regex.
    Returns the minimum number of years found, or None.
    """
    if not text:
        return None

    # Patterns: "3+ years", "at least 5 years", "3 to 5 years", "min 2 years"
    patterns = [
        r"(\d+)\s*\+?\s*years?",
        r"at least\s*(\d+)\s*years?",
        r"minimum\s*(?:of)?\s*(\d+)\s*years?",
        r"(\d+)\s*-\s*\d+\s*years?",
        r"min\s*(\d+)\s*years?",
    ]

    all_years = []
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        for m in matches:
            all_years.append(int(m))

    if all_years:
        return min(all_years)  # Usually the "minimum" requirement

    return None


def classify_seniority(title: str, experience_years: int | None) -> str:
    """
    Classifies seniority based on title keywords and years of experience.
    """
    t = (title or "").lower()

    # High priority keywords in title
    if any(x in t for x in ["executive", "c-level", "chief", "vp", "vice president"]):
        return "Executive"
    if any(x in t for x in ["director", "head of", "principal"]):
        return "Executive"
    if any(x in t for x in ["senior", "lead", "sr.", "sr "]):
        return "Senior"
    if any(x in t for x in ["manager", "supervisor"]):
        return "Senior"  # Often counts as senior/management
    if any(
        x in t
        for x in ["junior", "entry", "intern", "graduate", "trainee", "assistant"]
    ):
        return "Entry"

    # Experience based fallback
    if experience_years is not None:
        if experience_years >= 8:
            return "Executive"
        if experience_years >= 5:
            return "Senior"
        if experience_years >= 2:
            return "Mid-Level"
        return "Entry"

    return "Mid-Level"  # Default fallback


def extract_task_statements(text: str) -> list[dict]:
    """
    Extract task statements with confidence and evidence snippets.
    Returns a list of dicts: {"value": str, "confidence": float, "evidence": str}.
    """
    if not text:
        return []

    verbs = {
        "analyze",
        "build",
        "design",
        "develop",
        "maintain",
        "manage",
        "coordinate",
        "deliver",
        "monitor",
        "support",
        "implement",
        "optimize",
        "report",
        "review",
        "test",
        "collaborate",
    }

    candidates = []
    for line in text.splitlines():
        line = line.strip(" \t-*•")
        if not line:
            continue
        if len(line) < 10:
            continue
        lower = line.lower()
        confidence = 0.3
        if any(lower.startswith(verb) for verb in verbs):
            confidence += 0.3
        if any(f" {verb} " in lower for verb in verbs):
            confidence += 0.2
        if len(line) > 120:
            confidence -= 0.1
        confidence = max(0.2, min(0.9, confidence))
        candidates.append(
            {
                "value": line,
                "confidence": round(confidence, 2),
                "evidence": line[:200],
            }
        )

    return candidates
