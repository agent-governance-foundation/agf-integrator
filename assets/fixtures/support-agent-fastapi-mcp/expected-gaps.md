# Expected gap-analysis output for this fixture

Hand-written golden reference for `references/self-test.md` step 1. When running Steps 1-3 of
the skill against `server.py`, the produced report should match this, modulo wording — the
Present/Partial/Missing verdicts and reasons must match; exact prose does not need to.

**Corrected 2026-08-25** after a live test found `issue_refund()`'s baseline `guard_tool()` call
(no `chain=`/`chain_provider=`) would actually 422 on every real invocation — Decision was
wrongly scored Present for it before this correction. See
`references/implement-fastapi-mcp.md` for the full finding.

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
  Authority:            Missing — no chain= or chain_provider= passed, only a static API key on the client
  Decision:             Missing — guard_tool() IS wired, but with no chain mechanism at all it
                         will return a live 422 on every real invocation, not a functioning
                         ALLOW/DENY gate. Do not score this Present just because the decorator
                         is structurally present — see references/gap-analysis.md's Authority
                         scoring note.
  Receipt:              Missing — no correlated receipt
  Execution-validation: Missing — no re-check between decision and dispatch
```

## After Step 6 implements the corrected plan (regression-check run, see self-test.md step 6)

Assuming the plan closes Decision + Authority + Execution-validation for all three actions
using the real, corrected pattern (one-time enrollment, `chain_provider=`,
`validate_execution=True` — see `references/implement-fastapi-mcp.md`), and does NOT add
Receipt (the one remaining genuine SDK gap):

```
All three actions — Decision: Present (chain_provider wired, live-verified pattern)
                     Authority: Present — self-signed single-hop chain (self-attested, not a
                                delegated chain from a separate issuer — say so explicitly)
                     Execution-validation: Present (validate_execution=True wired)
                     Actor: Present/Partial depending on whether a real per-caller id exists
                     (this fixture has none — service-level identity, same caveat as before)

All three:
  Receipt: still Missing — no agf-sdk client method exists (the one remaining genuine gap)
```

If a regression-check run shows Receipt as Present without `sdk-gap-fallback.md` having been
explicitly used (and a confirmed real endpoint found), that is a bug — the skill has
false-positived "governed" purely because `agf-sdk` is imported, which is exactly what the
Honesty Rules exist to prevent. Equally, if Decision/Authority/Execution-validation are scored
Missing/Partial despite `chain_provider=`/`validate_execution=True` actually being wired
correctly, that's the opposite bug — under-crediting a real, working capability.
