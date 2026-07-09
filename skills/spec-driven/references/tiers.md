# Tiers — sizing the spec to the change

The gate must be proportionate, or people route around it. Match the spec's weight to the blast radius of the change. Most work is Tier 1. Pick the **highest** tier that any part of the change triggers.

| Tier | Trigger | The "spec" is | Approved by | Where it lives |
|------|---------|---------------|-------------|----------------|
| **0 · none** | Typo, one-line fix, obvious bug, comment, config value, dependency bump, formatting | Nothing — the PR description | Area owner (normal PR review) | — |
| **1 · inline** | A small feature in a **single area**, **no boundary crossed** (no new/changed API, event, or shared type), fits one owner, ≲ 2 days | The **GitHub issue** (problem · approach · test · flag), moved to `Approved` before a branch opens | Area owner | the issue |
| **2 · full doc** | **Any** of: crosses a service/module boundary · changes a contract (API, event, shared schema) · touches money, auth, privacy, or data-retention · a DB migration · > ~3 days · irreversible or hard-to-reverse | A doc in `docs/specs/NNNN-name.md` | **Area owner + architect** (both) | `docs/specs/` |

## Decision procedure

Ask, in order — the first "yes" sets the tier:

1. Does it change an **API, event, or shared type** another area consumes? → **Tier 2**
2. Does it touch **money, auth, privacy, data-retention, or a migration**? → **Tier 2**
3. Is it **more than ~3 days** or **hard to reverse**? → **Tier 2**
4. Is it a **real feature** (new behavior a user or another service sees), even if small and single-area? → **Tier 1**
5. Otherwise (mechanical / cosmetic / config) → **Tier 0**.

## Rules that keep tiers honest

- **Tier is about risk, not size.** A 20-line change to the money ledger is Tier 2. A 300-line CSS refactor is Tier 1.
- **When in doubt, go up a tier.** The cost of an unnecessary spec is minutes; the cost of an unspecced boundary break is a migration and a wasted week.
- **Splitting to dodge Tier 2 is a smell.** If someone slices a cross-service feature into "single-area" pieces to stay Tier 1, the feature is still Tier 2 — spec the whole thing, then implement in slices.
- **The constitution can promote a class.** If `.specdriven/constitution.md` names something as always-Tier-2 (e.g. "anything touching the ledger"), honor that over this table.

## What each tier still shares

Even Tier 0/1 changes obey the constitution and the Definition of Done (tests at the right level, observability on new paths, a flag + rollback story for user-visible work). The tier decides **how much is written down and who approves** — not whether the engineering bar applies.
