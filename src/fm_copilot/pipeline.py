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


def _load_tactic(context_dir: str) -> dict:
    """Load context/tactic.yaml if it exists. Returns {} if missing or unparseable."""
    import yaml
    path = Path(context_dir) / "tactic.yaml"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception:
        return {}


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


def _section_value(text: str, heading: str) -> str:
    """Extract the text under a ## Heading from a markdown string."""
    lines = text.splitlines()
    capturing = False
    result = []
    for line in lines:
        if line.strip().lower() == f"## {heading.lower()}":
            capturing = True
            continue
        if capturing:
            if line.startswith("## "):
                break
            result.append(line)
    return "\n".join(result).strip()


def _extract_meta_from_context(ctx: dict, cfg: dict) -> dict:
    """Pull all club/context fields from context/ files."""
    club_text = ctx.get("club", "")

    meta: dict = {
        "club_name":          "My Club",
        "league":             "",
        "competitions":       "",
        "fm_season":          "",
        "dof_mode":           cfg.get("dof_mode", "edwards"),
        "generated":          date.today().isoformat(),
        "ai_narrative":       False,
        "tactical_direction": ctx.get("tactical-direction", "").replace("# Tactical Direction", "").strip(),
        "user_squad_read":    ctx.get("user-squad-read", "").replace("# Your Squad Assessment", "").strip(),
    }

    meta["club_name"]    = _section_value(club_text, "Club") or meta["club_name"]
    meta["league"]       = _section_value(club_text, "League") or ""
    meta["competitions"] = _section_value(club_text, "Cup Competitions") or ""
    meta["fm_season"]    = _section_value(club_text, "FM Season") or ""

    # Clean placeholder text
    for key in ("club_name", "league", "competitions", "fm_season"):
        v = meta[key]
        if v.startswith("[") or "Not specified" in v or "Run the" in v:
            meta[key] = ""

    for key in ("tactical_direction", "user_squad_read"):
        v = meta[key]
        if "Run the Setup Wizard" in v or "Not specified" in v or v.startswith("["):
            meta[key] = ""

    return meta


def _extract_budget_from_context(ctx: dict) -> int:
    """Parse context/club.md transfer budget line → int."""
    budget_section = _section_value(ctx.get("club", ""), "Budget")
    for line in budget_section.splitlines():
        if "transfer budget" in line.lower():
            for part in line.split(":"):
                cleaned = part.strip().lstrip("£").replace(",", "").split("/")[0]
                b = _parse_budget(cleaned.strip())
                if b > 0:
                    return b
    return 15_000_000  # fallback £15m


def _extract_fm_season_year(fm_season: str) -> int:
    """Parse 'YYYY/YY' or 'YYYY' → start year integer."""
    if not fm_season:
        return date.today().year
    try:
        return int(fm_season.strip()[:4])
    except (ValueError, TypeError):
        return date.today().year


def _compare_priorities(
    user_labels: list[str],
    dof_recs: list[dict],
) -> dict:
    """
    Diff user-stated priorities against DoF analysis-derived recommendations.

    Returns three lists — agreed, user_only, dof_only — each containing
    priority dicts suitable for rendering in the Priority Alignment section.
    """
    user_set = {l.upper() for l in user_labels}
    dof_by_label = {r["label"].upper(): r for r in dof_recs}
    dof_set = set(dof_by_label)

    return {
        "agreed":    [dof_by_label[l] for l in sorted(user_set & dof_set)],
        "user_only": [{"label": l} for l in sorted(user_set - dof_set)],
        "dof_only":  [dof_by_label[l] for l in sorted(dof_set - user_set)],
    }


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
    """Assemble the full v2 report_data dict consumed by report.generate_html()."""
    from .analysis import (
        build_shortlist, age_profile, key_players, versatile_players,
    )
    from .archetypes import candidate_score

    dof          = cfg.get("dof_mode", "edwards")
    gaps         = analysis.get("gaps", [])
    capable_t    = analysis.get("capable_threshold", 55)
    strong_t     = analysis.get("strong_threshold", 65)
    league_tier  = analysis.get("league_tier", 2)

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
        "squad_size":      len(squad),
        "depth":           "Critical" if n_crit >= 3 else ("Thin" if n_crit >= 1 else "Adequate"),
        "age_profile":     age_desc,
        "wage_structure":  f"£{total_w:,}/w" if total_w else "Unknown",
        "critical_gaps":   n_crit,
        "youth":           len(age_groups.get("youth", [])),
        "prime":           n_prime,
        "experienced":     len(age_groups.get("experienced", [])),
        "veteran":         n_vet,
    }

    # ── Shortlist ────────────────────────────────────────────────────────────
    squad_names = {p["name"] for p in squad}
    shortlist: dict = {}
    if market:
        shortlist = build_shortlist(
            market=market,
            priorities=priorities,
            squad_names=squad_names,
            total_budget=total_budget,
            candidate_threshold=float(capable_t),
            top_n=int(cfg.get("candidates_per_position", 3)),
        )

    # ── Priority positions (for signing section) ─────────────────────────────
    priority_positions = []
    for pri in priorities:
        label     = pri["label"]
        role_keys = pri.get("role_keys", [])

        current_players = []
        for p in squad:
            if not role_keys:
                continue
            best_score = max((p.get("role_scores", {}).get(rk, 0) for rk in role_keys), default=0)
            if best_score >= capable_t:
                current_players.append({
                    "name":       p["name"],
                    "age":        p.get("age", "?"),
                    "role_score": best_score,
                    "wage":       p.get("wage", 0),
                })
        current_players.sort(key=lambda x: x["role_score"], reverse=True)

        gap_severity = "medium"
        for g in gaps:
            if g["role"] in role_keys:
                gap_severity = g["severity"]
                break

        n_capable = len(current_players)
        n_strong  = sum(1 for p in current_players if p["role_score"] >= strong_t)
        if n_capable == 0:
            situation = "No capable player in the squad for this role — immediate signing required."
        elif n_strong == 0:
            situation = f"{n_capable} capable option(s) in the squad but no one above the quality threshold — upgrade needed."
        else:
            situation = f"{n_strong} strong option(s) in the squad — reinforcing depth or quality."

        top_cands = []
        for c in shortlist.get(label, []):
            role_fit  = c.get("shortlist_score", 0)
            adj_score = candidate_score(c, role_fit, dof, total_budget, cfg.get("archetypes_file"))
            top_cands.append({
                **c,
                "role_score":      role_fit,
                "shortlist_score": adj_score,
                "value_low":       c.get("transfer_value_low", 0),
                "value_high":      c.get("transfer_value_high", 0),
            })

        role_label = role_keys[0].replace("_", " ").title() if role_keys else label
        priority_positions.append({
            "position":        label,
            "role":            role_label,
            "role_key":        role_keys[0] if role_keys else "",
            "severity":        gap_severity,
            "situation":       situation,
            "current_players": current_players[:4],
            "top_candidates":  top_cands,
        })

    # ── Young talent (U23 above capable threshold) ───────────────────────────
    young_talent = []
    for p in sorted(squad, key=lambda x: x.get("best_role_score", 0), reverse=True):
        if p.get("age", 30) <= 23 and p.get("best_role_score", 0) >= capable_t:
            young_talent.append({
                "name":            p["name"],
                "age":             p.get("age", "?"),
                "positions_raw":   p.get("positions_raw", ""),
                "best_role":       p.get("best_role", "—"),
                "best_role_score": p.get("best_role_score", 0),
                "wage":            p.get("wage", 0),
            })

    # ── Decline risks (age ≥ 30 and below capable threshold) ─────────────────
    decline_risks = []
    for p in squad:
        age   = p.get("age", 0)
        score = p.get("best_role_score", 0)
        if age >= 30 and score < capable_t:
            decline_risks.append({
                "name":             p["name"],
                "age":              age,
                "role_score":       score,
                "contract_expires": str(p.get("contract_expires", "")),
                "wage":             p.get("wage", 0),
                "best_role":        p.get("best_role", "—"),
            })
    decline_risks.sort(key=lambda x: x["role_score"])

    # ── Contract risks (from analysis) ───────────────────────────────────────
    contract_risks = analysis.get("contract_risks", [])

    # ── Financial audit ───────────────────────────────────────────────────────
    avg_wage = (sum(p.get("wage", 0) for p in squad) / len(squad)) if squad else 0
    overpaid = []
    for p in squad:
        score = p.get("best_role_score", 0)
        wage  = p.get("wage", 0)
        if score < capable_t and wage > avg_wage * 1.5:
            overpaid.append({
                "name":       p["name"],
                "wage":       wage,
                "role_score": score,
                "reason":     "High wage relative to role contribution",
            })
    wage_by_group = analysis.get("wage_by_group", {})

    # ── Who must be sold ─────────────────────────────────────────────────────
    sell_candidates = []
    for p in squad:
        score     = p.get("best_role_score", 0)
        age       = p.get("age", 0)
        val_high  = p.get("transfer_value_high", 0)
        wage      = p.get("wage", 0)
        reasons   = []
        if score < capable_t:
            reasons.append("below capable threshold for any system role")
        if age >= 30 and score < capable_t:
            reasons.append("approaching decline age")
        if score < 45 and val_high > 500_000:
            reasons.append(f"sell while value exists (est. £{val_high:,})")
        if wage > avg_wage * 2 and score < capable_t:
            reasons.append("wage disproportionate to contribution")
        if reasons:
            sell_candidates.append({
                "name":       p["name"],
                "age":        age,
                "role_score": score,
                "value_high": val_high,
                "wage":       wage,
                "reason":     "; ".join(reasons),
            })
    sell_candidates.sort(key=lambda x: x["role_score"])

    return {
        "meta":              meta,
        "squad_health":      squad_health,
        "analysis":          analysis,
        "priority_positions": priority_positions,
        "shortlist":         shortlist,
        "young_talent":      young_talent,
        "decline_risks":     decline_risks,
        "contract_risks":    contract_risks,
        "financial_audit": {
            "overpaid":      overpaid,
            "wage_by_group": wage_by_group,
            "total_weekly":  wages.get("total_weekly", 0),
            "top_earners":   wages.get("top_earners", []),
        },
        "sell_candidates":   sell_candidates,
        # AI fills these — free mode shows data tables only
        "narratives":        {},
    }


def run_report(config: dict) -> str:
    """
    Main pipeline function. Both front doors call this.

    config: the dict returned by config.load()
    Returns: path to the written HTML report.
    """
    from .parser import load_squad
    from .analysis import (
        run_analysis, annotate_players,
        dof_recommended_priorities, load_league_tiers, resolve_league_tier,
    )
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

    # Load context first — needed for league tier before analysis
    context_dir = config.get("context_dir", "context")
    ctx    = _load_context(context_dir)
    meta   = _extract_meta_from_context(ctx, config)
    budget = _extract_budget_from_context(ctx)
    fm_season_year = _extract_fm_season_year(meta.get("fm_season", ""))

    # Resolve league tier from the club's league name
    tiers_data  = load_league_tiers()
    league_tier = resolve_league_tier(meta.get("league", ""), tiers_data)
    print(f"[pipeline] League: {meta.get('league') or 'unknown'} — Tier {league_tier}", flush=True)

    # Load formation / role choices from context/tactic.yaml
    tactic = _load_tactic(context_dir)
    system_positions = None
    tactic_warnings: list[str] = []
    if tactic:
        from .analysis import build_system_positions
        formation = tactic.get("formation", "")
        role_map  = tactic.get("roles", {})
        if formation:
            system_positions, tactic_warnings = build_system_positions(
                formation, role_map, config.get("roles_file")
            )
            print(f"[pipeline] Formation: {formation} ({len(system_positions)} slots)", flush=True)
            for w in tactic_warnings:
                print(f"[pipeline] ⚠  {w}", flush=True)
        else:
            print("[pipeline] tactic.yaml has no formation — using default system.", flush=True)
    else:
        print("[pipeline] No tactic.yaml found — using default 4-3-3 system.", flush=True)

    # API key diagnostic
    api_key = config.get("api_key", "")
    if api_key:
        masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
        print(f"[pipeline] API key detected: {masked}", flush=True)
    else:
        print("[pipeline] No API key — running in free mode (no AI narrative).", flush=True)

    print("[pipeline] Running analysis...", flush=True)
    analysis = run_analysis(
        squad,
        system_positions=system_positions,
        roles_path=config.get("roles_file"),
        league_tier=league_tier,
        fm_season_year=fm_season_year,
    )

    # Bundle all v2 context files for the AI prompt
    ctx_sections = []
    for key in ("club", "tactical-direction", "user-squad-read", "dof-profile"):
        text = ctx.get(key, "").strip()
        if text:
            ctx_sections.append(text)
    meta["club_context"] = "\n\n---\n\n".join(ctx_sections)

    # DoF-recommended priorities (data-driven) drive the shortlist and signing section.
    # The AI compares these against user_squad_read to produce the alignment commentary.
    dof_recs    = dof_recommended_priorities(analysis.get("gaps", []), config.get("dof_mode", "edwards"))
    pri_configs = _build_priorities_config([r["label"] for r in dof_recs], config)

    if market:
        annotate_players(market, config.get("roles_file"))

    report_data = _build_report_data(
        squad, market, analysis, config, meta, pri_configs, budget,
    )
    report_data["dof_recommended"] = dof_recs

    output_path = config.get("output_file", "output/report.html")
    print(f"[pipeline] Writing report to {output_path}...", flush=True)
    path = generate_report(
        report_data,
        output_path,
        api_key=config.get("api_key", ""),
        model=config.get("model", "claude-sonnet-4-6"),
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
