Load this only when validating the agf-integrator skill's own files (e.g. after editing
SKILL.md or a reference file, before considering the change done). Never load this during a
real integration run against a user's actual target repo — it is not part of Steps 1-7.

# Self-test

No traditional unit tests exist for a markdown-instruction skill. This is the manual
pre-release checklist to run against `assets/fixtures/support-agent-fastapi-mcp/` before
considering a change to this skill's files complete.

**CI (2026-08-26)**: `.github/workflows/self-test.yml` now runs items 0-3 and the item-6
regression check automatically on every push/PR that touches `SKILL.md`, `references/**`,
`templates/**`, or `assets/fixtures/**`, via a non-interactive Claude Code invocation diffed
against `expected-gaps.md`'s structured verdicts (`scripts/diff_gap_analysis.py`). CI is a
regression net, not a replacement for actually reading the output — still walk this full
checklist by hand before a release, especially items 3-5 (plan/implementation quality, not just
verdict correctness, still need a human read).

## The fixture

`assets/fixtures/support-agent-fastapi-mcp/` is a small synthetic MCP+FastAPI server with
three tools, each deliberately built with a different gap class, matching the shape used
throughout this skill's own reference docs:

- `search_customer` — no guard at all (fully ungoverned)
- `update_ticket` — an ad-hoc role check only, no AGF Decision
- `issue_refund` — already has `guard_tool` wired with **no `chain=`/`chain_provider=`** — a
  live-confirmed non-functioning gate (422 on every real call), corrected 2026-08-25. This is
  now the fixture's sharpest test: does Step 3 correctly score its Decision as Missing (not
  Present) despite the decorator's structural presence? See `references/gap-analysis.md`'s
  Authority scoring note.

`assets/fixtures/support-agent-fastapi-mcp/expected-gaps.md` records the hand-written expected
Step 3 output for this fixture — the closest available thing to a golden file.

## Checklist

0. Run Step 0 against the fixture. Confirm it reports BLOCKED (the fixture has no credential
   configured anywhere) with a specific, correctly-attributed reason, and confirm it does NOT
   block continuing to Step 1 — readiness is informational until Step 7.
1. Run Steps 1-3 against the fixture. Diff the produced gap-analysis report against
   `expected-gaps.md`. Any unexplained divergence is a bug in `discover.md`/`aap-mapping.md`/
   `gap-analysis.md` — fix before proceeding.
2. Run Step 4. Confirm it correctly matches the FastAPI+MCP profile (this fixture is built to
   match).
3. Run Step 5. Manually inspect the generated plan: every file:line reference must be real
   (point at actual lines in the fixture), every `agf-sdk` call must match the real signatures
   in `references/implement-fastapi-mcp.md` — no invented API.
4. Approve the plan and run Step 6 against a **throwaway copy** of the fixture (never the
   checked-in copy). Confirm: a new branch was created, only the planned files were touched, a
   diff was shown per file, no commit was made.
5. Run Step 7. Confirm the evidence checklist accurately reflects what Step 6 actually did.
   Since `agf-sdk >= 0.6.0`'s canonical recipe wires `validate_execution=True` AND
   `report_outcome=True` by default (RR-0005), a correct run closes all six AAP-Core objects —
   Receipt must show Present and explicitly marked `self_reported`, never silently equated with
   a Gateway-observed receipt. Not falsely marking anything Present just because `agf-sdk` is
   imported is still the point — see `expected-gaps.md`'s post-implementation table for the
   exact expected verdicts. Also confirm Deny-path/Revocation correctly say "BLOCKED — see
   Step 0: ..." rather than a generic "not tested," given Step 0's BLOCKED finding from item 0.
6. **Regression check** — re-run Steps 1-3 on the now-implemented throwaway copy. Confirm all
   six objects score per `expected-gaps.md`'s post-implementation table (Decision/Authority/
   Execution-validation/Receipt/correlation Present, Actor Present-or-Partial per the fixture's
   caveat) — matching what Step 6 actually wired, not over- or under-crediting it. This is the
   sharpest test of the Honesty Rules — a regression here (something reads as more or less
   governed than it actually is, purely because `agf-sdk` is imported) is the single most
   important failure mode to catch before shipping a change.

Document the result of this checklist (pass/fail per item) in your own working notes when
making a change — this file doesn't dictate where, since no CI is wired up for v1.

## A2A profile fixture

`assets/fixtures/a2a-support-agent/` is the second-profile equivalent, same three-gap-class
shape adapted to A2A's real one-executor-per-entrypoint model: `SearchOrderExecutor` (no guard),
`UpdateTicketExecutor` (ad-hoc `call_context.user.is_authenticated` check, not AGF-backed),
`IssueRefundExecutor` (`client.decide()` called with an empty `chain=[]` — the same
structurally-present-but-non-functional trap as the MCP fixture's `issue_refund`). Run the same
0-6 checklist against it when changing anything in `profile-a2a.md`/`implement-a2a.md`.

**Run 2026-08-26** (manual — no `claude` CLI available in that session, so this was executed by
hand rather than via a live `/agf-integrator` invocation): building this fixture surfaced two
real bugs in `implement-a2a.md`/`profile-a2a.md` as originally shipped (an invented
`AgentGovernance` constructor call missing a required arg, and a check against a nonexistent
`.decision` field) — found by installing the real `a2a-sdk`/`agf-sdk` and reading actual source
before writing the fixture, not by the fixture itself. Both fixed before the fixture was built.
With the fix in place: Step 6 applied cleanly to a throwaway copy (new branch, one commit —
baseline only, `server.py` + a new `scripts/agf_enroll.py` changed, diffs reviewed), every
symbol used (`AGFClient.decide`/`validate_execution`/`report_outcome`, `build_self_signed_chain`,
`AGFDeniedError`, `a2a.server.agent_execution.AgentExecutor`/`RequestContext`,
`a2a.server.events.event_queue.EventQueue`) was confirmed to actually import and match its real
signature, and the regression check (re-deriving verdicts from the implemented code) matched
`expected-gaps.md`'s post-implementation table exactly for all three executors — no over- or
under-crediting. **Not done in this run**: no live local `agf-runtime` was stood up, so this
tests that the recipe is syntactically/semantically correct against real installed SDKs, not
that a live `decide()`/`validate_execution()` call actually succeeds end-to-end the way the MCP
profile's pattern was separately live-verified.

**Live-tested 2026-08-26** against a real local `agf-runtime` (Docker Postgres+OPA, real
migrations, real uvicorn) — closing the gap above. Confirmed real DENY (unenrolled agent,
identity-based hard denial) and, more valuably, surfaced a genuine third outcome this recipe
hadn't accounted for: a freshly-enrolled agent's first action commonly gets `REVIEW_REQUIRED`
under this environment's default risk config (`DEFAULT_RISK=50` + zero trust from a brand-new
self-signed chain crosses the ≥70 threshold) — **not transient**, live-confirmed that approving
the resulting `approval_request_id` neither retroactively unblocks that artifact_id
(`validate_execution()` correctly 400s on it) nor changes a later fresh `decide()` call's risk
scoring. `implement-a2a.md`'s original `execute()` example didn't catch
`AGFReviewRequiredError` at all — would have propagated as an uncaught exception (the framework
turns that into a generic `TASK_STATE_ERROR`) instead of the real, purpose-built
`TASK_STATE_AUTH_REQUIRED` the `AgentExecutor` interface actually defines for this. Fixed using
the real, verified `TaskUpdater.requires_auth()` helper. This is exactly the kind of gap live
self-testing exists to catch — a fixture/syntax-level pass alone wouldn't have surfaced it, since
`REVIEW_REQUIRED` only appears from a real runtime's actual risk-scoring pipeline.

**Real target-repo validation completed 2026-08-26** (`yandex-ai-studio/customer-support-chatbot`,
cloned to a scratchpad throwaway, a real airline customer-support A2A agent — the equivalent of
PyMCP-FS's role for the MCP profile). Classify correctly matched on the real `a2a-sdk`
dependency + `AgentExecutor` subclass signals against unfamiliar code, not the skill's own
fixture. Step 5 surfaced a genuinely new kind of governance-architecture limitation neither the
fixture nor PyMCP-FS had exercised: the repo's single A2A entrypoint
(`CustomerSupportAgentExecutor.execute()`) can only be gated at the level of "may this agent run
a support conversation turn at all" — the real mutating actions (seat change, cancellation,
baggage, meal preference, assistance — genuine `airline-api` REST endpoints) are selected and
invoked entirely inside the LLM's own MCP tool-calling, downstream and outside this executor's
process boundary. This is a coarser ceiling than the already-documented "per-tool, not
per-instance" caveat — per-conversation-turn, not even per-tool — and was disclosed explicitly
in the plan and verification report rather than letting "Decision: Present" imply more coverage
than it has. Step 6 applied cleanly (new branch, no commit, only the plan's 3 declared files
touched, `airline-api`/`chatkit-agent`/`frontend` confirmed untouched); Step 7 reported PARTIAL,
Deny-path/Revocation correctly BLOCKED per Step 0 (no live credential configured for this
specific validation). Nothing pushed to the third-party repo — this stays local, matching how
PyMCP-FS's validation was handled.

## LangGraph profile fixture

`assets/fixtures/langgraph-support-agent/` is the third-profile equivalent, adapted to
LangGraph's `StateGraph.add_node()` model. Deliberately tests only the graph-node surface
(`guard_node`) — the tool-calling surface (`ToolNode`/`create_react_agent`) already reuses the
FastAPI/MCP fixture's `AGFGuardedTool` pattern untouched, no new ground to cover there. Same
three-gap-class shape as the other fixtures: `search_order` (no guard), `update_ticket` (ad-hoc
`state["authenticated"]` check, not AGF-backed), `issue_refund` (`@guard_node(..., chain=[])`
applied — the same structurally-present-but-non-functional empty-chain trap as the MCP/A2A
fixtures' `issue_refund`/`IssueRefundExecutor`). Run the same 0-6 checklist against it when
changing anything in `profile-langgraph.md`/`implement-langgraph.md`.

**Run 2026-08-27** (manual — no `claude` CLI available in this session, same limitation the A2A
fixture build hit): the fixture itself imports and compiles cleanly against the real installed
`langgraph`/`agf-sdk` (verified directly, not assumed) — no bugs found in `profile-langgraph.md`/
`implement-langgraph.md` this time (unlike A2A's first pass, which caught two real API bugs).
Applied the `implement-langgraph.md` recipe by hand to a throwaway copy (a new
`scripts/agf_enroll.py`, `server.py` rewritten with `chain_provider=`/`validate_execution=True`/
`report_outcome=True` on all three nodes): every cited symbol (`guard_node`, `build_self_signed_chain`,
`AGFClient.register_agent`/`validate_execution`/`report_outcome`) confirmed to actually import and
match its real signature via direct inspection, and the regression check (re-deriving verdicts
from the implemented code) matched `expected-gaps.md`'s post-implementation table exactly for all
three nodes — no over- or under-crediting.

**Live-tested 2026-08-27** against a real local `agf-runtime` (Docker Postgres+OPA, real
migrations, real uvicorn) — a fixture-shaped 3-node graph (`search_order` at default risk config,
`issue_refund` at a real low-risk action type, an unenrolled-identity DENY case), all matching
`profile-langgraph.md`'s recipe exactly. **Surfaced a real, previously-unknown bug in `agf-sdk`
itself, not the fixture**: `agf.mcp._run_async_from_sync()` (shared by `guard_tool()`/
`guard_node()`/`guard_action()`) created a brand-new event loop on every sync-bridged call, which
breaks a shared `AGFClient`'s pooled httpx connections on the second call —
`RuntimeError: Event loop is closed`. Reproduced in complete isolation (no LangGraph involved)
with plain `guard_tool()` called twice. **This is the exact combination
`implement-fastapi-mcp.md`'s own canonical example uses** (async `AGFClient` guarding a sync
`def` tool) — any real MCP server handling more than one request was affected, as shipped in
`agf-sdk` 0.6.0 on PyPI. Fixed in `agf-sdk` by routing all three functions through the
already-correct, already-tested `agf._sync_bridge.run_sync` (a single persistent background
loop) instead of a fresh-loop-per-call approach — the same fix `agf.langchain`/`agf.crewai`
already had via a different bridge. Regression tests added to `test_mcp_guard.py`/
`test_langgraph_guard.py`/`test_browser_guard.py`. A second, narrower, related constraint was
also found and documented (not a bug the bridge fix can solve): mixing direct `await` calls on
an app's main event loop with sync-bridged calls, on the *same* `AGFClient` instance, is still
unsafe — `httpx.AsyncClient` can only be used from one event loop for its lifetime. This is why
enrollment must use its own, separate, discarded client instance (now stated explicitly in
`implement-fastapi-mcp.md`'s enrollment section, not just implied by file-separation style).
After both fixes, the full 3-outcome live-test passed end-to-end: DENY, REVIEW_REQUIRED, and
ALLOW with a real Receipt row confirmed in Postgres.

**Real target-repo validation completed 2026-08-27** —
[wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
(2.6k stars, 616 forks, 160 commits — real, independently maintained, not an official
LangChain/LangGraph tutorial; the LangGraph equivalent of PyMCP-FS/`customer-support-chatbot`'s
role for the other two profiles). Classify correctly matched on real signals against previously-
unseen code. Surfaced two genuinely new findings the fixture never exercised, both incorporated
into `profile-langgraph.md`/`implement-langgraph.md` before this write-up:

1. **A third real-world node shape**: a single generic `"tool_call"` dispatcher node that loops
   over `state.messages[-1].tool_calls` and invokes each by dynamic name lookup — neither
   `ToolNode` nor "one node per action" (the fixture's assumption). `guard_node`'s
   `action_type=`/`resource=` are fixed at decoration time, so wrapping the whole dispatcher can
   only express a coarse "may this agent call *some* tool" gate — the correct fix is a direct,
   dynamic `AGFClient.decide()` call inside the dispatcher's per-call closure instead, matching
   `implement-a2a.md`'s dynamic-`resource=` pattern. This is a coarser-than-fixture-assumed
   ceiling discovered from the opposite direction of A2A's per-turn finding — LangGraph's *own*
   idiomatic shape for tool-calling agents, not just a framework boundary.
2. **A real bug caught before it shipped, not just documented after**: `_chat` is a bound
   instance method (a class holding graph nodes as methods — common real code, never exercised by
   the fixture's plain module-level functions). `guard_node` wraps the plain function *before*
   binding, so the real call carries a leading `self` positional arg neither the method's own
   signature nor a naively-written `chain_provider` accounts for. A `chain_provider` matching
   `_chat`'s declared `(state, config)` signature raised `TypeError: takes 2 positional arguments
   but 3 were given` — reproduced directly against the real `guard_node`, confirmed the generic
   `lambda *args, **kwargs: ...` fix works, *then* wrote the doc guidance — not the other way
   around.

Step 1-3 found: `/chat`/`/chat/stream` routes gated by the target's own real JWT session auth
(`get_current_session`) — preserved untouched, not replaced, per `plan-format.md`'s standing rule.
Two current tools, both low-stakes as shipped (`duckduckgo_search_tool` read-only,
`ask_human` a human-confirmation pause, not itself a mutating action) — noted honestly rather than
inflating the stakes; the dispatcher-node finding is an architecture-level observation independent
of what specific tools exist today. Real per-caller identity is available in this repo
(`session.id`/`username` from its own auth) that no fixture ever had — but disclosed explicitly
that `guard_node`'s `agent_id=` is *also* fixed at decoration time, so this recipe's Actor is
still a static service-level identity, not per-session, despite richer identity being available
one layer up. Step 5 plan: `guard_node` on `_chat` (coarse turn-level gate) plus the direct-call
pattern inside `_execute_tool` (real per-tool Decision on both tools). Step 6 applied cleanly to a
throwaway clone (new branch, no commit, only the plan's 2 declared files touched — `scripts/
agf_enroll.py` new, `app/core/langgraph/graph.py` modified). Step 7 reported PARTIAL (the Actor
limitation, disclosed rather than rounded up); Deny-path/Revocation correctly BLOCKED per Step 0
(no live credential configured for this specific validation). Nothing pushed to the third-party
repo — stays local, matching how every other real-repo validation this session was handled.

## OpenAI Agents SDK profile fixture

`assets/fixtures/openai-agents-support-agent/` is the fourth-profile equivalent. Simpler than
the other three — this SDK has only one governance surface (every tool is a `FunctionTool`), no
"which surface does this belong to" split needed. Same three-gap-class shape: `search_order`
(no guard), `update_ticket` (ad-hoc `authenticated` argument check, not AGF-backed),
`issue_refund` (`guard_function_tool(issue_refund, client, ..., chain=[])` applied — the same
structurally-present-but-non-functional empty-chain trap as every other fixture's
`issue_refund`). Run the same 0-6 checklist against it when changing anything in
`profile-openai-agents.md`/`implement-openai-agents.md`.

**Run 2026-08-27** (manual — no `claude` CLI available in this session, same limitation every
other fixture build hit): the fixture itself imports and builds cleanly against the real
installed `openai-agents`/`agf-sdk` (verified directly). One naming issue caught and fixed
*while building the fixture*, before it ever reached the golden file: the guarded tool's
underlying function was initially named `_issue_refund_impl` to distinguish it from the guarded
variable, but `guard_function_tool` preserves `tool.name` unchanged — so the LLM-visible tool
name and `guard_function_tool`'s default `resource=`/`action_type=` would have been
`_issue_refund_impl`, not `issue_refund`, silently leaking an internal naming choice into the
tool's real identity. Fixed by renaming the function to `issue_refund` and the guarded variable
to `guarded_issue_refund` instead (matching `implement-openai-agents.md`'s own convention) —
confirmed via direct inspection that `agent.tools[*].name` reads `issue_refund` afterward. No
bugs found in `profile-openai-agents.md`/`implement-openai-agents.md` themselves. Applied the
`implement-openai-agents.md` recipe by hand to a throwaway copy (a new `scripts/agf_enroll.py`,
`server.py` rewritten with `chain_provider=`/`validate_execution=True`/`report_outcome=True` on
all three tools): every cited symbol (`guard_function_tool`, `build_self_signed_chain`,
`AGFClient.register_agent`/`validate_execution`/`report_outcome`) confirmed to actually import
and match its real signature, and the regression check matched `expected-gaps.md`'s
post-implementation table exactly for all three tools — no over- or under-crediting.

**Live-tested 2026-08-27** against a real local `agf-runtime`, same infra session as LangGraph's
live-test above: `search_order` at default risk config (REVIEW_REQUIRED, expected), `read_calendar`
at a real low-risk action type (ALLOW, real Receipt row confirmed in Postgres), an
unenrolled-identity DENY case. `guard_function_tool` does not share the `_run_async_from_sync`
bridge `guard_tool()`/`guard_node()` use (it only needs the opposite bridging direction, via
`asyncio.to_thread`) — unaffected by the bug found during the LangGraph fixture's live-test, and
this run confirmed that directly: all three outcomes passed cleanly on the first attempt, no
fix needed here.

**All four supported profiles now have a self-test fixture, and all four have now been
live-tested against a real local `agf-runtime`** (FastAPI/MCP, A2A, LangGraph, OpenAI Agents
SDK) — the LangGraph pass surfaced and fixed a real `agf-sdk` bug affecting `guard_tool()` too,
documented above.

**Real target-repo validation completed 2026-08-27** —
[jawwad-ali/ai-customer-support-agent](https://github.com/jawwad-ali/ai-customer-support-agent)
(10 stars, 4 forks, 73 commits, 258 automated tests — real, independently built, not an official
OpenAI tutorial; the OpenAI Agents SDK equivalent of PyMCP-FS/`customer-support-chatbot`/
`fastapi-langgraph-agent-production-ready-template`'s role for the other three profiles).
Genuinely different shape from the LangGraph target: real async, DB-mutating `@function_tool`s
(`create_ticket`/`update_ticket` — actual `INSERT`/`UPDATE` against Postgres inside a
transaction) and — unlike the LangGraph target's real JWT auth — **this repo has no
authentication or authorization anywhere** (confirmed: no `Depends(...)`, no session handling on
`/api/chat` or the Gmail/WhatsApp webhook routes; the README itself lists multi-tenancy/auth as a
future improvement). Closer in spirit to PyMCP-FS's original "real, ungoverned" finding than the
LangGraph target's richer-but-still-gapped case. Classify correctly matched on real signals
against previously-unseen code. **No new architectural finding this time** — confirmed, not
assumed: this repo's shape (one `Agent` + several independent `@function_tool`s wrapping real DB
writes, each taking `ctx: RunContextWrapper[AgentContext]` as its first param) is exactly what
`implement-openai-agents.md` already documents. The one thing this session's own fixture/unit
tests had never exercised — `guard_function_tool` wrapping a tool whose first param is
`ctx: RunContextWrapper[...]` rather than a plain typed arg — was verified directly in isolation
before finalizing the diff: worked cleanly, app context passed through untouched, `decide()`
called correctly, `tool.name` preserved. Step 5 plan: `guard_function_tool` on `create_ticket`
and `update_ticket` (2 of 11 tools — a representative subset, not every gap, same as every other
validation's scope). Step 6 applied cleanly to a throwaway clone (new branch, no commit, only
`agent/tools/ticket.py` + a new `scripts/agf_enroll.py` touched). Step 7 reported PARTIAL — Actor
scored Missing/static (this codebase has no per-caller identity anywhere, not even the weaker
"Partial" every fixture defaulted to), Deny-path/Revocation correctly BLOCKED per Step 0 (no
live credential configured for this validation). Nothing pushed to the third-party repo. **All
four supported profiles are now validated to the same three-tier standard** (fixture self-test,
live-runtime test, real third-party target-repo validation) — this closes out the validation arc
for every profile this skill supports at that time.

## AWS Lambda profile fixture

`assets/fixtures/lambda-support-agent/` is the fifth-profile equivalent, and the only one where
no new `agf-sdk` code was needed at all — `guard_tool()` (the same primitive the FastAPI/MCP
profile uses) already works unmodified on a raw Lambda handler. Deliberately three **separate**
handler functions, not three actions behind one entrypoint — that's Lambda's real deployment
unit (one function per handler), unlike every other profile's single-process shape. Same
three-gap-class shape as every other fixture: `search_order` (no guard), `update_ticket` (ad-hoc
check against a plain event field an API Gateway authorizer might set, not AGF-backed),
`issue_refund` (`@guard_tool(..., chain=[])` applied — the same structurally-present-but-
non-functional empty-chain trap as every other fixture's `issue_refund`). Run the same 0-6
checklist against it when changing anything in `profile-aws-lambda.md`/`implement-aws-lambda.md`.

**Run 2026-08-27** (manual — no `claude` CLI available in this session, same limitation every
other fixture build hit): confirmed the fixture imports and behaves correctly against the real
installed `agf-sdk`, invoked exactly the way the real `awslambdaric` runtime calls a handler
(positional, synchronous, using a real `awslambdaric.lambda_context.LambdaContext`, not a fake) —
`search_order`/`update_ticket` behaved as expected, and `issue_refund` correctly attempted a real
network call and failed at auth (no live credential configured, matching Step 0 BLOCKED — this is
actually a stronger confirmation than the other profiles' fixture builds got, since it proves the
wiring reaches a real endpoint rather than just constructing cleanly). No bugs found in
`profile-aws-lambda.md`/`implement-aws-lambda.md` themselves. Applied the `implement-aws-lambda.md`
recipe by hand to a throwaway copy (a new `scripts/agf_enroll.py`, `handlers.py` rewritten with
`chain_provider=`/`validate_execution=True`/`report_outcome=True` on all three handlers): every
cited symbol confirmed to import and match its real signature, and the regression check matched
`expected-gaps.md`'s post-implementation table exactly for all three handlers — no over- or
under-crediting. **Not done in this run**: no live local `agf-runtime` call and no real-target-
repo validation against a genuine AWS Lambda deployment — both deliberately deferred, same
pacing as every other profile's build (profile+implement+fixture first; live-test and real-repo
validation are separate, smaller follow-on steps if wanted next).

**Live-tested 2026-08-27** against a real local `agf-runtime` (Docker Postgres+OPA, real
migrations, real uvicorn), calling the fixture's guarded handlers exactly the way the real
`awslambdaric` runtime calls a handler (positional, synchronous, using a real
`awslambdaric.lambda_context.LambdaContext` per invocation). Confirmed: DENY for an unenrolled
agent identity; ALLOW with `validate_execution=True`/`report_outcome=True` for a real low-risk
action (`read:calendar`), with a real Receipt row confirmed in Postgres. One deviation from every
other profile's precedent, reported honestly rather than forced to match: the first call
(`search_order`, default risk config) returned ALLOW immediately rather than the usual
REVIEW_REQUIRED — not treated as a bug (the live-test's job is to report what actually happened,
not to enforce a specific outcome), just noted as an observed variation. **The Lambda-specific
check no other profile's live test exercises**: five consecutive calls through the *same*
guarded handler sharing the *same* module-level `AGFClient`, simulating a warm Lambda container's
repeated invocations — exactly the shape `agf-sdk`'s pre-0.7.0 sync-bridge bug broke on the
second call. All five succeeded, each producing its own real Receipt row (6 total confirmed in
Postgres for this action, including the earlier ALLOW call) — definitively confirming the 0.7.0
fix holds for this profile's real, characteristic usage pattern. No live real-target-repo
validation yet — the remaining, smaller optional item.

**All five supported profiles now have a self-test fixture; four of five (all but AWS Lambda's
real-repo pass) are validated to the full three-tier standard.**
