from __future__ import annotations

import re
from typing import Any, Dict, List

from .education_mapping import education_levels


def _word_boundary_pattern(term: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


def _find_first_match(text: str, term: str) -> re.Match | None:
    pattern = _word_boundary_pattern(term)
    return pattern.search(text)


def _score_modifier(window: str) -> float:
    signal_words = {"required", "minimum", "must", "mandatory", "need", "preferred"}
    lowered = window.lower()
    return 0.1 if any(word in lowered for word in signal_words) else 0.0


def extract_education_detailed(text: str) -> Dict[str, Any] | None:
    if not text:
        return None

    candidates: List[Dict[str, Any]] = []
    lowered = text.lower()
    for level in education_levels():
        value = str(level.get("value", "")).strip()
        if not value:
            continue
        rank = int(level.get("rank", 0))
        aliases = level.get("aliases", [])
        for alias in aliases:
            if not alias:
                continue
            match = _find_first_match(lowered, alias)
            if not match:
                continue
            window = lowered[max(0, match.start() - 40) : match.end() + 40]
            confidence = 0.55 + (rank * 0.08) + _score_modifier(window)
            confidence = min(confidence, 0.95)
            candidates.append(
                {
                    "value": value.title() if value != "phd" else "PhD",
                    "confidence": round(confidence, 2),
                    "evidence": text[match.start() : match.end()],
                    "start": match.start(),
                    "end": match.end(),
                    "source": "education_mapping",
                    "rank": rank,
                }
            )

    if not candidates:
        return None

    candidates.sort(key=lambda c: (c["rank"], c["confidence"]), reverse=True)
    result = candidates[0]
    result.pop("rank", None)
    return result


def extract_education_level(text: str) -> str | None:
    """Detects the highest education level required in the job description."""
    detailed = extract_education_detailed(text)
    return detailed["value"] if detailed else None


def extract_experience_years_detailed(text: str) -> Dict[str, Any] | None:
    if not text:
        return None

    patterns = [
        (r"at least\s*(\d+)\s*years?", 0.88),
        (r"minimum\s*(?:of)?\s*(\d+)\s*years?", 0.86),
        (r"min(?:imum)?\s*(\d+)\s*years?", 0.84),
        (r"(\d+)\s*\+?\s*years?", 0.78),
        (r"(\d+)\s*-\s*(\d+)\s*years?", 0.76),
        (r"(\d+)\s*to\s*(\d+)\s*years?", 0.76),
        (r"(\d+)\s*yrs?", 0.74),
        (r"(\d+)\s*years?\s*experience", 0.82),
        (r"(\d+)\s*months?", 0.55),
        (r"(\d+)\s*-\s*(\d+)\s*months?", 0.5),
    ]

    candidates: List[Dict[str, Any]] = []
    lowered = text.lower()
    for pattern, base_conf in patterns:
        for match in re.finditer(pattern, lowered):
            nums = [int(n) for n in match.groups() if n and n.isdigit()]
            if not nums:
                continue
            value = min(nums)
            if "month" in match.group(0):
                value = max(1, round(value / 12))
            window = lowered[max(0, match.start() - 40) : match.end() + 40]
            confidence = min(base_conf + _score_modifier(window), 0.9)
            candidates.append(
                {
                    "value": value,
                    "confidence": round(confidence, 2),
                    "evidence": text[match.start() : match.end()],
                    "start": match.start(),
                    "end": match.end(),
                    "source": "experience_pattern",
                }
            )

    if not candidates:
        return None

    candidates.sort(key=lambda c: (-c["confidence"], c["value"]))
    return candidates[0]


def extract_experience_years(text: str) -> int | None:
    """Extracts required years of experience using evidence-aware patterns."""
    detailed = extract_experience_years_detailed(text)
    return detailed["value"] if detailed else None


def classify_seniority_detailed(
    title: str, experience_years: int | None
) -> Dict[str, Any]:
    t = (title or "").lower()
    candidates: List[Dict[str, Any]] = []

    def add_candidate(value: str, confidence: float, evidence: str, source: str):
        if not value:
            return
        idx = t.find(evidence.lower()) if evidence else -1
        start = idx if idx >= 0 else None
        end = (idx + len(evidence)) if idx >= 0 else None
        candidates.append(
            {
                "value": value,
                "confidence": round(confidence, 2),
                "evidence": evidence,
                "start": start,
                "end": end,
                "source": source,
            }
        )

    # Title keyword cues
    title_keywords = [
        (
            "Executive",
            [
                "executive",
                "c-level",
                "chief",
                "vp",
                "vice president",
                "founder",
                "co-founder",
            ],
            0.9,
        ),
        ("Executive", ["director", "head of", "principal", "partner"], 0.85),
        ("Senior", ["senior", "lead", "sr.", "sr ", "staff", "architect"], 0.8),
        ("Senior", ["manager", "supervisor", "consultant", "specialist"], 0.75),
        ("Mid-Level", ["associate", "intermediate", "mid-level", "mid level"], 0.65),
        (
            "Entry",
            ["junior", "entry", "intern", "graduate", "trainee", "assistant"],
            0.7,
        ),
    ]
    for value, terms, conf in title_keywords:
        for term in terms:
            if term in t:
                add_candidate(value, conf, term, "title_keyword")
                break

    # Experience fallback
    if experience_years is not None:
        if experience_years >= 8:
            add_candidate("Executive", 0.7, f"{experience_years} years", "experience")
        elif experience_years >= 5:
            add_candidate("Senior", 0.65, f"{experience_years} years", "experience")
        elif experience_years >= 2:
            add_candidate("Mid-Level", 0.6, f"{experience_years} years", "experience")
        else:
            add_candidate("Entry", 0.55, f"{experience_years} years", "experience")

    if not candidates:
        return {
            "value": "Mid-Level",
            "confidence": 0.4,
            "evidence": "",
            "start": None,
            "end": None,
            "source": "default",
        }

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates[0]


def classify_seniority(title: str, experience_years: int | None) -> str:
    """Classifies seniority based on title keywords and years of experience."""
    detailed = classify_seniority_detailed(title, experience_years)
    return detailed["value"]


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
        "configure",
        "design",
        "develop",
        "deploy",
        "maintain",
        "manage",
        "coordinate",
        "deliver",
        "document",
        "monitor",
        "support",
        "implement",
        "optimize",
        "report",
        "review",
        "test",
        "collaborate",
        "evaluate",
        "research",
        "troubleshoot",
        "operate",
        "own",
        "lead",
        "improve",
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
        idx = text.find(line)
        start = idx if idx >= 0 else None
        end = (idx + len(line)) if idx >= 0 else None
        candidates.append(
            {
                "value": line,
                "confidence": round(confidence, 2),
                "evidence": line[:200],
                "start": start,
                "end": end,
                "source": "line_heuristic",
            }
        )

    return candidates
