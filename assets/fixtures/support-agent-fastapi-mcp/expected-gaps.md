# Expected gap-analysis output for this fixture

Hand-written golden reference for `references/self-test.md` step 1. When running Steps 1-3 of
the skill against `server.py`, the produced report should match this, modulo wording — the
Present/Partial/Missing verdicts and reasons must match; exact prose does not need to.

## Before any implementation (initial run)

```
search_customer() — server.py:18
  Actor:                Missing — no caller identity anywhere in the call
  Authority:            Missing — no delegation, no scoping of any kind
  Decision:             Missing — no guard, no check, nothing gates this call
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — nothing to re-check, since there's no decision to validate

update_ticket() — server.py:32
  Actor:                Missing — role check has no real caller identity, only an assumed static role
  Authority:            Missing — no delegation or scoping
  Decision:             Partial — an ad-hoc role check exists, but it is not AGF-backed
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — no runtime re-check of anything

issue_refund() — server.py:39
  Actor:                Partial — agent_id is passed, but it's a static constant, not a real per-caller identity
  Authority:            Missing — no chain= passed, only a static API key on the client
  Decision:             Present — guard_tool() is wired and gates the call
  Receipt:              Missing — no correlated receipt
  Execution-validation: Missing — no re-check between decision and dispatch
```

## After Step 6 implements the plan (regression-check run, see self-test.md step 6)

Assuming the plan closed Decision (and, where possible, Actor) for `search_customer` and
`update_ticket` using the same `guard_tool` pattern already present on `issue_refund`, and did
NOT add Authority scoping, Receipt, or Execution-validation anywhere (those remain out of
scope per the SDK gap — see `references/sdk-gap-fallback.md`):

```
search_customer() — Actor: Present (assuming a real id was threaded through) or Partial (if a
                     static constant was used, same caveat as issue_refund) | Decision: Present
update_ticket()   — Actor: Present/Partial (same caveat) | Decision: Present (now AGF-backed,
                     the ad-hoc role check may remain alongside it or be removed per the plan)
issue_refund()    — unchanged from before, since it already had Decision wired

All three:
  Authority:            still Missing — not addressed by this profile's default codegen
  Receipt:               still Missing — no agf-sdk client method exists
  Execution-validation:  still Missing — no agf-sdk client method exists
```

If a regression-check run instead shows Receipt or Execution-validation as Present without
`sdk-gap-fallback.md` having been explicitly used, that is a bug — the skill has false-positived
"governed" purely because `agf-sdk` is imported, which is exactly what the Honesty Rules exist
to prevent.
