"""Setup wizard: interactive CLI club configurator + generate_context_from_form().

Two entry points:
  run_wizard()                  – interactive CLI (used by setup.command / setup.bat)
  generate_context_from_form()  – non-interactive, used by the Colab notebook
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).parent.parent.parent


def _repo_path(rel: str) -> Path:
    return _REPO_ROOT / rel


# ── Template generators ───────────────────────────────────────────────────────

def _club_md(answers: dict) -> str:
    return textwrap.dedent(f"""\
        # Club Profile

        **Club:** {answers['club_name']}
        **League:** {answers['league']}

        ## Budget
        - Transfer budget: £{answers['transfer_budget']}
        - Weekly wage budget: £{answers['wage_budget']}/w

        ## Board Objectives
        {answers['objective']}

        ## Recruitment Directive
        {answers['directive']}
    """)


def _playing_style_md(answers: dict) -> str:
    formation = answers.get("formation", "4-3-3")
    roles_section = ""
    if answers.get("position_roles"):
        lines = ["\n## Position Roles\n"]
        for pos, role, duty in answers["position_roles"]:
            lines.append(f"- **{pos}:** {role} ({duty})")
        roles_section = "\n".join(lines)

    return textwrap.dedent(f"""\
        # Playing Style

        ## Formation
        {formation}

        ## Pressing
        - Intensity: {answers.get('pressing', 'Mixed')}
        - Home/Away variation: {answers.get('press_variation', 'Same approach everywhere')}

        ## Build-up
        {answers.get('build_up', 'Balanced')}

        ## Defensive Line
        {answers.get('def_line', 'Standard')}
        {roles_section}
    """)


def _window_priorities_md(answers: dict) -> str:
    priorities = answers.get("priorities", [])
    if not priorities:
        return "# Transfer Window Priorities\n\nNo specific priorities set.\n"
    lines = ["# Transfer Window Priorities\n"]
    for i, pos in enumerate(priorities, 1):
        lines.append(f"## Priority {i}\n**{pos}**\n")
    exits = answers.get("exits", "")
    if exits:
        lines.append(f"\n## Planned Exits\n{exits}")
    return "\n".join(lines) + "\n"


def _dof_profile_md(answers: dict, archetypes: dict) -> str:
    key  = answers.get("dof_mode", "edwards")
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

def write_context_files(answers: dict, context_dir: str | Path | None = None) -> None:
    context_dir = Path(context_dir or _repo_path("context"))
    context_dir.mkdir(parents=True, exist_ok=True)

    arch_path = _repo_path("data/archetypes.yaml")
    with open(arch_path, encoding="utf-8") as f:
        archetypes = yaml.safe_load(f) or {}

    files = {
        "club.md":              _club_md(answers),
        "playing-style.md":     _playing_style_md(answers),
        "window-priorities.md": _window_priorities_md(answers),
        "dof-profile.md":       _dof_profile_md(answers, archetypes),
    }

    for filename, content in files.items():
        (context_dir / filename).write_text(content, encoding="utf-8")

    print(f"✅ Context files written to {context_dir}/")


def generate_context_from_form(values: dict, context_dir: str | Path | None = None) -> None:
    """
    Non-interactive entry point used by the Colab notebook.

    values dict keys (all optional, fall back to defaults):
        club_name, league, transfer_budget, wage_budget, formation,
        board_objective, dof_mode, pressing, build_up, def_line,
        priority_positions (list), exits (str)
    """
    answers = {
        "club_name":        values.get("club_name", "My Club"),
        "league":           values.get("league", "Unknown League"),
        "transfer_budget":  values.get("transfer_budget", "0"),
        "wage_budget":      values.get("wage_budget", "0"),
        "objective":        values.get("board_objective", "Comfortable mid-table"),
        "directive":        values.get("recruitment_directive", "Balanced"),
        "formation":        values.get("formation", "4-3-3"),
        "pressing":         values.get("pressing", "Mixed"),
        "press_variation":  values.get("press_variation", "Same approach everywhere"),
        "build_up":         values.get("build_up", "Balanced"),
        "def_line":         values.get("def_line", "Standard"),
        "dof_mode":         values.get("dof_mode", "edwards"),
        "priorities":       values.get("priority_positions", []),
        "exits":            values.get("exits", ""),
    }
    write_context_files(answers, context_dir)


# ── Interactive wizard ────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "", validate=None) -> str:
    display = f"{prompt} [{default}]: " if default else f"{prompt}: "
    while True:
        val = input(display).strip() or default
        if validate:
            try:
                validate(val)
            except ValueError as e:
                print(f"  ⚠  {e}")
                continue
        return val


def _ask_choice(prompt: str, choices: list[tuple], default: int = 1) -> tuple:
    print(f"\n{prompt}")
    for i, (label, _) in enumerate(choices, 1):
        marker = " ← default" if i == default else ""
        print(f"  [{i}] {label}{marker}")
    while True:
        raw = input(f"  > ").strip() or str(default)
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
    """
    Run the interactive setup wizard. Returns the collected answers dict.
    """
    prev = _load_previous()

    print("\n" + "=" * 52)
    print("  FM Save Copilot — Club Setup Wizard ⚽")
    print("=" * 52)
    print("\nPress Enter to accept the default shown in [brackets].\n")

    if prev:
        print("Previous setup found. Defaults pre-filled from last run.\n")

    answers: dict = {}

    # ── Section 1: Club basics ────────────────────────────────
    print("── Club Details ──────────────────────────────────────")
    answers["club_name"] = _ask("Club name", prev.get("club_name", ""))
    answers["league"]    = _ask("Current league", prev.get("league", ""))

    # ── Section 2: Budget & objectives ────────────────────────
    print("\n── Budget & Objectives ───────────────────────────────")
    answers["transfer_budget"] = _ask(
        "Transfer budget (e.g. 15m, 500k)", prev.get("transfer_budget", "15m"))
    answers["wage_budget"] = _ask(
        "Weekly wage budget (e.g. 100k)", prev.get("wage_budget", "100k"))

    obj_choices = [
        ("Win the league",              "Win the league"),
        ("Compete for a European place", "Compete for a European place"),
        ("Comfortable mid-table",        "Comfortable mid-table"),
        ("Avoid relegation",             "Avoid relegation"),
        ("Survive / overachieve",        "Survive / overachieve"),
    ]
    _, answers["objective"] = _ask_choice("Board objective?", obj_choices, default=3)

    dir_choices = [
        ("Youth-focused — develop young players",              "Youth-focused"),
        ("Balanced — youth where possible, experience as needed", "Balanced"),
        ("Win-now — best available regardless of age",         "Win-now"),
    ]
    _, answers["directive"] = _ask_choice("Recruitment directive?", dir_choices, default=2)

    # ── Section 3: Formation ──────────────────────────────────
    print("\n── Formation & Roles ─────────────────────────────────")
    answers["formation"] = _ask(
        "Formation (e.g. 4-3-3, 4-2-3-1, 3-5-2)", prev.get("formation", "4-3-3"))

    # ── Section 4: Playing style ──────────────────────────────
    print("\n── Playing Style ─────────────────────────────────────")
    press_choices = [
        ("High press (win the ball high)",    "High press"),
        ("Mixed (press situationally)",        "Mixed"),
        ("Low block (sit deep, hit on break)", "Low block"),
    ]
    _, answers["pressing"] = _ask_choice("Pressing intensity?", press_choices, default=2)

    var_choices = [
        ("Yes — higher press at home, lower away", "Higher home / lower away"),
        ("No — same approach everywhere",          "Same approach everywhere"),
    ]
    _, answers["press_variation"] = _ask_choice("Press home/away variation?", var_choices, default=1)

    build_choices = [
        ("Patient possession (play out from back)", "Patient possession"),
        ("Balanced",                                "Balanced"),
        ("Direct (get it forward quickly)",         "Direct"),
    ]
    _, answers["build_up"] = _ask_choice("Build-up style?", build_choices, default=2)

    line_choices = [
        ("High",     "High"),
        ("Standard", "Standard"),
        ("Deep",     "Deep"),
    ]
    _, answers["def_line"] = _ask_choice("Defensive line height?", line_choices, default=2)

    # ── Section 5: Priorities ─────────────────────────────────
    print("\n── Transfer Window Priorities ────────────────────────")
    print("Available positions: GK, RB, LB, CB, DM, CM, AM, LW, RW, ST")
    raw_prio = _ask(
        "Positions to strengthen (comma-separated, or Enter to skip)",
        ",".join(prev.get("priorities", [])),
    )
    answers["priorities"] = [p.strip().upper() for p in raw_prio.split(",") if p.strip()]

    answers["exits"] = _ask(
        "Players to sell / move on (names or Enter to skip)",
        prev.get("exits", ""),
    )

    # ── Section 6: DoF mode ───────────────────────────────────
    print("\n── Director of Football Mode ─────────────────────────")
    dof_choices = [
        ("Michael Edwards — data-driven, system-first", "edwards"),
        ("Monchi — market trader, buy young, sell high", "monchi"),
        ("Edu Gaspar — profile-first, wage discipline",  "edu"),
    ]
    _, answers["dof_mode"] = _ask_choice("Which DoF analyses your squad?", dof_choices, default=1)

    # ── Section 7: Confirm & write ────────────────────────────
    print("\n── Summary ───────────────────────────────────────────")
    print(f"  Club:        {answers['club_name']} ({answers['league']})")
    print(f"  Budget:      £{answers['transfer_budget']} transfer, £{answers['wage_budget']}/w wages")
    print(f"  Objective:   {answers['objective']}")
    print(f"  Formation:   {answers['formation']}")
    print(f"  Style:       {answers['pressing']}, {answers['build_up']}, {answers['def_line']} line")
    print(f"  Priorities:  {', '.join(answers['priorities']) or 'none specified'}")
    print(f"  DoF:         {answers['dof_mode']}")
    print()

    confirm = _ask("Write these files? [Y/n]", "Y")
    if confirm.lower().startswith("n"):
        print("Cancelled. No files written.")
        return answers

    write_context_files(answers, context_dir)
    _save_answers(answers)

    print("\n✅ Setup complete!")
    print("   Next: export your squad from FM24 (see VIEW-SETUP.md)")
    print("   Then run the tool:\n"
          "     Windows: double-click run.bat\n"
          "     Mac:     double-click run.command\n")

    return answers


if __name__ == "__main__":
    run_wizard()
