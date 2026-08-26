Load this only from SKILL.md Step 4. Never read this file during Steps 1-3, 5-7.

# Profile: Python + A2A (Agent2Agent protocol) + agf-runtime

**Caution**: `a2a-sdk` moves fast (0.2.x → 1.1.x across its release history). The shapes below
are verified against a real installed `a2a-sdk` (1.1.2), not just docs — but re-check against
the target repo's actual pinned version before writing code; don't assume this file stays
accurate forever the way you shouldn't assume that for MCP either.

## Detection signals

Match if **both**:

- `a2a-sdk` (or `a2a`) appears as a dependency, **and**
- a class inheriting from `a2a.server.agent_execution.AgentExecutor` was found in Step 1's
  discovery, implementing `async def execute(self, context, event_queue)` — this is A2A's real
  task-execution entrypoint (roughly: an MCP tool call's equivalent, but for a whole task/turn,
  not a single tool). `async def cancel(self, context, event_queue)` is the companion
  cancellation handler on the same class.

If neither holds, that's a no-match.

## If it matches

Continue to Step 5. This profile does **not** use `agf-runtime`'s A2A Gateway proxy
(`gateway="a2a"`, `target_url` registration) — that's a materially larger, different
integration (per `references/sdk-gap-fallback.md`'s framing of Gateway-proxy routing in
general) than this skill's default pattern. Instead, mirror the FastAPI+MCP profile's actual
approach: call the same generic `agf-sdk` surface **directly inside `execute()`**, not through
a decorator:

- `agf.AGFClient.decide(action_type, resource, *, chain=None, audience="agf", context=None) -> DecisionResult`
  (`agf-sdk/agf/client.py`, **async** — the same client `guard_tool()` uses internally) — called
  at the top of `execute()`, before any of the agent's real task logic runs. Raises
  `AGFDeniedError` on DENY. `execute()` is a fixed-name class method with a fixed
  `(context, event_queue)` signature, so `guard_tool()`'s per-tool decorator (built around
  wrapping an arbitrarily-named function and defaulting `resource=` to its name) doesn't fit
  here — direct `decide()` calls inside the function body are already this skill's documented
  pattern for exactly this case (see `references/implement-fastapi-mcp.md`'s note on
  per-instance/dynamic `resource=`). Use the async client, not the sync `AgentGovernance` facade
  — `execute()` is `async def` by contract, and blocking calls inside it is a real correctness
  problem for a server handling concurrent tasks, not just style.
- Build a fresh `chain=` per call via `agf.keys.build_self_signed_chain()` — same reason as the
  MCP profile: a chain built once expires in 5 minutes. No `chain_provider=` machinery to wire
  here (that's specific to `guard_tool()`'s decorator use case).
- `agf.AGFClient.validate_execution()` / `report_outcome()` — call the same way, directly, right
  before and after invoking the real task logic, same as the MCP profile's
  `validate_execution=True`/`report_outcome=True` recipe.

**Receipts here are `gateway="self_reported"`, never `"a2a"`** — the `"a2a"` gateway value means
Gateway-*observed* (AGF directly forwarded the call), which this direct-call pattern never does.
Getting this label wrong would silently overstate the evidence tier; say so explicitly in the
plan and verification report, exactly as the MCP profile does for its own self-reported Receipts.

What `context: RequestContext` actually exposes for extracting a real caller/task identity (for
Actor) is version-specific — read the target's installed `a2a-sdk` source to confirm the real
attribute before claiming Actor: Present on anything beyond a static service-level identity.

See `references/implement-a2a.md` for concrete before/after code.

## If it doesn't match

Report status **UNSUPPORTED PROFILE**, same as `profile-fastapi-mcp.md`'s no-match handling —
tell the user what was actually detected, mention `agf-sdk`'s standalone adapters
(`langchain.py`/`crewai.py`/`browser.py`) if relevant, and do not force this profile's codegen
onto a different shape. Stop here. Do not proceed to Step 5 on a no-match.
