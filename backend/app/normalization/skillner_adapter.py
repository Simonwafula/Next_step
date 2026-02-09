from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List


from .skill_mapping import custom_skills

logger = logging.getLogger(__name__)

_SKILLNER_LOCK = threading.Lock()
_SKILLNER_READY = False
_SKILLNER_CONTEXT: Dict[str, Any] = {}


def _skillner_data_dir() -> Path:
    env_dir = os.getenv("SKILLNER_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).with_name("skillner_data")


def _load_skill_db(data_dir: Path) -> Dict[str, Any]:
    skill_db_path = data_dir / "skill_db_relax_20.json"
    with skill_db_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _make_custom_skill_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    return f"CUSTOM{slug.upper()}"


def _extend_skill_db(skills_db: Dict[str, Any]) -> Dict[str, Any]:
    existing_names = {info["skill_name"].lower() for info in skills_db.values()}
    for entry in custom_skills():
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        name_lower = name.lower()
        if name_lower in existing_names:
            continue
        aliases = [
            alias.lower()
            for alias in entry.get("aliases", [])
            if isinstance(alias, str) and alias.strip()
        ]
        full_form = name_lower
        low_forms = [full_form] + [alias for alias in aliases if alias != full_form]
        skills_db[_make_custom_skill_id(name_lower)] = {
            "skill_name": name,
            "skill_type": "Hard Skill",
            "skill_len": len(full_form.split()),
            "high_surfce_forms": {"full": full_form},
            "low_surface_forms": low_forms,
            "match_on_tokens": len(full_form.split()) > 1,
        }
        existing_names.add(name_lower)
    return skills_db


def _load_spacy_model():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return spacy.blank("en")


def _ensure_skillner_context() -> bool:
    global _SKILLNER_READY, _SKILLNER_CONTEXT
    if _SKILLNER_READY:
        return True
    data_dir = _skillner_data_dir()
    if not data_dir.exists():
        logger.warning("SkillNER data dir missing: %s", data_dir)
        return False
    with _SKILLNER_LOCK:
        if _SKILLNER_READY:
            return True
        cwd = os.getcwd()
        try:
            os.chdir(data_dir)
            import importlib

            text_class = importlib.import_module("skillNer.text_class")
            matcher_class = importlib.import_module("skillNer.matcher_class")
            utils_mod = importlib.import_module("skillNer.utils")
        except Exception:
            logger.exception("Failed to import SkillNER modules.")
            return False
        finally:
            os.chdir(cwd)

        from spacy.matcher import PhraseMatcher

        skills_db = _extend_skill_db(_load_skill_db(data_dir))
        nlp = _load_spacy_model()
        matchers = matcher_class.Matchers(nlp, skills_db, PhraseMatcher).load_matchers()
        skill_getters = matcher_class.SkillsGetter(nlp)
        utils = utils_mod.Utils(nlp, skills_db)

        _SKILLNER_CONTEXT = {
            "skills_db": skills_db,
            "nlp": nlp,
            "matchers": matchers,
            "skill_getters": skill_getters,
            "utils": utils,
            "text_class": text_class,
        }
        _SKILLNER_READY = True
    return True


def _build_evidence(text: str, words_position, node_ids: List[int]) -> Dict[str, Any]:
    if not node_ids:
        return {"start": None, "end": None, "snippet": ""}
    valid_ids = [idx for idx in node_ids if 0 <= idx < len(words_position)]
    if not valid_ids:
        return {"start": None, "end": None, "snippet": ""}
    start_idx = words_position[min(valid_ids)].start
    end_idx = words_position[max(valid_ids)].end
    snippet = text[start_idx:end_idx]
    return {"start": start_idx, "end": end_idx, "snippet": snippet}


def extract_skillner_matches(text: str) -> List[Dict[str, Any]]:
    if not text or not _ensure_skillner_context():
        return []

    context = _SKILLNER_CONTEXT
    text_class = context["text_class"]
    nlp = context["nlp"]
    matchers = context["matchers"]
    skill_getters = context["skill_getters"]
    utils = context["utils"]
    skills_db = context["skills_db"]

    text_obj = text_class.Text(text, nlp)
    skills_full, text_obj = skill_getters.get_full_match_skills(
        text_obj, matchers["full_matcher"]
    )
    skills_abv, text_obj = skill_getters.get_abv_match_skills(
        text_obj, matchers["abv_matcher"]
    )
    skills_uni_full, text_obj = skill_getters.get_full_uni_match_skills(
        text_obj, matchers["full_uni_matcher"]
    )
    skills_low_form, text_obj = skill_getters.get_low_match_skills(
        text_obj, matchers["low_form_matcher"]
    )
    skills_on_token = skill_getters.get_token_match_skills(
        text_obj, matchers["token_matcher"]
    )
    full_matches = skills_full + skills_abv
    to_process = skills_on_token + skills_low_form + skills_uni_full
    process_n_gram = utils.process_n_gram(to_process, text_obj)

    transformed_text = text_obj.transformed_text
    words_position = text_class.Text.words_start_end_position(transformed_text)

    matches: List[Dict[str, Any]] = []

    for match in full_matches:
        skill_id = match.get("skill_id")
        if skill_id not in skills_db:
            continue
        evidence = _build_evidence(
            transformed_text, words_position, match["doc_node_id"]
        )
        matches.append(
            {
                "skill": skills_db[skill_id]["skill_name"].lower(),
                "confidence": 0.9,
                "start": evidence["start"],
                "end": evidence["end"],
                "evidence": evidence["snippet"],
                "source": "skillner_full",
            }
        )

    for match in process_n_gram:
        skill_id = match.get("skill_id")
        if skill_id not in skills_db:
            continue
        score = float(match.get("score", 0.5))
        confidence = 0.6 + (0.35 * min(score, 1.0))
        evidence = _build_evidence(
            transformed_text, words_position, match["doc_node_id"]
        )
        matches.append(
            {
                "skill": skills_db[skill_id]["skill_name"].lower(),
                "confidence": confidence,
                "start": evidence["start"],
                "end": evidence["end"],
                "evidence": evidence["snippet"],
                "source": "skillner_ngram",
            }
        )

    return matches
