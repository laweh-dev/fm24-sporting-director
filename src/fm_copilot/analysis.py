"""Squad analysis: depth per position, gaps, age profile, wage flags, shortlist.

All functions here operate on lists of player dicts produced by parser.py.
Players must have their role scores pre-computed (via pipeline.py annotating
each player with 'role_scores', 'best_role', 'best_role_score').
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .roles import can_play_role, load_roles, score_player_for_role

CAPABLE_THRESHOLD = 55
STRONG_THRESHOLD  = 65


# ── System position definitions ────────────────────────────────────────────────

SYSTEM_POSITIONS = [
    ("GK",  "Sweeper Keeper",     "sweeper_keeper"),
    ("RB",  "Inv. Full Back",     "inverted_full_back"),
    ("CB",  "Central Defender",   "central_defender"),
    ("CB",  "Central Defender",   "central_defender"),
    ("LB",  "Inv. Wing Back",     "inverted_wing_back"),
    ("DM",  "Half Back",          "half_back"),
    ("CM",  "Box-to-Box Mid",     "box_to_box_midfielder"),
    ("CM",  "Mezzala",            "mezzala"),
    ("RW",  "Inverted Winger",    "inverted_winger"),
    ("LW",  "Winger",             "winger"),
    ("ST",  "Deep Lying Forward", "deep_lying_forward"),
]


# ── Annotations ───────────────────────────────────────────────────────────────

def annotate_players(
    players: list[dict],
    roles_path: str | Path | None = None,
) -> list[dict]:
    """Add 'role_scores', 'best_role', 'best_role_score' to each player dict."""
    roles = load_roles(roles_path)
    for p in players:
        scores: dict[str, float] = {}
        for role_key in roles:
            if can_play_role(p, role_key, roles_path):
                duty = (roles[role_key].get("duties") or [None])[0]
                scores[role_key] = score_player_for_role(p, role_key, duty, roles_path)
        p["role_scores"] = scores
        if scores:
            best = max(scores, key=scores.__getitem__)
            p["best_role"]       = best
            p["best_role_score"] = scores[best]
        else:
            p["best_role"]       = ""
            p["best_role_score"] = 0.0
    return players


# ── Depth matrix ───────────────────────────────────────────────────────────────

def _depth_rating(capable: int, strong: int) -> str:
    if strong >= 2:   return "Strong"
    if capable >= 2:  return "Adequate"
    if capable == 1:  return "Thin"
    return "Critical"


def depth_by_role(squad: list[dict]) -> dict:
    """
    Return {role_key: [{"name", "score", "age"}]} sorted by score desc.
    Only players above CAPABLE_THRESHOLD are included.
    """
    result: dict[str, list] = defaultdict(list)
    seen_roles: set[str] = set()

    for p in squad:
        for role_key, score in (p.get("role_scores") or {}).items():
            if score >= CAPABLE_THRESHOLD:
                result[role_key].append({
                    "name":  p["name"],
                    "score": score,
                    "age":   p.get("age", 0),
                })

    for role_key in result:
        result[role_key].sort(key=lambda x: x["score"], reverse=True)
        seen_roles.add(role_key)

    return dict(result)


def build_depth_matrix(squad: list[dict], system_positions=None) -> list[dict]:
    """
    Return the depth matrix for the active system (one entry per slot).
    """
    system_positions = system_positions or SYSTEM_POSITIONS
    depth = depth_by_role(squad)
    matrix = []
    used_per_role: dict[str, int] = defaultdict(int)

    for pos_label, role_label, role_key in system_positions:
        all_opts = depth.get(role_key, [])
        skip = used_per_role[role_key]
        starter = all_opts[skip]     if len(all_opts) > skip     else None
        backup  = all_opts[skip + 1] if len(all_opts) > skip + 1 else None
        capable = sum(1 for x in all_opts if x["score"] >= CAPABLE_THRESHOLD)
        strong  = sum(1 for x in all_opts if x["score"] >= STRONG_THRESHOLD)
        used_per_role[role_key] += 1
        matrix.append({
            "position":    pos_label,
            "role_label":  role_label,
            "role_key":    role_key,
            "starter":     starter,
            "backup":      backup,
            "depth_rating": _depth_rating(capable, strong),
        })
    return matrix


# ── Gaps ──────────────────────────────────────────────────────────────────────

def identify_gaps(depth: dict, system_positions=None) -> list[dict]:
    """
    Return roles with no strong option or no capable option.
    """
    system_positions = system_positions or SYSTEM_POSITIONS
    seen = set()
    gaps = []
    for _, _, role_key in system_positions:
        if role_key in seen:
            continue
        seen.add(role_key)
        players = depth.get(role_key, [])
        capable = sum(1 for p in players if p["score"] >= CAPABLE_THRESHOLD)
        strong  = sum(1 for p in players if p["score"] >= STRONG_THRESHOLD)
        if capable == 0:
            severity, desc = "critical", "No capable players"
        elif strong == 0:
            severity, desc = "weak", "No strong options"
        elif capable == 1:
            severity, desc = "thin", "Single capable player — no cover"
        else:
            continue
        gaps.append({
            "role":     role_key,
            "severity": severity,
            "capable":  capable,
            "strong":   strong,
            "description": desc,
        })
    return gaps


# ── Age profile ───────────────────────────────────────────────────────────────

def age_profile(squad: list[dict]) -> dict:
    groups: dict[str, list[str]] = {"youth": [], "prime": [], "experienced": [], "veteran": []}
    for p in squad:
        age = p.get("age", 0)
        name = p["name"]
        if age < 22:
            groups["youth"].append(name)
        elif age <= 26:
            groups["prime"].append(name)
        elif age <= 31:
            groups["experienced"].append(name)
        else:
            groups["veteran"].append(name)
    return groups


# ── Wage breakdown ────────────────────────────────────────────────────────────

def wage_breakdown(squad: list[dict], top_n: int = 5) -> dict:
    total_w = sum(p.get("wage", 0) for p in squad)
    earners = sorted(squad, key=lambda p: p.get("wage", 0), reverse=True)
    return {
        "total_weekly":  total_w,
        "total_annual":  total_w * 52,
        "top_earners": [
            {"name": p["name"], "wage": p.get("wage", 0)}
            for p in earners[:top_n]
        ],
    }


# ── Key / versatile players ───────────────────────────────────────────────────

def key_players(squad: list[dict], threshold: float = STRONG_THRESHOLD) -> list[dict]:
    result = [
        {
            "name":            p["name"],
            "best_role":       p.get("best_role", ""),
            "best_role_score": p.get("best_role_score", 0),
            "positions_raw":   p.get("positions_raw", ""),
            "wage":            p.get("wage", 0),
        }
        for p in squad
        if p.get("best_role_score", 0) >= threshold
    ]
    return sorted(result, key=lambda x: x["best_role_score"], reverse=True)


def versatile_players(squad: list[dict], min_roles: int = 3) -> list[dict]:
    result = []
    for p in squad:
        capable = [r for r, s in (p.get("role_scores") or {}).items() if s >= CAPABLE_THRESHOLD]
        if len(capable) >= min_roles:
            result.append({
                "name":          p["name"],
                "age":           p.get("age", 0),
                "num_roles":     len(capable),
                "capable_roles": capable,
                "positions_raw": p.get("positions_raw", ""),
            })
    return sorted(result, key=lambda x: x["num_roles"], reverse=True)


# ── Shortlist ─────────────────────────────────────────────────────────────────

def _fits_position_and_side(player: dict, position_codes: set, sides: set | None) -> bool:
    positions = player.get("positions", {})
    for code in position_codes:
        if code in positions:
            if sides is None:
                return True
            if set(positions[code]) & sides:
                return True
    return False


def build_shortlist(
    market: list[dict],
    priorities: list[dict],
    squad_names: set[str],
    total_budget: int = 15_000_000,
    candidate_threshold: float = 60.0,
    top_n: int = 3,
) -> dict[str, list[dict]]:
    """
    Filter market to top-N candidates per priority position.

    priorities is a list of dicts with keys:
        label, role_keys, position_codes (set of FM codes), sides (set or None),
        priority, age_min, age_max

    Returns {priority_label: [candidate_dicts]} with candidates sorted by score.
    """
    shortlist: dict[str, list] = {}

    for priority in priorities:
        label      = priority["label"]
        role_keys  = priority["role_keys"]
        pos_codes  = set(priority.get("position_codes", []))
        sides      = priority.get("sides")
        age_min    = priority.get("age_min", 16)
        age_max    = priority.get("age_max", 40)

        candidates = []
        for player in market:
            if player["name"] in squad_names:
                continue
            if not _fits_position_and_side(player, pos_codes, sides):
                continue
            age = player.get("age", 0)
            if not (age_min <= age <= age_max):
                continue
            tv_low = player.get("transfer_value_low", 0)
            if tv_low > total_budget:
                continue

            best_score = 0.0
            best_key   = role_keys[0] if role_keys else ""
            for rk in role_keys:
                s = (player.get("role_scores") or {}).get(rk, 0)
                if s > best_score:
                    best_score, best_key = s, rk

            if best_score < candidate_threshold:
                continue

            candidates.append({
                **player,
                "shortlist_score": best_score,
                "shortlist_role":  best_key,
            })

        candidates.sort(key=lambda x: x["shortlist_score"], reverse=True)
        shortlist[label] = candidates[:top_n]

    return shortlist


# ── Full analysis runner ──────────────────────────────────────────────────────

def run_analysis(
    squad: list[dict],
    system_positions: list | None = None,
    roles_path: str | Path | None = None,
) -> dict:
    """
    Run the full squad analysis on an already-loaded squad list.
    Returns a structured dict consumed by the report generator.
    """
    sp = system_positions or SYSTEM_POSITIONS

    annotate_players(squad, roles_path)

    depth  = depth_by_role(squad)
    gaps   = identify_gaps(depth, sp)
    matrix = build_depth_matrix(squad, sp)
    ages   = age_profile(squad)
    wages  = wage_breakdown(squad)

    n_crit = sum(1 for g in gaps if g["severity"] == "critical")
    n_weak = sum(1 for g in gaps if g["severity"] == "weak")

    return {
        "squad":               squad,
        "squad_size":          len(squad),
        "depth_by_role":       depth,
        "depth_matrix":        matrix,
        "gaps":                gaps,
        "age_profile":         ages,
        "wage_breakdown":      wages,
        "key_players":         key_players(squad),
        "versatile_players":   versatile_players(squad),
        "n_critical":          n_crit,
        "n_weak":              n_weak,
    }
