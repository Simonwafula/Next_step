from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_CACHE: Dict[str, Any] | None = None


def load_education_mapping() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    mapping_path = Path(__file__).with_name("education_mapping.json")
    if not mapping_path.exists():
        _CACHE = {"levels": []}
        return _CACHE
    with mapping_path.open("r", encoding="utf-8") as handle:
        _CACHE = json.load(handle)
    return _CACHE


def education_levels() -> List[Dict[str, Any]]:
    mapping = load_education_mapping()
    levels = mapping.get("levels", [])
    return levels if isinstance(levels, list) else []
