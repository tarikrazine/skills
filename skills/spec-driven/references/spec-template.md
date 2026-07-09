# The spec template — Requirements → Design → Tasks

This is the shape of a Tier-2 spec (`docs/specs/NNNN-name.md`). `new_spec.py` writes this skeleton; the agent fills it with the developer. The three-phase spine (Requirements → Design → Tasks) is the Kiro model; the surrounding sections are what the classic RFC/design-doc processes and the project's Definition of Done require.

**Fill it top-down, and get sign-off between phases for big features:** agree the Requirements before designing; agree the Design before listing Tasks. That phase-gating is where the cheap course-corrections happen.

## Section-by-section guide

### Header
`Author · Date · Status · Owner-area · Tier`. **Status** is one of `Draft → In review → Approved → Done` (see `approval-flow.md`). It starts `Draft`; `submit_for_approval.py` moves it to `In review`; approval moves it to `Approved`; shipping moves it to `Done`.

### 1. Problem & why
2–4 sentences. What is broken or missing, and what does the user/business lose without this? Ground it in a real need (a metric, a complaint, a legal requirement) — not "it would be nice". If you can't articulate the pain, you're not ready to spec.

### 2. Goals / Non-goals
- **Goals:** the outcomes this delivers (bullet list, each verifiable).
- **Non-goals:** what this explicitly does *not* do. Non-goals are the single best defense against scope creep — name the tempting adjacent things you are deliberately leaving out.

### 3. Requirements (EARS)
User stories, each with **EARS acceptance criteria** (`ears-notation.md`). Cover happy paths and the IF/error paths. These become the Test plan and the Tasks.

### 4. Design / Approach
How you'll build it, and *why this shape*. Must be consistent with `.specdriven/constitution.md` — if the feature bends a principle, say so explicitly and justify it (that's an architect conversation, not a silent choice). Include, when relevant:
- **Contract changes** — new/changed API endpoints; events/schemas produced or consumed. (In a contracts-first project, this section is what the contract PR will implement, and it goes in *before* code.)
- **Data model** — new tables/columns/indexes; the **migration plan** (prefer expand → backfill → contract, so the old version stays runnable for rollback).
- **Sequence** — for cross-service flows, a short step list or a diagram.
- **Alternatives considered** — the main option(s) you rejected and why (so the decision survives).

### 5. Affected areas
Which services/modules/owners this touches, and who must review what. Cross-reference the approver map — this drives the reviewers `submit_for_approval.py` requests.

### 6. Test plan
For each acceptance criterion, the test that proves it and at what level (unit / integration / contract / E2E). Name the **TDD zones** — the parts where a wrong answer is money, law, or safety, which must be written test-first.

### 7. Rollout
- **Flag:** name · owner · removal condition (or "not user-visible").
- **Canary:** the exposure ramp (e.g. 5 → 25 → 50 → 100%).
- **KPI to watch:** the metric each ramp step is checked against.

### 8. Rollback
How to undo in one action if it goes wrong. For a migration, this is where you confirm the previous version still runs against the new schema.

### 9. Risks / open questions
The things most likely to go wrong, and anything still undecided. Open questions block approval until resolved or explicitly deferred.

### 10. Approvals
The named approvers and their sign-off checkboxes (pre-filled from the approver map for this area/tier). **This section is the gate** — the spec is not `Approved` until every box here is checked on the PR. Expensive classes (contracts, money, auth, privacy, migrations) require the architect in addition to the area owner.

## Quality bar

A good spec passes `validate_spec.py` (mechanical completeness) *and* the human `review-checklist.md` (judgment). The mechanical check stops half-written specs from reaching a reviewer; the human check is what actually decides the green pass.
