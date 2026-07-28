"""Generate the HTML Director of Football report.

Consumes the structured output from pipeline.py.
If an API key is available, calls the AI for narrative sections.
Falls back gracefully (free mode) to data-only sections when no key is set.
"""

from __future__ import annotations

import html as _html
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

# ── CSS / design tokens ───────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:      #0D0F14; --surface: #141720; --border: #1E2330;
  --text:    #E8E3D5; --muted:   #9BA3B2; --gold:   #C8A96E;
  --gold-dim:rgba(200,169,110,0.15);
  --green:   #2ECC71; --amber:  #F39C12; --red:    #E74C3C; --blue: #3498DB;
}
html { scroll-behavior:smooth; }
body { background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;
  font-size:14px;line-height:1.65;max-width:1000px;margin:0 auto;
  padding:0 28px 64px;font-variant-numeric:tabular-nums; }
h1,h2,h3,.display,.pos-label,.badge,.section-eyebrow {
  font-family:'Barlow Condensed',sans-serif;letter-spacing:.03em; }
.mono { font-family:'JetBrains Mono',monospace; }
/* Cover */
.cover{padding:56px 0 48px;border-bottom:1px solid var(--border);}
.cover-eyebrow{font-family:'Barlow Condensed';font-size:14px;letter-spacing:.15em;
  text-transform:uppercase;color:var(--muted);margin-bottom:12px;}
.cover-title{font-family:'Barlow Condensed';font-size:64px;font-weight:800;
  color:var(--gold);line-height:1;margin-bottom:8px;text-transform:uppercase;}
.cover-subtitle{font-size:18px;color:var(--muted);margin-bottom:20px;}
.cover-meta{display:flex;align-items:center;gap:12px;margin-bottom:32px;}
.pill{display:inline-block;padding:4px 12px;border:1px solid var(--gold);
  border-radius:20px;font-size:12px;color:var(--gold);font-family:'Barlow Condensed';letter-spacing:.08em;}
.health-bar{display:flex;gap:24px;flex-wrap:wrap;padding:20px;
  background:var(--surface);border-radius:8px;border:1px solid var(--border);}
.health-item{display:flex;flex-direction:column;gap:4px;}
.health-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-family:'Barlow Condensed';}
.health-value{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:500;}
.health-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0;}
/* Sections */
.section-eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;
  color:var(--gold);margin:40px 0 4px;font-family:'Barlow Condensed';}
.section-heading{font-size:32px;font-weight:800;color:var(--text);margin-bottom:20px;line-height:1.1;}
.divider{border:none;border-top:1px solid var(--border);margin:40px 0;}
/* Cards */
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px;}
.card--gold{border-left:3px solid var(--gold);}
/* Exec summary */
.exec-text p{color:var(--muted);margin-bottom:12px;font-size:14px;line-height:1.7;}
.headline-stats{display:flex;gap:32px;margin-top:20px;padding-top:20px;border-top:1px solid var(--border);flex-wrap:wrap;}
.headline-stat{display:flex;flex-direction:column;gap:2px;}
.headline-stat-value{font-family:'Barlow Condensed';font-size:40px;font-weight:800;color:var(--gold);}
.headline-stat-label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
/* Tables */
.depth-table,.data-table,.mini-table{width:100%;border-collapse:collapse;}
.depth-table th,.data-table th,.mini-table th{
  font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  font-family:'Barlow Condensed';padding:10px 12px;text-align:left;
  border-bottom:1px solid var(--border);}
.depth-table td,.data-table td,.mini-table td{
  padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}
.depth-table tr:last-child td,.data-table tr:last-child td,.mini-table tr:last-child td{border-bottom:none;}
.depth-table .critical-row td:first-child{border-left:3px solid var(--red);}
.depth-table .thin-row td:first-child{border-left:3px solid var(--amber);}
.pos-label{display:inline-block;font-family:'Barlow Condensed';font-size:13px;font-weight:700;
  color:var(--gold);background:var(--gold-dim);padding:2px 6px;border-radius:4px;margin-right:6px;}
.role-name{font-size:12px;color:var(--muted);}
.score-chip{display:inline-block;padding:2px 7px;border-radius:12px;font-size:12px;font-weight:600;}
.depth-rating{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:500;}
/* Priority sections */
.priority-section{margin-bottom:0;}
.priority-header{display:flex;justify-content:space-between;align-items:flex-start;
  margin-bottom:12px;flex-wrap:wrap;gap:8px;}
.priority-pos-name{font-family:'Barlow Condensed';font-size:48px;font-weight:800;
  color:var(--text);line-height:1;}
.priority-role-name{font-size:14px;color:var(--muted);margin-top:2px;}
.badge{display:inline-block;padding:4px 12px;border-radius:4px;
  font-family:'Barlow Condensed';font-size:13px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;}
.badge--critical{background:var(--red);color:#fff;}
.badge--high{background:var(--amber);color:#0D0F14;}
.badge--medium{background:var(--blue);color:#fff;}
.situation-line{color:var(--muted);font-size:13px;margin-bottom:16px;font-style:italic;}
.candidates-grid{display:flex;flex-direction:column;gap:16px;margin-top:16px;}
/* Candidate cards */
.candidate-card{background:var(--surface);border:1px solid var(--border);
  border-radius:8px;overflow:hidden;}
.candidate-header{padding:16px 20px;background:rgba(30,35,48,0.6);
  border-bottom:1px solid var(--border);}
.candidate-name{font-family:'Barlow Condensed';font-size:24px;font-weight:700;color:var(--text);}
.candidate-meta{font-size:12px;color:var(--muted);margin-top:2px;}
.candidate-score-row{display:flex;align-items:baseline;gap:8px;margin-top:8px;}
.role-score-big{font-family:'JetBrains Mono';font-size:36px;font-weight:500;line-height:1;}
.role-score-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.candidate-details{display:flex;gap:0;border-bottom:1px solid var(--border);}
.candidate-detail{flex:1;padding:10px 16px;border-right:1px solid var(--border);}
.candidate-detail:last-child{border-right:none;}
.candidate-detail-label{display:block;font-size:10px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);margin-bottom:2px;}
.candidate-detail-value{font-family:'JetBrains Mono';font-size:12px;color:var(--text);}
.candidate-body{padding:16px 20px;display:grid;grid-template-columns:200px 1fr;
  gap:20px;align-items:start;}
@media(max-width:600px){.candidate-body{grid-template-columns:1fr;}}
.radar-wrap{width:200px;height:200px;flex-shrink:0;}
.attr-rows{display:flex;flex-direction:column;gap:8px;}
.attr-row{display:flex;align-items:center;gap:8px;}
.attr-name{font-size:11px;color:var(--muted);min-width:90px;text-align:right;}
.attr-track{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden;}
.attr-fill{height:100%;border-radius:2px;transition:width .3s;}
.attr-num{font-family:'JetBrains Mono';font-size:12px;min-width:20px;text-align:right;}
.attr-warn{color:var(--amber);font-size:10px;}
.verdict-block{grid-column:1/-1;margin-top:8px;padding:12px 14px;
  background:var(--gold-dim);border-left:3px solid var(--gold);border-radius:4px;
  font-size:13px;color:var(--muted);line-height:1.6;}
.verdict-label{font-family:'Barlow Condensed';font-size:12px;font-weight:700;
  color:var(--gold);letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px;}
/* Misc */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:600px){.two-col{grid-template-columns:1fr;}}
.outlook-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
@media(max-width:700px){.outlook-grid{grid-template-columns:1fr;}}
.outlook-window-label{font-family:'Barlow Condensed';font-size:13px;font-weight:700;
  color:var(--gold);letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px;}
.outlook-text{font-size:13px;color:var(--muted);line-height:1.6;}
.footer{padding:32px 0;margin-top:40px;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
.footer-brand{font-family:'Barlow Condensed';font-size:18px;font-weight:700;color:var(--gold);}
.free-mode-banner{background:rgba(52,152,219,0.1);border:1px solid var(--blue);
  border-radius:8px;padding:16px 20px;margin-bottom:20px;color:var(--muted);font-size:13px;}
/* Priority Alignment */
.align-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin-bottom:32px;}
.align-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 20px;}
.align-card.align-agreed{border-left:3px solid var(--green);}
.align-card.align-dof{border-left:3px solid var(--amber);}
.align-card.align-user{border-left:3px solid var(--blue);}
.align-header{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;}
.align-badge{font-family:'Barlow Condensed';font-size:11px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;padding:2px 8px;border-radius:3px;}
.badge-agreed{background:rgba(46,204,113,.12);color:var(--green);}
.badge-dof{background:rgba(243,156,18,.12);color:var(--amber);}
.badge-user{background:rgba(52,152,219,.12);color:var(--blue);}
.align-pos{font-family:'Barlow Condensed';font-size:32px;font-weight:800;color:var(--text);line-height:1;}
.align-sev{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;padding:2px 6px;border-radius:3px;margin-left:auto;}
.sev-critical{background:rgba(231,76,60,.15);color:var(--red);}
.sev-weak{background:rgba(243,156,18,.15);color:var(--amber);}
.sev-thin{background:rgba(52,152,219,.1);color:var(--blue);}
.align-text{font-size:13px;color:var(--muted);line-height:1.6;}
@media print{body{background:white;color:black;}
  .card{border:1px solid #ccc;background:white;}.cover-title{color:#333;}}
"""

_ATTR_LABELS = {
    "pace": "Pace", "acceleration": "Acceleration", "stamina": "Stamina",
    "strength": "Strength", "aggression": "Aggression", "bravery": "Bravery",
    "determination": "Determination", "work_rate": "Work Rate", "vision": "Vision",
    "passing": "Passing", "crossing": "Crossing", "technique": "Technique",
    "heading": "Heading", "finishing": "Finishing", "long_shots": "Long Shots",
    "first_touch": "First Touch", "dribbling": "Dribbling", "marking": "Marking",
    "tackling": "Tackling", "positioning": "Positioning", "anticipation": "Anticipation",
    "concentration": "Concentration", "decisions": "Decisions", "composure": "Composure",
    "off_the_ball": "Off The Ball", "teamwork": "Teamwork", "leadership": "Leadership",
    "reflexes": "Reflexes", "handling": "Handling", "one_on_ones": "One v One",
    "command_of_area": "Cmd of Area", "kicking": "Kicking", "throwing": "Throwing",
    "communication": "Communication", "aerial_reach": "Aerial Reach",
    "jumping_reach": "Jumping", "flair": "Flair", "agility": "Agility",
    "balance": "Balance", "rushing_out": "Rushing Out", "natural_fitness": "Nat Fitness",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return _html.escape(str(s))


def _score_color(s: float) -> str:
    if s >= 75: return "#2ECC71"
    if s >= 50: return "#F39C12"
    return "#E74C3C"


def _depth_dot(rating: str) -> str:
    c = {"Strong": "#2ECC71", "Adequate": "#F39C12", "Thin": "#F39C12", "Critical": "#E74C3C"}.get(rating, "#9BA3B2")
    return f'<span style="color:{c};font-size:16px;">●</span>'


def _fmt_fee(low: int, high: int) -> str:
    def _f(v: int) -> str:
        if v >= 1_000_000: return f"£{v/1_000_000:.1f}m"
        if v >= 1_000:     return f"£{v/1_000:.0f}k"
        return "—"
    if low == 0 and high == 0: return "Unknown"
    if low == high:            return _f(low)
    return f"{_f(low)}–{_f(high)}"


def _fmt_wage(w: int) -> str:
    return f"£{w:,}/w" if w else "—"


def _dot_color(val: str) -> str:
    low  = {"critical", "broken", "thin"}
    high = {"strong", "healthy", "young", "balanced"}
    v = val.lower()
    if any(x in v for x in low):  return "#E74C3C"
    if any(x in v for x in high): return "#2ECC71"
    return "#F39C12"


def _ideal_from_role(role_key: str, n: int = 8, roles_path: str | Path | None = None) -> dict:
    try:
        from .roles import load_roles
        roles = load_roles(roles_path)
        role_def = roles.get(role_key, {})
        attrs_def = role_def.get("attributes", {})
        # Flatten all tiers and sort by weight desc
        flat: list[tuple[str, int]] = []
        for tier, weight in (("key", 5), ("important", 3), ("useful", 1)):
            for attr in attrs_def.get(tier, []):
                flat.append((attr, weight))
        flat.sort(key=lambda x: x[1], reverse=True)
        # Map weight → ideal value
        w_to_ideal = {5: 16, 3: 13, 1: 11}
        return {attr: w_to_ideal[w] for attr, w in flat[:n]}
    except Exception:
        return {}


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_cover(data: dict) -> str:
    h = data.get("squad_health", {})
    health_items = [
        ("Squad Depth",   h.get("depth", "—")),
        ("Age Profile",   h.get("age_profile", "—")),
        ("Wages",         h.get("wage_structure", "—")),
        ("Priority Gaps", str(h.get("critical_gaps", 0))),
        ("Budget Used",   h.get("budget_committed", "—")),
    ]
    health_html = "".join(f"""
        <div class="health-item">
          <div class="health-label">{_esc(label)}</div>
          <div class="health-value">
            <span class="health-dot" style="background:{_dot_color(val)};"></span>
            {_esc(val)}
          </div>
        </div>""" for label, val in health_items)

    meta = data.get("meta", {})
    return f"""
<div class="cover">
  <div class="cover-eyebrow">Director of Football Report</div>
  <div class="cover-title">{_esc(meta.get('club_name', 'Squad Report'))}</div>
  <div class="cover-subtitle">{_esc(meta.get('window', 'Transfer Window'))}</div>
  <div class="cover-meta">
    <span class="pill">{_esc(meta.get('dof_mode', 'edwards').title())} Mode</span>
    <span style="color:var(--muted);font-size:13px;">Generated {_esc(meta.get('generated', ''))}</span>
  </div>
  <div class="health-bar">{health_html}</div>
</div>"""


def _render_exec_summary(data: dict) -> str:
    summary = data.get("executive_summary", "")
    if not summary:
        analysis = data.get("analysis", {})
        n_crit = analysis.get("n_critical", 0)
        n_weak = analysis.get("n_weak", 0)
        squad_size = analysis.get("squad_size", 0)
        summary = (
            f"Squad of {squad_size} players analysed. "
            f"{n_crit} critical gap(s), {n_weak} weak position(s) identified. "
            "Run in free mode — add an API key for the written narrative."
        )

    paras = "".join(f"<p>{_esc(p)}</p>" for p in summary.split("\n\n") if p.strip())

    stats = data.get("headline_stats", [])
    stats_html = "".join(f"""
        <div class="headline-stat">
          <span class="headline-stat-value">{_esc(s['value'])}</span>
          <div class="headline-stat-label">{_esc(s['label'])}</div>
        </div>""" for s in stats)

    free_banner = ""
    if not data.get("meta", {}).get("ai_narrative"):
        free_banner = """
<div class="free-mode-banner">
  <strong>Free mode</strong> — all the analysis and scoring below, without the AI narrative.
  Add an Anthropic API key to config.yaml to generate the written report (costs ~2p).
</div>"""

    return f"""
<div class="section-eyebrow">Overview</div>
<div class="section-heading">Executive Summary</div>
{free_banner}
<div class="card card--gold">
  <div class="exec-text">{paras}</div>
  {"<div class='headline-stats'>" + stats_html + "</div>" if stats_html else ""}
</div>
<hr class="divider">"""


def _render_depth_matrix(data: dict) -> str:
    matrix = (data.get("analysis") or {}).get("depth_matrix", [])
    rows = ""
    for entry in matrix:
        starter  = entry.get("starter")
        backup   = entry.get("backup")
        rating   = entry.get("depth_rating", "")
        row_class = "critical-row" if rating == "Critical" else ("thin-row" if rating == "Thin" else "")

        def _pc(p):
            if not p: return '<span style="color:var(--muted);">—</span>'
            sc = p.get("score", 0)
            return (f'<span class="score-chip mono" style="color:{_score_color(sc)};'
                    f'background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span> '
                    f'<span style="font-size:12px;">{_esc(p["name"])}</span> '
                    f'<span style="font-size:11px;color:var(--muted);">({p.get("age","?")})</span>')

        rows += f"""
        <tr class="{row_class}">
          <td><span class="pos-label">{_esc(entry['position'])}</span>
              <span class="role-name">{_esc(entry['role_label'])}</span></td>
          <td>{_pc(starter)}</td><td>{_pc(backup)}</td>
          <td><div class="depth-rating">{_depth_dot(rating)} {_esc(rating)}</div></td>
        </tr>"""

    return f"""
<div class="section-eyebrow">System Coverage</div>
<div class="section-heading">Squad Depth Matrix</div>
<div class="card" style="padding:0;overflow:hidden;">
  <table class="depth-table">
    <thead><tr><th>Position</th><th>Starter</th><th>Backup</th><th>Depth</th></tr></thead>
    <tbody>{rows or "<tr><td colspan='4' style='color:var(--muted);padding:16px;'>No depth data.</td></tr>"}</tbody>
  </table>
</div>
<hr class="divider">"""


def _render_attr_bar(attr: str, value: int, ideal: int) -> str:
    label = _ATTR_LABELS.get(attr, attr.replace("_", " ").title())
    pct   = min(value / 20 * 100, 100)
    warn  = ideal and value < (ideal - 2)
    if value >= 15:    fill = "var(--gold)"
    elif warn:         fill = "var(--red)"
    elif value >= 12:  fill = "var(--text)"
    else:              fill = "var(--muted)"
    warn_icon = ' <span class="attr-warn">▲</span>' if warn else ""
    return f"""
    <div class="attr-row">
      <span class="attr-name">{_esc(label)}</span>
      <div class="attr-track"><div class="attr-fill" style="width:{pct:.0f}%;background:{fill};"></div></div>
      <span class="attr-num" style="color:{fill};">{value}</span>{warn_icon}
    </div>"""


def _render_candidate_card(candidate: dict, chart_idx: int, roles_path=None) -> str:
    sc    = candidate.get("role_score", 0)
    attrs = candidate.get("attributes", {})
    role_key = candidate.get("shortlist_role", candidate.get("role_key", ""))
    ideal = candidate.get("role_ideal") or _ideal_from_role(role_key, 8, roles_path)

    radar_attrs  = [a for a in ideal if a in attrs][:8]
    radar_labels = json.dumps([_ATTR_LABELS.get(a, a) for a in radar_attrs])
    radar_actual = json.dumps([attrs.get(a, 0) for a in radar_attrs])
    radar_ideal  = json.dumps([ideal.get(a, 0) for a in radar_attrs])

    bars = "".join(_render_attr_bar(a, attrs.get(a, 0), ideal.get(a, 0)) for a in radar_attrs)

    verdict = candidate.get("verdict", "")
    verdict_html = (f'<div class="verdict-block"><div class="verdict-label">Verdict</div>'
                    f'{_esc(verdict)}</div>') if verdict else ""

    fee = _fmt_fee(candidate.get("value_low", 0), candidate.get("value_high", 0))

    return f"""
<div class="candidate-card">
  <div class="candidate-header">
    <div class="candidate-name">{_esc(candidate.get('name','Unknown'))}</div>
    <div class="candidate-meta">{_esc(candidate.get('positions_raw',''))}</div>
    <div class="candidate-score-row">
      <div class="role-score-big" style="color:{_score_color(sc)};">{sc:.1f}</div>
      <div class="role-score-label">Role Fit</div>
    </div>
  </div>
  <div class="candidate-details">
    <div class="candidate-detail">
      <span class="candidate-detail-label">Age</span>
      <span class="candidate-detail-value">{candidate.get('age','—')}</span>
    </div>
    <div class="candidate-detail">
      <span class="candidate-detail-label">Contract</span>
      <span class="candidate-detail-value">{_esc(str(candidate.get('contract_expires','—')))}</span>
    </div>
    <div class="candidate-detail">
      <span class="candidate-detail-label">Value</span>
      <span class="candidate-detail-value" style="font-size:11px;">{_esc(fee)}</span>
    </div>
    <div class="candidate-detail">
      <span class="candidate-detail-label">Wage</span>
      <span class="candidate-detail-value">{_esc(_fmt_wage(candidate.get('wage',0)))}</span>
    </div>
  </div>
  <div class="candidate-body">
    <div class="radar-wrap">
      <canvas id="radar-{chart_idx}" style="display:block;"></canvas>
    </div>
    <div class="attr-rows">{bars}</div>
    {verdict_html}
  </div>
</div>
<script>
(function(){{
  var ctx = document.getElementById('radar-{chart_idx}').getContext('2d');
  new Chart(ctx, {{
    type:'radar',
    data:{{
      labels:{radar_labels},
      datasets:[
        {{data:{radar_actual},backgroundColor:'rgba(200,169,110,0.30)',
          borderColor:'#C8A96E',borderWidth:2,pointBackgroundColor:'#C8A96E',pointRadius:3}},
        {{data:{radar_ideal},backgroundColor:'transparent',
          borderColor:'rgba(155,163,178,0.55)',borderWidth:1.5,
          borderDash:[4,3],pointRadius:0}}
      ]
    }},
    options:{{
      responsive:true,maintainAspectRatio:true,
      scales:{{r:{{min:0,max:20,ticks:{{stepSize:5,color:'#9BA3B2',backdropColor:'transparent',
        font:{{family:"'JetBrains Mono'",size:8}}}},
        grid:{{color:'rgba(30,35,48,0.9)'}},angleLines:{{color:'rgba(30,35,48,0.9)'}},
        pointLabels:{{color:'#9BA3B2',font:{{family:"'Inter'",size:9}}}}}}}},
      plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},
      animation:{{duration:600}}
    }}
  }});
}})();
</script>"""


def _render_priority_section(pos_data: dict, chart_idx: int, roles_path=None) -> tuple[str, int]:
    priority  = pos_data.get("priority", "MEDIUM")
    badge_cls = {"CRITICAL": "badge--critical", "HIGH": "badge--high"}.get(priority, "badge--medium")

    curr_rows = "".join(f"""
      <tr><td>{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">{p.get('age','—')}</td>
        <td><span class="score-chip mono" style="color:{_score_color(p.get('role_score',0))}">{p.get('role_score',0):.0f}</span></td>
        <td style="font-family:'JetBrains Mono';font-size:11px;color:var(--muted);">{_fmt_wage(p.get('wage',0))}</td>
      </tr>""" for p in pos_data.get("current_players", []))

    curr_section = (
        f'<table class="mini-table"><thead><tr><th>Current Squad</th>'
        f'<th>Age</th><th>Role Score</th><th>Wage</th></tr></thead>'
        f'<tbody>{curr_rows}</tbody></table>' if curr_rows else ""
    )

    cards_html = ""
    for cand in pos_data.get("top_candidates", [])[:3]:
        cards_html += _render_candidate_card(cand, chart_idx, roles_path)
        chart_idx += 1

    section = f"""
<div class="priority-section">
  <div class="priority-header">
    <div>
      <div class="priority-pos-name">{_esc(pos_data.get('position',''))}</div>
      <div class="priority-role-name">{_esc(pos_data.get('role',''))}</div>
    </div>
    <span class="badge {badge_cls}">{_esc(priority)}</span>
  </div>
  <p class="situation-line">{_esc(pos_data.get('situation',''))}</p>
  {curr_section}
  <div class="candidates-grid">{cards_html}</div>
</div>
<hr class="divider">"""
    return section, chart_idx


def _render_pipeline_table(players: list[dict], title: str, eyebrow: str, cols: list[tuple]) -> str:
    """Generic table renderer: cols = [(header, key|callable, style)]."""
    rows = ""
    for p in players:
        cells = ""
        for _, accessor, style in cols:
            val = accessor(p) if callable(accessor) else p.get(accessor, "—")
            cells += f'<td style="{style}">{_esc(str(val))}</td>'
        rows += f"<tr>{cells}</tr>"

    thead = "".join(f"<th>{h}</th>" for h, _, _ in cols)
    return f"""
<div class="section-eyebrow">{_esc(eyebrow)}</div>
<div class="section-heading">{_esc(title)}</div>
<div class="card" style="padding:0;overflow:hidden;">
  <table class="data-table">
    <thead><tr>{thead}</tr></thead>
    <tbody>{rows or "<tr><td colspan='99' style='color:var(--muted);padding:16px;'>None.</td></tr>"}</tbody>
  </table>
</div>
<hr class="divider">"""


def _render_strategic_outlook(data: dict) -> str:
    outlook = data.get("strategic_outlook", {})
    windows = [
        ("This Window",   outlook.get("this_window", "")),
        ("Next Window",   outlook.get("next_window", "")),
        ("12-Month View", outlook.get("twelve_month", "")),
    ]
    cards = "".join(f"""
      <div class="card">
        <div class="outlook-window-label">{_esc(label)}</div>
        <div class="outlook-text">{_esc(text)}</div>
      </div>""" for label, text in windows if text)

    return f"""
<div class="section-eyebrow">Planning</div>
<div class="section-heading">Strategic Outlook</div>
<div class="outlook-grid">{cards}</div>
<hr class="divider">"""


def _render_footer(data: dict) -> str:
    meta = data.get("meta", {})
    repo_url = "https://github.com/laweh-dev/fm24-sporting-director"
    return f"""
<footer class="footer">
  <a href="{repo_url}" style="text-decoration:none;">
    <span class="footer-brand">FM Save Copilot</span>
  </a>
  <span style="color:var(--muted);font-size:12px;">
    {_esc(meta.get('dof_mode','').title())} Mode · Generated {_esc(meta.get('generated',''))}
  </span>
</footer>"""


# ── AI narrative generation ────────────────────────────────────────────────────

def _generate_narrative(report_data: dict, api_key: str, model: str) -> dict:
    """Call the Anthropic API to generate narrative text for the report sections."""
    try:
        import anthropic
    except ImportError:
        return {}

    analysis = report_data.get("analysis", {})
    squad    = analysis.get("squad", [])
    gaps     = analysis.get("gaps", [])
    shortlist = report_data.get("shortlist", {})

    squad_summary = "\n".join(
        f"  {p['name']} (age {p.get('age','?')}, best role: {p.get('best_role','?')} "
        f"score {p.get('best_role_score',0):.0f}, wage £{p.get('wage',0):,}/w)"
        for p in sorted(squad, key=lambda x: x.get("best_role_score", 0), reverse=True)[:20]
    )
    gap_summary = "\n".join(
        f"  [{g['severity'].upper()}] {g['role']}: capable={g['capable']}, strong={g['strong']}"
        for g in gaps
    )
    shortlist_summary = ""
    for label, cands in shortlist.items():
        shortlist_summary += f"\n{label}:\n"
        for c in cands[:3]:
            shortlist_summary += (
                f"  {c['name']} (age {c.get('age','?')}, score {c.get('shortlist_score',0):.1f}, "
                f"fee {_fmt_fee(c.get('value_low',0), c.get('value_high',0))})\n"
            )

    meta = report_data.get("meta", {})
    club = meta.get("club_name", "the club")
    dof  = meta.get("dof_mode", "edwards")
    club_context = meta.get("club_context", "").strip()

    context_block = (
        f"\nCLUB CONTEXT (use this to shape your analysis — formation, objectives, budget):\n{club_context}\n"
        if club_context else ""
    )

    # Build the priority alignment block for the prompt
    alignment = report_data.get("priority_alignment", {})
    agreed_labels    = [p["label"] for p in alignment.get("agreed", [])]
    user_only_labels = [p["label"] for p in alignment.get("user_only", [])]
    dof_only_labels  = [p["label"] for p in alignment.get("dof_only", [])]
    all_priority_labels = agreed_labels + user_only_labels + dof_only_labels

    alignment_block = ""
    if all_priority_labels:
        alignment_block = f"""
PRIORITY ALIGNMENT:
Both flagged: {", ".join(agreed_labels) or "none"}
Manager wants (data doesn't flag as a gap): {", ".join(user_only_labels) or "none"}
Data flags (manager didn't prioritise): {", ".join(dof_only_labels) or "none"}

For every position listed above, write one direct paragraph in "priority_reasoning":
- Agreed: confirm it's the right call and why
- Manager-only: state whether you agree or have reservations, and your reasoning
- DoF-only: explain the gap and why the manager should make it a priority
"""

    prompt = f"""You are the Director of Football analysing {club}'s squad in the style of '{dof}'.
{context_block}
SQUAD (top 20 by role score):
{squad_summary}

GAPS:
{gap_summary}

SHORTLIST:
{shortlist_summary}
{alignment_block}
Write a Director of Football briefing to the manager. Reflect the formation, objectives, and budget in your analysis. Return ONLY a JSON object:
{{
  "executive_summary": "3-4 paragraphs of honest squad verdict (paragraphs separated by \\n\\n)",
  "strategic_outlook_this_window": "2-3 sentences on immediate transfer actions",
  "strategic_outlook_next_window": "2-3 sentences on the next window",
  "strategic_outlook_twelve_month": "2-3 sentences on 12-month squad trajectory",
  "priority_reasoning": {{
    "POSITION": "one paragraph — agreed: confirm; manager-only: agree or push back with reasons; dof-only: explain the concern"
  }}
}}

Voice: direct, analytical, opinionated. Name specific players. Ground every claim in the data.
No markdown, no code fences — return only the JSON object."""

    client = anthropic.Anthropic(api_key=api_key)
    chunks = []
    try:
        with client.messages.stream(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                chunks.append(chunk)
    except Exception as e:
        print(f"[report] AI call failed: {e}")
        return {}

    raw = "".join(chunks).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


# ── Priority Alignment section ────────────────────────────────────────────────

def _render_priority_alignment(report_data: dict) -> str:
    """Render the three-way priority alignment section (agreed / DoF-only / user-only)."""
    alignment = report_data.get("priority_alignment", {})
    reasoning = report_data.get("priority_reasoning", {})

    agreed    = alignment.get("agreed", [])
    dof_only  = alignment.get("dof_only", [])
    user_only = alignment.get("user_only", [])

    if not agreed and not dof_only and not user_only:
        return ""

    def _card(item: dict, kind: str) -> str:
        label = item["label"]
        sev   = item.get("severity", "")
        # AI reasoning wins; fall back to data-derived text; then generic fallback
        if kind == "user":
            fallback = "The squad data doesn't flag this as a gap — confirm whether this is an upgrade or a necessary signing. The DoF's view is below."
        else:
            fallback = item.get("data_reason", "")
        text = reasoning.get(label) or fallback
        badge = {"agreed": "Both agree", "dof": "DoF flags", "user": "Your call"}[kind]
        sev_html = (f'<span class="align-sev sev-{_esc(sev)}">{_esc(sev.title())}</span>' if sev else "")
        return (
            f'<div class="align-card align-{kind}">'
            f'<div class="align-header">'
            f'<span class="align-badge badge-{kind}">{badge}</span>'
            f'<span class="align-pos">{_esc(label)}</span>'
            f'{sev_html}'
            f'</div>'
            f'<p class="align-text">{_esc(text)}</p>'
            f'</div>'
        )

    cards = (
        [_card(i, "agreed") for i in agreed] +
        [_card(i, "dof")    for i in dof_only] +
        [_card(i, "user")   for i in user_only]
    )

    return (
        '<div class="section-eyebrow">Priority Alignment</div>'
        '<div class="section-heading">Where We Agree — and Where We Need to Talk</div>'
        f'<div class="align-grid">{"".join(cards)}</div>'
        '<hr class="divider">'
    )


# ── Main assembler ────────────────────────────────────────────────────────────

def generate_html(report_data: dict, roles_path=None) -> str:
    """
    Assemble the complete HTML report from report_data.

    report_data structure (built by pipeline.py):
        meta:      {club_name, window, dof_mode, generated, ai_narrative (bool)}
        squad_health: {depth, age_profile, wage_structure, critical_gaps, budget_committed}
        executive_summary: str
        headline_stats: [{value, label}]
        analysis: full analysis dict from analysis.py
        priority_positions: [{position, role, role_key, priority, situation,
                               current_players, top_candidates}]
        shortlist: {label: [candidate]}
        development_pipeline: [{name, age, role_score, best_role, recommendation}]
        decline_risks: [{name, age, role_score, contract_expires, wage, recommendation}]
        wage_audit: {overpaid: [...], sell_candidates: [...]}
        strategic_outlook: {this_window, next_window, twelve_month}
    """
    meta = report_data.get("meta", {})
    chart_idx = 0

    # ── Priority sections
    priority_html = ""
    for pos in report_data.get("priority_positions", []):
        section, chart_idx = _render_priority_section(pos, chart_idx, roles_path)
        priority_html += section

    # ── Development pipeline table
    pipeline_cols = [
        ("Player",         "name",            "font-size:13px;font-weight:500;"),
        ("Age",            "age",             "font-family:'JetBrains Mono';font-size:12px;"),
        ("Role Score",     lambda p: f"{p.get('best_role_score',0):.0f} ({p.get('best_role','')})",
                                              "font-family:'JetBrains Mono';font-size:12px;"),
        ("Recommendation", "recommendation",  "font-size:12px;color:var(--muted);"),
    ]
    pipeline_html = _render_pipeline_table(
        report_data.get("development_pipeline", []),
        "Development Pipeline", "Future Assets", pipeline_cols,
    )

    # ── Decline risks table
    decline_cols = [
        ("Player",   "name",             "font-size:13px;font-weight:500;"),
        ("Age",      "age",              "font-family:'JetBrains Mono';font-size:12px;"),
        ("Score",    lambda p: f"{p.get('role_score',0):.0f}", "font-family:'JetBrains Mono';font-size:12px;"),
        ("Contract", "contract_expires", "font-family:'JetBrains Mono';font-size:12px;color:var(--muted);"),
        ("Wage",     lambda p: _fmt_wage(p.get("wage",0)), "font-family:'JetBrains Mono';font-size:12px;color:var(--muted);"),
        ("Action",   "recommendation",   "font-size:12px;color:var(--muted);"),
    ]
    decline_html = _render_pipeline_table(
        report_data.get("decline_risks", []),
        "Decline & Contract Risks", "Risk Register", decline_cols,
    )

    # ── Wage audit
    wa = report_data.get("wage_audit", {})
    overpaid_rows = "".join(f"""
      <tr><td style="font-size:13px;">{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">{_fmt_wage(p.get('wage',0))}</td>
        <td><span class="score-chip mono" style="color:{_score_color(p.get('role_score',0))}">{p.get('role_score',0):.0f}</span></td>
        <td style="font-size:11px;color:var(--muted);">{_esc(p.get('reason',''))}</td>
      </tr>""" for p in wa.get("overpaid", []))
    sell_rows = "".join(f"""
      <tr><td style="font-size:13px;">{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--gold);">{_fmt_fee(0,p.get('value_high',0))}</td>
        <td><span class="score-chip mono" style="color:{_score_color(p.get('role_score',0))}">{p.get('role_score',0):.0f}</span></td>
        <td style="font-size:11px;color:var(--muted);">{_esc(p.get('reason',''))}</td>
      </tr>""" for p in wa.get("sell_candidates", []))

    def _wa_table(rows, empty_msg):
        return (f'<table class="data-table"><thead><tr>'
                f'<th>Player</th><th>Wage/Value</th><th>Score</th><th>Reason</th>'
                f'</tr></thead><tbody>'
                f'{rows or f"<tr><td colspan=4 style=color:var(--muted);padding:14px;>{empty_msg}</td></tr>"}'
                f'</tbody></table>')

    wage_html = f"""
<div class="section-eyebrow">Financial Audit</div>
<div class="section-heading">Wage &amp; Value Review</div>
<div class="two-col">
  <div>
    <h3 style="font-family:'Barlow Condensed';font-size:18px;margin-bottom:12px;">Overpaid</h3>
    <div class="card" style="padding:0;overflow:hidden;">{_wa_table(overpaid_rows, "None identified.")}</div>
  </div>
  <div>
    <h3 style="font-family:'Barlow Condensed';font-size:18px;margin-bottom:12px;">Sell Candidates</h3>
    <div class="card" style="padding:0;overflow:hidden;">{_wa_table(sell_rows, "None identified.")}</div>
  </div>
</div>
<hr class="divider">"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DoF Report — {_esc(meta.get('club_name',''))}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>{_CSS}</style>
</head>
<body>
{_render_cover(report_data)}
{_render_exec_summary(report_data)}
<div class="section-eyebrow">Formation Analysis</div>
{_render_depth_matrix(report_data)}
{_render_priority_alignment(report_data)}
<div class="section-eyebrow">Transfer Targets</div>
<div class="section-heading">Priority Signings</div>
{priority_html if priority_html else '<p style="color:var(--muted);">No priority positions configured. Run the setup wizard.</p><hr class="divider">'}
{pipeline_html}
{decline_html}
{wage_html}
{_render_strategic_outlook(report_data)}
{_render_footer(report_data)}
</body>
</html>"""


def generate_report(
    report_data: dict,
    output_path: str | Path,
    api_key: str = "",
    model: str = "claude-haiku-4-5",
    roles_path: str | Path | None = None,
) -> str:
    """
    Build the HTML report, optionally enriching with AI narrative, and write to output_path.
    Returns the path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if api_key:
        print("[report] Generating AI narrative...", flush=True)
        narr = _generate_narrative(report_data, api_key, model)
        if narr:
            if "executive_summary" in narr:
                report_data["executive_summary"] = narr["executive_summary"]
            outlook = report_data.setdefault("strategic_outlook", {})
            for field, narr_key in [
                ("this_window",  "strategic_outlook_this_window"),
                ("next_window",  "strategic_outlook_next_window"),
                ("twelve_month", "strategic_outlook_twelve_month"),
            ]:
                if narr_key in narr:
                    outlook[field] = narr[narr_key]
            if "priority_reasoning" in narr:
                report_data["priority_reasoning"] = narr["priority_reasoning"]
            report_data.setdefault("meta", {})["ai_narrative"] = True
            print("[report] AI narrative applied.", flush=True)
        else:
            print("[report] AI call returned nothing — free mode report.", flush=True)
    else:
        print("[report] No API key — generating free mode report.", flush=True)

    html = generate_html(report_data, roles_path)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
