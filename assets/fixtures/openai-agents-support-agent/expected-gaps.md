# Expected gap-analysis output for this fixture (OpenAI Agents SDK profile)

Hand-written golden reference for `references/self-test.md`. When running Steps 1-3 of the
skill against `server.py`, the produced report should match this, modulo wording — the
Present/Partial/Missing verdicts and reasons must match; exact prose does not need to.

## Before any implementation (initial run)

```
search_order(customer_id) — server.py:21
  Actor:                Missing — no caller identity anywhere in the call
  Authority:            Missing — no delegation, no scoping of any kind
  Decision:             Missing — no guard, no check, nothing gates this call
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — nothing to re-check, since there's no decision to validate

update_ticket(ticket_id, status, authenticated) — server.py:28
  Actor:                Missing — `authenticated` is a plain caller-supplied boolean argument,
                         not an AGF Actor/identity of any kind (a caller can pass True directly)
  Authority:             Missing — no delegation or scoping
  Decision:             Partial — an ad-hoc authenticated check exists, but it is not AGF-backed
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — no runtime re-check of anything

issue_refund(order_id, amount) — server.py:39 (wrapped by guarded_issue_refund, server.py:43)
  Actor:                Missing — no chain, no agent identity of any kind reaches decide()
  Authority:            Missing — chain=[] is empty; no delegation/scoping mechanism at all
  Decision:             Missing — guard_function_tool IS applied, but with an empty static
                         chain it cannot succeed on any real invocation (agf-runtime requires a
                         non-empty chain or a trust_summary). Do not score this Present just
                         because guard_function_tool() is structurally applied — see
                         references/gap-analysis.md's Authority scoring note (the same rule the
                         MCP/A2A/LangGraph fixtures' issue_refund traps test).
  Receipt:              Missing — no correlated receipt
  Execution-validation: Missing — no re-check between decision and dispatch
```

## After Step 6 implements the corrected plan (regression-check run, see self-test.md step 6)

Assuming the plan closes all six AAP-Core objects for all three tools using the real, corrected
pattern from `references/implement-openai-agents.md` (one-time enrollment, `chain_provider=`
built via `build_self_signed_chain()` per call, `validate_execution=True`, `report_outcome=True`):

```
search_order(customer_id) — server.py:21
  Actor:                Partial — a static service-level agent_id, not a real per-caller
                         identity (ToolContext.context is whatever the app passed to
                         Runner.run(), not a framework-level identity concept)
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

update_ticket(ticket_id, status, authenticated) — server.py:28
  Actor:                Partial — same caveat as above
  Authority:             Present — same as above
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present

issue_refund(order_id, amount) — server.py:39
  Actor:                Partial — same caveat as above
  Authority:             Present — same as above (the fixture's static chain=[] replaced with
                         chain_provider= per the corrected recipe)
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present
```

**A note specific to this profile's Receipt accuracy, not a scoring difference**: `Receipt:
Present` above means `report_outcome()` is wired and will fire — it does not by itself mean the
`"executed"`/`"not_executed"` value is accurate for every failure mode. Per
`implement-openai-agents.md`'s documented caveat, if `issue_refund`'s tool were rebuilt without
`@function_tool(failure_error_function=None)`, an internal exception inside the tool body would
be caught by the SDK's own default error handling and reported as `"executed"` regardless. This
fixture's `issue_refund` body has no internal-failure path to exercise that distinction, so the
gap-analysis scoring above is unaffected — but a real target repo's plan must still state this
caveat explicitly wherever `report_outcome=True` is proposed, per `profile-openai-agents.md`.

If a regression-check run shows Receipt as Missing despite `report_outcome()` being wired and
`agf-sdk >= 0.6.0` present, that's a bug — under-crediting a real, working capability. If it
shows Receipt as Present without `report_outcome()` actually wired (or on an older `agf-sdk`),
or Actor as Present rather than Partial without a real per-caller identity actually being
threaded through `ToolContext.context`, that's the opposite bug — the skill has false-positived
"governed" purely because `agf-sdk`/`openai-agents` are imported, which is exactly what the
Honesty Rules exist to prevent. The same over-/under-crediting check applies to
Decision/Authority/Execution-validation.
