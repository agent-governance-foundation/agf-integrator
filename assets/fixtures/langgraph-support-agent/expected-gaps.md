# Expected gap-analysis output for this fixture (LangGraph profile)

Hand-written golden reference for `references/self-test.md`. When running Steps 1-3 of the
skill against `server.py`, the produced report should match this, modulo wording — the
Present/Partial/Missing verdicts and reasons must match; exact prose does not need to.

## Before any implementation (initial run)

```
search_order(state) — server.py:33
  Actor:                Missing — no caller identity anywhere in the call
  Authority:            Missing — no delegation, no scoping of any kind
  Decision:             Missing — no guard, no check, nothing gates this call
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — nothing to re-check, since there's no decision to validate

update_ticket(state) — server.py:40
  Actor:                Missing — checks a plain state["authenticated"] flag, which is not an
                         AGF Actor/identity, just an app-defined boolean
  Authority:             Missing — no delegation or scoping
  Decision:             Partial — an ad-hoc authenticated-caller check exists, but it is not
                         AGF-backed
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — no runtime re-check of anything

issue_refund(state) — server.py:49
  Actor:                Missing — no chain, no agent identity of any kind reaches decide()
  Authority:            Missing — chain=[] is empty; no delegation/scoping mechanism at all
  Decision:             Missing — guard_node IS applied, but with an empty static chain it
                         cannot succeed on any real invocation (agf-runtime requires a
                         non-empty chain or a trust_summary). Do not score this Present just
                         because guard_node() is structurally applied — see
                         references/gap-analysis.md's Authority scoring note (the same rule the
                         MCP/A2A fixtures' issue_refund traps test).
  Receipt:              Missing — no correlated receipt
  Execution-validation: Missing — no re-check between decision and dispatch
```

## After Step 6 implements the corrected plan (regression-check run, see self-test.md step 6)

Assuming the plan closes all six AAP-Core objects for all three nodes using the real, corrected
pattern from `references/implement-langgraph.md` (one-time enrollment, `chain_provider=` built
via `build_self_signed_chain()` per call, `validate_execution=True`, `report_outcome=True`):

```
search_order(state) — server.py:33
  Actor:                Partial — a static service-level agent_id, not a real per-caller
                         identity threaded from state (LangGraph's state carries whatever the
                         target repo's own schema defines, no framework-level identity concept)
  Authority:             Present — self-signed single-hop chain (self-attested, not a
                         delegated chain from a separate issuer — say so explicitly)
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported (report_outcome() wired, agf-sdk >= 0.6.0).
                         Must be marked "self_reported", never silently equated with a
                         Gateway-observed receipt — see RR-0005.
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present (report_outcome() auto-correlates the prior
                         execution-validation record)

update_ticket(state) — server.py:40
  Actor:                Partial — same caveat as above
  Authority:             Present — same as above
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present

issue_refund(state) — server.py:49
  Actor:                Partial — same caveat as above
  Authority:             Present — same as above (the fixture's static chain=[] replaced with
                         chain_provider= per the corrected recipe)
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present
```

If a regression-check run shows Receipt as Missing despite `report_outcome()` being wired and
`agf-sdk >= 0.6.0` present, that's a bug — under-crediting a real, working capability. If it
shows Receipt as Present without `report_outcome()` actually wired (or on an older `agf-sdk`),
or Actor as Present rather than Partial without a real per-caller identity actually being
threaded through `state`, that's the opposite bug — the skill has false-positived "governed"
purely because `agf-sdk`/`langgraph` are imported, which is exactly what the Honesty Rules exist
to prevent. The same over-/under-crediting check applies to Decision/Authority/Execution-validation.
