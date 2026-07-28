"""Load roles.yaml and score players against FM roles.

Scoring formula (from role-library-spec.md):
    raw = Σ (attr_value × tier_weight) for all listed attributes
    max = Σ (20 × tier_weight)
    role_fit = (raw / max) × 100   →  0–100

Duty modifiers promote attributes up a tier before scoring.
Tier weights: key=5, important=3, useful=1
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

TIER_WEIGHTS = {"key": 5, "important": 3, "useful": 1}

# Positions in FM exports → set of position codes valid for each role position field
# (roles.yaml uses short codes like "DL", "DR", "GK", "DC", "MC" etc.)
_FM_POSITION_MAP = {
    "GK":  {"GK"},
    "D":   {"DL", "DR", "DC", "D"},
    "WB":  {"WBL", "WBR", "WB"},
    "DM":  {"DM"},
    "M":   {"MC", "ML", "MR", "M"},
    "AM":  {"AMC", "AML", "AMR", "AM"},
    "ST":  {"ST"},
}


@lru_cache(maxsize=1)
def _load_roles(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_roles(roles_path: str | Path | None = None) -> dict:
    """Return the raw roles dict from roles.yaml (cached)."""
    if roles_path is None:
        roles_path = Path(__file__).parent.parent.parent / "data" / "roles.yaml"
    return _load_roles(str(Path(roles_path).resolve()))


def _effective_tiers(role_def: dict, duty: str | None) -> dict[str, str]:
    """
    Return {attribute: tier} after applying duty modifiers.

    Promoted attributes move up: useful→important→key.
    """
    tier_of: dict[str, str] = {}
    for tier in ("key", "important", "useful"):
        for attr in (role_def.get("attributes") or {}).get(tier, []):
            tier_of[attr] = tier

    if duty:
        modifiers = (role_def.get("duty_modifiers") or {}).get(duty, {})
        promote = modifiers.get("promote", [])
        tier_order = ("useful", "important", "key")
        for attr in promote:
            current = tier_of.get(attr)
            if current and current != "key":
                idx = tier_order.index(current)
                tier_of[attr] = tier_order[idx + 1]

    return tier_of


def score_player_for_role(
    player: dict,
    role_key: str,
    duty: str | None = None,
    roles_path: str | Path | None = None,
) -> float:
    """
    Return a 0–100 role-fit score for the player against the given role/duty.

    player["attributes"] must use the full internal names (e.g. "passing",
    "acceleration") that match the role YAML.
    """
    roles = load_roles(roles_path)
    role_def = roles.get(role_key)
    if not role_def:
        return 0.0

    tiers = _effective_tiers(role_def, duty)
    if not tiers:
        return 0.0

    attrs = player.get("attributes", {})
    raw_score = 0.0
    max_score = 0.0
    for attr, tier in tiers.items():
        w = TIER_WEIGHTS[tier]
        raw_score += attrs.get(attr, 0) * w
        max_score += 20 * w

    return round((raw_score / max_score) * 100, 2) if max_score else 0.0


def can_play_role(player: dict, role_key: str, roles_path: str | Path | None = None) -> bool:
    """Return True if the player's position set overlaps with the role's valid positions."""
    roles = load_roles(roles_path)
    role_def = roles.get(role_key)
    if not role_def:
        return False

    role_positions = set(role_def.get("positions", []))
    player_positions = player.get("positions", {})  # {FM_code: [sides]}

    for fm_code in player_positions:
        # fm_code is e.g. "D", "WB", "GK", "M", "AM", "DM", "ST"
        # role positions are like "DL", "DR", "DC", "GK", "MC", etc.
        mapped = _FM_POSITION_MAP.get(fm_code, {fm_code})
        if mapped & role_positions:
            return True
    return False


def score_all_roles(
    player: dict,
    roles_path: str | Path | None = None,
) -> dict[str, float]:
    """Return {role_key: score} for every role the player can physically play."""
    roles = load_roles(roles_path)
    scores = {}
    for role_key, role_def in roles.items():
        if can_play_role(player, role_key, roles_path):
            # Score with default (first) valid duty
            duty = (role_def.get("duties") or [None])[0]
            scores[role_key] = score_player_for_role(player, role_key, duty, roles_path)
    return scores


def top_roles(player: dict, n: int = 3, roles_path: str | Path | None = None) -> list[tuple[str, float]]:
    """Return the top-n (role_key, score) pairs for the player, highest first."""
    all_scores = score_all_roles(player, roles_path)
    return sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:n]
