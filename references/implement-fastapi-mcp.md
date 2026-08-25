Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about signatures beyond what's written here — if you need to confirm one, read the
actual source in `agf-sdk/agf/mcp.py` or `agf-sdk/agf/govern.py` directly rather than guessing.

# Implement (FastAPI + MCP profile)

## Real API surface (verified against agf-sdk source, do not deviate)

```python
# agf-sdk/agf/mcp.py
def guard_tool(
    client: AGFClient | SyncAGFClient,
    *,
    agent_id: str,
    action_type: str | None = None,   # defaults to f"tool:{func.__name__}"
    resource: str | None = None,      # defaults to func.__name__
    audience: str = "agf",
    chain: list[str] | None = None,
    chain_provider: ChainProvider | None = None,
) -> Callable[[F], F]: ...

# agf-sdk/agf/govern.py
class AgentGovernance:
    def authorize(
        self,
        agent_id: str,
        action: str,
        resource: str,
        *,
        chain: list[str] | None = None,
        audience: str = "agf",
        context: dict[str, Any] | None = None,
    ) -> AuthResult: ...
```

`authorize()` never raises `AGFDeniedError`/`AGFReviewRequiredError` — check `result.allowed`
explicitly. `guard_tool()` raises those on denial by default (it's a hard gate at the decorator
level); confirm current exception behavior against the installed `agf-sdk` version's source
before writing gated code, in case it's changed since this file was written.

## Wiring an MCP tool (the common case)

Before:
```python
@mcp.tool()
def issue_refund(order_id: str, amount: float) -> str:
    ...
```

After:
```python
from agf.mcp import guard_tool

@mcp.tool()
@guard_tool(client, agent_id=AGENT_ID, action_type="tool:issue_refund", resource="issue_refund")
def issue_refund(order_id: str, amount: float) -> str:
    ...
```

`guard_tool` goes *between* `def` and `@mcp.tool()` (closer to `def`) so FastMCP's schema
introspection still sees the fully-wrapped function correctly. `client` must be an
`AGFClient`/`SyncAGFClient` instance already constructed somewhere accessible (module-level or
dependency-injected) — do not construct a new client per call.

Where `AGENT_ID` comes from is real, not placeholder: if Step 1 found a per-caller identity
(a JWT, a session user id), thread that through instead of a single static constant — a static
constant only correctly represents Actor when the server process really is the acting identity
for every call (rare; call this out explicitly in the plan if so).

## Wiring a plain FastAPI route (when there's no MCP layer for a given action)

```python
from agf import AgentGovernance

governance = AgentGovernance(api_key=...)

@app.post("/refund")
async def issue_refund_route(order_id: str, amount: float, actor_id: str = Depends(get_actor_id)):
    result = governance.authorize(actor_id, "tool:issue_refund", "issue_refund")
    if not result.allowed:
        raise HTTPException(status_code=403, detail=result.reason)
    ...
```

`get_actor_id` is illustrative of "wherever this repo's real per-caller identity comes from" —
never invent a `Depends(...)` that doesn't correspond to something Step 1 actually found; if
no real per-caller identity exists, say so in the plan rather than fabricating one.

## What this closes and what it doesn't

Wiring `guard_tool`/`authorize()` closes **Decision** (and, if a real per-caller id is threaded
through, **Actor**). It does **not** close:
- **Authority** unless a real delegation chain (`chain=`) is passed — a static `api_key` alone
  is not scoped Authority
- **Receipt** — nothing here records a correlated outcome; `agf-sdk` has no client-side receipt
  API (see SKILL.md Honesty Rules)
- **Execution-validation** — `agf-sdk` has no client wrapper for
  `POST /v1/decisions/{artifact_id}/validate-execution` (Spec 30) as of this writing; see
  `references/sdk-gap-fallback.md` if the user explicitly wants a hand-rolled call to it anyway

**Also flag explicitly when it matters**: `guard_tool`'s `resource=` defaults to the function
name and is fixed at decorator-application time — it scopes the Decision to "may this agent
call this *tool*," not to any specific runtime argument (e.g. a specific file path, record id,
or resource instance passed into the call). For a resource-oriented target (a filesystem
server, a per-record API, etc.) where "can call `write_file` at all" and "can write *this
specific path*" are meaningfully different questions, say so plainly in the plan rather than
letting a per-tool Decision imply per-instance authorization it doesn't provide. Per-instance
authorization would require calling `AgentGovernance.authorize()` directly inside the function
body with a dynamic `resource=` built from the actual argument, instead of (or in addition to)
the decorator — a larger, more invasive change that needs its own explicit plan entry and
approval, not something to fold in silently.

Say this plainly in the plan (Step 5) and the verification report (Step 7) — do not let a
`guard_tool` decorator's presence imply more coverage than it actually provides.

## Git workflow while implementing

- New branch, never the checked-out one: `git checkout -b agf-integrator/<date>`
- One file at a time; after each edit, show a diff-style summary before touching the next file
- Nothing outside the approved plan's file list
- No `git commit` — leave changes staged/unstaged for the user
