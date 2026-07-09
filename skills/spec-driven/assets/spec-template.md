# {{NUMBER}} — {{TITLE}}

> Author: {{AUTHOR}} · Date: {{DATE}} · **Status: Draft** · Owner-area: {{AREA}} · Tier: {{TIER}}
>
> Spec-driven gate: this spec must reach **Status: Approved** before any implementation branch opens.
> Fill every section. Replace each `<!-- FILL: … -->` marker. Run `validate_spec.py` before submitting.

## 1. Problem & why

<!-- FILL: 2–4 sentences. What is broken or missing, and what does the user/business lose without this? Ground it in a real need (a metric, a complaint, a legal requirement). -->

## 2. Goals / Non-goals

**Goals**
- <!-- FILL: the verifiable outcomes this delivers -->

**Non-goals** (explicitly out of scope — the fence against scope creep)
- <!-- FILL: the tempting adjacent things you are deliberately NOT doing -->

## 3. Requirements (EARS)

> Format each acceptance criterion as EARS: `WHEN/IF/WHILE ⟨trigger⟩, the system SHALL ⟨response⟩`. Cover happy paths AND unhappy paths (invalid input, dependency down, duplicate, abuse). See the skill's `references/ears-notation.md`.

**Story:** As a `<role>`, I want `<capability>`, so that `<benefit>`.

Acceptance criteria:
- WHEN <!-- FILL: trigger -->, the system SHALL <!-- FILL: response -->.
- IF <!-- FILL: error/edge condition -->, THEN the system SHALL <!-- FILL: response -->.
<!-- add as many criteria as needed; at least one must use SHALL -->

## 4. Design / Approach

<!-- FILL: how you'll build it and why this shape. Must obey .specdriven/constitution.md — if you bend a principle, say so here and justify it. -->

**Contract changes** (API endpoints, events/schemas produced or consumed)
- <!-- FILL: or write "None — no boundary crossed" -->

**Data model & migration**
- <!-- FILL: new tables/columns/indexes + migration plan (expand → backfill → contract). Or "None". -->

**Alternatives considered**
- <!-- FILL: the main option(s) you rejected and why -->

## 5. Affected areas

<!-- FILL: which services/modules/owners this touches, and who reviews what -->

## 6. Test plan

<!-- FILL: for each acceptance criterion, the test that proves it and its level (unit / integration / contract / E2E). Mark the TDD zones (money/law/safety = test-first). -->

## 7. Rollout

- **Flag:** name `<!-- FILL -->` · owner `<!-- FILL -->` · removal condition `<!-- FILL -->`  (or "not user-visible")
- **Canary:** <!-- FILL: exposure ramp, e.g. 5 → 25 → 50 → 100% -->
- **KPI to watch:** <!-- FILL: the metric each ramp step is checked against -->

## 8. Rollback

<!-- FILL: how to undo in one action. For a migration, confirm the previous version still runs against the new schema. -->

## 9. Risks / open questions

- <!-- FILL: what's most likely to go wrong; anything still undecided (open questions block approval until resolved or deferred) -->

## 10. Approvals

> The gate. This spec is not Approved until every box below is checked on the approval PR.

{{APPROVERS}}

---
<!-- managed by the spec-driven skill · do not delete the section headers or the status line -->
