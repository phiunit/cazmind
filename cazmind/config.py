"""Load and validate cazmind.json."""

import json
import os

DEFAULT_LEVELS = ["public", "internal", "restricted", "confidential"]
DEFAULT_ROLES = {
    "guest": "public",
    "staff": "internal",
    "lead": "restricted",
    "admin": "confidential",
}


def defaults():
    return {
        "org_name": "",
        "levels": list(DEFAULT_LEVELS),
        "roles": dict(DEFAULT_ROLES),
        "default_sensitivity": "internal",
        "max_chars": 1500,
        "refusals": [],
    }


def load(path=None):
    """Read a config file over the defaults. A missing file means defaults."""
    cfg = defaults()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: config must be a JSON object")
        cfg.update({k: v for k, v in data.items() if k in cfg})
    return validate(cfg)


def validate(cfg):
    """Check internal consistency and normalize names to lowercase."""
    levels = cfg["levels"]
    if not isinstance(levels, list) or not levels:
        raise ValueError("config 'levels' must be a non-empty list")
    levels = [str(x).strip().lower() for x in levels]
    if len(set(levels)) != len(levels):
        raise ValueError(f"config 'levels' has duplicates: {levels}")

    if not isinstance(cfg["roles"], dict):
        raise ValueError("config 'roles' must be an object of role -> level")
    roles = {}
    for role, level in cfg["roles"].items():
        level = str(level).strip().lower()
        if level not in levels:
            raise ValueError(
                f"role {role!r} has level {level!r}, which is not one of {levels}"
            )
        roles[str(role).strip().lower()] = level

    default = str(cfg["default_sensitivity"]).strip().lower()
    if default not in levels:
        raise ValueError(
            f"default_sensitivity {default!r} is not one of {levels}"
        )

    max_chars = cfg["max_chars"]
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("config 'max_chars' must be a positive integer")

    if not isinstance(cfg["refusals"], list):
        raise ValueError("config 'refusals' must be a list")

    cfg.update(levels=levels, roles=roles, default_sensitivity=default)
    return cfg
