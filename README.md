<div align="center">

# ⚽ FM Save Copilot

### Your Football Manager 2024 squad, analysed by a Director of Football.

*Export your squad. Get a full scouting dossier with transfer targets, squad gaps, radar charts, and a strategic plan — written in the style of football's greatest sporting directors.*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/laweh-dev/fm24-sporting-director/blob/main/notebooks/FM_Save_Copilot.ipynb)

[Getting Started](#-getting-started) · [How It Works](#-how-it-works) · [The DoF Modes](#-director-of-football-modes) · [FAQ](#-faq)

</div>

---

## What is this?

Football Manager gives you a squad. It doesn't give you a **Director of Football** — someone who looks at your whole club strategically and tells you what to do about it.

FM Save Copilot is that missing layer. You export your squad from FM24, and the tool produces a full **Director of Football report**: where you're strong, where you're exposed, who to sign, who to sell, what to train, and how to plan across multiple transfer windows.

It doesn't just say *"you need a left-back."* It says *"your left-back situation is a two-window problem — here's the 23-year-old who fits your system, here's the risk, and here's what it costs."*

The analysis is shaped by the philosophy of real sporting directors — **Michael Edwards**, **Monchi**, **Edu**, and more — so the advice reflects how the best in the world actually build squads.

---

## ✨ What you get

- **Squad depth analysis** — every position rated against your actual tactical system, not generic star ratings
- **Transfer targets** — real candidates from the FM database, ranked by how well they fit your system, your budget, and your needs
- **Radar charts** — see each target's attributes overlaid against the ideal profile for the role
- **Sell targets** — players whose market value exceeds their value to your system
- **A strategic plan** — multi-window thinking, contract risks, age-profile management
- **A beautiful report** — dark, data-dense, shareable. Looks like a real scouting dossier.

---

## 🚀 Getting Started

There are **two ways** to use FM Save Copilot:

### Option A — Google Colab (easiest, no install)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/laweh-dev/fm24-sporting-director/blob/main/notebooks/FM_Save_Copilot.ipynb)

Click the badge above. No Python installation needed. Upload your FM exports directly in the browser.

### Option B — Local Install (offline, faster, data stays on your machine)

> **Never used a command line before? Don't worry.** Follow these steps exactly and you'll be fine.

**What you'll need:**
1. **Football Manager 2024** (obviously)
2. **Python** — free, installed in Step 1
3. **An Anthropic API key** — for the written report (~2p per report, or skip for free analysis-only mode)

**Step 1 — Install Python**

Windows: [python.org/downloads](https://python.org/downloads) → tick **"Add Python to PATH"** → Install Now

Mac: [python.org/downloads](https://python.org/downloads) → download and install

**Step 2 — Download this tool**

Click the green **`<> Code`** button → **Download ZIP** → unzip to your Desktop

**Step 3 — Set up the tool**

- Windows: double-click **`setup.bat`**
- Mac: right-click **`setup.command`** → Open → Open (only needed first time)

**Step 4 — Add your API key** *(skip for free mode)*

1. Get a key at [console.anthropic.com](https://console.anthropic.com) (£5 = hundreds of reports)
2. Copy `config/config.example.yaml` → `config/config.yaml`
3. Open `config.yaml`, paste your key in `api_key: ""`

**Step 5 — Export your squad from FM24**

Set up the custom view (see [VIEW-SETUP.md](VIEW-SETUP.md)), then:
- Squad screen → Ctrl+A → Ctrl+P → Web Page → save as `squad.html` in `data_uploads/`
- Scouting screen → same process → save as `market.html` in `data_uploads/`

**Step 6 — Generate your report**

- Windows: double-click **`run.bat`**
- Mac: double-click **`run.command`**

Your report opens in your browser. **That's it.** 🎉

See [HOW-TO-USE.md](HOW-TO-USE.md) for the full walkthrough.

---

## 🎩 Director of Football Modes

| Mode | Philosophy | Best for |
|------|-----------|----------|
| **Michael Edwards** | Data-driven, system-first. Finds players whose profile predicts success in your tactics. | Analytical managers who want efficiency and value |
| **Monchi** | Market trader. Buy undervalued, develop, sell high, reinvest. | Selling clubs and buy-to-sell models |
| **Edu** | Profile-first squad building. Age structure, wage discipline, clear identity. | Rebuilds and long-term projects |
| *(more coming — contributions welcome!)* | | |

---

## 🔧 How It Works

```
Your FM24 squad export  ──┐
                          │
Your market export  ──────┤
                          ├──►  [ Local analysis on your computer — FREE ]
Your tactical system  ────┤         · Scores every player against every role
(context files)           │         · Finds gaps, risks, opportunities
                          │         · Filters thousands of players to a shortlist
                          │
                          └──►  [ AI writes the report — ~2p ]
                                    · Turns the analysis into a DoF briefing
                                    · In the voice of your chosen archetype
                                              │
                                              ▼
                                    📄  Your Director of Football Report
```

All the heavy number-crunching happens on your computer for free. The AI only writes the final narrative from a small summary — your 35,000-player database never gets uploaded anywhere.

See [WORKFLOW.md](WORKFLOW.md) for the full technical diagram.

---

## ❓ FAQ

**Do I have to pay to use this?**
No. The full squad analysis runs free on your computer. You only pay (pennies) if you want the AI-written narrative on top.

**How much does the report actually cost?**
About **2p per report** with default settings. £5 of credit lasts hundreds of reports. You pay Anthropic directly.

**Is this cheating?**
No more than a scouting spreadsheet. The tool only uses data FM already shows you — no hidden attributes, no CA/PA, no save-file hacking.

**Will this work with FM25 / FM26?**
It's built for FM24. Other versions export slightly differently. Community contributions to support other versions are welcome!

**My export isn't parsing correctly.**
Check your custom view has all the required columns from [VIEW-SETUP.md](VIEW-SETUP.md). If it still fails, [open an issue](../../issues) with the first few lines of your HTML file.

---

## 🤝 Contributing

Contributions are very welcome — especially:
- **New DoF archetypes** (Rangnick? Txiki? Damian Comolli?)
- **Role attribute weightings** — disagree with how a Mezzala is scored? PR it.
- **Support for other FM versions**
- **A friendlier UI for non-technical users**

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## ☕ Support

This tool is free and always will be. If it's helped your save:

**[☕ Buy me a coffee](https://buymeacoffee.com/laweh)**

A star on the repo ⭐ helps just as much.

---

## 📜 License

MIT — do what you like with it.

---

<div align="center">

*Not affiliated with Sports Interactive or SEGA. Football Manager is a trademark of Sports Interactive. This is a fan-made tool.*

**Made by a fan who just wanted a proper Director of Football.**

</div>
