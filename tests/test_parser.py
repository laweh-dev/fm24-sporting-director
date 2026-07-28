"""Tests for the FM24 HTML parser."""

import os
import sys
from pathlib import Path

import pytest

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fm_copilot.parser import load_squad, _parse_positions

SAMPLE_SQUAD = Path(__file__).parent / "sample_data" / "sample_squad.html"
ATTR_KEYS    = Path(__file__).parent.parent / "data" / "attribute-keys.yaml"


def test_load_squad_returns_list():
    if not SAMPLE_SQUAD.exists():
        pytest.skip("sample_squad.html not found")
    players = load_squad(str(SAMPLE_SQUAD), str(ATTR_KEYS))
    assert isinstance(players, list)
    assert len(players) > 0


def test_player_has_required_fields():
    if not SAMPLE_SQUAD.exists():
        pytest.skip("sample_squad.html not found")
    players = load_squad(str(SAMPLE_SQUAD), str(ATTR_KEYS))
    p = players[0]
    assert "name" in p
    assert "age" in p
    assert "positions" in p
    assert "attributes" in p
    assert isinstance(p["attributes"], dict)


def test_player_attributes_are_ints():
    if not SAMPLE_SQUAD.exists():
        pytest.skip("sample_squad.html not found")
    players = load_squad(str(SAMPLE_SQUAD), str(ATTR_KEYS))
    for p in players:
        for attr, val in p["attributes"].items():
            assert isinstance(val, (int, float)), f"{attr} = {val!r} is not numeric"


def test_parse_positions_gk():
    result = _parse_positions("GK")
    assert "GK" in result


def test_parse_positions_multiple():
    # FM exports use concatenated sides: "(CL)" not "(C, L)"
    result = _parse_positions("D (C), M (C)")
    assert "D" in result
    assert "M" in result
    assert "C" in result.get("D", [])


def test_parse_positions_wb():
    result = _parse_positions("WB (R)")
    assert "WB" in result
    assert "R" in result.get("WB", [])
