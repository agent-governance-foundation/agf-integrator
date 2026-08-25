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
- `issue_refund` — already has `guard_tool` wired (Decision present), but no Authority scoping,
  no Receipt, no Execution-validation

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
