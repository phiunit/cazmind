"""Sensitivity levels, role clearance, and topic refusals."""

import re

from . import config as _config

DEFAULT_REFUSAL = "This question can't be answered for your role."


def _cfg(config):
    return config if config is not None else _config.defaults()


def level_rank(label, config=None):
    """Position of a sensitivity label. Unknown labels rank highest (fail closed)."""
    levels = _cfg(config)["levels"]
    label = (label or "").strip().lower()
    return levels.index(label) if label in levels else len(levels) - 1


def clearance(role, config=None):
    """Highest level rank a role may see. Unknown roles get the lowest level."""
    cfg = _cfg(config)
    level = cfg["roles"].get((role or "").strip().lower())
    return cfg["levels"].index(level) if level in cfg["levels"] else 0


def can_see(role, passage, config=None):
    return level_rank(passage.get("sensitivity"), config) <= clearance(role, config)


def allowed_for(role, config=None):
    """Predicate for Index.search(allowed=...)."""
    rank = clearance(role, config)
    return lambda passage: level_rank(passage.get("sensitivity"), config) <= rank


def _mentions(question, phrase):
    phrase = phrase.strip().lower()
    return bool(phrase) and re.search(
        r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", question
    ) is not None


def check_question(role, question, config=None):
    """First refusal rule that covers this role and matches the question, else None."""
    role = (role or "").strip().lower()
    question = (question or "").lower()
    for rule in _cfg(config).get("refusals", []):
        roles = [str(r).strip().lower() for r in rule.get("roles", [])]
        if role in roles and any(_mentions(question, p) for p in rule.get("match_any", [])):
            return rule
    return None


def answer(index, config, role, question, k=5):
    """Refusal check, then a search filtered to what the role may see."""
    rule = check_question(role, question, config)
    if rule is not None:
        return {
            "refused": True,
            "message": rule.get("message") or DEFAULT_REFUSAL,
            "results": [],
        }
    return {
        "refused": False,
        "message": None,
        "results": index.search(question, k=k, allowed=allowed_for(role, config)),
    }
