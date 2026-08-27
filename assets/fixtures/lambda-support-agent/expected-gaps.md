# Expected gap-analysis output for this fixture (AWS Lambda profile)

Hand-written golden reference for `references/self-test.md`. When running Steps 1-3 of the
skill against `handlers.py`, the produced report should match this, modulo wording — the
Present/Partial/Missing verdicts and reasons must match; exact prose does not need to.

## Before any implementation (initial run)

```
search_order(event, context) — handlers.py:17
  Actor:                Missing — no caller identity anywhere in the call
  Authority:            Missing — no delegation, no scoping of any kind
  Decision:             Missing — no guard, no check, nothing gates this call
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — nothing to re-check, since there's no decision to validate

update_ticket(event, context) — handlers.py:29
  Actor:                Missing — checks a plain event field an API Gateway authorizer might
                         set, which is not an AGF Actor/identity of any kind
  Authority:             Missing — no delegation or scoping
  Decision:             Partial — an ad-hoc authenticated-caller check exists, but it is not
                         AGF-backed
  Receipt:              Missing — no record of outcome
  Execution-validation: Missing — no runtime re-check of anything

issue_refund(event, context) — handlers.py:41
  Actor:                Missing — no chain, no agent identity of any kind reaches decide()
  Authority:            Missing — chain=[] is empty; no delegation/scoping mechanism at all
  Decision:             Missing — guard_tool IS applied, but with a static, empty chain it
                         cannot succeed on any real invocation (agf-runtime requires a
                         non-empty chain or a trust_summary). Do not score this Present just
                         because guard_tool() is structurally applied — see
                         references/gap-analysis.md's Authority scoring note (the same rule
                         every other fixture's issue_refund trap tests).
  Receipt:              Missing — no correlated receipt
  Execution-validation: Missing — no re-check between decision and dispatch
```

## After Step 6 implements the corrected plan (regression-check run, see self-test.md step 6)

Assuming the plan closes all six AAP-Core objects for all three handlers using the real,
corrected pattern from `references/implement-aws-lambda.md` (one-time enrollment,
`chain_provider=` built via `build_self_signed_chain()` per call, `validate_execution=True`,
`report_outcome=True`, `agf-sdk >= 0.7.0` for warm-container-safe sync bridging):

```
search_order(event, context) — handlers.py:17
  Actor:                Partial — a static service-level agent_id, not a real per-caller
                         identity (Lambda's `event`/`context` carry whatever the invoking
                         trigger populates — API Gateway, EventBridge, etc. — target-repo-
                         specific, not a framework-level identity concept)
  Authority:             Present — self-signed single-hop chain (self-attested, not a
                         delegated chain from a separate issuer — say so explicitly)
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported (report_outcome() wired; this profile requires
                         agf-sdk >= 0.7.0, not just >= 0.6.0, for the warm-start-safe bridge).
                         Must be marked "self_reported", never silently equated with a
                         Gateway-observed receipt — see RR-0005.
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present (report_outcome() auto-correlates the prior
                         execution-validation record)

update_ticket(event, context) — handlers.py:29
  Actor:                Partial — same caveat as above
  Authority:             Present — same as above
  Decision:              Present (build_self_signed_chain() wired via chain_provider=, real
                         chain per call)
  Receipt:               Present — self-reported, same as above
  Execution-validation:  Present (validate_execution() wired)
  Decision↔Receipt correlation: Present

issue_refund(event, context) — handlers.py:41
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
`agf-sdk >= 0.7.0` present, that's a bug — under-crediting a real, working capability. If it
shows Receipt as Present without `report_outcome()` actually wired, or Actor as Present rather
than Partial without a real per-caller identity actually being threaded through, that's the
opposite bug — the skill has false-positived "governed" purely because `agf-sdk` is imported,
which is exactly what the Honesty Rules exist to prevent. The same over-/under-crediting check
applies to Decision/Authority/Execution-validation. Also confirm the plan explicitly flagged
`agf-sdk >= 0.7.0` as a hard requirement (not just a floor) for this profile, per
`profile-aws-lambda.md`'s warm-start note — a plan proposing this recipe against an older pin
without saying so is itself a gap.
