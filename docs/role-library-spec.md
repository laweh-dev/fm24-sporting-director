# Role Library — Spec

## What this is

A single source of truth for every FM role, defining which attributes matter for each role and how much. The role library is the foundation of all analysis — role scoring, gap detection, and shortlist filtering all read from it.

Users never interact with the scoring formula directly. They pick a role name; the library supplies the attribute profile.

## The data structure

Each role is defined in `data/roles.yaml`:

```yaml
inverted_wing_back:
  name: "Inverted Wing Back"
  short: "IWB"
  positions: ["DL", "DR", "WBL", "WBR"]
  duties: ["defend", "support", "attack"]
  attributes:
    key:        # weight 5 — defines the role
      - dribbling
      - passing
      - first_touch
      - decisions
      - composure
    important:  # weight 3 — strongly relevant
      - technique
      - vision
      - off_the_ball
      - stamina
      - work_rate
      - teamwork
    useful:     # weight 1 — helpful but not essential
      - acceleration
      - agility
      - balance
      - positioning
      - tackling
  duty_modifiers:
    attack:
      promote: [dribbling, off_the_ball, acceleration]
    defend:
      promote: [positioning, tackling, marking]
```

## Scoring formula

```
raw_score = Σ (attribute_value × tier_weight) for all listed attributes
max_score = Σ (20 × tier_weight) for all listed attributes
role_fit  = (raw_score / max_score) × 100
```

Duty modifiers promote attributes up a tier before scoring. So an IWB (attack) scores `off_the_ball` as key (5×) instead of important (3×).

This gives a clean 0–100 role fitness score comparable across all roles.

## Thresholds

- **Strong:** ≥ 65 — reliable starter for the role
- **Capable:** ≥ 55 — adequate backup
- **Below capable:** < 55 — not suitable for the role

## Attribute names

Internal names use full English (e.g. `acceleration`, `off_the_ball`, `work_rate`) to match `data/roles.yaml`. The mapping from FM export column headers (e.g. `Acc`, `OtB`, `Wor`) to internal names lives in `data/attribute-keys.yaml`.

## Adding new roles

Add a new entry to `data/roles.yaml`. Follow the existing format:
1. Set `positions` to the valid FM position codes (`DL`, `DR`, `DC`, `WBL`, `WBR`, `GK`, `MC`, `ML`, `MR`, `AMC`, `AML`, `AMR`, `DM`, `ST`)
2. Set `duties` to the valid FM duties for this role
3. Assign attributes to key/important/useful tiers based on which attributes most define the role in FM
4. Add `duty_modifiers` where the duty genuinely changes which attributes matter most

The new role will appear automatically in the wizard and all analysis — no code changes needed.

## How archetypes interact with roles

The archetype layer sits **on top** of the role library. Archetypes don't change role attribute definitions — they change how role fit combines with age/value and character into a final candidate score:

```
candidate_score = (role_fit × role_fit_weight)
                + (age_value_score × age_value_weight)
                + (character_score × character_weight)
```

See `data/archetypes.yaml` for the current archetypes and their weights.
