Load this only from SKILL.md Step 7. Never read this file during Steps 1-6.

# Verify

Goal: produce evidence of what was actually wired, checked against the target repo's real
current state after Step 6 — not against what the plan said it would do. This is the step
that makes the Hard Rule concrete: a claim without evidence is not verification.

**Corrected twice, both 2026-08-25**, after live tests against a real local `agf-runtime`: (1)
the original "Capability gaps" list was wrong about execution-time validation and revocation
testing — both real, achievable (`guard_tool(..., validate_execution=True)`, confirmed live).
Also, `chain=`/Authority is not just "usually unclosed because the target repo lacks a
delegation source" — a bare API key with no chain at all causes `/v1/decide` to return **422**,
not a degraded decision. (2) RR-0005 closed the last fixed gap: Receipt, via
`guard_tool(..., report_outcome=True)` (`agf-sdk >= 0.6.0`), live-verified end-to-end (real
success and failure paths, both producing correctly-classified receipts). There is no more
fixed SDK ceiling — every item below is a per-repo finding now, checked the same way.

## One checklist — trace and test every item, don't assume any of it

Every AAP-Core object this skill checks now has a real `agf-sdk` client method (as of
`>= 0.6.0`). Whether each one is actually closed depends on the *target repo* and the *approved
plan*, never on an SDK limitation anymore. Score every item the same way — Present/Partial/
Missing, per what Step 6 actually did — there is no separate "fixed ceiling" section.

## How to check each item (don't just assert — trace it)

- **Actor identified**: open each modified call site; confirm a real per-caller identity
  (not a hardcoded constant, unless that was explicitly justified in the plan) is passed into
  the `agf-sdk` call.
- **Authority identified/attached**: confirm a `chain_provider=` (not a static `chain=` — those
  expire in 300s, see `references/implement-fastapi-mcp.md`) is wired and actually builds a
  fresh self-signed chain per call via `build_self_signed_chain()`, backed by a persisted
  private key from a completed one-time `register_agent()` enrollment. If none of that exists —
  bare `agent_id=` with no chain mechanism at all — this doesn't just leave Authority unclosed,
  it means the integration will hard-fail with a 422 the moment it's actually invoked. Report
  that distinction explicitly: "Authority: Missing — AND the Decision call itself cannot
  succeed without one" is a materially different finding from "Authority: Missing, Decision
  still works."
- **Action identified**: confirm the action/resource strings passed to the `agf-sdk` call
  correctly correspond to the real function/route — a trivial check, but worth stating plainly
  rather than skipping.
- **Decision enforced**: confirm the `guard_tool`/`authorize()` call sits on the actual
  execution path — i.e. the guarded function cannot run without it, not that the call merely
  exists somewhere nearby unused. If there's no working chain mechanism (see Authority above),
  do not mark this Present on code-structure alone — a call that will 422 on every real
  invocation is not a functioning Decision gate; verify the chain-building path is real too.
- **Execution-time validation**: confirm `validate_execution=True` is passed to `guard_tool()`
  (or `client.validate_execution(artifact_id)` is called directly after `authorize()`/`decide()`
  for a non-decorator integration). Real, live-verified capability — there is no SDK reason to
  leave this unclosed; if it's missing, that's a plan/implementation gap, not unavailable.
- **Execution gated**: same evidence as Decision enforced — confirms the guard structurally
  wraps the real call site for every modified action, not just one of them.
- **Deny path tested**: run (or ask the user to run) a call with an identity/action that should
  be denied, and confirm the guarded function did not execute. If Step 0 reported BLOCKED, say
  so explicitly — "BLOCKED — see Step 0: <specific missing piece, e.g. AGF token not
  configured>" — rather than marking this Present on structural evidence alone. If Step 0
  reported READY but the run wasn't actually attempted for some other reason, say "not tested:
  <reason>" instead — don't default to the Step 0 phrasing when it isn't the actual cause.
- **Revocation test**: with execution-time validation wired, this is genuinely testable — revoke
  the agent (or let its self-signed chain expire) and confirm a subsequent call's
  `validate_execution()` re-check blocks it. If untested, say so; don't infer it from Decision
  being present.
- **Existing application tests still pass**: actually run the target repo's test suite if one
  exists and report the real result; if none exists, say so rather than marking this N/A as if
  it were a pass.

- **Receipt generated**: confirm `report_outcome=True` is wired on `guard_tool()` (requires
  `agf-sdk >= 0.6.0` — check the target's pinned version first) and that a real receipt was
  actually produced (fetch it via `list_receipts()`/`get_receipt()` and confirm it exists,
  don't infer from the flag's presence alone). Mark it explicitly as self-reported
  (`gateway="self_reported"`) — never imply it's Gateway-observed. If `agf-sdk` is older than
  0.6.0, or the flag wasn't wired, report Missing for this repo — that's a real, closeable gap
  now, not a fixed SDK ceiling, so don't soften the finding.
- **Decision↔Receipt correlation**: depends on Receipt existing — once it does, confirm the
  receipt's `execution_validation_ref` correlates to the right Spec 30 record if execution-time
  validation also ran for the same call.

## Coverage count

Count against Step 1's full discovery list, not just the actions the plan touched:

```
<N> actions discovered
<N> actions with a Decision-enforcing guard wired
<N> decisions actually enforced (traced, not just present)
<N> receipts generated
```

If the plan deliberately deferred some discovered actions (user chose not to address every
gap), state that plainly — the coverage count must reflect the whole repo's real state, with
deferred items clearly marked as "deferred by user choice," not silently excluded from the
denominator.

## Output

Render `templates/verification-report.md` into the target repo with the checklist and coverage
count filled in from what was actually traced/tested, not copied from the Step 5 plan's
intentions. Present the same report to the user directly in the conversation.

## If verification finds a discrepancy

If Step 6 didn't actually implement something the plan said it would (e.g. a guard was added
but doesn't correctly identify the real Actor), report that discrepancy plainly in the
verification report rather than smoothing it over — this is the step where an inaccurate
implementation gets caught, not hidden.
