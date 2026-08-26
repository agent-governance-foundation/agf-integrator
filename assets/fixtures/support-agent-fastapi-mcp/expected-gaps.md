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

**Updated 2026-08-26**: `agf-sdk >= 0.6.0` (RR-0005) closed the Receipt gap — the canonical
recipe in `references/implement-fastapi-mcp.md` now wires `validate_execution=True` AND
`report_outcome=True` by default, not just Decision/Authority/Execution-validation. This
fixture's `requirements.txt` pins `agf-sdk>=0.6.0`, so a correct Step 6 run should close all
six AAP-Core objects, not five.

Applies identically to all three tools (`search_customer()`, `update_ticket()`,
`issue_refund()`) once Step 6 wires the canonical recipe onto each:

```
search_customer() — server.py:18
  Actor:                Partial — still a static agent_id constant, not a real per-caller
                         identity; this fixture's plan doesn't thread one through (service-level
                         identity, same caveat as pre-implementation)
  Authority:            Present — self-signed single-hop chain (self-attested, not a delegated
                         chain from a separate issuer — say so explicitly)
  Decision:              Present (chain_provider wired, live-verified pattern)
  Receipt:               Present — self-reported (report_outcome=True wired, agf-sdk >= 0.6.0).
                         Must be marked "self_reported", never silently equated with a
                         Gateway-observed receipt — see RR-0005.
  Execution-validation:  Present (validate_execution=True wired)
  Decision↔Receipt correlation: Present (report_outcome() auto-correlates the prior
                         execution-validation record)

update_ticket() — server.py:32
  Actor:                Partial — same caveat as above
  Authority:            Present — same as above
  Decision:              Present (chain_provider wired, live-verified pattern)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution=True wired)
  Decision↔Receipt correlation: Present

issue_refund() — server.py:39
  Actor:                Partial — same caveat as above
  Authority:            Present — same as above
  Decision:              Present (chain_provider wired, live-verified pattern)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution=True wired)
  Decision↔Receipt correlation: Present
```

If a regression-check run shows Receipt as Missing despite `report_outcome=True` being wired
and `agf-sdk >= 0.6.0` present, that's a bug — under-crediting a real, working capability. If it
shows Receipt as Present without `report_outcome=True` actually wired (or on an older
`agf-sdk`), that's the opposite bug — the skill has false-positived "governed" purely because
`agf-sdk` is imported, which is exactly what the Honesty Rules exist to prevent. The same
over-/under-crediting check applies to Decision/Authority/Execution-validation.
