# 🤝 Contributing to FM Save Copilot

Thanks for wanting to make this better! This project thrives on community input — especially from people who know FM inside out.

You don't have to be a hardcore programmer to contribute. Some of the most valuable contributions are just football knowledge.

---

## Ways to contribute

### 🎩 New Director of Football archetypes
This is the most fun contribution. Each archetype is defined in `data/archetypes.yaml` — it describes how a sporting director thinks, talks, and prioritises, plus a set of score weights.

Want a **Ralf Rangnick** mode (pressing-obsessed, athletic profiles)? A **Txiki Begiristain** mode (technical, positional play)? Write the profile, tune the weightings, submit a PR.

Look at the existing archetypes in `data/archetypes.yaml` and the voice template in `context/dof-profile.md` for the format to follow.

### ⚖️ Role attribute weightings
Think a Mezzala needs more Vision and less Stamina? Disagree with how a Ball-Playing Defender is scored? The role definitions live in `data/roles.yaml`. Tweak the weightings, explain your reasoning in the PR, and let's discuss. Football opinions welcome.

### 🎮 Support for other FM versions
The parser is built for FM24's export format. FM23, FM25, and FM26 export slightly differently. If you play another version and can share a sample export, that helps enormously.

### 🖥️ A friendlier interface
The current tool is command-line based. Anything that makes it easier for non-technical FM players would open it up to way more people.

### 🐛 Bug reports
Found something broken? [Open an issue](../../issues). Include:
- What you were doing
- What happened vs what you expected
- Any error message (copy the whole thing)
- The first few lines of your HTML export if it's a parsing issue

---

## How to submit a change

1. Fork this repo
2. Make your changes
3. Test them against your own save if you can
4. Open a pull request describing what you changed and why

Don't worry about getting it perfect — open the PR and we'll work through it together.

---

## A note on scope

This tool deliberately only uses data FM already shows the player. **No hidden attributes, no Current/Potential Ability, no save-file memory scanning.** Contributions should respect that — it keeps the tool fair and accessible to everyone.

---

## Code style

Keep it simple and readable. This project is used and modified by people who aren't professional developers — clarity beats cleverness.

---

Thanks for helping build the Director of Football that FM never gave us. ⚽
