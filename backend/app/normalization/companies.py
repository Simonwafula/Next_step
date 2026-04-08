import re

# Common company suffixes to strip for better matching
COMPANY_SUFFIXES = [
    " ltd",
    " limited",
    " llc",
    " inc",
    " incorporated",
    " pvt",
    " private",
    " group",
    " corp",
    " corporation",
]

COMPANY_PREFIX_PATTERNS = [
    r"^jobs?\s+at\s+",
    r"^vacancies\s+at\s+",
    r"^careers?\s+at\s+",
    r"^job opportunities\s+at\s+",
    r"^current opportunities\s+at\s+",
    r"^positions?\s+at\s+",
    r"^openings?\s+at\s+",
]

COMPANY_ARTIFACT_PATTERNS = [
    r"^read more about this company$",
    r"^company profile$",
    r"^about the company$",
    r"^our vision is to be .+$",
]


def normalize_company_name(raw: str) -> str:
    """
    Standardizes company names by:
    1. Lowercasing
    2. Stripping common suffixes
    3. Trimming whitespace
    """
    if not raw:
        return ""

    # Lowercase and strip whitespace
    name = re.sub(r"\s+", " ", raw.lower()).strip()

    for pattern in COMPANY_ARTIFACT_PATTERNS:
        if re.fullmatch(pattern, name, flags=re.IGNORECASE):
            return ""

    for pattern in COMPANY_PREFIX_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # Remove common suffixes
    for suffix in COMPANY_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
            break

    # Remove any trailing " & co", " and co"
    name = re.sub(r"\s+(and|&)\s+co\.?$", "", name)
    name = re.sub(r"[^\w\s&+.-]", "", name)
    name = re.sub(r"\s+", " ", name).strip(" .,-")

    if not name:
        return ""

    # Handle known aliases (can be expanded)
    ALIASES = {
        "kcb": "kcb bank",
        "equity": "equity bank",
        "safari com": "safaricom",
        "co-operative bank": "co-op bank",
    }

    if name in ALIASES:
        name = ALIASES[name]

    return name.title()  # Return title case for cleaner storage
