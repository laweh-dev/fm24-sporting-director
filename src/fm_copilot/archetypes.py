"""Load archetypes.yaml and compute the final candidate score.

The archetype layer sits on top of role fit. It does NOT change role
attribute definitions — it changes how role fit combines with age/value
and character to produce a final recruitment score.

Final score formula (from role-library-spec.md):
    candidate_score = (role_fit × role_fit_weight)
                    + (age_value_score × age_value_weight)
                    + (character_score × character_weight)
                    + archetype_bonuses
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
def _load_archetypes(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_archetypes(archetypes_path: str | Path | None = None) -> dict:
    if archetypes_path is None:
        archetypes_path = Path(__file__).parent.parent.parent / "data" / "archetypes.yaml"
    return _load_archetypes(str(Path(archetypes_path).resolve()))


def _age_value_score(player: dict, archetype_def: dict) -> float:
    """
    Score 0-100 based on age relative to the archetype's preferred peak age band.
    Players inside the band score 100; outside, score falls linearly to 0 at ±10 years.
    """
    age = player.get("age", 0)
    if not age:
        return 50.0  # unknown age → neutral

    pref = archetype_def.get("flags", {}).get("prefer_peak_age", [22, 28])
    lo, hi = pref[0], pref[1]

    if lo <= age <= hi:
        return 100.0
    dist = min(abs(age - lo), abs(age - hi))
    return max(0.0, 100.0 - dist * 10)


def _character_score(player: dict) -> float:
    """
    Rough character proxy from the player's personality string.
    FM personality labels roughly map to character quality.
    """
    personality = (player.get("personality") or "").lower()
    high = {"professional", "model professional", "model citizen", "determined", "perfectionist"}
    mid  = {"balanced", "temperamental", "light-hearted", "fairly professional", "fairly determined"}
    low  = {"casual", "unambitious", "slack"}

    for word in high:
        if word in personality:
            return 90.0
    for word in mid:
        if word in personality:
            return 65.0
    for word in low:
        if word in personality:
            return 30.0
    return 60.0  # unknown personality → moderate


def _transfer_value_score(player: dict, total_budget: int) -> float:
    """
    Higher score for players priced below budget, declining to 0 at 2× budget.
    """
    tv_low = player.get("transfer_value_low", 0)
    if tv_low == 0:
        return 70.0  # unknown value → moderate score
    if total_budget <= 0:
        return 70.0
    ratio = tv_low / total_budget
    if ratio <= 0.5:
        return 100.0
    if ratio <= 1.0:
        return 100.0 - (ratio - 0.5) * 100
    if ratio <= 2.0:
        return max(0.0, 50.0 - (ratio - 1.0) * 50)
    return 0.0


def candidate_score(
    player: dict,
    role_fit: float,
    archetype_key: str,
    total_budget: int = 15_000_000,
    archetypes_path: str | Path | None = None,
) -> float:
    """
    Combine role_fit (0-100) with age/value and character into a final score.

    Returns 0-100.
    """
    archetypes = load_archetypes(archetypes_path)
    arch = archetypes.get(archetype_key, archetypes.get("edwards", {}))

    weights = arch.get("weights", {"role_fit": 0.70, "age_value": 0.15, "character": 0.15})
    w_role  = weights.get("role_fit",  0.70)
    w_age   = weights.get("age_value", 0.15)
    w_char  = weights.get("character", 0.15)

    age_val_sc  = _age_value_score(player, arch)
    char_sc     = _character_score(player)

    score = (role_fit * w_role) + (age_val_sc * w_age) + (char_sc * w_char)

    # Resale bonus for archetypes that care about it (e.g. Monchi)
    flags = arch.get("flags", {})
    if flags.get("resale_bonus"):
        tv_sc = _transfer_value_score(player, total_budget)
        score = score * 0.9 + tv_sc * 0.1  # small nudge, doesn't dominate

    return round(min(score, 100.0), 2)


def get_archetype(key: str, archetypes_path: str | Path | None = None) -> dict:
    """Return the archetype definition dict for the given key."""
    return load_archetypes(archetypes_path).get(key, {})
