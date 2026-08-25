---
name: agf-integrator
description: "Use when integrating an AI-agent codebase (FastAPI + MCP agents; more profiles later) with AGF governance (agf-runtime/agf-sdk) — discovers agent/tool entrypoints, maps them to the AAP-Core object model, finds governance gaps, proposes an integration plan for approval, implements it, and verifies with evidence. Never modifies a target repo without an approved plan."
---

# /agf-integrator

## What this skill is for

**Discover, integrate, and verify AGF authorization in supported AI-agent codebases.** That is
the whole promise — not "make the agent AGF compliant." This MVP has a real architectural
ceiling (no `agf-sdk` client surface for execution-time validation or receipts; see Capability
gaps in Step 7), so this skill never claims full compliance as an outcome. Its output describes
exactly what's integrated and what isn't — nothing more, nothing rounded up.

Takes an existing AI-agent codebase (a target repo — not this skill's own files) and:

0. Checks whether the environment has what a real integration needs — `agf-sdk`, a runtime
   URL, an agent identity, a credential source — without ever inventing or writing a secret
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
- **PARTIAL** — some governed actions have Decision enforced; others don't, or Capability-gap
  items remain (which they always do until `agf-sdk` grows the missing client surface).
- **FULL** — every discovered action has Decision enforced, traced, and tested. Given the
  Capability-gap ceiling, this MVP will rarely if ever report FULL — say PARTIAL honestly
  instead of stretching for FULL.

## Hard rule (read this before Step 0)

**Never claim AGF compliance merely because AGF libraries are installed.** Compliance means:
a governed action was identified, authorization is enforced at the execution boundary, and
there is evidence (a report, a test result, a receipt) — not just an import statement. Every
step below that produces output must distinguish "implemented and verified" from "present but
unverified" from "not implemented." See Honesty Rules at the end.

## Step 0 — AGF Readiness

Read `references/readiness.md` now. Check whether `agf-sdk` is available, whether an
`agf-runtime` base URL and agent identity are determinable, and whether a credential source
exists — without ever reading, printing, inventing, or writing an actual secret value. Present
the readiness report to the user (format in `references/readiness.md`). This step never blocks
Steps 1-6 — static discovery, mapping, gap analysis, planning, and code generation are all
valid without a live credential. It only determines whether Step 7's live-verification items
(Deny-path tested, Revocation test) can actually run, or must be reported BLOCKED with a
specific reason rather than a vague "not tested."

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

If, during this review, the user asks for execution-validation or receipt calls to be included
even though `agf-sdk` has no client method for them yet (see Honesty Rules), read
`references/sdk-gap-fallback.md` now and fold its raw-HTTP pattern into the plan, clearly
labeled as a hand-maintained fallback, not standard SDK usage.

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
Execution gated, Deny path tested, existing app tests — everything `agf-sdk`'s real
`authorize()`/`guard_tool()` surface can support, scored against what this specific target repo
actually has) and **Capability gaps** (Execution-time validation, Receipt, Decision↔Receipt
correlation, Revocation test — things `agf-sdk` has no client method for at all, so MVP cannot
close them regardless of the target repo). Include the coverage count (N actions discovered vs.
N governed vs. N decisions enforced vs. N receipts generated). Per the Hard Rule above,
Capability-gap items must be reported as "Not implemented — SDK capability unavailable" (or
"Not verifiable in MVP" where the item depends on another unavailable capability) unless
`references/sdk-gap-fallback.md` was explicitly used in Step 5/6 — never report them as covered
just because `agf-sdk` is now imported in the file. If Step 0 reported BLOCKED, the Deny-path
and Revocation-test items must say so explicitly — "BLOCKED — see Step 0: <specific missing
piece>" — rather than a generic "not tested."

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
- Never emit `agf-sdk` calls that don't exist. If a needed method (execution-validation,
  receipts) has no SDK wrapper, say so — do not invent one or silently substitute a different
  call that changes the semantics.
- Never proceed past Step 5's approval gate without an explicit user confirmation.
- Never touch files outside what Step 5's plan declared.
- Never run `git commit` on the user's behalf.
- If Step 3 finds nothing missing, or Step 4 finds no matching profile, say so and stop —
  don't manufacture work.
- Step 7's report must reflect what Step 6 actually did, not what Step 5 planned to do.
