---
name: agf-integrator
description: "Use when integrating an AI-agent codebase (FastAPI + MCP agents; more profiles later) with AGF governance (agf-runtime/agf-sdk) — discovers agent/tool entrypoints, maps them to the AAP-Core object model, finds governance gaps, proposes an integration plan for approval, implements it, and verifies with evidence. Never modifies a target repo without an approved plan."
---

# /agf-integrator

## What this skill is for

**Discover, integrate, and verify AGF authorization in supported AI-agent codebases.** That is
the whole promise — not "make the agent AGF compliant." This MVP has one real architectural
ceiling left (no `agf-sdk` client surface for receipts; see Capability gaps in Step 7), so this
skill never claims full compliance as an outcome. Its output describes exactly what's
integrated and what isn't — nothing more, nothing rounded up.

**Corrected 2026-08-25** after a live test against a real local `agf-runtime` found two errors
in this skill's earlier self-understanding: (1) execution-time validation
(`validate_execution=True`) is a real, working capability, not a gap — it was wrongly listed as
one from an incorrect initial grep. (2) More seriously: `guard_tool()`/`authorize()` with a bare
`agent_id=` and no chain mechanism doesn't just leave Authority unclosed — `/v1/decide` returns
**422** without a chain or trust_summary, meaning every integration this skill generated before
this correction would fail in production. See `references/implement-fastapi-mcp.md` for the
corrected, live-verified pattern (self-signed chain via `chain_provider=`, one-time agent
enrollment).

Takes an existing AI-agent codebase (a target repo — not this skill's own files) and:

0. Checks whether the environment has what a real integration needs — `agf-sdk`, a runtime
   URL, an agent identity, an API token, AND a persisted agent private key from a completed
   enrollment — without ever inventing or writing a secret
1. Discovers where it exposes agent/tool actions
2. Maps what it finds onto the AAP-Core object model (Actor, Authority, Action, Decision, Receipt, Invalidation)
3. Reports exactly which governance objects are missing, per action
4. Confirms the codebase matches a supported integration profile
5. Proposes a concrete plan — file:line, exact code, exact `agf-sdk` calls — and **stops for approval**
6. Only after approval, implements the plan on a dedicated branch, one file at a time, with a diff shown for each
7. Verifies what was actually wired, with evidence — not a claim

## Status vocabulary

Every outcome this skill reports uses exactly one of these four words — never "compliant,"
"non-compliant," or similar:

- **UNSUPPORTED PROFILE** — Step 4 found no matching integration profile for this repo.
- **NOT INTEGRATED** — a profile matched, but nothing has been wired yet (gap analysis ran,
  or a plan was never approved/implemented).
- **PARTIAL** — some governed actions have Decision enforced; others don't, or Receipt/
  correlation remain open (which they always do until `agf-sdk` grows a receipt client method
  — the one remaining fixed gap).
- **FULL** — every discovered action has Decision, Authority, and Execution-validation enforced,
  traced, and tested. Achievable now for Required verification (corrected 2026-08-25 — Authority
  via a self-signed chain and Execution-validation are both real, working capabilities, not
  gaps) — but Receipt/correlation still cap the *overall* status at PARTIAL. Don't stretch FULL
  to cover a repo where Receipt remains open.

## Hard rule (read this before Step 0)

**Never claim AGF compliance merely because AGF libraries are installed.** Compliance means:
a governed action was identified, authorization is enforced at the execution boundary, and
there is evidence (a report, a test result, a receipt) — not just an import statement. Every
step below that produces output must distinguish "implemented and verified" from "present but
unverified" from "not implemented." See Honesty Rules at the end.

## Step 0 — AGF Readiness

Read `references/readiness.md` now. Check whether `agf-sdk` is available, whether an
`agf-runtime` base URL and agent identity are determinable, and whether **two** distinct
credential sources exist — the API token AND a persisted agent private key from a completed
one-time enrollment (`register_agent()`) — without ever reading, printing, inventing, or
writing an actual secret value. Present the readiness report to the user (format in
`references/readiness.md`). This step never blocks Steps 1-6 — static discovery, mapping, gap
analysis, planning, and code generation are all valid without a live credential. It determines
whether Step 7's live-verification items (Deny-path tested, Revocation test) can actually run,
or must be reported BLOCKED with a specific reason rather than a vague "not tested" — and
whether the private-key/enrollment piece is missing specifically, since that means generated
`guard_tool()` calls will 422 on every real invocation, not just be unverifiable.

## Step 1 — Discover

Read `references/discover.md` now. It gives the concrete grep/read patterns for entrypoints,
tool execution paths, identity/credential handling, existing authorization logic, external
side effects, and existing audit/logging. Produces a discovery summary (present it to the
user as a short list, not a raw dump) — this is the input to Step 2, not a deliverable on
its own.

If the repo has no discoverable agent/tool entrypoints at all (no MCP tools, no FastAPI routes
reachable from an LLM call, no obvious agent loop), stop here and tell the user — do not
proceed to fabricate a mapping for nothing.

## Step 2 — Map to AAP-Core

Read `references/aap-mapping.md` now. For each tool/action discovered in Step 1, label what's
present against the six AAP-Core objects (Actor, Authority, Action, Decision, Receipt,
Invalidation), per `agf-profile/specifications/00-aap-core.md` §3.1–3.6. This step only labels
— it does not yet render a verdict or a report. Its output feeds Step 3 directly.

## Step 3 — Gap Analysis

Read `references/gap-analysis.md` now. Turn the Step 2 mapping into a per-tool-call report:
for each discovered action, mark each of {Actor, Authority, Decision, Receipt,
Execution-validation} as Present / Partial / Missing, with a one-line reason. Present this
report to the user in full — it's the deliverable they need before deciding whether to
continue. If every action already scores Present across the board (status would be FULL), say
so plainly and stop; there's nothing to plan or implement.

## Step 4 — Classify

Read `references/profile-fastapi-mcp.md` now. Check the target repo's detected stack against
the one supported MVP profile (Python + FastAPI + MCP + agf-runtime). This is a binary
match/no-match, not a lookup table — only one profile exists today.

- **Match**: continue to Step 5.
- **No match**: report status **UNSUPPORTED PROFILE**. Tell the user exactly what stack you
  detected instead (e.g. LangGraph, A2A, OpenAI Agents SDK, raw HTTP agent) and that no adapter
  exists for it in this skill yet. `agf-sdk` already ships standalone
  `langchain.py`/`crewai.py`/`browser.py` adapters usable directly without this skill — mention
  them if relevant, but do not attempt to auto-wire an unsupported stack. Stop here.

## Step 5 — Plan

Read `references/plan-format.md` now. Render `templates/integration-plan.md` into the target
repo at `.agf-integrator/integration-plan.md`: for every gap from Step 3, the exact guard to
add, the exact call site (file:line), the exact real `agf-sdk` call (see
`references/implement-fastapi-mcp.md` for the real signatures — never invent an API), and an
explicit list of every file that will be touched and confirmation that nothing else will be.

**Hard stop.** Present the plan to the user and ask them to explicitly approve it before
continuing. A plan file existing on disk is not approval — approval is the user's explicit
confirmation in this conversation. Do not proceed to Step 6 without it.

Execution-time validation (`validate_execution=True`) is real and live-verified — include it by
default for every guarded action, it is not a fallback. If, during this review, the user asks
for receipt calls to be included even though `agf-sdk` has no client method for them (the one
remaining genuine gap — see Honesty Rules), read `references/sdk-gap-fallback.md` now and fold
its pattern into the plan, clearly labeled as a hand-maintained fallback, not standard SDK usage.

## Step 6 — Implement

Only run this step once Step 5's plan has been explicitly approved. Read
`references/implement-fastapi-mcp.md` now for the real codegen recipes. Preconditions, checked
in order, each a hard stop if unmet:

1. The approved plan from Step 5 exists and was confirmed by the user in this conversation.
2. Check the target repo's git status. If there are pre-existing uncommitted changes unrelated
   to this integration, warn the user and confirm before proceeding — the diff they review at
   the end must be attributable to this run alone.
3. Create a new branch (`agf-integrator/<date>`) in the target repo. Never work directly on
   the branch that was checked out.
4. Change each file the plan named, one at a time. After each file, show a diff-style summary
   before moving to the next — do not silently batch every change into one unreviewed dump.
5. Touch nothing outside the plan's declared file list. If implementation surfaces a genuine
   need to touch an undeclared file, stop and re-run Step 5 for that addition — do not expand
   scope silently.
6. Do not run `git commit`. Leave the branch with the changes staged/unstaged for the user's
   own commit — commit authorship and message stay in their control.

## Step 7 — Verify

Read `references/verify.md` now. Render `templates/verification-report.md` with the evidence
checklist, checked against the **actual current state of the target repo after Step 6** — not
against what the plan said it would do. The checklist has two distinct sections, kept visually
separate, not one flat list: **Required verification** (Actor, Authority, Action, Decision,
Execution-time validation, Execution gated, Deny path tested, Revocation test, existing app
tests — everything `agf-sdk`'s real API surface can support, scored against what this specific
target repo actually has) and **Capability gaps** (Receipt, Decision↔Receipt correlation — the
one thing `agf-sdk` has no client method for at all, so MVP cannot close it regardless of the
target repo). Include the coverage count (N actions discovered vs. N governed vs. N decisions
enforced vs. N receipts generated). Per the Hard Rule above, do not mark Decision/Authority
Present if the guarded call has no working chain mechanism — an unchained `guard_tool()` call
422s on every real invocation, which is not a functioning gate regardless of how the code reads
structurally. The Receipt/correlation Capability-gap items must be reported as "Not implemented
— SDK capability unavailable" unless `references/sdk-gap-fallback.md` was explicitly used in
Step 5/6 — never report them as covered just because `agf-sdk` is now imported in the file. If
Step 0 reported BLOCKED, the Deny-path and Revocation-test items must say so explicitly —
"BLOCKED — see Step 0: <specific missing piece>" — rather than a generic "not tested."

## Validating this skill itself

If you are working on this skill's own files (not integrating a user's target repo), read
`references/self-test.md` — it is not part of the normal Steps 1–7 flow and must not be loaded
during a real integration run.

## Honesty Rules

- Never invent, generate, provision, read, print, or write an actual AGF credential/token
  value anywhere — only ever reference the environment-variable *name*. Provisioning a real
  credential is the user's action, through their own secret mechanism, always.
- Never mark an AAP-Core object Present because a library is imported — mark it Present only
  when a real call is made at the actual execution boundary and you have traced the code path.
- Never emit `agf-sdk` calls that don't exist. If a needed method (receipts — the one remaining
  gap) has no SDK wrapper, say so — do not invent one or silently substitute a different call
  that changes the semantics. Conversely, when a real method exists (execution-validation does —
  confirmed 2026-08-25 via source and a live test after an earlier, wrong claim otherwise), use
  it; don't perpetuate a stale "unavailable" claim without re-checking against current source.
- Never emit a `guard_tool()`/`authorize()` call with `agent_id=` and no working chain mechanism
  (`chain_provider=` backed by a real enrolled keypair, or an equivalent). Live-confirmed: this
  isn't a softer "Authority unclosed" state — it's a 422 on every real invocation. Never use a
  static `chain=` for a self-signed chain either — it expires in 5 minutes
  (`build_self_signed_chain`'s `exp = now + 300`); use `chain_provider=` so a fresh chain is
  built per call.
- Never proceed past Step 5's approval gate without an explicit user confirmation.
- Never touch files outside what Step 5's plan declared.
- Never run `git commit` on the user's behalf.
- If Step 3 finds nothing missing, or Step 4 finds no matching profile, say so and stop —
  don't manufacture work.
- Step 7's report must reflect what Step 6 actually did, not what Step 5 planned to do.
