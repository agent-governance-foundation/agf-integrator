Load this only when validating the agf-integrator skill's own files (e.g. after editing
SKILL.md or a reference file, before considering the change done). Never load this during a
real integration run against a user's actual target repo — it is not part of Steps 1-7.

# Self-test

No traditional unit tests exist for a markdown-instruction skill. This is the manual
pre-release checklist to run against `assets/fixtures/support-agent-fastapi-mcp/` before
considering a change to this skill's files complete.

**CI (2026-08-26)**: `.github/workflows/self-test.yml` now runs items 0-3 and the item-6
regression check automatically on every push/PR that touches `SKILL.md`, `references/**`,
`templates/**`, or `assets/fixtures/**`, via a non-interactive Claude Code invocation diffed
against `expected-gaps.md`'s structured verdicts (`scripts/diff_gap_analysis.py`). CI is a
regression net, not a replacement for actually reading the output — still walk this full
checklist by hand before a release, especially items 3-5 (plan/implementation quality, not just
verdict correctness, still need a human read).

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
5. Run Step 7. Confirm the evidence checklist accurately reflects what Step 6 actually did.
   Since `agf-sdk >= 0.6.0`'s canonical recipe wires `validate_execution=True` AND
   `report_outcome=True` by default (RR-0005), a correct run closes all six AAP-Core objects —
   Receipt must show Present and explicitly marked `self_reported`, never silently equated with
   a Gateway-observed receipt. Not falsely marking anything Present just because `agf-sdk` is
   imported is still the point — see `expected-gaps.md`'s post-implementation table for the
   exact expected verdicts. Also confirm Deny-path/Revocation correctly say "BLOCKED — see
   Step 0: ..." rather than a generic "not tested," given Step 0's BLOCKED finding from item 0.
6. **Regression check** — re-run Steps 1-3 on the now-implemented throwaway copy. Confirm all
   six objects score per `expected-gaps.md`'s post-implementation table (Decision/Authority/
   Execution-validation/Receipt/correlation Present, Actor Present-or-Partial per the fixture's
   caveat) — matching what Step 6 actually wired, not over- or under-crediting it. This is the
   sharpest test of the Honesty Rules — a regression here (something reads as more or less
   governed than it actually is, purely because `agf-sdk` is imported) is the single most
   important failure mode to catch before shipping a change.

Document the result of this checklist (pass/fail per item) in your own working notes when
making a change — this file doesn't dictate where, since no CI is wired up for v1.
