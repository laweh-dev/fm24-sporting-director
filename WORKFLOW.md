# 🔄 How FM Save Copilot Works

This document shows how all the pieces fit together — from your FM24 save to a finished Director of Football report.

---

## The big picture

```mermaid
flowchart TD
    A[["🎮 FM24 Save"]] -->|Ctrl+A → Ctrl+P → Web Page| B[squad.html]
    A -->|Scouting screen export| C[market.html]

    B --> D{{"parser.py<br/>Reads the HTML"}}
    C --> D

    D --> E[["Clean player data<br/>(runs on your computer)"]]

    F[/"📁 Context files<br/>your club, style, priorities"/] --> G
    E --> G{{"analysis.py<br/>The number crunching"}}

    G --> H["Role fitness scores<br/>Every player × every role"]
    G --> I["Squad gaps & depth<br/>Age, decline, wage risks"]
    G --> J["Filtered shortlist<br/>~50 best candidates"]

    H --> K{{"report.py<br/>Assembles everything"}}
    I --> K
    J --> K
    L[/"🎩 DoF profile<br/>Edwards / Monchi / Edu"/] --> K

    K -->|"small summary sent to AI<br/>(~2p per report)"| M[["🤖 Claude API<br/>Writes the briefing"]]

    M --> N[["📄 report.html<br/>Your DoF dossier"]]
    K -->|"tables & charts<br/>built locally, free"| N

    style A fill:#2d5a3d,stroke:#4caf50,color:#fff
    style N fill:#5a4a2d,stroke:#C8A96E,color:#fff
    style M fill:#3d3d5a,stroke:#7986cb,color:#fff
    style E fill:#1e2330,stroke:#555,color:#fff
    style G fill:#1e2330,stroke:#555,color:#fff
    style K fill:#1e2330,stroke:#555,color:#fff
```

---

## What happens at each stage

### 1. Export (you do this, in FM24)
You export two HTML files from your save — your squad, and the pool of players you could realistically sign. This is the only manual step, and it takes about 30 seconds once your view is set up.

### 2. Parsing (automatic, free, on your computer)
`parser.py` reads the messy HTML that FM produces and turns it into clean, structured data — every player's attributes, age, wage, positions, and value, ready to analyse.

### 3. Analysis (automatic, free, on your computer)
`analysis.py` is the brain. It:
- Scores every player against every role in **your** tactical system
- Identifies your squad's gaps, depth issues, decline risks, and wage imbalances
- Filters the entire market down to the best candidates for your specific needs

**None of this costs anything.** It's just maths running locally. Your player database never leaves your machine.

### 4. Report assembly (automatic, on your computer)
`report.py` takes all the analysis and builds the visual report — the tables, the depth matrix, the radar charts. Then it sends a **small summary** (just the shortlisted players and your squad analysis) to the AI.

### 5. The AI briefing (~2p, uses your API key)
The AI receives the summary plus your chosen **Director of Football profile** and writes the narrative: the executive summary, the reasoning behind each recommendation, the strategic plan. This is the only step that costs money.

### 6. Your report
Everything comes together as a single `report.html` file that opens in your browser.

---

## The context files — your club's DNA

```mermaid
flowchart LR
    A[club.md<br/>Budget & objectives] --> E((Director of<br/>Football))
    B[playing-style.md<br/>Your tactical system] --> E
    C[window-priorities.md<br/>What you need now] --> E
    D[dof-profile.md<br/>Which archetype] --> E

    style E fill:#5a4a2d,stroke:#C8A96E,color:#fff
```

- **`club.md`** — your budget, wage room, and board objectives (the constraints)
- **`playing-style.md`** — your formation, roles, and how you play (the north star — every player is judged against this)
- **`window-priorities.md`** — what you're looking to do this window
- **`dof-profile.md`** — which sporting director's philosophy shapes the analysis

You fill these in once at the start, then tweak them as your save evolves. The **Setup Wizard** (runs automatically after install) generates them through a set of simple questions.
