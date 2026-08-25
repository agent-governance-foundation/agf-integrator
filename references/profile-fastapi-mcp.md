Load this only from SKILL.md Step 4. Never read this file during Steps 1-3, 5-7.

# Profile: Python + FastAPI + MCP + agf-runtime

This is the only integration profile this skill supports today (v1 / MVP). This file is
written so that adding a second profile later means adding a sibling file + one row to a
table, not rewriting Step 4's control flow — but for now there is exactly one row.

## Detection signals

The governed surface is MCP tool calls, not FastAPI specifically — `mcp.server.fastmcp.FastMCP`
is built on Starlette, not FastAPI, so a real MCP tool server commonly has no `fastapi`
dependency at all despite the similar name. Don't require FastAPI as a co-signal; require it
only when there's also a REST route surface to govern.

Match if **either**:

- `mcp` or `fastmcp` appears as a dependency, or `@mcp.tool()` / `FastMCP(` appears in the code,
  **and** at least one function decorated with `@mcp.tool()` was found in Step 1's discovery
  (this alone is sufficient — most real target repos are pure MCP tool servers), **or**
- `fastapi` appears as a dependency (`requirements.txt`, `pyproject.toml`, or an actual
  `import fastapi` / `from fastapi import FastAPI` in the code) **and** at least one route was
  found in Step 1 reachable from an agent/LLM tool-calling layer (not just any REST route —
  a plain CRUD API with no agent-facing surface is a no-match)

If neither holds — no MCP tools and no agent-reachable FastAPI routes — that's a no-match; this
skill governs agent tool-call surfaces, not general APIs.

## If it matches

Continue to Step 5. The relevant real `agf-sdk` surface for this profile is:

- `agf.mcp.guard_tool(client, *, agent_id, action_type=None, resource=None, audience="agf", chain=None, chain_provider=None, validate_execution=False)`
  — a decorator, applied *between* `def` and `@mcp.tool()` (closer to `def`) so FastMCP's
  schema introspection sees the fully-wrapped function. Real signature, verified directly
  against `agf-sdk/agf/mcp.py`. **`chain`/`chain_provider` are not optional in practice** — a
  bare `agent_id=` with neither returns a live 422 from `agf-runtime` (`/v1/decide` requires a
  non-empty `chain` or a `trust_summary`); a static `chain=` also fails once it expires (5
  minutes for a self-signed chain). Use `chain_provider=` per `references/implement-fastapi-mcp.md`.
- `agf.AgentGovernance.authorize(agent_id, action, resource, *, chain=None, audience="agf", context=None) -> AuthResult`
  — the lower-level call `guard_tool` wraps, useful when a FastAPI route (not an MCP tool)
  needs a direct decision check instead of the decorator. Real signature, verified directly
  against `agf-sdk/agf/govern.py`. `AgentGovernance(private_key_pem=...)` self-signs its chain
  automatically per call — simpler than manual `chain_provider` wiring for plain routes.

See `references/implement-fastapi-mcp.md` for concrete before/after code using these, including
the one-time agent enrollment these calls depend on.

## If it doesn't match

Report status **UNSUPPORTED PROFILE**. Tell the user plainly what you *did* detect instead (e.g. "this repo uses LangGraph with no
MCP layer" or "this is a plain FastAPI REST API with no agent tool-calling surface"), and that
no adapter for that shape exists in this skill yet. Do not attempt to force this profile's
codegen onto a different shape.

Mention, if relevant, that `agf-sdk` already ships standalone adapters usable without this
skill: `agf/langchain.py` (`AGFGuardedTool`), `agf/crewai.py`, `agf/browser.py`
(`guard_action`/`GuardedPage` for Playwright-driven browser agents) — a user could wire these
in by hand today; this skill just doesn't yet automate discovery/gap-analysis/planning for
those stacks.

Stop here. Do not proceed to Step 5 on a no-match.
