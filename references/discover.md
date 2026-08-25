Load this only from SKILL.md Step 1. Never read this file during Steps 2-7.

# Discover

Goal: find every place the target repo lets an AI agent take an action, and everything
already surrounding that action (identity, auth, logging). This step only gathers facts —
it does not judge them. Judgment happens in Step 3 (Gap Analysis).

## What to look for

**Entrypoints / tool execution paths**
- `@mcp.tool()` decorators (FastMCP or the `mcp` package) — the primary MVP signal
- FastAPI routes (`@app.post(...)`, `@router.post(...)`, etc.) that an LLM call or agent loop
  reaches, directly or via a tool-calling layer
- Any `async def` / `def` reachable from a "tool call" dispatch table (e.g. a dict mapping
  tool names to functions, common in hand-rolled agent loops without MCP)

For each one found, note: function name, file:line, decorator stack order (this matters —
e.g. does an existing `@guard_tool` sit *under* `@mcp.tool()`, or is there no guard at all).

**Identity / credential handling**
Look for two distinct things and do not conflate them:
- How the *process* authenticates outward (a static API key, a service-account credential,
  env vars like `API_KEY`, `SERVICE_TOKEN`)
- How the *calling agent or end-user* is identified for a given tool call, if at all (a
  session user id, a `agent_id`/`user_id` parameter, a JWT passed through, or — commonly —
  nothing distinguishing one caller from another)

Most target repos have the first and lack the second. That gap is exactly what "Actor" in
Step 2 will flag.

**Existing authorization logic**
- Any `if user.role != ...`, `if not is_admin(...)`, permission-check helper, or similar
  ad-hoc gate already present at a call site
- Any existing `agf-sdk` usage: grep for `from agf import`, `from agf.mcp import guard_tool`,
  `AgentGovernance(`, `AGFClient(`. If found, note exactly which call sites already have it and
  which don't — partial coverage is common and must be reported precisely, not rounded up.

**External side effects**
Grep for risky-verb function/route names that indicate a real-world effect, not just a read:
`update_`, `delete_`, `issue_`, `send_`, `refund`, `charge`, `create_`, `cancel_`, `transfer_`,
`write_`. A tool named `search_x` or `get_x` is usually read-only and lower priority than one
of these, but still gets listed — Step 3 will decide priority based on what's actually missing,
not the verb alone.

**Existing audit/logging**
- Structured logging around tool calls (what gets logged, and does it include who/what/when/outcome)
- Any existing receipt, audit-trail, or "record of what happened" mechanism, AGF or otherwise

## Output

Produce a discovery summary as a simple list, one entry per discovered tool/action:

```
- <function_name> (<file>:<line>)
  entrypoint: mcp.tool | fastapi.route | dispatch-table
  guard stack: none | <existing decorator/check>
  actor signal: none | <how a caller is identified>
  side effect: read-only | <verb category>
  existing audit: none | <what exists>
```

Present this list to the user directly (short form) rather than dumping raw grep output. This
is the input to Step 2 — do not skip ahead and start labeling AAP-Core objects here.

If nothing is discoverable at all, say so and stop per SKILL.md Step 1's guard — do not
proceed to invent a mapping for an empty result.
