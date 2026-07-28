"""Parse Football Manager 2024 HTML exports into structured player data.

Reads column headers dynamically from the HTML, then uses data/attribute-keys.yaml
to map them to internal names. Robust to different column orderings across FM
versions and custom export views.

Supports two export formats, auto-detected from the first header cell:
  - Squad export  (header[0] == "Age"):  single attribute values (1–20)
  - Range export  (header[0] == "Rec"):  attribute ranges ("11-18") → midpoints
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

# Internal attribute keys that are numeric (1-20)
_NUMERIC_ATTRS = frozenset([
    "acceleration", "aggression", "agility", "anticipation", "balance", "bravery",
    "command_of_area", "communication", "composure", "concentration", "corners",
    "crossing", "decisions", "determination", "dribbling", "eccentricity",
    "finishing", "first_touch", "flair", "free_kicks", "handling", "heading",
    "jumping_reach", "kicking", "leadership", "long_shots", "long_throws",
    "marking", "natural_fitness", "off_the_ball", "one_on_ones", "pace",
    "passing", "penalties", "positioning", "punching", "reflexes", "rushing_out",
    "stamina", "strength", "tackling", "teamwork", "technique", "throwing",
    "vision", "work_rate", "aerial_reach",
])

_STATUS_MAP = {
    "Inj": "injured",
    "Unh": "unhappy",
    "Wnt": "transfer_listed",
    "Loa": "loaned_out",
    "Una": "unavailable",
}


def load_key_map(attribute_keys_path: str | Path) -> dict:
    """Load data/attribute-keys.yaml and return normalised lookup dicts."""
    with open(attribute_keys_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    attr_map = {k.lower(): v for k, v in (raw.get("attributes") or {}).items()}
    id_map   = {k.lower(): v for k, v in (raw.get("identity")   or {}).items()}
    return {"attributes": attr_map, "identity": id_map}


def _parse_positions(raw: str) -> dict:
    """
    Parse FM position string into {base_pos: [sides]}.

    Examples:
      "GK"          → {"GK": ["C"]}
      "D (RC)"      → {"D": ["R","C"]}
      "D/WB/M (R)"  → {"D": ["R"], "WB": ["R"], "M": ["R"]}
    """
    if not raw or not raw.strip():
        return {}

    positions = {}
    segments = re.split(r",\s*(?![^(]*\))", raw)
    for seg in segments:
        seg = seg.strip()
        side_m = re.search(r"\(([RLCD]+)\)", seg)
        if side_m:
            sides = list(side_m.group(1))
            base  = re.sub(r"\s*\([^)]*\)", "", seg).strip()
        else:
            sides = ["C"]
            base  = seg.strip()
        for pos in base.split("/"):
            pos = pos.strip()
            if pos:
                positions[pos] = sides
    return positions


def _parse_wage(raw: str) -> int:
    if not raw:
        return 0
    raw = raw.replace("£", "").replace(",", "").replace("p/w", "").replace("/w", "").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def _parse_transfer_value(raw: str) -> tuple[int, int]:
    if not raw or raw.strip() in ("-", ""):
        return (0, 0)
    raw = raw.replace("£", "").strip()
    parts = [p.strip() for p in raw.split("-")]
    vals = []
    for p in parts:
        mult = 1
        if p.upper().endswith("M"):
            mult, p = 1_000_000, p[:-1]
        elif p.upper().endswith("K"):
            mult, p = 1_000, p[:-1]
        try:
            vals.append(int(float(p) * mult))
        except ValueError:
            vals.append(0)
    if len(vals) == 2:
        return (vals[0], vals[1])
    if len(vals) == 1:
        return (vals[0], vals[0])
    return (0, 0)


def _parse_measurement(raw: str, unit: str) -> int:
    if not raw:
        return 0
    try:
        return int(raw.replace(unit, "").strip())
    except ValueError:
        return 0


def _parse_range_attr(raw: str) -> int:
    """Parse "11-18" → 14 (midpoint), "15" → 15, "-" → 0."""
    raw = raw.strip()
    if not raw or raw == "-":
        return 0
    m = re.match(r"^(\d+)-(\d+)$", raw)
    if m:
        return round((int(m.group(1)) + int(m.group(2))) / 2)
    try:
        return int(raw)
    except ValueError:
        return 0


def _build_col_map(headers: list[str], key_map: dict) -> dict:
    """
    Map column index → ("attr"|"id", internal_key) using key_map.

    Handles the duplicate "Nat" header: first occurrence = natural_fitness
    (the attribute), second occurrence = nationality (identity).
    """
    attr_lkp = key_map["attributes"]
    id_lkp   = key_map["identity"]
    col_map  = {}
    nat_seen = 0

    for i, h in enumerate(headers):
        h_low = h.strip().lower()

        if h_low == "nat":
            # First "Nat" = Natural Fitness (attribute), second = Nationality (identity)
            if nat_seen == 0:
                col_map[i] = ("attr", "natural_fitness")
            else:
                col_map[i] = ("id", "nationality")
            nat_seen += 1
        elif h_low in attr_lkp:
            col_map[i] = ("attr", attr_lkp[h_low])
        elif h_low in id_lkp:
            col_map[i] = ("id", id_lkp[h_low])
        # else: unknown column, skip silently

    return col_map


def _cells_to_player(
    cells: list[str],
    col_map: dict,
    is_range: bool,
) -> dict:
    """Convert a list of cell strings into a player dict using col_map."""
    id_data   = {}
    attr_data = {}

    parse_attr = _parse_range_attr if is_range else (lambda v: int(v) if v.isdigit() else 0)

    for idx, (kind, key) in col_map.items():
        if idx >= len(cells):
            continue
        cell = cells[idx].strip()
        if kind == "attr":
            attr_data[key] = parse_attr(cell)
        else:
            id_data[key] = cell

    name = id_data.get("name", "").replace(" - Pick Player", "").strip()
    if not name:
        return {}

    tv_low, tv_high = _parse_transfer_value(id_data.get("transfer_value_raw", ""))

    # "positions_raw" key might be "pos" in range exports
    pos_raw = id_data.get("positions_raw", "") or id_data.get("pos", "")

    return {
        "name":               name,
        "nationality":        id_data.get("nationality", ""),
        "age":                int(id_data["age"]) if id_data.get("age", "").isdigit() else 0,
        "personality":        id_data.get("personality", ""),
        "status":             _STATUS_MAP.get(id_data.get("inf", ""), "available"),
        "contract_expires":   id_data.get("contract_expires", ""),
        "wage":               _parse_wage(id_data.get("wage", "")),
        "transfer_value_low": tv_low,
        "transfer_value_high": tv_high,
        "height_cm":          _parse_measurement(id_data.get("height_cm", ""), "cm"),
        "weight_kg":          _parse_measurement(id_data.get("weight_kg", ""), "kg"),
        "positions_raw":      pos_raw,
        "positions":          _parse_positions(pos_raw),
        "attributes":         attr_data,
    }


def load_squad(
    filepath: str | Path,
    attribute_keys_path: str | Path | None = None,
) -> list[dict]:
    """
    Parse an FM24 HTML export (squad or market range) into a list of player dicts.

    If attribute_keys_path is None, looks for data/attribute-keys.yaml relative
    to this file's package location.
    """
    filepath = Path(filepath)

    if attribute_keys_path is None:
        attribute_keys_path = Path(__file__).parent.parent.parent / "data" / "attribute-keys.yaml"
    key_map = load_key_map(attribute_keys_path)

    with open(filepath, encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    if not rows:
        return []

    # Read header row to build column map
    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    is_range = bool(header_cells and header_cells[0] == "Rec")

    col_map = _build_col_map(header_cells, key_map)

    players = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if not cells:
            continue
        player = _cells_to_player(cells, col_map, is_range)
        if player.get("name"):
            players.append(player)

    return players
