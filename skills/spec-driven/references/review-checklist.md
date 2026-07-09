# Review checklist — how an approver decides the green pass

`validate_spec.py` already confirmed the spec is *complete* (every section filled, EARS present, approvers set). Your job as a reviewer is the part a script can't do: **judgment**. Read the spec against the constitution and these questions, then Approve, Request changes, or leave "Yes, if …" conditions.

## The questions

**Problem**
- [ ] Is the problem real and worth solving now? Could you state it back in one sentence?
- [ ] Do the **Non-goals** fence the scope tightly enough that this won't sprawl?

**Requirements (EARS)**
- [ ] Is every acceptance criterion **testable** — could you write the test from it as written?
- [ ] Are the **unhappy paths** covered (invalid input, dependency down, duplicate, abuse)? Missing IF-criteria are the most common gap.
- [ ] Is anything ambiguous ("fast", "handles errors", "etc.")? Push for a number or a concrete behavior.

**Design (against the constitution)**
- [ ] Does it **obey `.specdriven/constitution.md`**? If it bends a principle, is that called out and justified — or is it a silent violation?
- [ ] **Contract changes:** additive by default? A breaking change should carry a versioning/migration plan, not happen in place.
- [ ] **Data model / migration:** expand→backfill→contract, so the previous version stays runnable for rollback? No destructive change riding in the same PR that deploys new code.
- [ ] Are the **boundaries** respected (no reaching into another service's data; the right owner owns the change)?
- [ ] Were real **alternatives** weighed, or is this the first idea written down?

**Operability**
- [ ] **Test plan:** right level for each criterion; the money/law/safety parts marked as TDD zones?
- [ ] **Rollout:** flag named with a removal condition; a sensible canary ramp; a KPI to watch?
- [ ] **Rollback:** genuinely one action? For a migration, does the old version still run against the new schema?
- [ ] **Observability:** will you be able to debug the new paths from logs/traces/metrics alone?

**Decision**
- [ ] Are all the **right approvers** on it (area owner; architect for expensive classes; every affected area's owner for cross-cutting specs)?
- [ ] Does anything here **bind the future** enough to deserve an ADR?

## How to respond

- **Approve** when it's right, or right-enough that remaining nits can be fixed in implementation review.
- **"Yes, if …"** — approve conditionally, listing the specific changes required. This is the default for "good direction, a few gaps": it keeps momentum without rubber-stamping. (Squarespace's whole RFC culture is built on "Yes, if".)
- **Request changes** — for a wrong problem, a constitution violation, or missing unhappy-path coverage on something risky. Say *what evidence or change* would move you to yes.

Avoid the two failure modes: **rubber-stamping** (approving to be nice — the gate then protects nothing) and **bikeshedding** (blocking on cosmetic preferences — that belongs in code review, not the spec gate). Review the decision, not the prose.

## After approval

Confirm the status flips to `Approved`, the approval boxes are checked, and — if it bound the future — an ADR is filed. Then the author gets the green pass to open the implementation branch.
