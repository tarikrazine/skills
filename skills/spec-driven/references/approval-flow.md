# Approval flow — statuses, approvers, and the green pass

The gate has one job: **make "who decides" unambiguous, and make implementation wait for their yes.** As the Pragmatic Engineer's survey of Google/Amazon/Uber/Stripe puts it — *if the named approvers don't say yes, implementation doesn't start.* This file defines how that works here.

## Statuses

A spec carries exactly one status in its header at all times:

| Status | Meaning | Set by |
|--------|---------|--------|
| `Draft` | Being written; not yet up for review | `new_spec.py` |
| `In review` | Submitted; approvers have been requested | `submit_for_approval.py` |
| `Approved` | Every named approver said yes → **green pass to implement** | approvers (PR approved + merged) |
| `Done` | The feature has shipped | the author, on ship |
| `Rejected` / `Withdrawn` | Not proceeding (rare; record why) | author or approver |

The **only** transition that unlocks an implementation branch is → `Approved`. Nothing else.

## Who approves (the approver map)

`init_spec_config.py` builds the map from the repo's `CODEOWNERS`. Two rules:

1. **The area owner always approves.** A spec whose changes live in area X needs X's owner.
2. **Expensive classes need a second key.** Paths the project marks as sensitive — contracts, event schemas, DB migrations, auth paths, money paths — require the **architect** in addition to the area owner. This is the "two keys on the expensive doors" rule, and it maps straight onto CODEOWNERS entries that list two owners.

The tier sets the floor: **Tier 1** = area owner; **Tier 2** = area owner + architect. A spec spanning several areas needs each affected area's owner.

## The green-pass mechanism (GitHub PR)

The approval venue is a **GitHub pull request** — the same gate that already guards merges, so no new system to run:

1. `submit_for_approval.py` creates a branch containing the spec file, opens a PR labeled `spec`, requests the mapped approvers as reviewers, and sets status → `In review`.
2. Approvers review against `review-checklist.md`. They **Approve**, **Request changes**, or leave **"Yes, if …"** conditions (approve-with-conditions beats a flat reject — it keeps momentum while capturing the fix).
3. When all required approvers have approved, the author sets status → `Approved`, checks the approval boxes, and the PR merges. The spec is now committed to the repo next to the code it will govern.
4. **Green pass.** The implementation branch may now open. Each implementation PR links back (`Spec: docs/specs/NNNN-…`).

## What "closed, not reviewed" means

If someone opens an **implementation** PR whose spec was never approved (or doesn't exist), it is **closed, not reviewed** — the conversation belongs in the spec, before the code. The point isn't bureaucracy; it's that reviewing code for a design nobody agreed to wastes everyone's time and pressures reviewers to rubber-stamp. Spec first, always.

## Keeping it healthy

- **Review SLA.** Treat a spec PR like any PR — first review within the team's SLA (commonly one working day). A spec stuck in `In review` is a person stuck.
- **The index.** `docs/specs/README.md` lists every spec with its status — the live picture of what's approved, in flight, and shipped. Skim it at planning.
- **Bind the future → ADR.** If a spec decides something the team will live with (a schema, a vendor, an irreversible stance), file an ADR when it's approved so the reasoning outlives the spec.
- **Evolve the gate.** If reviewers keep catching the same class of issue, promote it into `.specdriven/constitution.md` or `review-checklist.md` so the next spec never reaches review with it.
