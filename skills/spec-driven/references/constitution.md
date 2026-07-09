# The constitution — how to derive and use a project's non-negotiable principles

The **constitution** is the file that makes this skill fit *your* project instead of a generic one. It is a short list of the project's **non-negotiable principles** — the things every spec must obey. GitHub Spec Kit popularized the name and the idea; here it is a plain markdown file at `.specdriven/constitution.md`, and it is the single most important input to good specs. A wrong constitution silently mis-guides every spec written against it.

`init_spec_config.py` seeds a starter constitution by reading the repo; the team then corrects it. This file explains **what belongs in it** and **how to derive it**.

## What a principle looks like

Each principle is a rule a spec can be checked against — testable, not a slogan. Group them; keep the whole thing to roughly one page.

**Good (checkable):**
- "Every service owns its own database; no service reads another's tables — data crosses only as events."
- "Auth is stateless: services validate a short-lived signed token locally; they never call an auth service on the hot path."
- "Any change to money movement is Tier 2 and written test-first."
- "Cross-boundary changes start with a contract PR, approved before implementation."

**Bad (unfalsifiable):**
- "Write clean code." · "Be secure." · "Move fast." — a reviewer can't hold a design to these.

## Where to derive them (in priority order)

1. **Architecture docs** (`docs/architecture*.md`, ADRs, design-decisions) — the richest source. Pull out the load-bearing rules: data ownership, communication style (sync vs async), auth model, boundaries, tiering of sensitive areas.
2. **The operating model / contributing guide** — process principles: branch policy, review gates, Definition of Done, "expensive classes" that need extra approval.
3. **`CODEOWNERS`** — encodes ownership (→ the approver map) and which paths are sensitive (paths with two owners are usually the expensive classes).
4. **The code itself** — the module-boundary lint config, the folder structure, naming conventions. What the compiler already enforces is a principle worth stating.
5. **The team** — after seeding, *read the draft to them and ask what's missing or wrong.* Some principles live only in people's heads ("we never store PII outside the EU cell") and must be captured by asking.

## Suggested sections for the file

```
# <Project> — Constitution

## Data & boundaries        # ownership, what may depend on what, no cross-DB reads
## Communication            # sync vs async rules, allowed synchronous edges
## Security & privacy       # auth model, data classes, what never crosses where
## Change management        # contracts-first, additive-by-default, migration policy
## Testing & quality        # TDD zones, the Definition of Done, observability floor
## Tiering                  # classes of change that are always Tier 2
## Product law (optional)   # non-negotiable product stances, if any
```

## How the constitution is used

- **Writing a spec:** the Design section must be consistent with it; a spec that bends a principle must say so and justify it (an architect conversation).
- **Reviewing a spec:** `review-checklist.md`'s first design question is "does it obey the constitution?".
- **Improving the gate:** when reviewers keep catching the same issue, add a principle here — the next spec then can't reach review with it. This is how the gate gets sharper over time.

## Keep it small and living

A constitution of 40 principles is ignored; one of 8–12 sharp ones is followed. Prune rules that never fire; add rules a review kept needing. Version it in git next to the code it governs — its history is a record of what the team learned.
