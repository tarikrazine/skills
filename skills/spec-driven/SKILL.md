---
name: spec-driven
description: Runs a team's spec-driven development gate — every feature gets a written spec (Requirements in EARS notation → Design → Tasks) that must be APPROVED before any implementation branch opens. Self-configures to the host project on install by reading its docs and CODEOWNERS into a project "constitution" and an approver map, then guides each developer to write a spec that respects the project's patterns, validates it is complete, and submits it as a GitHub PR for the named approvers to green-light. Use whenever someone is about to start a feature, change, or task and says things like "I want to build X", "let's add Y", "spec this", "start a new feature", "write the RFC/design doc", or asks how to get a change approved before coding — even without the word "spec". Also use to set the gate up in a repo ("install spec-driven", "configure the spec process"). Don't use for one-off throwaway scripts, or for work that is already spec-approved and mid-implementation.
---

# Spec-Driven Development

The rule this skill enforces, in one line: **every feature begins with a written spec, and no implementation branch is opened until that spec is `Approved`.** Flow: **Spec → Approve → (contract change if a boundary moves) → Build → Review → Release.**

This skill is public and project-agnostic. It **self-configures** to whatever repo it is installed in: on first run it reads the project's own docs and `CODEOWNERS` into a **constitution** (the project's non-negotiable principles) and an **approver map**, so every spec it produces respects that project's patterns and routes to that project's approvers. Nothing about any one company is hard-coded.

## How the pieces fit

Scripts do the deterministic work (config, scaffolding, the completeness gate, PR submission); the agent does the judgment (drawing out requirements, designing against the constitution, sizing the tier):

| Step | Who | Tool |
|------|-----|------|
| Bootstrap the gate in a repo (constitution + approver map) | script | `scripts/init_spec_config.py` **[bootstrap]** |
| Pick the tier for a change | **agent** | `references/tiers.md` |
| Scaffold the spec file at the right tier | script | `scripts/new_spec.py` **[mutating]** |
| Write Requirements as EARS acceptance criteria | **agent** | `references/ears-notation.md` |
| Write Design that obeys the constitution | **agent** | `references/spec-template.md` + `.specdriven/constitution.md` |
| Break Design into numbered atomic Tasks | **agent** | `references/spec-template.md` |
| Gate: is the spec complete enough to submit? | script | `scripts/validate_spec.py` **[read-only]** |
| Submit for approval as a GitHub PR | script | `scripts/submit_for_approval.py` **[mutating]** |
| Review someone else's spec | **agent** | `references/review-checklist.md` |

All script paths below are relative to this skill's directory. Resolve `<skill-dir>` to the directory containing this SKILL.md before running commands. Scripts are Python 3 standard library only — no pip installs. `submit_for_approval.py` uses the `gh` CLI if present (falls back to printing exact instructions if not).

## Where things live (in the host repo)

The skill writes into the project itself — specs are committed alongside code, the way Kiro and Spec Kit do it:

```
<repo>/
├── .specdriven/
│   ├── config.json          # approver map, tiers, github + paths  (generated on install)
│   └── constitution.md      # the project's non-negotiable principles (edited by the team)
└── docs/specs/              # (path is configurable)
    ├── README.md            # the spec index — every spec + its status
    └── NNNN-name.md         # one file per Tier-2 spec
```

## First-time setup (install the gate in a repo)

Run once per repo. Idempotent — never overwrites an existing constitution or config.

```bash
python3 <skill-dir>/scripts/init_spec_config.py --repo <repo-root>
```

It will:
1. Detect `CODEOWNERS` (`.github/`, root, or `docs/`) and turn its path→owner map into the **approver map** (owners approve their area; paths with two owners require both).
2. Scan for project docs (`docs/architecture*.md`, `*operating-model*.md`, `README.md`, ADRs) and seed **`.specdriven/constitution.md`** with the principles it can infer plus clearly-marked `TODO` slots for the team to fill.
3. Write **`.specdriven/config.json`** (tiers, specs dir, GitHub repo, spec label).
4. Create **`docs/specs/README.md`** (the index) if absent.

After it runs, **read `.specdriven/constitution.md` aloud to the user and ask them to confirm or correct the inferred principles and the approver map** — this is the "adapt to our patterns" moment. The constitution is the contract every future spec is checked against; a wrong constitution silently mis-guides every spec.

## The per-feature workflow (what a developer runs)

When someone is about to start a feature, follow this loop. Do **not** write feature code during it — the whole point is that code waits for the green pass.

1. **Understand the change**, then **pick the tier** using `references/tiers.md`:
   - **Tier 0** (typo, one-liner, config/dep bump) → no spec; tell them to just open the PR. Stop here.
   - **Tier 1** (small, single-area, no boundary crossed) → the spec is the **GitHub issue**; scaffold a short one and get the area owner's approval before a branch.
   - **Tier 2** (cross-service, or touches contracts/money/auth/privacy, or > ~3 days) → a full spec doc.
2. **Scaffold** the spec at the chosen tier:
   ```bash
   python3 <skill-dir>/scripts/new_spec.py --repo <repo-root> --title "short name" --tier 2 --area apps/services/identity
   ```
   This writes `docs/specs/NNNN-short-name.md` from the template, numbers it, and pre-fills the approvals block from the approver map for that area/tier.
3. **Load the constitution** (`.specdriven/constitution.md`) and keep it open — every design decision must obey it.
4. **Fill the spec, section by section, with the developer:**
   - **Requirements** — user stories with **EARS acceptance criteria** (`references/ears-notation.md`): *WHEN/IF/WHILE ⟨trigger⟩, the system SHALL ⟨response⟩*. Unambiguous and testable.
   - **Design** — approach, **contract changes** (endpoints, events/schemas), **data model + migration**, affected areas/owners — all consistent with the constitution. Flag any principle the feature is tempted to bend.
   - **Tasks** — a numbered list of atomic, independently-reviewable changes, each mapped to an owner, each ≤ ~2 days.
   - **Test plan / Rollout (flag + canary + KPI) / Rollback / Risks** — decided now, so the eventual PR just confirms them.
5. **Gate — validate completeness:**
   ```bash
   python3 <skill-dir>/scripts/validate_spec.py docs/specs/NNNN-short-name.md
   ```
   If it exits non-zero, it prints exactly what's missing (an empty section, no EARS criterion, an unfilled contract/rollback, no approvers). Fix and re-run until green. **Never submit a spec that fails validation.**
6. **Submit for approval:**
   ```bash
   python3 <skill-dir>/scripts/submit_for_approval.py docs/specs/NNNN-short-name.md --repo <repo-root>
   ```
   Sets the spec's status to `In review`, opens a branch + PR labeled `spec`, and requests the approvers named in the spec. Print the PR URL to the user. (`references/approval-flow.md` covers the statuses and the two-key "expensive class" rule.)
7. **Wait for the green pass.** Only when the approvers approve the PR (status becomes `Approved` and it merges) may the developer open the **implementation** branch. If asked to start coding before that, refuse and point at the pending spec PR.

## Reviewing a spec (for an approver)

When the user is reviewing someone else's spec PR, use `references/review-checklist.md`: check it against the constitution, verify the EARS criteria are testable, confirm the contract/migration/rollback are real (not placeholders), and either approve, or leave "Yes, if …" conditions rather than a flat rejection. Record binding decisions as ADRs.

## Improving the gate over time

This is meant to evolve. As the team learns, edit `.specdriven/constitution.md` (add a principle a review kept catching), tune `references/tiers.md` (move a class of change up or down a tier), or extend `references/review-checklist.md`. The scripts read config + constitution at runtime, so improvements take effect on the next spec with no code change. Keep `docs/specs/README.md` as the living index, reviewed at planning.
