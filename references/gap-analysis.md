Load this only from SKILL.md Step 3. Never read this file during Steps 1-2, 4-7.

# Gap Analysis

Goal: turn Step 2's per-action mapping into a verdict — Present / Partial / Missing — for
each of {Actor, Authority, Decision, Receipt, Execution-validation}, with a one-line reason
per cell. This is the report the user actually reads to decide whether to continue.

Note: Action and Invalidation from Step 2 are not scored here — Action is nearly always
present (it's just the verb+target) and isn't a governance gap; Invalidation is reported
qualitatively in the notes but Execution-validation (whether the *runtime* actually re-checks
revocation/expiry at dispatch time, not just at decision time — see
`references/implement-fastapi-mcp.md` for what this really requires) is the more actionable
signal for this report and replaces it as the fifth scored column.

## Scoring rubric

- **Present**: a real, traced call exists at the actual execution boundary — not just an
  import, not just a check somewhere else in the file that doesn't gate this call site.
- **Partial**: something exists but doesn't fully satisfy the object — e.g. an ad-hoc role
  check (Decision: Partial, not AGF-backed), or generic logging without Decision correlation
  (Receipt: Partial).
- **Missing**: nothing found for this object at this call site.

Never mark Present on the strength of an import statement alone (Honesty Rules, SKILL.md).

**Authority scoring note (corrected 2026-08-25, live-verified)**: a self-signed single-hop
chain (`agf.keys.build_self_signed_chain()`, backed by a `register_agent()`-enrolled keypair)
is a real, legitimate way to score Authority Present — not just "no delegation chain, static
key only." If a target repo already has this wired, score it Present and note it's
self-attested (not a multi-hop delegation from a separate issuer). If a target has an
`agf-sdk` call with **no** chain mechanism at all — bare `agent_id=` and nothing else — that's
worse than Authority: Missing alone: live-confirmed, `/v1/decide` requires a non-empty `chain`
or a `trust_summary` and returns **422** without either, meaning **Decision can't function at
all**, not just "Decision present, Authority absent." Score Decision as Missing in that case
too (a call that will error on every real invocation isn't a working Decision gate), and say so
explicitly in the reason.

## Output format

One block per discovered action, worked example shape (matches the pattern of a support-agent
with `search_customer`, `update_ticket`, `issue_refund`):

```
<action_name>() — <file>:<line>
  Actor:               Present | Partial | Missing — <one-line reason>
  Authority:           Present | Partial | Missing — <one-line reason>
  Decision:            Present | Partial | Missing — <one-line reason>
  Receipt:             Present | Partial | Missing — <one-line reason>
  Execution-validation: Present | Partial | Missing — <one-line reason>
```

Example (illustrative only, not a literal template to reuse verbatim):

```
issue_refund() — payments/tools.py:41
  Actor:                Present — agent_id passed explicitly into the tool call
  Authority:            Missing — no delegation chain, only a static service API key
  Decision:             Missing — no authorize()/guard_tool() call at this call site
  Receipt:              Missing — no receipt or correlated audit record
  Execution-validation: Missing — no runtime re-check between decision and dispatch
```

## After the report

Present the full report to the user, plainly. Then:
- If every action already scores Present across the board, say so and stop — there's nothing
  to plan or implement (SKILL.md Step 3 guard).
- Otherwise, proceed to Step 4 (Classify) to check whether an integration profile applies
  before drafting any plan.

Do not editorialize about how bad the gaps are or push the user toward implementing — the
report is the deliverable; the decision to continue is theirs.
