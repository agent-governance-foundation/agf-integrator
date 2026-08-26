# RR-DRAFT: <title>

**This is an unnumbered proposal, not a filed Review Record.** A human must assign the real
next sequential `RR-NNNN` (check the highest existing file in
`agf-profile/implementation/review-records/` — there is no index, numbering is manual) only at
the point they actually copy this into that directory. Never write this file there yourself,
and never write `RR-NNNN` anywhere in this file except as this placeholder instruction.

| Field | Value |
|---|---|
| Review ID | RR-DRAFT — assign the real next sequential number only when filed |
| Review Type | <Security \| Architecture \| Cryptography \| Privacy \| Compliance> |
| Subject | <short name of the AGF-itself capability gap found> |
| Artifact | <this proposal file's path once copied into review-records/, or a linked design note> |
| Status | Pending |
| Reviewer | TBD |
| Reviewer Role | <the authority who'd need to approve this — e.g. "TL/Architect"> |
| Due Date | TBD |
| Decision | Pending |
| Linked Commits | — |
| Created | <date this was drafted> |
| Completed | — |

## Why this exists

<What specific action, during this integration, needed something AGF genuinely doesn't
support today — not "the target repo doesn't use AGF yet," but "AGF itself has no client
method / server endpoint / mechanism for this." Cite the exact `agf-sdk`/`agf-runtime` call or
endpoint that doesn't exist, confirmed by checking current source, not assumed.>

## Acceptance Checklist

<What a reviewer would need to approve before this gap could be closed — mirror the shape of a
real RR's checklist: the specific design questions this gap raises, not a generic list.>

- [ ] <first open design question this gap raises>
- [ ] <second, if any>

## Evidence

- What was checked to confirm this is a real gap, not a documentation gap or a caller-side
  fix: <exact files/functions grepped, exact absence confirmed>
- What integration attempt surfaced this: <target repo, action, plan step>

## Decision

Pending. This proposal exists so the gap isn't lost, not to imply it will be approved as
described — a human reviewer may reach a different design than this draft's shape suggests.
