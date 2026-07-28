"""Setup wizard — free-text input flow for FM Save Copilot v2.

Two entry points:
  run_wizard()               – interactive CLI (setup.command / setup.bat)
  generate_context_from_form() – non-interactive, used by the Colab notebook

Context files are the underlying storage format — the wizard writes them,
power users can edit them directly by hand, and the pipeline reads them.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).parent.parent.parent


def _repo_path(rel: str) -> Path:
    return _REPO_ROOT / rel


# ── Template writers ──────────────────────────────────────────────────────────

def _club_md(a: dict) -> str:
    cups = a.get("competitions", "").strip() or "None specified"
    return textwrap.dedent(f"""\
        # Club Context

        ## Club
        {a['club_name']}

        ## League
        {a['league']}

        ## Cup Competitions
        {cups}

        ## FM Season
        {a.get('fm_season', 'Not specified')}

        ## Budget
        - Transfer budget: £{a['transfer_budget']}
        - Weekly wage budget: £{a['wage_budget']}/week

        ## Board Objectives
        {a.get('board_objective', 'Not specified')}
    """)


def _tactical_direction_md(a: dict) -> str:
    text = a.get("tactical_direction", "").strip() or "Not specified"
    return f"# Tactical Direction\n\n{text}\n"


def _user_squad_read_md(a: dict) -> str:
    text = a.get("user_squad_read", "").strip() or "Not specified"
    return f"# Your Squad Assessment\n\n{text}\n"


def _dof_profile_md(a: dict, archetypes: dict) -> str:
    key  = a.get("dof_mode", "edwards")
    arch = archetypes.get(key, {})
    name = arch.get("name", key.title())
    tag  = arch.get("tagline", "")
    voice = (arch.get("voice") or "").strip()
    return textwrap.dedent(f"""\
        # Director of Football Profile

        **Mode:** {name}
        **Philosophy:** {tag}

        ## Voice & Approach
        {voice}
    """)


# ── File writer ───────────────────────────────────────────────────────────────

def _tactic_yaml(a: dict) -> str:
    """Produce the tactic.yaml content from wizard answers."""
    formation = a.get("formation", "4-2-3-1")
    roles = {
        "gk":   a.get("gk_role",   "sweeper_keeper"),
        "fb":   a.get("fb_role",   "inverted_full_back"),
        "wb":   a.get("wb_role",   "complete_wing_back"),
        "cb":   a.get("cb_role",   "central_defender"),
        "dm":   a.get("dm_role",   "half_back"),
        "cm":   a.get("cm_role",   "box_to_box_midfielder"),
        "am":   a.get("am_role",   "advanced_playmaker"),
        "wide": a.get("wide_role", "inverted_winger"),
        "st":   a.get("st_role",   "advanced_forward"),
    }
    lines = [f"formation: {formation!r}", "roles:"]
    for slot, role_key in roles.items():
        lines.append(f"  {slot}: {role_key}")
    return "\n".join(lines) + "\n"


def write_context_files(answers: dict, context_dir: str | Path | None = None) -> None:
    context_dir = Path(context_dir or _repo_path("context"))
    context_dir.mkdir(parents=True, exist_ok=True)

    arch_path = _repo_path("data/archetypes.yaml")
    with open(arch_path, encoding="utf-8") as f:
        archetypes = yaml.safe_load(f) or {}

    files = {
        "club.md":                _club_md(answers),
        "tactical-direction.md":  _tactical_direction_md(answers),
        "user-squad-read.md":     _user_squad_read_md(answers),
        "dof-profile.md":         _dof_profile_md(answers, archetypes),
        "tactic.yaml":            _tactic_yaml(answers),
    }

    for filename, content in files.items():
        (context_dir / filename).write_text(content, encoding="utf-8")

    print(f"✅ Context files written to {context_dir}/")


# ── Colab / programmatic entry point ─────────────────────────────────────────

def generate_context_from_form(values: dict, context_dir: str | Path | None = None) -> None:
    """
    Non-interactive entry point used by the Colab notebook.

    values dict keys (all optional):
        club_name, league, competitions, fm_season,
        transfer_budget, wage_budget, board_objective,
        tactical_direction, user_squad_read,
        dof_mode (edwards / monchi / edu),
        formation (e.g. "4-2-3-1"),
        gk_role, fb_role, wb_role, cb_role, dm_role,
        cm_role, am_role, wide_role, st_role  — role_key strings
    """
    answers = {
        "club_name":          values.get("club_name", "My Club"),
        "league":             values.get("league", "Unknown League"),
        "competitions":       values.get("competitions", ""),
        "fm_season":          values.get("fm_season", ""),
        "transfer_budget":    values.get("transfer_budget", "0"),
        "wage_budget":        values.get("wage_budget", "0"),
        "board_objective":    values.get("board_objective", ""),
        "tactical_direction": values.get("tactical_direction", ""),
        "user_squad_read":    values.get("user_squad_read", ""),
        "dof_mode":           values.get("dof_mode", "edwards"),
        # Tactic
        "formation":          values.get("formation", "4-2-3-1"),
        "gk_role":            values.get("gk_role",   "sweeper_keeper"),
        "fb_role":            values.get("fb_role",   "inverted_full_back"),
        "wb_role":            values.get("wb_role",   "complete_wing_back"),
        "cb_role":            values.get("cb_role",   "central_defender"),
        "dm_role":            values.get("dm_role",   "half_back"),
        "cm_role":            values.get("cm_role",   "box_to_box_midfielder"),
        "am_role":            values.get("am_role",   "advanced_playmaker"),
        "wide_role":          values.get("wide_role", "inverted_winger"),
        "st_role":            values.get("st_role",   "advanced_forward"),
    }
    write_context_files(answers, context_dir)


# ── Interactive CLI wizard ────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "", multiline_hint: bool = False) -> str:
    if multiline_hint:
        print(f"\n{prompt}")
        print("(Type your answer. Press Enter twice when done.)")
        lines = []
        blank_count = 0
        while True:
            line = input()
            if line == "":
                blank_count += 1
                if blank_count >= 2:
                    break
                lines.append(line)
            else:
                blank_count = 0
                lines.append(line)
        result = "\n".join(lines).strip()
        return result or default
    else:
        display = f"{prompt} [{default}]: " if default else f"{prompt}: "
        return input(display).strip() or default


def _ask_choice(prompt: str, choices: list[tuple], default: int = 1) -> tuple:
    print(f"\n{prompt}")
    for i, (label, _) in enumerate(choices, 1):
        marker = " ← default" if i == default else ""
        print(f"  [{i}] {label}{marker}")
    while True:
        raw = input("  > ").strip() or str(default)
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print(f"  ⚠  Enter a number between 1 and {len(choices)}.")


def _load_previous() -> dict:
    path = _repo_path("wizard_answers.json")
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_answers(answers: dict) -> None:
    path = _repo_path("wizard_answers.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(answers, f, indent=2)
    except Exception:
        pass


def run_wizard(context_dir: str | Path | None = None) -> dict:
    """Run the interactive setup wizard. Returns the collected answers dict."""
    prev = _load_previous()

    print("\n" + "=" * 54)
    print("  FM Save Copilot v2 — Club Setup Wizard ⚽")
    print("=" * 54)
    if prev:
        print("\nPrevious setup found — defaults pre-filled from last run.\n")
    else:
        print("\nPress Enter to accept the default shown in [brackets].\n")

    answers: dict = {}

    # ── Club basics ──────────────────────────────────────────────
    print("── Club Details ───────────────────────────────────────")
    answers["club_name"]    = _ask("Club name", prev.get("club_name", ""))
    answers["league"]       = _ask("Current league (e.g. Championship, Serie A)",
                                   prev.get("league", ""))
    answers["competitions"] = _ask("Cup competitions (e.g. FA Cup, Carabao Cup — or leave blank)",
                                   prev.get("competitions", ""))
    answers["fm_season"]    = _ask("Current FM season (e.g. 2027/28)",
                                   prev.get("fm_season", ""))

    # ── Budget ───────────────────────────────────────────────────
    print("\n── Budget ─────────────────────────────────────────────")
    answers["transfer_budget"] = _ask("Transfer budget (e.g. 15m, 500k)",
                                      prev.get("transfer_budget", "15m"))
    answers["wage_budget"]     = _ask("Weekly wage budget (e.g. 100k)",
                                      prev.get("wage_budget", "100k"))
    answers["board_objective"] = _ask("Board objective (e.g. Avoid relegation, Win the league)",
                                      prev.get("board_objective", ""))

    # ── Tactical direction (free text) ───────────────────────────
    print("\n── Tactical Direction ─────────────────────────────────")
    print("Describe how you play. Formation, roles, pressing, build-up — whatever")
    print("feels important. No format required. Example:")
    print('  "4-2-3-1, high press at home, low block away. Inverted wingers,')
    print('   box-to-box in the 8 role, sweeper keeper."')
    answers["tactical_direction"] = _ask(
        "Your tactical approach",
        prev.get("tactical_direction", ""),
        multiline_hint=True,
    )

    # ── User's squad read (free text) ────────────────────────────
    print("\n── Your Squad Assessment ──────────────────────────────")
    print("What do you think the squad needs? Your own read — positions, types of")
    print("player, areas of concern. The DoF will compare this against the data.")
    print('Example: "I think we need a left back urgently. Midfield is fine.')
    print('  Striker depth is thin and we might want a backup keeper."')
    answers["user_squad_read"] = _ask(
        "What does the squad need?",
        prev.get("user_squad_read", ""),
        multiline_hint=True,
    )

    # ── DoF archetype ────────────────────────────────────────────
    print("\n── Director of Football Mode ──────────────────────────")
    dof_choices = [
        ("Michael Edwards — data-driven, system-first, role fit dominates", "edwards"),
        ("Monchi — market trader, buy young and undervalued, sell high",     "monchi"),
        ("Edu Gaspar — profile-first, age structure, wage discipline",       "edu"),
    ]
    _, answers["dof_mode"] = _ask_choice("Which DoF analyses your squad?", dof_choices, default=1)

    # ── Summary & confirm ────────────────────────────────────────
    print("\n── Summary ────────────────────────────────────────────")
    print(f"  Club:      {answers['club_name']} ({answers['league']})")
    if answers.get("competitions"):
        print(f"  Cups:      {answers['competitions']}")
    print(f"  Season:    {answers.get('fm_season', 'not set')}")
    print(f"  Budget:    £{answers['transfer_budget']} transfer · £{answers['wage_budget']}/w wages")
    print(f"  DoF:       {answers['dof_mode']}")
    print()

    confirm = _ask("Write context files? [Y/n]", "Y")
    if confirm.lower().startswith("n"):
        print("Cancelled. No files written.")
        return answers

    write_context_files(answers, context_dir)
    _save_answers(answers)

    print("\n✅ Setup complete!")
    print("   Next: export your squad from FM24 (see VIEW-SETUP.md)")
    print("   Then run: Windows → run.bat | Mac → run.command\n")

    return answers


if __name__ == "__main__":
    run_wizard()
