"""The single pipeline entry point: run_report(config).

Both front doors call this:
    - scripts/run.bat / run.command  (local)
    - notebooks/FM_Save_Copilot.ipynb (Colab)

Usage:
    from fm_copilot import pipeline
    pipeline.run_report(config)         # config is the dict from config.load()

Or as a CLI:
    python -m fm_copilot [--config path/to/config.yaml] [--open]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


def _parse_budget(budget_str: str) -> int:
    """Convert '15m', '1.5m', '500k', '1000000' → int."""
    s = str(budget_str).strip().lower().replace(",", "")
    try:
        if s.endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("k"):
            return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _load_context(context_dir: str) -> dict:
    """Read any markdown files in context/ into a dict {filename: text}."""
    ctx: dict[str, str] = {}
    cdir = Path(context_dir)
    if cdir.is_dir():
        for md in cdir.glob("*.md"):
            try:
                ctx[md.stem] = md.read_text(encoding="utf-8")
            except Exception:
                pass
    return ctx


def _extract_meta_from_context(ctx: dict, cfg: dict) -> dict:
    """Pull club name, budget, window label etc from context/club.md if present."""
    meta: dict = {
        "club_name": "My Club",
        "window": "Transfer Window",
        "dof_mode": cfg.get("dof_mode", "edwards"),
        "generated": date.today().isoformat(),
        "ai_narrative": False,
    }
    club_text = ctx.get("club", "")
    for line in club_text.splitlines():
        line = line.strip()
        if line.startswith("**Club:**"):
            meta["club_name"] = line.replace("**Club:**", "").strip()
        elif line.startswith("**League:**"):
            meta["window"] = line.replace("**League:**", "").strip() + " — Transfer Window"
    return meta


def _extract_priorities_from_context(ctx: dict) -> list[str]:
    """Parse window-priorities.md to extract priority position strings."""
    text = ctx.get("window-priorities", "")
    prios: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## Priority ") and not line.endswith("Priorities"):
            pass  # next non-empty line has the position
        elif line.startswith("**") and line.endswith("**"):
            prios.append(line.strip("*").strip())
    return prios


def _extract_budget_from_context(ctx: dict) -> int:
    """Parse context/club.md transfer budget line → int."""
    for line in ctx.get("club", "").splitlines():
        if "Transfer budget" in line or "transfer budget" in line:
            for part in line.split(":"):
                cleaned = part.strip().lstrip("£").replace(",", "")
                b = _parse_budget(cleaned)
                if b > 0:
                    return b
    return 15_000_000  # fallback £15m


def _build_priorities_config(priority_labels: list[str], cfg: dict) -> list[dict]:
    """
    Convert plain position labels (e.g. "RB", "LW") to priority dicts
    consumable by analysis.build_shortlist().
    """
    from .analysis import SYSTEM_POSITIONS

    # Map common shorthand to role_key and position_codes
    pos_map: dict[str, dict] = {
        "GK":  {"role_keys": ["sweeper_keeper", "goalkeeper"],
                "position_codes": {"GK"}, "sides": None},
        "RB":  {"role_keys": ["inverted_full_back", "complete_wing_back", "wing_back"],
                "position_codes": {"D", "WB"}, "sides": {"R"}},
        "LB":  {"role_keys": ["inverted_wing_back", "wing_back", "complete_wing_back"],
                "position_codes": {"D", "WB"}, "sides": {"L"}},
        "CB":  {"role_keys": ["central_defender", "ball_playing_defender", "libero"],
                "position_codes": {"D"}, "sides": {"C"}},
        "DM":  {"role_keys": ["half_back", "defensive_midfielder", "regista"],
                "position_codes": {"DM"}, "sides": None},
        "CM":  {"role_keys": ["box_to_box_midfielder", "mezzala", "deep_lying_playmaker"],
                "position_codes": {"M"}, "sides": None},
        "AM":  {"role_keys": ["advanced_playmaker", "enganche", "shadow_striker"],
                "position_codes": {"AM"}, "sides": None},
        "LW":  {"role_keys": ["winger", "wide_midfielder", "inverted_winger"],
                "position_codes": {"M", "AM"}, "sides": {"L"}},
        "RW":  {"role_keys": ["inverted_winger", "wide_midfielder", "winger"],
                "position_codes": {"M", "AM"}, "sides": {"R"}},
        "ST":  {"role_keys": ["deep_lying_forward", "pressing_forward", "advanced_forward",
                               "complete_forward"],
                "position_codes": {"ST"}, "sides": None},
    }

    priorities = []
    for label in priority_labels:
        norm = label.strip().upper()
        if norm in pos_map:
            entry = {"label": label, **pos_map[norm]}
        else:
            # Unknown position label — try matching against SYSTEM_POSITIONS role labels
            entry = {"label": label, "role_keys": [], "position_codes": set(), "sides": None}
            for pos_code, role_label, role_key in SYSTEM_POSITIONS:
                if norm in (pos_code.upper(), role_label.upper()):
                    entry["role_keys"] = [role_key]
                    entry["position_codes"] = {pos_code}
                    break
        priorities.append(entry)

    return priorities


def _build_report_data(
    squad: list[dict],
    market: list[dict],
    analysis: dict,
    cfg: dict,
    meta: dict,
    priorities: list[dict],
    total_budget: int,
) -> dict:
    """Assemble the full report_data dict consumed by report.generate_html()."""
    from .analysis import (
        STRONG_THRESHOLD, CAPABLE_THRESHOLD,
        build_shortlist, age_profile, key_players, versatile_players,
    )
    from .archetypes import candidate_score

    dof  = cfg.get("dof_mode", "edwards")
    gaps = analysis.get("gaps", [])

    # ── Squad health summary ──────────────────────────────────────────────────
    age_groups = analysis.get("age_profile", age_profile(squad))
    n_prime = len(age_groups.get("prime", []))
    n_youth = len(age_groups.get("youth", []))
    n_vet   = len(age_groups.get("veteran", []))
    n_crit  = analysis.get("n_critical", 0)
    wages   = analysis.get("wage_breakdown", {})
    total_w = wages.get("total_weekly", 0)

    age_desc = "Balanced"
    if n_youth + n_prime >= len(squad) * 0.6:
        age_desc = "Young / developing"
    elif n_vet >= len(squad) * 0.35:
        age_desc = "Ageing squad"

    squad_health = {
        "depth":           "Critical" if n_crit >= 3 else ("Thin" if n_crit >= 1 else "Adequate"),
        "age_profile":     age_desc,
        "wage_structure":  f"£{total_w:,}/w total" if total_w else "Unknown",
        "critical_gaps":   str(n_crit),
        "budget_committed": f"£{total_budget:,}" if total_budget else "Unknown",
    }

    # ── Headline stats ────────────────────────────────────────────────────────
    headline_stats = [
        {"value": str(len(squad)),  "label": "Players Analysed"},
        {"value": str(n_crit),      "label": "Critical Gaps"},
        {"value": str(n_prime),     "label": "Prime Age (22–26)"},
        {"value": f"£{total_w:,}", "label": "Wage Bill/Week"},
    ]

    # ── Priority signings section ─────────────────────────────────────────────
    squad_names = {p["name"] for p in squad}
    shortlist   = {}
    if market:
        shortlist = build_shortlist(
            market=market,
            priorities=priorities,
            squad_names=squad_names,
            total_budget=total_budget,
            candidate_threshold=float(cfg.get("candidate_threshold", 60)),
            top_n=int(cfg.get("candidates_per_position", 3)),
        )

    # Build the priority_positions structure for report.py
    priority_positions = []
    for pri in priorities:
        label     = pri["label"]
        role_keys = pri.get("role_keys", [])

        # Current squad coverage for this position
        current_players = []
        for p in squad:
            if not role_keys:
                continue
            best_score = max((p.get("role_scores", {}).get(rk, 0) for rk in role_keys), default=0)
            if best_score >= CAPABLE_THRESHOLD:
                current_players.append({
                    "name":       p["name"],
                    "age":        p.get("age", "?"),
                    "role_score": best_score,
                    "wage":       p.get("wage", 0),
                })
        current_players.sort(key=lambda x: x["role_score"], reverse=True)

        # Determine priority level from gap analysis
        gap_severity = "medium"
        for g in gaps:
            if g["role"] in role_keys:
                gap_severity = g["severity"]
                break
        priority_level = {
            "critical": "CRITICAL",
            "weak":     "HIGH",
            "thin":     "HIGH",
        }.get(gap_severity, "MEDIUM")

        # Situation description
        n_capable = len(current_players)
        n_strong  = sum(1 for p in current_players if p["role_score"] >= STRONG_THRESHOLD)
        if n_capable == 0:
            situation = f"No capable player in the squad for this role. Immediate signing required."
        elif n_strong == 0:
            situation = f"{n_capable} capable option(s) in the squad but nobody above the strong threshold — quality upgrade needed."
        else:
            situation = f"{n_strong} strong option(s) in the squad. Reinforcing depth or quality."

        # Annotate candidates with archetype-adjusted scores
        top_cands = []
        for c in shortlist.get(label, []):
            role_fit = c.get("shortlist_score", 0)
            adj_score = candidate_score(
                c, role_fit, dof, total_budget,
                cfg.get("archetypes_file"),
            )
            top_cands.append({
                **c,
                "role_score":   role_fit,
                "shortlist_score": adj_score,
                "value_low":    c.get("transfer_value_low", 0),
                "value_high":   c.get("transfer_value_high", 0),
            })

        # Role label for display (first role key → human-readable)
        role_label = role_keys[0].replace("_", " ").title() if role_keys else label

        priority_positions.append({
            "position":       label,
            "role":           role_label,
            "role_key":       role_keys[0] if role_keys else "",
            "priority":       priority_level,
            "situation":      situation,
            "current_players": current_players[:4],
            "top_candidates": top_cands,
        })

    # ── Development pipeline (young + improving) ──────────────────────────────
    development_pipeline = []
    for p in sorted(squad, key=lambda x: x.get("best_role_score", 0), reverse=True):
        if p.get("age", 30) <= 23 and p.get("best_role_score", 0) >= CAPABLE_THRESHOLD:
            development_pipeline.append({
                "name":          p["name"],
                "age":           p.get("age", "?"),
                "best_role":     p.get("best_role", "—"),
                "best_role_score": p.get("best_role_score", 0),
                "recommendation": "Develop — protect from unnecessary sales.",
            })

    # ── Decline / contract risks ──────────────────────────────────────────────
    decline_risks = []
    for p in squad:
        age       = p.get("age", 0)
        score     = p.get("best_role_score", 0)
        contract  = str(p.get("contract_expires", ""))
        wage      = p.get("wage", 0)
        # Flag: veteran with falling score or expiring contract
        if age >= 30 and score < CAPABLE_THRESHOLD:
            reason = "Veteran below capable threshold"
            if contract and contract <= str(date.today().year + 1):
                reason += " — expiring contract"
            decline_risks.append({
                "name":             p["name"],
                "age":              age,
                "role_score":       score,
                "contract_expires": contract,
                "wage":             wage,
                "recommendation":   "Assess sell / release in next window.",
            })

    decline_risks.sort(key=lambda x: x["role_score"])

    # ── Wage audit ────────────────────────────────────────────────────────────
    avg_score = (sum(p.get("best_role_score", 0) for p in squad) / len(squad)) if squad else 0
    avg_wage  = (sum(p.get("wage", 0) for p in squad) / len(squad)) if squad else 0
    overpaid  = []
    sells     = []
    for p in squad:
        score = p.get("best_role_score", 0)
        wage  = p.get("wage", 0)
        if score < CAPABLE_THRESHOLD and wage > avg_wage * 1.5:
            overpaid.append({
                "name":       p["name"],
                "wage":       wage,
                "role_score": score,
                "reason":     "High wage, low role fit",
            })
        if score < 40 and p.get("transfer_value_high", 0) > 500_000:
            sells.append({
                "name":        p["name"],
                "role_score":  score,
                "value_high":  p.get("transfer_value_high", 0),
                "reason":      "Low role fit — sell while value exists",
            })

    wage_audit = {"overpaid": overpaid, "sell_candidates": sells}

    # ── Strategic outlook (placeholder — AI will fill later) ─────────────────
    strategic_outlook = {
        "this_window":  "",
        "next_window":  "",
        "twelve_month": "",
    }

    return {
        "meta":               meta,
        "squad_health":       squad_health,
        "headline_stats":     headline_stats,
        "executive_summary":  "",  # AI fills; free mode leaves blank
        "analysis":           analysis,
        "priority_positions": priority_positions,
        "shortlist":          shortlist,
        "development_pipeline": development_pipeline,
        "decline_risks":      decline_risks,
        "wage_audit":         wage_audit,
        "strategic_outlook":  strategic_outlook,
    }


def run_report(config: dict) -> str:
    """
    Main pipeline function. Both front doors call this.

    config: the dict returned by config.load()
    Returns: path to the written HTML report.
    """
    from .parser import load_squad
    from .analysis import run_analysis, annotate_players
    from .report import generate_report

    print(f"[pipeline] Loading squad from {config['squad_file']}...", flush=True)
    squad = load_squad(config["squad_file"], config.get("attribute_keys_file"))
    print(f"[pipeline] Parsed {len(squad)} players.", flush=True)
    if not squad:
        raise ValueError(
            "No players were parsed from the squad file. "
            "Make sure you exported from FM24 using the HTML export format "
            "(File → Save as Webpage) from the Squad screen with the correct view loaded. "
            "See VIEW-SETUP.md for instructions."
        )

    # Load market file if it exists
    market_file = config.get("market_file", "")
    market: list[dict] = []
    if market_file and Path(market_file).exists():
        print(f"[pipeline] Loading market file {market_file}...", flush=True)
        market = load_squad(market_file, config.get("attribute_keys_file"))
        print(f"[pipeline] Parsed {len(market)} market players.", flush=True)
    else:
        print("[pipeline] No market file — skipping shortlist.", flush=True)

    print("[pipeline] Running analysis...", flush=True)
    analysis = run_analysis(squad, roles_path=config.get("roles_file"))

    # Context
    ctx     = _load_context(config.get("context_dir", "context"))
    meta    = _extract_meta_from_context(ctx, config)
    budget  = _extract_budget_from_context(ctx)

    # Priority positions
    raw_prios   = _extract_priorities_from_context(ctx)
    pri_configs = _build_priorities_config(raw_prios, config)

    # Annotate market players too (so shortlist scoring works)
    if market:
        annotate_players(market, config.get("roles_file"))

    report_data = _build_report_data(
        squad, market, analysis, config, meta, pri_configs, budget,
    )

    output_path = config.get("output_file", "output/report.html")
    print(f"[pipeline] Writing report to {output_path}...", flush=True)
    path = generate_report(
        report_data,
        output_path,
        api_key=config.get("api_key", ""),
        model=config.get("model", "claude-haiku-4-5"),
        roles_path=config.get("roles_file"),
    )
    print(f"[pipeline] Done! Report: {path}", flush=True)
    return path


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: python -m fm_copilot [--config ...] [--open]"""
    parser = argparse.ArgumentParser(
        prog="fm_copilot",
        description="FM Save Copilot — generate a Director of Football squad report.",
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to config.yaml (default: config/config.yaml)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open the report in a browser after generating.",
    )
    args = parser.parse_args(argv)

    from . import config as cfg_mod

    try:
        config = cfg_mod.load(args.config)
    except cfg_mod.ConfigError as e:
        print(f"\n[FM Copilot] Configuration problem:\n\n{e}\n", file=sys.stderr)
        sys.exit(1)

    try:
        report_path = run_report(config)
    except Exception as e:
        print(f"\n[FM Copilot] Error generating report:\n{e}\n", file=sys.stderr)
        raise

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{Path(report_path).resolve()}")


if __name__ == "__main__":
    main()
