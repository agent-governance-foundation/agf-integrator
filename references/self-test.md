Load this only when validating the agf-integrator skill's own files (e.g. after editing
SKILL.md or a reference file, before considering the change done). Never load this during a
real integration run against a user's actual target repo — it is not part of Steps 1-7.

# Self-test

No traditional unit tests exist for a markdown-instruction skill. This is the manual
pre-release checklist to run against `assets/fixtures/support-agent-fastapi-mcp/` before
considering a change to this skill's files complete.

## The fixture

`assets/fixtures/support-agent-fastapi-mcp/` is a small synthetic MCP+FastAPI server with
three tools, each deliberately built with a different gap class, matching the shape used
throughout this skill's own reference docs:

- `search_customer` — no guard at all (fully ungoverned)
- `update_ticket` — an ad-hoc role check only, no AGF Decision
- `issue_refund` — already has `guard_tool` wired with **no `chain=`/`chain_provider=`** — a
  live-confirmed non-functioning gate (422 on every real call), corrected 2026-08-25. This is
  now the fixture's sharpest test: does Step 3 correctly score its Decision as Missing (not
  Present) despite the decorator's structural presence? See `references/gap-analysis.md`'s
  Authority scoring note.

`assets/fixtures/support-agent-fastapi-mcp/expected-gaps.md` records the hand-written expected
Step 3 output for this fixture — the closest available thing to a golden file.

## Checklist

0. Run Step 0 against the fixture. Confirm it reports BLOCKED (the fixture has no credential
   configured anywhere) with a specific, correctly-attributed reason, and confirm it does NOT
   block continuing to Step 1 — readiness is informational until Step 7.
1. Run Steps 1-3 against the fixture. Diff the produced gap-analysis report against
   `expected-gaps.md`. Any unexplained divergence is a bug in `discover.md`/`aap-mapping.md`/
   `gap-analysis.md` — fix before proceeding.
2. Run Step 4. Confirm it correctly matches the FastAPI+MCP profile (this fixture is built to
   match).
3. Run Step 5. Manually inspect the generated plan: every file:line reference must be real
   (point at actual lines in the fixture), every `agf-sdk` call must match the real signatures
   in `references/implement-fastapi-mcp.md` — no invented API.
4. Approve the plan and run Step 6 against a **throwaway copy** of the fixture (never the
   checked-in copy). Confirm: a new branch was created, only the planned files were touched, a
   diff was shown per file, no commit was made.
5. Run Step 7. Confirm the evidence checklist accurately reflects what Step 6 actually did —
   in particular, confirm Receipt and Execution-validation are correctly reported as Missing
   (unless the self-test deliberately exercised the `sdk-gap-fallback.md` path), not falsely
   marked Present just because `agf-sdk` is now imported. Also confirm Deny-path/Revocation
   correctly say "BLOCKED — see Step 0: ..." rather than a generic "not tested," given Step 0's
   BLOCKED finding from item 0 above.
6. **Regression check** — re-run Steps 1-3 on the now-implemented throwaway copy. Confirm:
   `search_customer`/`update_ticket`/`issue_refund` now score Actor/Decision as Present
   (matching what Step 6 actually wired), while Receipt and Execution-validation still
   correctly score Missing. This is the sharpest test of the Honesty Rules — a regression here
   (something reads as more governed than it is, purely because `agf-sdk` is imported) is the
   single most important failure mode to catch before shipping a change.

Document the result of this checklist (pass/fail per item) in your own working notes when
making a change — this file doesn't dictate where, since no CI is wired up for v1.

## A2A profile fixture

`assets/fixtures/a2a-support-agent/` is the second-profile equivalent, same three-gap-class
shape adapted to A2A's real one-executor-per-entrypoint model: `SearchOrderExecutor` (no guard),
`UpdateTicketExecutor` (ad-hoc `call_context.user.is_authenticated` check, not AGF-backed),
`IssueRefundExecutor` (`client.decide()` called with an empty `chain=[]` — the same
structurally-present-but-non-functional trap as the MCP fixture's `issue_refund`). Run the same
0-6 checklist against it when changing anything in `profile-a2a.md`/`implement-a2a.md`.

**Run 2026-08-26** (manual — no `claude` CLI available in that session, so this was executed by
hand rather than via a live `/agf-integrator` invocation): building this fixture surfaced two
real bugs in `implement-a2a.md`/`profile-a2a.md` as originally shipped (an invented
`AgentGovernance` constructor call missing a required arg, and a check against a nonexistent
`.decision` field) — found by installing the real `a2a-sdk`/`agf-sdk` and reading actual source
before writing the fixture, not by the fixture itself. Both fixed before the fixture was built.
With the fix in place: Step 6 applied cleanly to a throwaway copy (new branch, one commit —
baseline only, `server.py` + a new `scripts/agf_enroll.py` changed, diffs reviewed), every
symbol used (`AGFClient.decide`/`validate_execution`/`report_outcome`, `build_self_signed_chain`,
`AGFDeniedError`, `a2a.server.agent_execution.AgentExecutor`/`RequestContext`,
`a2a.server.events.event_queue.EventQueue`) was confirmed to actually import and match its real
signature, and the regression check (re-deriving verdicts from the implemented code) matched
`expected-gaps.md`'s post-implementation table exactly for all three executors — no over- or
under-crediting. **Not done in this run**: no live local `agf-runtime` was stood up, so this
tests that the recipe is syntactically/semantically correct against real installed SDKs, not
that a live `decide()`/`validate_execution()` call actually succeeds end-to-end the way the MCP
profile's pattern was separately live-verified.

**Live-tested 2026-08-26** against a real local `agf-runtime` (Docker Postgres+OPA, real
migrations, real uvicorn) — closing the gap above. Confirmed real DENY (unenrolled agent,
identity-based hard denial) and, more valuably, surfaced a genuine third outcome this recipe
hadn't accounted for: a freshly-enrolled agent's first action commonly gets `REVIEW_REQUIRED`
under this environment's default risk config (`DEFAULT_RISK=50` + zero trust from a brand-new
self-signed chain crosses the ≥70 threshold) — **not transient**, live-confirmed that approving
the resulting `approval_request_id` neither retroactively unblocks that artifact_id
(`validate_execution()` correctly 400s on it) nor changes a later fresh `decide()` call's risk
scoring. `implement-a2a.md`'s original `execute()` example didn't catch
`AGFReviewRequiredError` at all — would have propagated as an uncaught exception (the framework
turns that into a generic `TASK_STATE_ERROR`) instead of the real, purpose-built
`TASK_STATE_AUTH_REQUIRED` the `AgentExecutor` interface actually defines for this. Fixed using
the real, verified `TaskUpdater.requires_auth()` helper. This is exactly the kind of gap live
self-testing exists to catch — a fixture/syntax-level pass alone wouldn't have surfaced it, since
`REVIEW_REQUIRED` only appears from a real runtime's actual risk-scoring pipeline.

Remaining real gap for this profile: no real target-repo validation (an A2A equivalent of
PyMCP-FS) has been run yet.
