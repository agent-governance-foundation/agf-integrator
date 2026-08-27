Load this only from SKILL.md Step 4. Never read this file during Steps 1-3, 5-7.

# Profile: Python + LangGraph + agf-runtime

**Caution**: `langgraph` moves fast, same caveat as `a2a-sdk`. The shapes below are verified
against a real installed `langgraph` (1.2.11) and `langchain-core` (1.4.9), not just docs — but
re-check against the target repo's actual pinned version before writing code.

## Detection signals

Match if **both**:

- `langgraph` (or `langgraph-prebuilt`) appears as a dependency, **and**
- a `StateGraph(...)` instance with at least one `.add_node(name, fn)` call was found in Step 1's
  discovery.

If neither holds, that's a no-match.

## If it matches

Two distinct governance surfaces exist — tell them apart before proposing a plan, they have
different recipes:

1. **Tool-calling nodes** (`langgraph.prebuilt.ToolNode`, `create_react_agent`) — these accept
   plain `langchain_core.tools.BaseTool` instances. `agf.langchain.AGFGuardedTool` (the
   FastAPI/MCP profile's tool wrapper — see `references/profile-fastapi-mcp.md`) already *is* a
   `BaseTool`, so wrapping a tool with it and handing the wrapped instance to `ToolNode`/
   `create_react_agent` already works today, **with zero new code from this skill or `agf-sdk`**
   — verified directly against a real `ToolNode` this session, not assumed. If Step 1 discovers
   the target's tools are wired this way, the plan for those tools is exactly the FastAPI/MCP
   profile's `AGFGuardedTool` recipe — do not invent a LangGraph-specific variant that doesn't
   exist.
2. **Graph nodes with one action per node** (`StateGraph.add_node(name, fn)`, `fn` a distinct
   function per business action) — every real node shape (`langgraph.graph._node.StateNode`)
   takes `state` as its first positional arg, optionally followed by keyword-only `config`/
   `writer`/`store`/`runtime`. There is no way to route this through `AGFGuardedTool`. Use
   `agf.langgraph.guard_node` — see `references/implement-langgraph.md` for the real signature
   and a before/after example.
3. **A single generic dispatcher node** (`StateGraph.add_node("tool_call", fn)` where `fn` loops
   over `state.messages[-1].tool_calls` and invokes each by dynamic name lookup — a real, common
   pattern, found validating this profile against a real target repo, not a hypothetical) —
   `guard_node`'s `action_type=`/`resource=` are resolved **once at decoration time**, so a
   decorator on the whole dispatcher node can only express "may this agent invoke *some* tool at
   all," never "gate this specific dynamically-named tool" — the same class of ceiling as A2A's
   per-turn-not-per-tool finding, but discovered from the opposite direction (LangGraph's *own*
   idiomatic shape for tool-calling agents, not just a coarse framework boundary). For this
   shape, use a **direct, dynamic `AGFClient.decide()` call inside the dispatcher's per-call
   closure**, parameterized by the tool's real runtime name (`action_type=f"tool:{tool_call['name']}"`)
   — the same direct-call pattern `implement-a2a.md` already documents for per-instance/dynamic
   `resource=`, not `guard_node` at all. See `references/implement-langgraph.md` for a concrete
   before/after.

Like A2A, this profile does **not** use an `agf-runtime` Gateway proxy — there is no LangGraph
Gateway integration, and even if there were, it wouldn't fit this skill's existing direct-call
pattern any better than A2A's did. Call the generic `agf-sdk` surface directly:

- `agf.langgraph.guard_node(client, *, agent_id, action_type=None, resource=None, audience="agf",
  chain=None, chain_provider=None, validate_execution=False, report_outcome=False)` — a decorator
  applied directly to the function passed to `StateGraph.add_node()`. Raises `AGFDeniedError` on
  DENY and `AGFReviewRequiredError` on REVIEW_REQUIRED — **live-confirmed a real, non-rare
  outcome** for a freshly-enrolled agent under default risk config, same as every other profile.
  `guard_node` does **not** catch `AGFReviewRequiredError` itself and there is no LangGraph-native
  "requires auth" graph state to map it onto (unlike A2A's real `TaskUpdater.requires_auth()`) —
  it propagates to the caller. Say this explicitly in the plan: the target repo's own graph
  error-handling (or the caller of `.invoke()`/`.ainvoke()`) is what has to decide what happens
  next, this skill cannot manufacture a framework primitive that doesn't exist.
- Build a fresh `chain=` per call via `agf.keys.build_self_signed_chain()`, supplied through
  `chain_provider=` (never a static `chain=` — self-signed chains expire in 5 minutes), same
  reason as every other profile.
- **If the node is a bound instance method** (very common in real code — a class holding the
  graph's node functions as methods, e.g. `self._chat`), `guard_node` wraps the plain function
  *before* binding, so the real call — and `chain_provider`'s own args — carry a leading `self`
  positional arg the wrapped function's own signature doesn't show. A `chain_provider` written
  to match `_chat`'s declared `(state, config)` signature will raise `TypeError: takes 2
  positional arguments but 3 were given` at runtime — live-confirmed, not theoretical. Write
  `chain_provider` generically (`lambda *args, **kwargs: ...`) whenever the guarded function is a
  method, not a plain module-level function.
- `validate_execution=True` / `report_outcome=True` — same semantics as `guard_tool()`, include
  both by default per SKILL.md Step 5's standing instruction.

**Receipts here are `gateway="self_reported"`, never a Gateway-observed value** — same reasoning
as A2A, say so explicitly in the plan and verification report.

What a node's `state` actually carries for caller/task identity is entirely target-repo-specific
— LangGraph's `state` is just whatever `TypedDict`/schema the target defines, not a framework-
level identity concept the way even A2A's `RequestContext` loosely was. Confirm what the target
repo actually puts in `state` before claiming Actor: Present on anything beyond a static
service-level identity. **Even when a target has real per-caller identity available elsewhere**
(e.g. a session/user id resolved by the target's own separate auth layer, at the API-route level
above the graph) — `guard_node`'s `agent_id=` is a fixed string resolved once at decoration time,
same as `action_type=`/`resource=`. There is currently no built-in way to thread a dynamic
per-session AGF identity through `guard_node`; say so explicitly rather than let Authority/
Decision being Present imply the Actor tracing is stronger than a static service-level identity.

See `references/implement-langgraph.md` for concrete before/after code.

## If it doesn't match

Report status **UNSUPPORTED PROFILE**, same as the other profiles' no-match handling — tell the
user what was actually detected, mention `agf-sdk`'s standalone adapters (`langchain.py`/
`crewai.py`/`browser.py`/`openai_agents.py`) if relevant, and do not force this profile's codegen
onto a different shape. Stop here. Do not proceed to Step 5 on a no-match.
