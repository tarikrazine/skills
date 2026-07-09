# EARS — writing acceptance criteria that can't be misread

**EARS = Easy Approach to Requirements Syntax.** It's the format Amazon Kiro and NASA/Rolls-Royce requirements teams use to make each requirement a single, testable sentence. The whole idea: a requirement written in EARS has exactly one meaning, and you can write a test straight from it.

Use EARS in the **Requirements** section of every Tier-2 spec (and in the "test" line of a Tier-1 issue when it helps).

## The five patterns

Every acceptance criterion is one of these shapes. The keyword before **SHALL** tells you which.

| Pattern | Shape | Use for |
|---------|-------|---------|
| **Ubiquitous** | *The system SHALL ⟨response⟩.* | An always-true property (no trigger) |
| **Event-driven** | ***WHEN** ⟨trigger⟩, the system SHALL ⟨response⟩.* | Something happens → a response |
| **State-driven** | ***WHILE** ⟨state⟩, the system SHALL ⟨response⟩.* | Continuous behavior during a state |
| **Unwanted / error** | ***IF** ⟨condition⟩, **THEN** the system SHALL ⟨response⟩.* | Error handling, edge cases, abuse |
| **Optional-feature** | ***WHERE** ⟨feature is present⟩, the system SHALL ⟨response⟩.* | Behavior only when a feature/flag is on |

You can combine a precondition with an event: *WHILE ⟨state⟩, WHEN ⟨trigger⟩, the system SHALL ⟨response⟩.*

## Rules

- **One requirement, one sentence, one SHALL.** If you need "and", it's probably two criteria — split them.
- **"SHALL"**, not "should/must/will" — SHALL is the requirement keyword; keep it consistent so they're greppable and countable.
- **Name the actor as "the system"** (or the specific service, e.g. "the `identity` service") — not "we" or "the app".
- **Make the response observable and testable.** "the system SHALL respond within 200 ms" beats "the system SHALL be fast".
- **Cover the unhappy paths.** For every WHEN, ask: what IF the input is invalid / the dependency is down / it's a duplicate? Those IF criteria are where real specs earn their keep.

## Worked example — a resumable upload feature

**User story:** As a creator, I want my video to keep uploading through a bad connection, so a submission is never lost.

**Acceptance criteria (EARS):**
- WHEN a creator selects a video to submit, the system SHALL create an upload session and begin uploading in the background.
- WHILE an upload is in progress, the system SHALL persist its progress so it survives an app restart.
- WHEN network connectivity is lost during an upload, the system SHALL pause and retry with exponential backoff until it succeeds.
- IF the same clip is submitted twice (same idempotency key), THEN the system SHALL accept it once and return the original result.
- WHERE the "large-file Wi-Fi-only" flag is enabled, the system SHALL defer files over 100 MB until the device is on Wi-Fi.
- The system SHALL upload media bytes directly to the storage provider, never through the API.

Notice: 6 lines, each independently testable, each becoming one test in the spec's Test plan. That traceability — criterion → test → task — is the point.

## From criteria to tasks

Good EARS criteria make the **Tasks** section almost fall out: each criterion (or small group) maps to one atomic task, and the Test plan lists the test that proves it. If a criterion has no obvious task or test, it's either vague (rewrite it) or out of scope (move it to Non-goals).
