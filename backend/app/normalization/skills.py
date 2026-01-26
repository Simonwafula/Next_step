from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .skill_mapping import canonicalize_skill, custom_skills
from .skillner_adapter import extract_skillner_matches

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


def _skillner_enabled() -> bool:
    return os.getenv("SKILL_EXTRACTOR_MODE", "skillner").lower() in {
        "skillner",
        "hybrid",
    }


def _pattern_enabled() -> bool:
    return os.getenv("SKILL_EXTRACTOR_MODE", "skillner").lower() in {
        "patterns",
        "hybrid",
    }


def _build_word_boundary_pattern(term: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


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


def _upsert_skill_result(
    results: Dict[str, Dict[str, Any]],
    skill: str,
    confidence: float,
    evidence: str,
    start: int | None,
    end: int | None,
    source: str,
) -> None:
    if not skill:
        return
    existing = results.get(skill)
    if not existing or confidence > existing["confidence"]:
        results[skill] = {
            "value": skill,
            "confidence": confidence,
            "evidence": evidence,
            "start": start,
            "end": end,
            "source": source,
        }


def _extract_pattern_matches(text: str) -> List[Dict[str, Any]]:
    matches = []
    lowered = text.lower()
    for skill, needles in SKILL_PATTERNS.items():
        for needle in needles:
            needle_clean = needle.strip()
            if not needle_clean:
                continue
            match = re.search(re.escape(needle_clean), lowered)
            if match:
                matches.append(
                    {
                        "skill": skill,
                        "confidence": 0.7,
                        "evidence": lowered[match.start() : match.end()],
                        "start": match.start(),
                        "end": match.end(),
                        "source": "pattern",
                    }
                )
                break
    return matches


def _extract_custom_matches(text: str) -> List[Dict[str, Any]]:
    matches = []
    lowered = text.lower()
    for entry in custom_skills():
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        terms = [name] + [alias for alias in entry.get("aliases", []) if alias]
        for term in terms:
            pattern = _build_word_boundary_pattern(term)
            match = pattern.search(lowered)
            if not match:
                continue
            matches.append(
                {
                    "skill": name.lower(),
                    "confidence": 0.75,
                    "evidence": lowered[match.start() : match.end()],
                    "start": match.start(),
                    "end": match.end(),
                    "source": "custom",
                }
            )
            break
    return matches


def extract_skills_detailed(text: str) -> Dict[str, Dict[str, Any]]:
    """Return skill extraction details with value/confidence/evidence."""
    if not text:
        return {}
    results: Dict[str, Dict[str, Any]] = {}

    if _skillner_enabled():
        for match in extract_skillner_matches(text):
            canonical = canonicalize_skill(match["skill"])
            _upsert_skill_result(
                results,
                canonical,
                float(match["confidence"]),
                match.get("evidence", ""),
                match.get("start"),
                match.get("end"),
                match.get("source", "skillner"),
            )

    if _pattern_enabled():
        for match in _extract_pattern_matches(text):
            canonical = canonicalize_skill(match["skill"])
            _upsert_skill_result(
                results,
                canonical,
                float(match["confidence"]),
                match.get("evidence", ""),
                match.get("start"),
                match.get("end"),
                match.get("source", "pattern"),
            )

    for match in _extract_custom_matches(text):
        canonical = canonicalize_skill(match["skill"])
        _upsert_skill_result(
            results,
            canonical,
            float(match["confidence"]),
            match.get("evidence", ""),
            match.get("start"),
            match.get("end"),
            match.get("source", "custom"),
        )

    for phrase in extract_skill_phrases(text):
        canonical = canonicalize_skill(phrase)
        idx = text.lower().find(phrase.lower())
        start = idx if idx >= 0 else None
        end = (idx + len(phrase)) if idx >= 0 else None
        _upsert_skill_result(
            results,
            canonical,
            0.65,
            phrase.lower(),
            start,
            end,
            "section_phrase",
        )

    return results


def extract_skills(text: str) -> list[str]:
    detailed = extract_skills_detailed(text)
    ordered = sorted(
        detailed.items(), key=lambda item: item[1]["confidence"], reverse=True
    )
    return [skill for skill, _ in ordered]


def extract_and_normalize_skills(text: str) -> dict:
    """Return a mapping of skill -> confidence for given text."""
    skills = extract_skills_detailed(text)
    return {name: info["confidence"] for name, info in skills.items()}


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
