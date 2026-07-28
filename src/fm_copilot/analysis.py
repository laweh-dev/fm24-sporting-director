"""Squad analysis: depth per position, gaps, age profile, wage flags, shortlist.

All functions here operate on lists of player dicts produced by parser.py.
Players must have their role scores pre-computed (via pipeline.py annotating
each player with 'role_scores', 'best_role', 'best_role_score').
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from .roles import can_play_role, load_roles, score_player_for_role

CAPABLE_THRESHOLD = 55
STRONG_THRESHOLD  = 65

# ── League tier system ────────────────────────────────────────────────────────

_LEAGUE_TIERS_PATH = Path(__file__).parent.parent.parent / "data" / "league-tiers.yaml"


def load_league_tiers(path: str | Path | None = None) -> dict:
    p = Path(path or _LEAGUE_TIERS_PATH)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_league_tier(league_text: str, tiers_data: dict | None = None) -> int:
    """Return the tier (1–4) for a league name, defaulting to tier 2 if unrecognised."""
    if not league_text:
        return (tiers_data or {}).get("default_tier", 2)
    data = tiers_data or load_league_tiers()
    text_lower = league_text.lower()
    for entry in data.get("leagues", []):
        candidates = [entry["name"]] + entry.get("aliases", [])
        if any(c.lower() in text_lower or text_lower in c.lower() for c in candidates):
            return entry["tier"]
    return data.get("default_tier", 2)


def thresholds_for_tier(tier: int, tiers_data: dict | None = None) -> tuple[int, int]:
    """Return (CAPABLE, STRONG) score thresholds for a given tier."""
    data = tiers_data or load_league_tiers()
    t = data.get("thresholds", {}).get(tier, {})
    return t.get("capable", CAPABLE_THRESHOLD), t.get("strong", STRONG_THRESHOLD)


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


# ── Role display names ────────────────────────────────────────────────────────

ROLE_DISPLAY_NAMES: dict[str, str] = {
    "advanced_forward":        "Advanced Forward",
    "advanced_playmaker":      "Advanced Playmaker",
    "anchor":                  "Anchor",
    "attacking_midfielder":    "Attacking Midfielder",
    "ball_playing_defender":   "Ball-Playing Defender",
    "ball_winning_midfielder": "Ball-Winning Midfielder",
    "box_to_box_midfielder":   "Box-to-Box Midfielder",
    "carrilero":               "Carrilero",
    "central_defender":        "Central Defender",
    "central_midfielder":      "Central Midfielder",
    "complete_forward":        "Complete Forward",
    "complete_wing_back":      "Complete Wing Back",
    "deep_lying_forward":      "Deep-Lying Forward",
    "deep_lying_playmaker":    "Deep-Lying Playmaker",
    "defensive_midfielder":    "Defensive Midfielder",
    "defensive_winger":        "Defensive Winger",
    "enganche":                "Enganche",
    "false_nine":              "False Nine",
    "full_back":               "Full Back",
    "goalkeeper":              "Goalkeeper",
    "half_back":               "Half Back",
    "inside_forward":          "Inside Forward",
    "inverted_full_back":      "Inverted Full Back",
    "inverted_wing_back":      "Inverted Wing Back",
    "inverted_winger":         "Inverted Winger",
    "mezzala":                 "Mezzala",
    "no_nonsense_centre_back": "No-Nonsense CB",
    "poacher":                 "Poacher",
    "pressing_forward":        "Pressing Forward",
    "raumdeuter":              "Raumdeuter",
    "regista":                 "Regista",
    "roaming_playmaker":       "Roaming Playmaker",
    "segundo_volante":         "Segundo Volante",
    "shadow_striker":          "Shadow Striker",
    "sweeper_keeper":          "Sweeper Keeper",
    "target_forward":          "Target Forward",
    "trequartista":            "Trequartista",
    "wide_centre_back":        "Wide Centre Back",
    "wide_playmaker":          "Wide Playmaker",
    "wing_back":               "Wing Back",
    "winger":                  "Winger",
}

# ── Formation slot definitions ────────────────────────────────────────────────
# Each value is a list of (pos_label, slot_type) tuples.
# slot_type maps to the per-slot role choice in SLOT_DEFAULT_ROLES.

SLOT_DEFAULT_ROLES: dict[str, str] = {
    "gk":   "sweeper_keeper",
    "fb":   "inverted_full_back",
    "wb":   "complete_wing_back",
    "cb":   "central_defender",
    "dm":   "half_back",
    "cm":   "box_to_box_midfielder",
    "am":   "advanced_playmaker",
    "wide": "inverted_winger",
    "st":   "advanced_forward",
}

FORMATION_SLOTS: dict[str, list[tuple[str, str]]] = {
    "4-2-3-1": [
        ("GK",  "gk"),   ("RB",  "fb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("LB",  "fb"),
        ("DM",  "dm"),   ("DM",  "dm"),
        ("RW",  "wide"), ("AM",  "am"),   ("LW",  "wide"), ("ST",  "st"),
    ],
    "4-3-3": [
        ("GK",  "gk"),   ("RB",  "fb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("LB",  "fb"),
        ("CM",  "dm"),   ("CM",  "cm"),   ("CM",  "cm"),
        ("RW",  "wide"), ("ST",  "st"),   ("LW",  "wide"),
    ],
    "4-4-2": [
        ("GK",  "gk"),   ("RB",  "fb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("LB",  "fb"),
        ("RM",  "wide"), ("CM",  "dm"),   ("CM",  "cm"),  ("LM",  "wide"),
        ("ST",  "st"),   ("ST",  "st"),
    ],
    "3-5-2": [
        ("GK",  "gk"),   ("CB",  "cb"),   ("CB",  "cb"),  ("CB",  "cb"),
        ("RWB", "wb"),   ("CM",  "dm"),   ("CM",  "cm"),  ("CM",  "dm"),  ("LWB", "wb"),
        ("ST",  "st"),   ("ST",  "st"),
    ],
    "4-1-4-1": [
        ("GK",  "gk"),   ("RB",  "fb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("LB",  "fb"),
        ("DM",  "dm"),
        ("RM",  "wide"), ("CM",  "cm"),   ("CM",  "cm"),  ("LM",  "wide"),
        ("ST",  "st"),
    ],
    "5-3-2": [
        ("GK",  "gk"),   ("RWB", "wb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("CB",  "cb"),  ("LWB", "wb"),
        ("CM",  "dm"),   ("CM",  "cm"),   ("CM",  "cm"),
        ("ST",  "st"),   ("ST",  "st"),
    ],
    "3-4-3": [
        ("GK",  "gk"),   ("CB",  "cb"),   ("CB",  "cb"),  ("CB",  "cb"),
        ("RWB", "wb"),   ("CM",  "cm"),   ("CM",  "dm"),  ("LWB", "wb"),
        ("RW",  "wide"), ("ST",  "st"),   ("LW",  "wide"),
    ],
    "4-2-2-2": [
        ("GK",  "gk"),   ("RB",  "fb"),   ("CB",  "cb"),  ("CB",  "cb"),  ("LB",  "fb"),
        ("DM",  "dm"),   ("DM",  "dm"),
        ("RAM", "am"),   ("LAM", "am"),
        ("ST",  "st"),   ("ST",  "st"),
    ],
}


def build_system_positions(
    formation: str,
    role_map: dict[str, str],
    roles_path: str | Path | None = None,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """
    Build a system_positions list from a formation name and per-slot role choices.

    role_map keys: slot_type strings (gk, fb, wb, cb, dm, cm, am, wide, st)
    role_map values: role_key strings from roles.yaml

    Returns (system_positions, warnings).
    Falls back to SYSTEM_POSITIONS with a warning if the formation is unknown.
    """
    warnings: list[str] = []

    slots = FORMATION_SLOTS.get(formation)
    if slots is None:
        warnings.append(
            f"Formation '{formation}' not recognised — using default 4-3-3. "
            f"Supported: {', '.join(FORMATION_SLOTS)}"
        )
        return list(SYSTEM_POSITIONS), warnings

    valid_roles: set[str] = set(ROLE_DISPLAY_NAMES.keys())
    if roles_path is not None:
        try:
            loaded = load_roles(roles_path)
            valid_roles = set(loaded.keys())
        except Exception:
            pass

    system_positions: list[tuple[str, str, str]] = []
    for pos_label, slot_type in slots:
        chosen_key = role_map.get(slot_type, "")
        if chosen_key and chosen_key in valid_roles:
            role_key = chosen_key
        else:
            role_key = SLOT_DEFAULT_ROLES.get(slot_type, "central_defender")
            if chosen_key:
                warnings.append(
                    f"Role '{chosen_key}' for slot '{slot_type}' not in roles.yaml — "
                    f"using default '{role_key}'."
                )
        role_label = ROLE_DISPLAY_NAMES.get(role_key, role_key.replace("_", " ").title())
        system_positions.append((pos_label, role_label, role_key))

    return system_positions, warnings


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


def depth_by_role(squad: list[dict], capable_threshold: int = CAPABLE_THRESHOLD) -> dict:
    """
    Return {role_key: [{"name", "score", "age"}]} sorted by score desc.
    Only players above capable_threshold are included.
    """
    result: dict[str, list] = defaultdict(list)

    for p in squad:
        for role_key, score in (p.get("role_scores") or {}).items():
            if score >= capable_threshold:
                result[role_key].append({
                    "name":  p["name"],
                    "score": score,
                    "age":   p.get("age", 0),
                })

    for role_key in result:
        result[role_key].sort(key=lambda x: x["score"], reverse=True)

    return dict(result)


def build_depth_matrix(
    squad: list[dict],
    system_positions=None,
    capable_threshold: int = CAPABLE_THRESHOLD,
    strong_threshold: int = STRONG_THRESHOLD,
) -> list[dict]:
    """Return the depth matrix for the active system (one entry per slot)."""
    system_positions = system_positions or SYSTEM_POSITIONS
    depth = depth_by_role(squad, capable_threshold)
    matrix = []
    used_per_role: dict[str, int] = defaultdict(int)

    for pos_label, role_label, role_key in system_positions:
        all_opts = depth.get(role_key, [])
        skip = used_per_role[role_key]
        starter = all_opts[skip]     if len(all_opts) > skip     else None
        backup  = all_opts[skip + 1] if len(all_opts) > skip + 1 else None
        capable = sum(1 for x in all_opts if x["score"] >= capable_threshold)
        strong  = sum(1 for x in all_opts if x["score"] >= strong_threshold)
        used_per_role[role_key] += 1
        matrix.append({
            "position":     pos_label,
            "role_label":   role_label,
            "role_key":     role_key,
            "starter":      starter,
            "backup":       backup,
            "depth_rating": _depth_rating(capable, strong),
        })
    return matrix


# ── Gaps ──────────────────────────────────────────────────────────────────────

def identify_gaps(
    depth: dict,
    system_positions=None,
    capable_threshold: int = CAPABLE_THRESHOLD,
    strong_threshold: int = STRONG_THRESHOLD,
) -> list[dict]:
    """Return roles with no strong option or no capable option."""
    system_positions = system_positions or SYSTEM_POSITIONS
    seen = set()
    gaps = []
    for _, _, role_key in system_positions:
        if role_key in seen:
            continue
        seen.add(role_key)
        players = depth.get(role_key, [])
        capable = sum(1 for p in players if p["score"] >= capable_threshold)
        strong  = sum(1 for p in players if p["score"] >= strong_threshold)
        if capable == 0:
            severity, desc = "critical", "No capable players"
        elif strong == 0:
            severity, desc = "weak", "No strong options"
        elif capable == 1:
            severity, desc = "thin", "Single capable player — no cover"
        else:
            continue
        gaps.append({
            "role":        role_key,
            "severity":    severity,
            "capable":     capable,
            "strong":      strong,
            "description": desc,
        })
    return gaps


# ── DoF priority recommendation ──────────────────────────────────────────────

# First-occurrence mapping from role_key → short position label
_ROLE_TO_POS: dict[str, str] = {}
for _pl, _, _rk in SYSTEM_POSITIONS:
    if _rk not in _ROLE_TO_POS:
        _ROLE_TO_POS[_rk] = _pl


def _star_label(stars: int | None) -> str:
    """Return a star string like '★★★' for display, or '' if unrated."""
    if stars is None:
        return ""
    return "★" * stars


def dof_recommended_priorities(
    gaps: list[dict],
    dof_mode: str = "edwards",
    top_n: int = 4,
    squad: list[dict] | None = None,
) -> list[dict]:
    """
    Derive the DoF's recommended priority positions from the gap analysis.

    Returns up to top_n items, most urgent first:
        [{label, role_key, severity, capable, strong, data_reason, high_potential_prospect}]

    When squad is provided, also surfaces any high-potential young player (4-5 stars)
    whose best role matches a gap position — flagged as a development accelerant.
    """
    _ORDER = {"critical": 0, "weak": 1, "thin": 2}
    sorted_gaps = sorted(gaps, key=lambda g: (_ORDER.get(g["severity"], 9), g.get("capable", 0)))

    # Index high-potential young players by their best role
    _high_pot: dict[str, list[str]] = {}  # role_key → [player names]
    for p in (squad or []):
        stars = p.get("potential_stars")
        if stars and stars >= 4 and p.get("age", 99) <= 23:
            role = p.get("best_role", "")
            if role:
                _high_pot.setdefault(role, []).append(p["name"])

    result: list[dict] = []
    seen: set[str] = set()
    for gap in sorted_gaps:
        label = _ROLE_TO_POS.get(gap["role"], gap["role"])
        if label in seen:
            continue
        seen.add(label)
        c, s = gap.get("capable", 0), gap.get("strong", 0)
        if gap["severity"] == "critical":
            reason = f"No capable player at {label} — this is a structural hole in the squad."
        elif gap["severity"] == "weak":
            reason = f"{c} capable player(s) at {label} but no one strong enough to depend on."
        else:
            reason = f"Only {c} capable player at {label} — one injury and there's no cover."
        prospects = _high_pot.get(gap["role"], [])
        result.append({
            "label":                    label,
            "role_key":                 gap["role"],
            "severity":                 gap["severity"],
            "capable":                  c,
            "strong":                   s,
            "data_reason":              reason,
            "high_potential_prospects": prospects,
        })
        if len(result) >= top_n:
            break
    return result


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

# Position group mappings for financial audit
_POS_GROUP: dict[str, str] = {
    "GK": "Goalkeepers",
    "D":  "Defenders", "WB": "Defenders",
    "DM": "Midfielders", "M": "Midfielders", "AM": "Midfielders",
    "ST": "Forwards", "FC": "Forwards",
}


def _player_position_group(player: dict) -> str:
    positions = player.get("positions", {})
    for code in ("ST", "FC", "AM", "M", "DM", "WB", "D", "GK"):
        if code in positions:
            return _POS_GROUP.get(code, "Other")
    return "Other"


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


def wage_by_position_group(squad: list[dict]) -> dict[str, dict]:
    """Aggregate weekly wage spend by position group."""
    groups: dict[str, list] = defaultdict(list)
    for p in squad:
        g = _player_position_group(p)
        groups[g].append(p)
    result = {}
    for g, players in sorted(groups.items()):
        total = sum(p.get("wage", 0) for p in players)
        result[g] = {
            "count":  len(players),
            "total":  total,
            "avg":    total // len(players) if players else 0,
        }
    return result


# ── Contract risk ─────────────────────────────────────────────────────────────

def _months_remaining(contract_year_str: str, fm_season_year: int) -> int:
    """
    Estimate months remaining on a contract.
    contract_year_str: e.g. "2027" (the year the contract expires)
    fm_season_year: the current FM season year (e.g. 2027 for the 2027/28 season)
    Returns approximate months (positive = time left, 0 or negative = expired).
    """
    try:
        exp_year = int(str(contract_year_str).strip()[:4])
    except (ValueError, TypeError):
        return 999
    return (exp_year - fm_season_year) * 12


def contract_risk_flags(
    squad: list[dict],
    fm_season_year: int,
    urgent_months: int = 12,
    risk_months: int = 24,
) -> list[dict]:
    """
    Flag players whose contracts are expiring.
    Returns list sorted by months_remaining ascending.
    urgent  = < urgent_months remaining
    risk    = urgent_months <= remaining < risk_months
    """
    flagged = []
    for p in squad:
        months = _months_remaining(p.get("contract_expires", ""), fm_season_year)
        if months <= 0:
            tier = "expired"
        elif months < urgent_months:
            tier = "urgent"
        elif months < risk_months:
            tier = "risk"
        else:
            continue
        flagged.append({
            "name":             p["name"],
            "age":              p.get("age", 0),
            "contract_expires": p.get("contract_expires", ""),
            "months_remaining": months,
            "wage":             p.get("wage", 0),
            "best_role":        p.get("best_role", ""),
            "role_score":       p.get("best_role_score", 0),
            "contract_tier":    tier,
        })
    flagged.sort(key=lambda x: x["months_remaining"])
    return flagged


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
    league_tier: int = 2,
    fm_season_year: int | None = None,
) -> dict:
    """
    Run the full squad analysis on an already-loaded squad list.
    Returns a structured dict consumed by the report generator.
    """
    sp = system_positions or SYSTEM_POSITIONS
    capable_t, strong_t = thresholds_for_tier(league_tier)

    annotate_players(squad, roles_path)

    depth  = depth_by_role(squad, capable_threshold=capable_t)
    gaps   = identify_gaps(depth, sp, capable_threshold=capable_t, strong_threshold=strong_t)
    matrix = build_depth_matrix(squad, sp, capable_threshold=capable_t, strong_threshold=strong_t)
    ages   = age_profile(squad)
    wages  = wage_breakdown(squad)
    wage_groups = wage_by_position_group(squad)

    n_crit = sum(1 for g in gaps if g["severity"] == "critical")
    n_weak = sum(1 for g in gaps if g["severity"] == "weak")

    fm_year = fm_season_year or __import__("datetime").date.today().year
    contract_risks = contract_risk_flags(squad, fm_year)

    return {
        "squad":               squad,
        "squad_size":          len(squad),
        "depth_by_role":       depth,
        "depth_matrix":        matrix,
        "gaps":                gaps,
        "age_profile":         ages,
        "wage_breakdown":      wages,
        "wage_by_group":       wage_groups,
        "contract_risks":      contract_risks,
        "key_players":         key_players(squad),
        "versatile_players":   versatile_players(squad),
        "n_critical":          n_crit,
        "n_weak":              n_weak,
        "league_tier":         league_tier,
        "capable_threshold":   capable_t,
        "strong_threshold":    strong_t,
    }
