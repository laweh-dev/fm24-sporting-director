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
        ("Squad Size",    str(h.get("squad_size", "—"))),
        ("Squad Depth",   h.get("depth", "—")),
        ("Age Profile",   h.get("age_profile", "—")),
        ("Wages",         h.get("wage_structure", "—")),
        ("Priority Gaps", str(h.get("critical_gaps", 0))),
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
    narr    = (data.get("narratives") or {}).get("executive_summary", "")
    if not narr:
        h = data.get("squad_health", {})
        narr = (
            f"Squad of {h.get('squad_size', '?')} players analysed. "
            f"{h.get('critical_gaps', 0)} critical gap(s) identified. "
            "Running in free mode — add an Anthropic API key to config.yaml to unlock the written narrative."
        )

    paras = "".join(f"<p>{_esc(p)}</p>" for p in narr.split("\n\n") if p.strip())

    h = data.get("squad_health", {})
    inline_stats = [
        (str(h.get("squad_size", "?")),    "Players"),
        (str(h.get("critical_gaps", 0)),   "Critical Gaps"),
        (str(h.get("prime", 0)),           "Prime Age (22–29)"),
        (h.get("wage_structure", "—"),     "Weekly Wages"),
    ]
    stats_html = "".join(f"""
        <div class="headline-stat">
          <span class="headline-stat-value">{_esc(s[0])}</span>
          <div class="headline-stat-label">{_esc(s[1])}</div>
        </div>""" for s in inline_stats)

    free_banner = ""
    if not data.get("meta", {}).get("ai_narrative"):
        free_banner = """
<div class="free-mode-banner">
  <strong>Free mode</strong> — all the analysis and scoring below, without the AI narrative.
  Add an Anthropic API key to config.yaml to generate the written report (costs ~$0.05).
</div>"""

    return f"""
<div class="section-eyebrow">Overview</div>
<div class="section-heading">Executive Summary</div>
{free_banner}
<div class="card card--gold">
  <div class="exec-text">{paras}</div>
  <div class="headline-stats">{stats_html}</div>
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
    narr = data.get("narratives") or {}
    windows = [
        ("This Window",   narr.get("strategic_this_window", "")),
        ("Next Window",   narr.get("strategic_next_window", "")),
        ("1–3 Years",     narr.get("strategic_long_term", "")),
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


# ── AI narrative generation (v2) ──────────────────────────────────────────────

def _generate_narrative(report_data: dict, api_key: str, model: str) -> dict:
    """Single structured AI call returning JSON keyed by section slug."""
    try:
        import anthropic
    except ImportError:
        return {}

    meta          = report_data.get("meta", {})
    analysis      = report_data.get("analysis", {})
    squad         = analysis.get("squad", [])
    gaps          = analysis.get("gaps", [])
    shortlist     = report_data.get("shortlist", {})
    young_talent  = report_data.get("young_talent", [])
    decline_risks = report_data.get("decline_risks", [])
    sell_cands    = report_data.get("sell_candidates", [])
    fa            = report_data.get("financial_audit", {})
    dof_recs      = report_data.get("dof_recommended", [])

    club         = meta.get("club_name", "the club")
    league       = meta.get("league", "")
    dof          = meta.get("dof_mode", "edwards")
    club_context = meta.get("club_context", "").strip()
    user_read    = meta.get("user_squad_read", "").strip()
    tactical     = meta.get("tactical_direction", "").strip()

    def _fmt_squad(players, n=25):
        return "\n".join(
            f"  {p['name']} ({p.get('age','?')}yo) — best: {p.get('best_role','?')} "
            f"[{p.get('best_role_score',0):.0f}], wage: £{p.get('wage',0):,}/w"
            for p in sorted(players, key=lambda x: x.get("best_role_score", 0), reverse=True)[:n]
        )

    def _fmt_gaps(gaps_list):
        return "\n".join(
            f"  [{g['severity'].upper()}] {g['role']}: capable={g['capable']}, strong={g['strong']}"
            for g in gaps_list
        ) or "  None"

    def _fmt_shortlist(sl):
        out = ""
        for label, cands in sl.items():
            out += f"\n  {label}:\n"
            for c in cands[:3]:
                out += (f"    {c['name']} ({c.get('age','?')}yo) — "
                        f"score {c.get('shortlist_score',0):.1f}, "
                        f"fee {_fmt_fee(c.get('value_low',0), c.get('value_high',0))}\n")
        return out or "  None"

    # Pre-compute all string blocks to avoid f-string nesting pitfalls
    _squad_block    = _fmt_squad(squad)
    _gaps_block     = _fmt_gaps(gaps)
    _shortlist_block = _fmt_shortlist(shortlist)
    def _fmt_rec(r):
        txt = r["label"]
        prospects = r.get("high_potential_prospects", [])
        if prospects:
            txt += f" [high-pot prospect: {', '.join(prospects)}]"
        return txt
    _dof_rec_str    = ", ".join(_fmt_rec(r) for r in dof_recs) if dof_recs else "none"
    def _fmt_stars(stars):
        if stars is None:
            return "unrated"
        return f"{'★' * stars}{'☆' * (5 - stars)} ({stars}/5)"

    _young_block    = "\n".join(
        f"  {p['name']} ({p.get('age','?')}yo) — {p.get('best_role','')} [{p.get('best_role_score',0):.0f}]"
        f", AM potential: {_fmt_stars(p.get('potential_stars'))}"
        f"{', personality: ' + p.get('personality') if p.get('personality') else ''}"
        for p in young_talent
    ) or "  None"
    _decline_block  = "\n".join(
        f"  {p['name']} ({p.get('age','?')}yo) — score {p.get('role_score',0):.0f},"
        f" expires {p.get('contract_expires','?')}, wage £{p.get('wage',0):,}/w"
        for p in decline_risks[:10]
    ) or "  None"
    _sell_block     = "\n".join(
        f"  {p['name']} — {p.get('reason','')}"
        for p in sell_cands[:10]
    ) or "  None"
    _wage_block     = "\n".join(
        f"  {g}: £{s.get('total', 0):,}/w ({s.get('count', 0)} players)"
        for g, s in fa.get("wage_by_group", {}).items()
    ) or "  No data"
    _tactical_line  = f"Tactical context: {tactical}" if tactical else ""
    _read_line      = f"Manager squad read: {user_read}" if user_read else ""

    prompt = (
        f"You are the Director of Football at {club} ({league}), writing a formal briefing for the manager.\n"
        f"Your analytical style: {dof}\n"
        f"{_tactical_line}\n"
        f"{_read_line}\n"
        "\n"
        "FULL CONTEXT:\n"
        f"{club_context}\n"
        "\n"
        "SQUAD (top 25 by role fit):\n"
        f"{_squad_block}\n"
        "\n"
        "GAPS IDENTIFIED BY DATA:\n"
        f"{_gaps_block}\n"
        "\n"
        f"DATA-RECOMMENDED PRIORITY POSITIONS: {_dof_rec_str}\n"
        "\n"
        "SIGNING SHORTLIST:\n"
        f"{_shortlist_block}\n"
        "\n"
        "YOUNG TALENT (U23 above capable threshold):\n"
        f"{_young_block}\n"
        "\n"
        "DECLINE & CONTRACT RISKS:\n"
        f"{_decline_block}\n"
        "\n"
        "SELL CANDIDATES:\n"
        f"{_sell_block}\n"
        "\n"
        "WAGE BY GROUP:\n"
        f"{_wage_block}\n"
        "\n"
        "Write an honest, direct briefing. Name specific players. Ground every claim in the data above.\n"
        "Return ONLY valid JSON — no markdown, no code fences, no trailing commas:\n"
        '{\n'
        '  "executive_summary": "3-4 paragraphs, paragraph breaks as \\n\\n. Honest overall verdict.",\n'
        '  "squad_unit_goalkeeper": "2-3 sentences on GK unit quality vs league standard.",\n'
        '  "squad_unit_defence": "2-3 sentences on defensive unit quality.",\n'
        '  "squad_unit_midfield": "2-3 sentences on midfield unit quality.",\n'
        '  "squad_unit_attack": "2-3 sentences on attacking unit quality.",\n'
        '  "priority_areas": "2-3 sentences introducing the priority signing areas and why.",\n'
        '  "priority_reasoning": {\n'
        '    "POSITION_LABEL": "one paragraph — if data flags it: explain the gap. If manager flagged it but data does not: push back or confirm with reasoning."\n'
        '  },\n'
        '  "young_talent": "2-3 sentences on the U23 players and their development path.",\n'
        '  "decline_risks": "2-3 sentences on aging or contract-risk players and the recommended action.",\n'
        '  "financial_audit": "2-3 sentences on wage structure, efficiency, and any imbalances.",\n'
        '  "sell_list": "2-3 sentences introducing the sell list and the logic behind it.",\n'
        '  "strategic_this_window": "2-3 sentences on immediate transfer window actions.",\n'
        '  "strategic_next_window": "2-3 sentences on next window priorities.",\n'
        '  "strategic_long_term": "2-3 sentences on 1-3 year squad trajectory."\n'
        '}'
    )

    client = anthropic.Anthropic(api_key=api_key)
    chunks = []
    try:
        with client.messages.stream(
            model=model,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                chunks.append(chunk)
    except Exception as e:
        print(f"[report] AI call failed: {e}")
        return {"_error": str(e)}

    raw = "".join(chunks).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[report] AI response was not valid JSON: {e}")
        return {"_error": f"AI response parse error: {e}"}


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


# ── New v2 section renderers ─────────────────────────────────────────────────

def _unit_label(position: str) -> str:
    p = position.upper()
    if p in ("GK",):
        return "Goalkeeper"
    if any(p.startswith(x) for x in ("D ", "WB ", "D(", "WB(")):
        return "Defence"
    if any(p.startswith(x) for x in ("DM", "M ", "M(")):
        return "Midfield"
    if any(p.startswith(x) for x in ("AM", "ST", "F ")):
        return "Attack"
    if "GK" in p:
        return "Goalkeeper"
    if p in ("RB", "LB", "CB", "RWB", "LWB"):
        return "Defence"
    if p in ("DM", "CM", "RM", "LM"):
        return "Midfield"
    if p in ("RW", "LW", "ST", "CF", "SS", "AM"):
        return "Attack"
    return "Other"


def _render_current_squad_units(data: dict) -> str:
    matrix  = (data.get("analysis") or {}).get("depth_matrix", [])
    narr    = (data.get("narratives") or {})

    unit_order = ["Goalkeeper", "Defence", "Midfield", "Attack", "Other"]
    units: dict[str, list] = {u: [] for u in unit_order}
    for entry in matrix:
        unit = _unit_label(entry.get("position", ""))
        units.setdefault(unit, []).append(entry)

    def _pc(p):
        if not p:
            return '<span style="color:var(--muted);">—</span>'
        sc = p.get("score", 0)
        return (
            f'<span class="score-chip mono" style="color:{_score_color(sc)};'
            f'background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span> '
            f'<span style="font-size:12px;">{_esc(p["name"])}</span> '
            f'<span style="font-size:11px;color:var(--muted);">({p.get("age","?")})</span>'
        )

    blocks = ""
    for unit in unit_order:
        entries = units.get(unit, [])
        if not entries:
            continue
        rows = ""
        for e in entries:
            rating   = e.get("depth_rating", "")
            row_cls  = "critical-row" if rating == "Critical" else ("thin-row" if rating == "Thin" else "")
            rows += f"""
            <tr class="{row_cls}">
              <td><span class="pos-label">{_esc(e['position'])}</span>
                  <span class="role-name">{_esc(e.get('role_label',''))}</span></td>
              <td>{_pc(e.get('starter'))}</td>
              <td>{_pc(e.get('backup'))}</td>
              <td><div class="depth-rating">{_depth_dot(rating)} {_esc(rating)}</div></td>
            </tr>"""

        unit_narr = narr.get(f"squad_unit_{unit.lower()}", "")
        narr_html = (f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin:12px 0 0;">'
                     f'{_esc(unit_narr)}</p>') if unit_narr else ""

        blocks += f"""
<h3 style="font-family:'Barlow Condensed';font-size:20px;font-weight:700;
   color:var(--gold);margin:24px 0 10px;letter-spacing:.04em;">{_esc(unit)}</h3>
<div class="card" style="padding:0;overflow:hidden;">
  <table class="depth-table">
    <thead><tr><th>Position</th><th>Starter</th><th>Backup</th><th>Depth</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {narr_html}
</div>"""

    return f"""
<div class="section-eyebrow">Squad Assessment</div>
<div class="section-heading">Current Squad</div>
{blocks}
<hr class="divider">"""


def _render_star_pips(stars: int | None) -> str:
    """Render AM potential stars as coloured pip elements."""
    if not stars:
        return '<span style="color:var(--muted);font-size:11px;">unrated</span>'
    filled = "★" * stars
    empty  = "☆" * (5 - stars)
    color  = ("#f59e0b" if stars >= 4 else "#6b7280")
    return (
        f'<span style="color:{color};font-size:14px;letter-spacing:1px;" '
        f'title="AM Potential: {stars}/5 stars">{filled}'
        f'<span style="color:#374151;">{empty}</span></span>'
    )


def _render_young_talent_section(data: dict) -> str:
    players = data.get("young_talent", [])
    narr    = (data.get("narratives") or {}).get("young_talent", "")
    narr_html = (f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:16px;">'
                 f'{_esc(narr)}</p>') if narr else ""

    has_stars = any(p.get("potential_stars") is not None for p in players)

    rows = ""
    for p in players:
        sc    = p.get("best_role_score", 0)
        stars = p.get("potential_stars")
        personality = p.get("personality", "")
        star_cell = (
            f'<td style="white-space:nowrap;">{_render_star_pips(stars)}</td>'
            if has_stars else ""
        )
        personality_html = (
            f'<span style="font-size:10px;color:var(--muted);display:block;">'
            f'{_esc(personality)}</span>'
        ) if personality else ""
        rows += f"""
      <tr>
        <td style="font-size:13px;font-weight:500;">{_esc(p['name'])}{personality_html}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{p.get('age','—')}</td>
        <td style="font-size:11px;color:var(--muted);">{_esc(p.get('positions_raw',''))}</td>
        <td><span class="score-chip mono" style="color:{_score_color(sc)};
            background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span>
            <span style="font-size:11px;color:var(--muted);margin-left:4px;">
              {_esc(p.get('best_role',''))}</span></td>
        {star_cell}
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">
          {_fmt_wage(p.get('wage',0))}</td>
      </tr>"""

    star_header = "<th>AM Potential</th>" if has_stars else ""
    colspan = "6" if has_stars else "5"
    return f"""
<div class="section-eyebrow">Academy &amp; Development</div>
<div class="section-heading">Young Talent to Nurture</div>
{narr_html}
<div class="card" style="padding:0;overflow:hidden;">
  <table class="data-table">
    <thead><tr><th>Player</th><th>Age</th><th>Positions</th><th>Role Score</th>{star_header}<th>Wage</th></tr></thead>
    <tbody>{rows or f"<tr><td colspan='{colspan}' style='color:var(--muted);padding:16px;'>No U23 players above the capable threshold.</td></tr>"}</tbody>
  </table>
</div>
<hr class="divider">"""


def _render_decline_risks_section(data: dict) -> str:
    players       = data.get("decline_risks", [])
    contract_risks = data.get("contract_risks", [])
    narr          = (data.get("narratives") or {}).get("decline_risks", "")
    narr_html     = (f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:16px;">'
                     f'{_esc(narr)}</p>') if narr else ""

    rows = ""
    for p in players:
        sc = p.get("role_score", 0)
        rows += f"""
      <tr>
        <td style="font-size:13px;font-weight:500;">{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{p.get('age','—')}</td>
        <td><span class="score-chip mono" style="color:{_score_color(sc)};
            background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span>
            <span style="font-size:11px;color:var(--muted);margin-left:4px;">
              {_esc(p.get('best_role',''))}</span></td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">
          {_esc(str(p.get('contract_expires','—')))}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">
          {_fmt_wage(p.get('wage',0))}</td>
      </tr>"""

    contract_rows = ""
    for r in contract_risks:
        urgency = r.get("urgency", "risk")
        color   = "var(--red)" if urgency == "urgent" else "var(--amber)"
        contract_rows += f"""
      <tr>
        <td style="font-size:13px;">{_esc(r.get('name',''))}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{r.get('age','—')}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:{color};">
          {_esc(r.get('months_remaining','?'))} mo</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">
          {_fmt_wage(r.get('wage',0))}</td>
      </tr>"""

    contract_section = ""
    if contract_rows:
        contract_section = f"""
<h3 style="font-family:'Barlow Condensed';font-size:18px;font-weight:700;
   margin:20px 0 10px;">Contract Risks (18-24 months)</h3>
<div class="card" style="padding:0;overflow:hidden;">
  <table class="data-table">
    <thead><tr><th>Player</th><th>Age</th><th>Contract Left</th><th>Wage</th></tr></thead>
    <tbody>{contract_rows}</tbody>
  </table>
</div>"""

    return f"""
<div class="section-eyebrow">Risk Register</div>
<div class="section-heading">Decline &amp; Contract Risks</div>
{narr_html}
<div class="card" style="padding:0;overflow:hidden;">
  <table class="data-table">
    <thead><tr><th>Player</th><th>Age</th><th>Role Score</th><th>Expires</th><th>Wage</th></tr></thead>
    <tbody>{rows or "<tr><td colspan='5' style='color:var(--muted);padding:16px;'>None identified.</td></tr>"}</tbody>
  </table>
</div>
{contract_section}
<hr class="divider">"""


def _render_financial_audit_section(data: dict) -> str:
    fa   = data.get("financial_audit", {})
    narr = (data.get("narratives") or {}).get("financial_audit", "")
    narr_html = (f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:16px;">'
                 f'{_esc(narr)}</p>') if narr else ""

    # Wage by position group
    wbg = fa.get("wage_by_group", {})
    group_rows = ""
    for group, stats in wbg.items():
        total = stats.get("total", 0)
        count = stats.get("count", 0)
        avg   = total // count if count else 0
        group_rows += f"""
      <tr>
        <td style="font-size:13px;font-weight:500;">{_esc(group.title())}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{count}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{_fmt_wage(total)}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">{_fmt_wage(avg)}</td>
      </tr>"""

    # Overpaid players
    overpaid_rows = ""
    for p in fa.get("overpaid", []):
        sc = p.get("role_score", 0)
        overpaid_rows += f"""
      <tr>
        <td style="font-size:13px;">{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--amber);">
          {_fmt_wage(p.get('wage',0))}</td>
        <td><span class="score-chip mono" style="color:{_score_color(sc)};
            background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span></td>
        <td style="font-size:11px;color:var(--muted);">{_esc(p.get('reason',''))}</td>
      </tr>"""

    total_w = fa.get("total_weekly", 0)
    total_html = (f'<p style="font-family:\'JetBrains Mono\';font-size:13px;color:var(--muted);'
                  f'margin-bottom:16px;">Total squad wage bill: {_fmt_wage(total_w)} / week</p>') if total_w else ""

    return f"""
<div class="section-eyebrow">Financial Audit</div>
<div class="section-heading">Wage &amp; Budget Review</div>
{narr_html}
{total_html}
<div class="two-col">
  <div>
    <h3 style="font-family:'Barlow Condensed';font-size:18px;font-weight:700;margin-bottom:10px;">
      Wage by Position Group</h3>
    <div class="card" style="padding:0;overflow:hidden;">
      <table class="data-table">
        <thead><tr><th>Group</th><th>Players</th><th>Total/w</th><th>Avg/w</th></tr></thead>
        <tbody>{group_rows or "<tr><td colspan='4' style='color:var(--muted);padding:14px;'>No wage data.</td></tr>"}</tbody>
      </table>
    </div>
  </div>
  <div>
    <h3 style="font-family:'Barlow Condensed';font-size:18px;font-weight:700;margin-bottom:10px;">
      Overpaid Relative to Contribution</h3>
    <div class="card" style="padding:0;overflow:hidden;">
      <table class="data-table">
        <thead><tr><th>Player</th><th>Wage</th><th>Score</th><th>Reason</th></tr></thead>
        <tbody>{overpaid_rows or "<tr><td colspan='4' style='color:var(--muted);padding:14px;'>None identified.</td></tr>"}</tbody>
      </table>
    </div>
  </div>
</div>
<hr class="divider">"""


def _render_sell_candidates_section(data: dict) -> str:
    players = data.get("sell_candidates", [])
    narr    = (data.get("narratives") or {}).get("sell_list", "")
    narr_html = (f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:16px;">'
                 f'{_esc(narr)}</p>') if narr else ""
    rows = ""
    for p in players:
        sc = p.get("role_score", 0)
        rows += f"""
      <tr>
        <td style="font-size:13px;font-weight:500;">{_esc(p['name'])}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;">{p.get('age','—')}</td>
        <td><span class="score-chip mono" style="color:{_score_color(sc)};
            background:rgba({_score_color(sc)[1:]},0.1);">{sc:.0f}</span></td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--gold);">
          {_fmt_fee(0, p.get('value_high',0))}</td>
        <td style="font-family:'JetBrains Mono';font-size:12px;color:var(--muted);">
          {_fmt_wage(p.get('wage',0))}</td>
        <td style="font-size:11px;color:var(--muted);">{_esc(p.get('reason',''))}</td>
      </tr>"""
    return f"""
<div class="section-eyebrow">Outgoings</div>
<div class="section-heading">Who Must Be Sold</div>
{narr_html}
<div class="card" style="padding:0;overflow:hidden;">
  <table class="data-table">
    <thead><tr><th>Player</th><th>Age</th><th>Score</th><th>Est. Value</th><th>Wage</th><th>Reason</th></tr></thead>
    <tbody>{rows or "<tr><td colspan='6' style='color:var(--muted);padding:16px;'>No sell candidates identified.</td></tr>"}</tbody>
  </table>
</div>
<hr class="divider">"""


# ── Main assembler ────────────────────────────────────────────────────────────

def _render_ai_error_banner(meta: dict) -> str:
    ai_error = meta.get("ai_error", "")
    if not ai_error:
        return ""
    return (
        '<div style="background:#7f1d1d;border-left:4px solid #ef4444;padding:14px 20px;'
        'margin:0 0 24px;border-radius:4px;font-size:13px;color:#fca5a5;line-height:1.6;">'
        '<strong style="color:#fca5a5;">AI Narrative Failed</strong> — '
        'This report was generated in free mode because the AI call did not complete. '
        f'Error: {_esc(ai_error)}'
        '</div>'
    )


def generate_html(report_data: dict, roles_path=None) -> str:
    """Assemble the complete v2 HTML report from report_data."""
    meta      = report_data.get("meta", {})
    chart_idx = 0

    # Section 5: Priority Signings — candidate cards with radar charts
    priority_html = ""
    for pos in report_data.get("priority_positions", []):
        section, chart_idx = _render_priority_section(pos, chart_idx, roles_path)
        priority_html += section

    priority_narr = (report_data.get("narratives") or {}).get("priority_areas", "")
    priority_narr_html = (
        f'<p style="color:var(--muted);font-size:13px;line-height:1.7;margin-bottom:16px;">'
        f'{_esc(priority_narr)}</p>'
    ) if priority_narr else ""

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
{_render_ai_error_banner(meta)}
<!-- 1. Cover -->
{_render_cover(report_data)}
<!-- 2. Executive Summary -->
{_render_exec_summary(report_data)}
<!-- 3. Current Squad by unit -->
{_render_current_squad_units(report_data)}
<!-- 4. Squad Depth Matrix -->
{_render_depth_matrix(report_data)}
<!-- 5. Priority Areas (alignment) -->
{_render_priority_alignment(report_data)}
<!-- 6. Priority Signings -->
<div class="section-eyebrow">Transfer Targets</div>
<div class="section-heading">Priority Signings</div>
{priority_narr_html}
{priority_html if priority_html else '<p style="color:var(--muted);">No priority positions identified. Run the setup wizard or export a squad file.</p><hr class="divider">'}
<!-- 7. Young Talent -->
{_render_young_talent_section(report_data)}
<!-- 8. Decline & Contract Risks -->
{_render_decline_risks_section(report_data)}
<!-- 9. Financial Audit -->
{_render_financial_audit_section(report_data)}
<!-- 10. Who Must Be Sold -->
{_render_sell_candidates_section(report_data)}
<!-- 11. Strategic Outlook -->
{_render_strategic_outlook(report_data)}
{_render_footer(report_data)}
</body>
</html>"""


def generate_report(
    report_data: dict,
    output_path: str | Path,
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    roles_path: str | Path | None = None,
) -> str:
    """Build the HTML report, optionally enriching with AI narrative, and write to output_path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if api_key:
        print("[report] Generating AI narrative...", flush=True)
        narr = _generate_narrative(report_data, api_key, model)
        ai_error = narr.pop("_error", None) if narr else None
        real_sections = {k: v for k, v in (narr or {}).items() if not k.startswith("_")}
        if real_sections:
            narratives = report_data.setdefault("narratives", {})
            for key, val in real_sections.items():
                if key != "priority_reasoning":
                    narratives[key] = val
            if "priority_reasoning" in real_sections:
                report_data["priority_reasoning"] = real_sections["priority_reasoning"]
            report_data.setdefault("meta", {})["ai_narrative"] = True
            print("[report] AI narrative applied.", flush=True)
        else:
            msg = ai_error or "empty response"
            print(f"[report] AI call returned nothing ({msg}) — free mode report.", flush=True)
            if ai_error:
                report_data.setdefault("meta", {})["ai_error"] = ai_error
    else:
        print("[report] No API key — generating free mode report.", flush=True)

    html = generate_html(report_data, roles_path)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
