# 🎨 Setting Up Your FM24 Export View

The tool needs specific player information from FM. You set up a custom "view" once, save it, and reuse it every time. Takes about 5 minutes.

---

## Why this is needed

By default, FM's squad screen only shows a handful of columns. The tool needs all the player attributes to do its analysis. A custom view adds those columns, and FM lets you save it so you never have to set it up again.

---

## Step by step

1. In FM24, go to your **Squad** screen
2. Right-click on any column header
3. Choose **Customise Current View** (or **View → Customise**)
4. Add the columns listed below
5. Once added, click the view dropdown → **Save View As** → name it `Copilot Export`
6. From now on, just select this view whenever you want to export

---

## Required columns

Add all of these. The tool reads them by name, so as long as they're present, the order doesn't matter.

### Identity & contract
- Name
- Age
- Position
- Nationality
- Personality
- Media Description
- Height
- Weight
- Wage
- Transfer Value
- Expires (contract expiry)

### Technical attributes
Corners, Crossing, Dribbling, Finishing, First Touch, Free Kick Taking, Heading, Long Shots, Long Throws, Marking, Passing, Penalty Taking, Tackling, Technique

### Mental attributes
Aggression, Anticipation, Bravery, Composure, Concentration, Decisions, Determination, Flair, Leadership, Off the Ball, Positioning, Teamwork, Vision, Work Rate

### Physical attributes
Acceleration, Agility, Balance, Jumping Reach, Natural Fitness, Pace, Stamina, Strength

### Goalkeeper attributes (if you want GK analysis)
Aerial Reach, Command of Area, Communication, Eccentricity, First Touch (GK), Handling, Kicking, One on Ones, Passing (GK), Punching, Reflexes, Rushing Out, Throwing

---

## Exporting once your view is ready

1. Make sure your `Copilot Export` view is selected
2. Press **`Ctrl + A`** to select all players
3. Press **`Ctrl + P`**
4. Choose **Web Page** as the format
5. Save it where the tool expects it:
   - `data_uploads/squad.html` for your squad
   - `data_uploads/market.html` for the transfer market

---

## Getting the transfer market export

For transfer targets, you want a big pool of available players:

1. Go to **Scouting → Players in Range** (or use Player Search with filters)
2. Optionally filter — e.g. players you can afford, within a certain age range
3. Apply your `Copilot Export` view
4. **`Ctrl + A`** → **`Ctrl + P`** → **Web Page**
5. Save as `market.html` in the `data_uploads` folder

> A big market file (30,000+ players) is completely fine. The tool crunches it locally in seconds.

---

## Tip: attribute masking

Make sure **attribute masking is OFF** for the fullest data, or the export may show ranges/dashes for players you haven't fully scouted. You'll find this in Preferences. (Purists who want to respect scouting knowledge can leave it on — the tool handles missing values, it just works better with complete data.)
