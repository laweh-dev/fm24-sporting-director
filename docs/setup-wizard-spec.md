# Setup Wizard — Spec

## What this is

An interactive script (`scripts/setup_wizard.py`) that asks the user simple questions and generates all their context files automatically. No markdown editing required.

The wizard is the recommended first step for all users, offered automatically at the end of setup.

## Entry points

### Interactive (CLI)

```python
from fm_copilot.wizard import run_wizard
run_wizard()
```

Called by `scripts/setup_wizard.py` (launched from `setup.bat` / `setup.command`).

### Non-interactive (Colab)

```python
from fm_copilot.wizard import generate_context_from_form
generate_context_from_form({
    "club_name": "Notts County",
    "league": "Premier League",
    "transfer_budget": "15m",
    "wage_budget": "100k",
    "formation": "4-2-3-1",
    "board_objective": "Survive / overachieve",
    "dof_mode": "edwards",
    "priority_positions": ["LB", "RB", "CM"],
    "exits": "",
})
```

Both entry points call the same underlying template functions and write the same context files.

## Files generated

| File | Generated from |
|------|---------------|
| `context/club.md` | Club name, league, budget, objective |
| `context/playing-style.md` | Formation, pressing, build-up, defensive line |
| `context/window-priorities.md` | Priority positions, exits |
| `context/dof-profile.md` | Chosen DoF archetype (from archetypes.yaml) |

## Design principles

1. **Never ask users about attributes.** They pick role names and preferences; the library handles attributes.
2. **Sensible defaults everywhere.** Every question has a default (press Enter to accept).
3. **Re-runnable.** Previous answers are saved to `wizard_answers.json` and pre-filled on re-runs.
4. **Confirm before writing.** A summary is shown; the user confirms before any files are written.

## Saved state

Answers are persisted to `wizard_answers.json` (gitignored). On re-runs, all questions are pre-filled from the previous run's answers.

## Adding new archetypes to the wizard

Add the archetype to `data/archetypes.yaml`. The wizard reads archetype options dynamically from this file — no code changes needed.
