Load this only from SKILL.md Step 7. Never read this file during Steps 1-6.

# Verify

Goal: produce evidence of what was actually wired, checked against the target repo's real
current state after Step 6 — not against what the plan said it would do. This is the step
that makes the Hard Rule concrete: a claim without evidence is not verification.

## Two kinds of checklist item — don't conflate them

**Required verification** covers everything `agf-sdk`'s real `authorize()`/`guard_tool()`
surface can support today — whether each one is actually closed depends on the *target repo*
and the *approved plan*, not on any SDK limitation. Score these normally (Present/Partial/
Missing, per what Step 6 actually did).

**Capability gaps** covers things `agf-sdk` has no client method for at all (execution-time
validation, receipts, and anything that depends on those) — these are **not** MVP failures to
investigate per-repo; they're a fixed ceiling that applies to every integration this skill
performs until `agf-sdk` grows the missing client surface. Keep them in a visually separate
section of the report so a reader doesn't have to figure out which kind of "Missing" they're
looking at.

## How to check each item (don't just assert — trace it)

### Required verification (Authorization)

- **Actor identified**: open each modified call site; confirm a real per-caller identity
  (not a hardcoded constant, unless that was explicitly justified in the plan) is passed into
  the `agf-sdk` call.
- **Authority identified/attached**: confirm whether a `chain=` was actually passed, or whether
  this remains a static-key-only setup (if so, report Authority as still not closed — see
  `references/implement-fastapi-mcp.md`'s "what this closes" section). This is checked, not
  assumed unavailable — `guard_tool`/`authorize()` both accept `chain=` today; it's usually
  unclosed because the target repo has no real delegation source, not because the SDK lacks it.
- **Action identified**: confirm the action/resource strings passed to the `agf-sdk` call
  correctly correspond to the real function/route — a trivial check, but worth stating plainly
  rather than skipping.
- **Decision enforced**: confirm the `guard_tool`/`authorize()` call sits on the actual
  execution path — i.e. the guarded function cannot run without it, not that the call merely
  exists somewhere nearby unused.
- **Execution gated**: same evidence as Decision enforced — confirms the guard structurally
  wraps the real call site for every modified action, not just one of them.
- **Deny path tested**: run (or ask the user to run) a call with an identity/action that should
  be denied, and confirm the guarded function did not execute. If Step 0 reported BLOCKED, say
  so explicitly — "BLOCKED — see Step 0: <specific missing piece, e.g. AGF token not
  configured>" — rather than marking this Present on structural evidence alone. If Step 0
  reported READY but the run wasn't actually attempted for some other reason, say "not tested:
  <reason>" instead — don't default to the Step 0 phrasing when it isn't the actual cause.
- **Existing application tests still pass**: actually run the target repo's test suite if one
  exists and report the real result; if none exists, say so rather than marking this N/A as if
  it were a pass.

### Capability gaps (fixed MVP ceiling, not a per-repo finding)

- **Execution-time validation**: "Not implemented — SDK capability unavailable" unless
  `references/sdk-gap-fallback.md` was used and its call is actually wired at dispatch time, in
  which case check it like any Required-verification item instead.
- **Receipt generated**: "Not implemented — SDK capability unavailable" under the same
  condition/exception as above.
- **Decision↔Receipt correlation**: "Not verifiable in MVP" — depends on Receipt existing at
  all; only becomes checkable once Receipt does (via the fallback).
- **Revocation test**: "Not verifiable in MVP" — testing revocation means confirming a
  mid-session change blocks a subsequent dispatch, which is exactly what execution-time
  validation checks; with no execution-time validation wired, there's no mechanism to test
  against. Only becomes checkable once execution-time validation does (via the fallback). If
  it would otherwise be checkable (fallback used) but Step 0 reported BLOCKED, use the
  BLOCKED phrasing from the Deny-path item above instead.

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
