TITLE_ALIASES = {
    "data analyst": [
        "data ninja",
        "bi analyst",
        "analytics associate",
        "m&e officer (data)",
        "business intelligence analyst",
        "data scientist junior",
        "quantitative analyst",
    ],
    "data scientist": [
        "machine learning engineer",
        "ai specialist",
        "ml engineer",
        "data science specialist",
    ],
    "research analyst": [
        "research assistant",
        "insight analyst",
        "market researcher",
        "research associate",
    ],
    "biostatistics assistant": [
        "biostat assistant",
        "clinical data assistant",
        "epidemiology assistant",
    ],
    "monitoring & evaluation officer": [
        "m&e officer",
        "m and e officer",
        "monitoring and evaluation officer",
        "program evaluation specialist",
    ],
    "software developer": [
        "programmer",
        "software engineer",
        "web developer",
        "full stack developer",
        "backend developer",
        "frontend developer",
    ],
    "systems administrator": [
        "it administrator",
        "network administrator",
        "devops engineer",
        "infrastructure engineer",
    ],
    "cybersecurity analyst": [
        "information security analyst",
        "security specialist",
        "cyber security officer",
    ],
    "database administrator": ["dba", "database manager", "data engineer"],
    "financial analyst": [
        "finance analyst",
        "investment analyst",
        "budget analyst",
        "financial planning analyst",
    ],
    "accountant": [
        "accounting clerk",
        "bookkeeper",
        "accounts assistant",
        "finance officer",
    ],
    "auditor": [
        "internal auditor",
        "external auditor",
        "compliance officer",
        "risk analyst",
    ],
    "credit analyst": ["loan officer", "credit officer", "risk assessment specialist"],
    "marketing coordinator": [
        "marketing assistant",
        "digital marketing specialist",
        "marketing officer",
    ],
    "communications specialist": [
        "communications officer",
        "pr specialist",
        "public relations officer",
    ],
    "content creator": [
        "content writer",
        "copywriter",
        "social media manager",
        "digital content specialist",
    ],
    "hr generalist": [
        "human resources officer",
        "hr coordinator",
        "people operations specialist",
    ],
    "recruiter": [
        "talent acquisition specialist",
        "recruitment consultant",
        "hiring coordinator",
    ],
    "training coordinator": ["learning and development specialist", "training officer"],
    "clinical research coordinator": [
        "clinical research associate",
        "clinical trials coordinator",
    ],
    "health program officer": ["public health officer", "health promotion specialist"],
    "medical assistant": ["clinical assistant", "healthcare assistant"],
    "program coordinator": [
        "project coordinator",
        "program assistant",
        "program officer",
    ],
    "training specialist": ["trainer", "facilitator", "capacity building officer"],
    "policy analyst": [
        "economist (policy)",
        "policy researcher",
        "government analyst",
        "public policy specialist",
    ],
    "program officer": ["development officer", "project officer", "field officer"],
    "sales representative": [
        "sales executive",
        "business development representative",
        "account executive",
    ],
    "business analyst": [
        "business systems analyst",
        "process analyst",
        "operations analyst",
    ],
    "operations coordinator": [
        "operations assistant",
        "logistics coordinator",
        "supply chain coordinator",
    ],
    "project manager": ["project coordinator", "program manager", "project lead"],
}

DEGREE_TO_CAREERS = {
    "economics": [
        "data analyst",
        "financial analyst",
        "policy analyst",
        "research analyst",
        "business analyst",
    ],
    "statistics": [
        "data analyst",
        "data scientist",
        "biostatistics assistant",
        "research analyst",
        "business analyst",
    ],
    "mathematics": [
        "data analyst",
        "data scientist",
        "financial analyst",
        "research analyst",
        "software developer",
    ],
    "computer science": [
        "software developer",
        "data scientist",
        "systems administrator",
        "cybersecurity analyst",
        "database administrator",
    ],
    "information technology": [
        "software developer",
        "systems administrator",
        "cybersecurity analyst",
        "database administrator",
    ],
    "business administration": [
        "business analyst",
        "project manager",
        "hr generalist",
        "marketing coordinator",
        "operations coordinator",
    ],
    "finance": ["financial analyst", "accountant", "auditor", "credit analyst"],
    "accounting": ["accountant", "auditor", "financial analyst"],
    "marketing": [
        "marketing coordinator",
        "communications specialist",
        "content creator",
        "business analyst",
    ],
    "psychology": [
        "hr generalist",
        "recruiter",
        "training coordinator",
        "research analyst",
    ],
    "public health": [
        "health program officer",
        "monitoring & evaluation officer",
        "research analyst",
        "biostatistics assistant",
    ],
    "medicine": [
        "clinical research coordinator",
        "health program officer",
        "medical assistant",
    ],
    "nursing": [
        "clinical research coordinator",
        "health program officer",
        "medical assistant",
    ],
    "education": ["training specialist", "program coordinator", "training coordinator"],
    "international relations": [
        "policy analyst",
        "program officer",
        "research analyst",
    ],
    "political science": ["policy analyst", "program officer", "research analyst"],
    "sociology": [
        "research analyst",
        "program officer",
        "monitoring & evaluation officer",
    ],
    "development studies": [
        "program officer",
        "monitoring & evaluation officer",
        "policy analyst",
        "research analyst",
    ],
    "journalism": [
        "communications specialist",
        "content creator",
        "marketing coordinator",
    ],
    "communications": [
        "communications specialist",
        "content creator",
        "marketing coordinator",
    ],
    "engineering": [
        "software developer",
        "systems administrator",
        "project manager",
        "data analyst",
    ],
}


def classify_seniority(title: str) -> str:
    """
    Classify seniority level from job title.

    Returns one of: entry, mid, senior, manager, executive
    """
    t = (title or "").lower().strip()

    if any(
        keyword in t
        for keyword in [
            "ceo",
            "cto",
            "cfo",
            "coo",
            "cmo",
            "chief ",
            "executive director",
            "managing director",
            "president",
            "founder",
            "co-founder",
        ]
    ):
        return "executive"

    if any(
        keyword in t
        for keyword in [
            "manager",
            "head of",
            "director",
            "vp ",
            "vice president",
            "country director",
            "regional director",
        ]
    ):
        return "manager"

    if any(
        keyword in t
        for keyword in [
            "senior",
            " sr ",
            "sr.",
            "lead ",
            "principal",
            "staff ",
            "expert",
        ]
    ):
        return "senior"

    if any(
        keyword in t
        for keyword in [
            "junior",
            "entry",
            "intern",
            "trainee",
            "graduate",
            "assistant",
            "intern ",
        ]
    ):
        return "entry"

    if (
        any(
            keyword in t
            for keyword in [
                "officer",
                "coordinator",
                "specialist",
                "associate",
                "analyst",
                "engineer",
                "developer",
            ]
        )
        and "senior" not in t
        and "lead" not in t
        and "principal" not in t
    ):
        return "mid"

    return "mid"


def normalize_title(raw: str) -> tuple[str, str]:
    """Normalize job title to family and canonical form"""
    r = (raw or "").lower().strip()

    for canon, aliases in TITLE_ALIASES.items():
        if canon in r or any(alias.lower() in r for alias in aliases):
            if any(
                keyword in canon
                for keyword in ["data", "research", "analyst", "statistics"]
            ):
                return ("data_analytics", canon)
            elif any(
                keyword in canon
                for keyword in [
                    "software",
                    "developer",
                    "engineer",
                    "systems",
                    "cyber",
                    "database",
                ]
            ):
                return ("technology", canon)
            elif any(
                keyword in canon
                for keyword in ["financial", "accountant", "auditor", "credit"]
            ):
                return ("finance", canon)
            elif any(
                keyword in canon
                for keyword in ["marketing", "communications", "content"]
            ):
                return ("marketing_communications", canon)
            elif any(keyword in canon for keyword in ["hr", "recruiter", "training"]):
                return ("human_resources", canon)
            elif any(keyword in canon for keyword in ["clinical", "health", "medical"]):
                return ("healthcare", canon)
            elif any(keyword in canon for keyword in ["policy", "program officer"]):
                return ("government_policy", canon)
            elif any(keyword in canon for keyword in ["sales", "business"]):
                return ("business_development", canon)
            elif any(
                keyword in canon for keyword in ["operations", "project", "logistics"]
            ):
                return ("operations", canon)
            else:
                return ("other", canon)

    return ("other", r)


def normalize_title_with_seniority(raw: str) -> tuple[str, str, str]:
    """
    Normalize job title with seniority classification.

    Returns: (family, canonical_title, seniority)

    Example:
        "Senior Data Analyst" -> ("data_analytics", "data analyst", "senior")
        "Junior Software Developer" -> ("technology", "software developer", "entry")
    """
    family, canonical = normalize_title(raw)
    seniority = classify_seniority(raw)
    return (family, canonical, seniority)


def get_careers_for_degree(degree: str) -> list[str]:
    """Get relevant career paths for a given degree"""
    degree_lower = degree.lower().strip()

    if degree_lower in DEGREE_TO_CAREERS:
        return DEGREE_TO_CAREERS[degree_lower]

    for deg, careers in DEGREE_TO_CAREERS.items():
        if deg in degree_lower or degree_lower in deg:
            return careers

    return [
        "program coordinator",
        "research analyst",
        "business analyst",
        "operations coordinator",
    ]


def explain_title_match(
    original: str, normalized_family: str, normalized_title: str
) -> str:
    """Generate explanation for why a title was normalized"""
    if normalized_family == "other":
        return f"Treating '{original}' as general role"

    family_descriptions = {
        "data_analytics": "data and analytics",
        "technology": "technology and engineering",
        "finance": "finance and accounting",
        "marketing_communications": "marketing and communications",
        "human_resources": "human resources",
        "healthcare": "healthcare and medical",
        "government_policy": "government and policy",
        "business_development": "business development and sales",
        "operations": "operations and project management",
    }

    family_desc = family_descriptions.get(normalized_family, normalized_family)
    return f"Mapped '{original}' to {family_desc} family as '{normalized_title}'"


def update_title_mappings(new_mappings: dict) -> None:
    """Merge new title alias mappings into the existing TITLE_ALIASES.

    This is a lightweight helper used by learning pipelines to persist
    discovered aliases during tests.
    """
    for k, v in (new_mappings or {}).items():
        if k in TITLE_ALIASES:
            existing = set(TITLE_ALIASES[k])
            existing.update(v if isinstance(v, (list, tuple)) else [v])
            TITLE_ALIASES[k] = list(existing)
        else:
            TITLE_ALIASES[k] = list(v) if isinstance(v, (list, tuple)) else [v]
