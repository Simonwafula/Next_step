from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_MAPPING_CACHE: Dict[str, Any] | None = None


def load_skill_mapping() -> Dict[str, Any]:
    global _MAPPING_CACHE
    if _MAPPING_CACHE is not None:
        return _MAPPING_CACHE
    mapping_path = Path(__file__).with_name("skill_mapping.json")
    if not mapping_path.exists():
        _MAPPING_CACHE = {"aliases": {}, "custom_skills": []}
        return _MAPPING_CACHE
    with mapping_path.open("r", encoding="utf-8") as handle:
        _MAPPING_CACHE = json.load(handle)
    return _MAPPING_CACHE


def canonicalize_skill(name: str) -> str:
    if not name:
        return ""
    normalized = " ".join(name.strip().lower().split())
    mapping = load_skill_mapping()
    aliases = mapping.get("aliases", {})
    return aliases.get(normalized, normalized)


def custom_skills() -> List[Dict[str, Any]]:
    mapping = load_skill_mapping()
    custom = mapping.get("custom_skills", [])
    return custom if isinstance(custom, list) else []
