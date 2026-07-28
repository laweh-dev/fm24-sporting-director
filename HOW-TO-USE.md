# 📖 How to Use FM Save Copilot — Step by Step

A complete walkthrough, written for people who have **never touched code or a command line.** If you can play Football Manager, you can use this.

---

## Before you start

You need three things. Two are free, one costs a few pence per report.

| What | Cost | Why |
|------|------|-----|
| Football Manager 2024 | You already have it | Where your save lives |
| Python | Free | The engine the tool runs on |
| Anthropic API key | ~2p per report | Writes the actual report |

> **Want to spend nothing at all?** You can! The tool will still analyse your whole squad and give you scores, rankings, and shortlists for free. You only need the API key for the written "briefing" on top. Skip Part 4 if you want the free version.

> **Prefer the browser?** Click the Open in Colab badge in the README — no Python install needed at all.

---

## Part 1 — Install Python (once)

### Windows
1. Go to **[python.org/downloads](https://www.python.org/downloads/)**
2. Click the big yellow **Download Python** button
3. Open the file that downloads
4. ⚠️ **VERY IMPORTANT:** On the first screen, tick the box that says **"Add Python to PATH"**. The tool won't work without it.
5. Click **Install Now** and wait for it to finish

### Mac
1. Go to **[python.org/downloads](https://www.python.org/downloads/)**
2. Click the big yellow **Download Python** button
3. Open the downloaded file and click through the installer

✅ **Done.** You never have to think about Python again.

---

## Part 2 — Download the tool (once)

1. Go to the tool's GitHub page
2. Click the green **`<> Code`** button near the top right
3. Click **Download ZIP**
4. Find the downloaded ZIP and **unzip it** — Windows: right-click → Extract All. Mac: double-click it.
5. Move the unzipped folder somewhere easy to find, like your **Desktop**

---

## Part 3 — Set up the tool (once)

Inside the `fm24-sporting-director` folder, find the setup file:

- **Windows:** double-click **`setup.bat`**
- **Mac:** double-click **`setup.command`**

A window will open and text will scroll past. This is normal — it's installing what the tool needs. When it says **"Setup complete!"** you can close the window.

> **Mac blocking you?** Right-click the file → **Open** → **Open**. You only need to do this the first time.

✅ **Done.** Setup only happens once.

---

## Part 4 — Add your API key (once) — *skip for the free version*

### Get the key
1. Go to **[console.anthropic.com](https://console.anthropic.com)**
2. Create a free account
3. Click **Billing** and add a little credit — **£5 is hundreds of reports**
4. Click **API Keys** → **Create Key**
5. Copy the key (a long string of letters and numbers)

### Put the key in the tool
1. In the folder, open the **`config`** folder
2. Find the file **`config.example.yaml`**
3. Make a copy of it and rename the copy to **`config.yaml`** (remove ".example")
4. Open `config.yaml` in Notepad (Windows) or TextEdit (Mac)
5. Find the line that says `api_key: ""`
6. Paste your key between the quote marks: `api_key: "sk-ant-your-actual-key"`
7. Save the file and close it

> 🔒 **Is this safe?** Yes. Your key never leaves your computer. It is never uploaded anywhere.

---

## Part 5 — Set up your FM24 export view (once)

FM needs to know which player information to export. You set up a "view" with the right columns once, save it, and reuse it forever.

👉 **Follow the [VIEW-SETUP.md](VIEW-SETUP.md) guide** for the exact columns and how to save the view. It takes about 5 minutes.

---

## Part 6 — Tell the tool about your club (once, then tweak)

Open the **`context`** folder. There are files here that tell your Director of Football about your club. Open each in Notepad/TextEdit and fill in your details:

| File | What to put in it |
|------|-------------------|
| **`club.md`** | Your league, budget, wage room, and board objectives |
| **`playing-style.md`** | Your formation and the roles you play |
| **`window-priorities.md`** | What you're hoping to sign or sell this window |
| **`dof-profile.md`** | Which Director of Football style you want (Edwards is the default) |

Or — run the **Setup Wizard** (offered automatically after setup) which fills these in through simple questions.

---

## Part 7 — Export your squad from FM24 (each time you want a report)

Inside FM24:

1. Load your save
2. Go to your **Squad** screen
3. Apply your saved custom view (from Part 5)
4. Press **`Ctrl + A`** — selects every player
5. Press **`Ctrl + P`** — a menu appears
6. Choose **Web Page** and save as **`squad.html`** into the tool's **`data_uploads`** folder

**For transfer targets:**
7. Go to **Scouting → Players in Range**
8. Same view, **`Ctrl + A`**, **`Ctrl + P`**
9. Save as **`market.html`** into the **`data_uploads`** folder

---

## Part 8 — Generate your report! (each time)

- **Windows:** double-click **`run.bat`**
- **Mac:** double-click **`run.command`**

Wait about 15–30 seconds. Your report will **open automatically in your web browser**.

🎉 **That's your Director of Football report.**

---

## Doing it again next window

Once set up, generating a new report is just:

1. Export `squad.html` and `market.html` from FM (Part 7)
2. Double-click `run.bat` / `run.command` (Part 8)

Two steps. Thirty seconds. Do it every transfer window.

---

## 🆘 Troubleshooting

**"Python is not recognised" / "command not found"**
Python didn't install correctly, or "Add Python to PATH" wasn't ticked on Windows. Reinstall Python and make sure that box is ticked.

**The setup window flashed and closed instantly**
Right-click the setup file and choose "Run as administrator" (Windows) or open via right-click → Open (Mac).

**"No config file found"**
You haven't created `config.yaml` yet. Copy `config/config.example.yaml` → `config/config.yaml`.

**"Squad file not found"**
Your FM export isn't in the right place. Make sure it's saved as `data_uploads/squad.html` inside the tool folder.

**My report has no players / wrong numbers**
Your FM export is missing columns. Double-check your view against [VIEW-SETUP.md](VIEW-SETUP.md).

**Still stuck?**
[Open an issue on GitHub](../../issues) with any error message you see.

---

## 💡 Tips

- **Save your FM view** so you don't rebuild it each time
- **Try different DoF modes** on the same squad — they give genuinely different advice
- **Update your context files** as your save evolves — new budget, new priorities
- **Generate a report each window** to keep the advice current

---

*Happy managing. May your Director of Football serve you better than the board deserves.* ⚽
