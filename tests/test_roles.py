"""Tests for role scoring logic."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fm_copilot.roles import (
    load_roles, score_player_for_role, can_play_role, top_roles,
)

ROLES_PATH = Path(__file__).parent.parent / "data" / "roles.yaml"


@pytest.fixture
def roles():
    return load_roles(str(ROLES_PATH))


def _make_player(positions: dict, **attrs) -> dict:
    defaults = {k: 10 for k in [
        "pace", "acceleration", "stamina", "strength", "work_rate", "decisions",
        "anticipation", "concentration", "composure", "positioning", "teamwork",
        "passing", "first_touch", "technique", "tackling", "marking", "heading",
        "dribbling", "finishing", "off_the_ball", "vision", "agility", "balance",
        "determination", "aggression", "bravery", "flair", "leadership",
    ]}
    defaults.update(attrs)
    return {"name": "Test Player", "age": 25, "positions": positions, "attributes": defaults}


def test_roles_loaded(roles):
    assert len(roles) > 0
    assert "central_defender" in roles
    assert "sweeper_keeper" in roles


def test_gk_can_play_sweeper_keeper(roles):
    player = _make_player({"GK": ["C"]})
    assert can_play_role(player, "sweeper_keeper", str(ROLES_PATH))


def test_outfield_cannot_play_gk_role(roles):
    player = _make_player({"D": ["C"]})
    assert not can_play_role(player, "sweeper_keeper", str(ROLES_PATH))


def test_score_is_0_to_100():
    player = _make_player({"D": ["C"]})
    score = score_player_for_role(player, "central_defender", roles_path=str(ROLES_PATH))
    assert 0.0 <= score <= 100.0


def test_perfect_player_scores_high():
    player = _make_player({"D": ["C"]}, **{
        "heading": 20, "marking": 20, "tackling": 20,
        "positioning": 20, "concentration": 20, "strength": 20,
        "decisions": 20, "anticipation": 20, "composure": 20,
        "bravery": 20, "aggression": 20, "jumping_reach": 20,
    })
    score = score_player_for_role(player, "central_defender", roles_path=str(ROLES_PATH))
    assert score >= 80.0


def test_top_roles_returns_sorted_list():
    player = _make_player({"D": ["C"]})
    result = top_roles(player, n=3, roles_path=str(ROLES_PATH))
    assert isinstance(result, list)
    if len(result) >= 2:
        assert result[0][1] >= result[1][1]


def test_unknown_role_returns_zero():
    player = _make_player({"D": ["C"]})
    score = score_player_for_role(player, "nonexistent_role_xyz", roles_path=str(ROLES_PATH))
    assert score == 0.0
