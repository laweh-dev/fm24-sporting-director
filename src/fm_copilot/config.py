"""Load and validate config/config.yaml. Resolve the API key from file or env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

# Locate the repo root relative to this file's install location
_PACKAGE_DIR = Path(__file__).parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent  # src/fm_copilot → src → repo root


def _repo_path(rel: str) -> Path:
    """Resolve a path relative to the repo root."""
    return _REPO_ROOT / rel


DEFAULTS = {
    "provider":              "anthropic",
    "model":                 "claude-haiku-4-5",
    "dof_mode":              "edwards",
    "squad_file":            "data_uploads/squad.html",
    "market_file":           "data_uploads/market.html",
    "roles_file":            "data/roles.yaml",
    "archetypes_file":       "data/archetypes.yaml",
    "attribute_keys_file":   "data/attribute-keys.yaml",
    "context_dir":           "context",
    "output_file":           "output/report.html",
    "candidate_threshold":   60,
    "candidates_per_position": 3,
    "api_key":               "",
}


class ConfigError(Exception):
    """Friendly config validation error shown to users in plain English."""


def load(config_path: str | Path | None = None) -> dict:
    """
    Load config/config.yaml (or the given path), apply defaults, and resolve
    the API key from the env var ANTHROPIC_API_KEY when the file has none.

    Returns a flat dict with resolved absolute paths.
    Raises ConfigError with a friendly message on any problem.
    """
    if config_path is None:
        config_path = _repo_path("config/config.yaml")
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(
            f"No config file found at {config_path}.\n"
            "Run setup first:\n"
            "  Windows: double-click setup.bat\n"
            "  Mac:     double-click setup.command\n"
            "Or copy config/config.example.yaml → config/config.yaml and fill in your settings."
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"config.yaml has a formatting problem:\n{e}")

    cfg = {**DEFAULTS, **raw}

    # Resolve API key: config file first, env var as fallback
    key = str(cfg.get("api_key", "")).strip()
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cfg["api_key"] = key  # empty string → free mode

    # Resolve all file paths relative to the repo root
    for field in (
        "squad_file", "market_file", "roles_file", "archetypes_file",
        "attribute_keys_file", "output_file",
    ):
        cfg[field] = str(_repo_path(cfg[field]))

    cfg["context_dir"] = str(_repo_path(cfg["context_dir"]))

    # Validate critical inputs with friendly messages
    _validate(cfg)
    return cfg


def _validate(cfg: dict) -> None:
    squad = Path(cfg["squad_file"])
    if not squad.exists():
        raise ConfigError(
            f"Squad file not found: {squad}\n\n"
            "Did you export your squad from FM24 and save it as squad.html?\n"
            "See VIEW-SETUP.md for the step-by-step export guide.\n"
            f"The file should go in: {squad.parent}"
        )

    dof = cfg.get("dof_mode", "")
    if dof not in ("edwards", "monchi", "edu"):
        raise ConfigError(
            f"Unknown dof_mode: '{dof}'\n"
            "Valid options: edwards, monchi, edu\n"
            "Check config.yaml."
        )
