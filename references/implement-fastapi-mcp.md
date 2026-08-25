Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about signatures beyond what's written here — if you need to confirm one, read the
actual source in `agf-sdk/agf/mcp.py`, `agf-sdk/agf/govern.py`, or `agf-sdk/agf/keys.py`
directly rather than guessing.

**Corrected 2026-08-25 after a live test against a real local `agf-runtime` caught a serious
bug in the previous version of this file**: `guard_tool(client, agent_id=...)` with no `chain=`
does not degrade to some weaker mode — `POST /v1/decide` hard-requires a non-empty `chain` or a
`trust_summary`, and returns **HTTP 422** without one. Every integration this skill generated
before this correction would fail in production, not just under-close Authority. This file now
documents the pattern that actually works, verified live end-to-end.

# Implement (Python + MCP profile)

## Real API surface (verified against agf-sdk source AND a live local runtime, do not deviate)

```python
# agf-sdk/agf/mcp.py
def guard_tool(
    client: AGFClient | SyncAGFClient,
    *,
    agent_id: str,
    action_type: str | None = None,        # defaults to f"tool:{func.__name__}"
    resource: str | None = None,           # defaults to func.__name__
    audience: str = "agf",
    chain: list[str] | None = None,        # DO NOT rely on this alone — see below
    chain_provider: ChainProvider | None = None,   # use this instead, see below
    validate_execution: bool = False,      # real, live-verified — see "Execution-time validation"
) -> Callable[[F], F]: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...    # -> (private_key_pem, public_key_pem)
def build_self_signed_chain(
    private_key_pem: str, agent_id: str, action: str, audience: str = "agf",
) -> list[str]: ...   # returns a ONE-ELEMENT list; JWT expires in 300s (5 min) — see below

# agf-sdk/agf/client.py
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...
    async def validate_execution(self, artifact_id: str) -> ExecutionValidationResult: ...

# agf-sdk/agf/govern.py
class AgentGovernance:
    def authorize(
        self, agent_id: str, action: str, resource: str, *,
        chain: list[str] | None = None, audience: str = "agf", context: dict[str, Any] | None = None,
    ) -> AuthResult: ...
```

## Why a static `chain=` doesn't work: chains expire in 5 minutes

`build_self_signed_chain()` sets `exp = now + 300` (`agf-sdk/agf/keys.py:82`) — a chain built
once and passed as a static `chain=` at decorator-application time (module load) will be
**expired for every call after the first 5 minutes of process uptime**. Live-confirmed: this is
not theoretical. Use `chain_provider=` instead — a callable invoked fresh on every guarded call
— never a static `chain=` for a self-signed chain.

## One-time agent enrollment (required prerequisite — not per-call)

Before any guarded call can succeed, the agent's public key must be registered with
`agf-runtime` **once**. This is separate from, and prior to, the per-call decorator wiring:

```python
from agf import AGFClient, generate_keypair

private_key_pem, public_key_pem = generate_keypair()
client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=os.environ["AGF_BASE_URL"])
await client.register_agent(name="<service name>", did=AGF_AGENT_ID, public_key_pem=public_key_pem)
```

- **Persist `private_key_pem`** — generating a fresh keypair on every process start means the
  newly-generated public key never matches what was registered, and self-signed chains built
  from it will be signed by an unrecognized key. Live-confirmed failure mode: this produces a
  policy **DENY** (not an error), which can look like a legitimate authorization decision if you
  aren't specifically watching for it. Generate once, store the private key through the target
  repo's own secret mechanism (same category as `AGF_TOKEN` — never hardcoded, never committed;
  see `references/readiness.md`), and load it at every subsequent process start instead of
  regenerating.
- **This is a real, standing prerequisite this skill must propose as its own plan step** — write
  a small one-time enrollment script (e.g. `scripts/agf_enroll.py`) as one of the plan's file
  changes, not something folded silently into the guarded server's normal request-path code.
  Re-running `register_agent()` with a *different* public key for an *already-registered* DID
  fails (`AGFAuthError`) rather than updating the key — treat re-enrollment as a deliberate,
  separate action, not an idempotent startup call.
- **Sandbox/test-mode API keys (`agfk_test_...`) are capped** — live-confirmed: 2 active agents
  per org on sandbox tier ("Sandbox accounts are limited to 2 active agents. Go live to register
  more.", `FORBIDDEN`). Worth surfacing in the plan if the target needs more than one distinct
  agent identity under a sandbox key.

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
from agf.keys import build_self_signed_chain

def _chain_for(action_type: str):
    def _provider(*args, **kwargs) -> list[str]:
        return build_self_signed_chain(AGF_PRIVATE_KEY_PEM, AGF_AGENT_ID, action_type, "agf")
    return _provider

@mcp.tool()
@guard_tool(
    client,
    agent_id=AGF_AGENT_ID,
    action_type="tool:issue_refund",
    resource="issue_refund",
    chain_provider=_chain_for("tool:issue_refund"),
)
def issue_refund(order_id: str, amount: float) -> str:
    ...
```

`guard_tool` goes *between* `def` and `@mcp.tool()` (closer to `def`) so FastMCP's schema
introspection still sees the fully-wrapped function correctly. `client` must be an
`AGFClient`/`SyncAGFClient` instance already constructed somewhere accessible (module-level or
dependency-injected) — do not construct a new client per call. `AGF_PRIVATE_KEY_PEM` is the
persisted private key from the one-time enrollment above, loaded from the same secret mechanism
as `AGF_TOKEN` — never regenerated per process start.

Where `AGF_AGENT_ID` comes from is real, not placeholder: if Step 1 found a per-caller identity
(a JWT, a session user id), thread that through instead of a single static constant — a static
constant only correctly represents Actor when the server process really is the acting identity
for every call (rare; call this out explicitly in the plan if so).

## Execution-time validation (Spec 30) — real, live-verified, use it

`guard_tool(..., validate_execution=True)` calls `client.validate_execution(artifact_id)`
immediately after the Decision call, before the tool body runs — re-checking
revocation/expiry/platform-halt drift between decision and dispatch (`agf-sdk/agf/mcp.py:142-145`,
confirmed against real source, not a claim from a stale earlier check in this skill's history).
Include it by default for any action worth gating at all — there's no real reason to omit it
now that it's confirmed to exist and work. It raises the same `AGFDeniedError` as a failed
Decision if the execution-time check fails.

## Wiring a plain FastAPI route (when there's no MCP layer for a given action)

```python
from agf import AgentGovernance

governance = AgentGovernance(api_key=os.environ["AGF_TOKEN"], base_url=os.environ["AGF_BASE_URL"],
                              private_key_pem=AGF_PRIVATE_KEY_PEM)

@app.post("/refund")
async def issue_refund_route(order_id: str, amount: float, actor_id: str = Depends(get_actor_id)):
    result = governance.authorize(actor_id, "tool:issue_refund", "issue_refund")
    if not result.allowed:
        raise HTTPException(status_code=403, detail=result.reason)
    ...
```

`AgentGovernance(private_key_pem=...)` self-signs its chain internally per call (see
`agf-sdk/agf/govern.py:149-158`) — this is the higher-level equivalent of the
`chain_provider=build_self_signed_chain(...)` pattern above; prefer it for plain routes since it
avoids re-deriving the chain-building boilerplate. `get_actor_id` is illustrative of "wherever
this repo's real per-caller identity comes from" — never invent a `Depends(...)` that doesn't
correspond to something Step 1 actually found; if no real per-caller identity exists, say so in
the plan rather than fabricating one.

## What this closes and what it doesn't

Wiring `guard_tool`/`authorize()` with a `chain_provider`/`private_key_pem` (as above) closes
**Decision**, **Execution-validation** (if `validate_execution=True`), and a real, if minimal,
**Authority** — a self-signed single-hop chain (`iss == sub == agent_id`) is a legitimate,
scoped, signed AAP-Core Authority object, just a self-attested one rather than a multi-hop
delegation from a separate issuing authority. Say which kind it is plainly in the plan — don't
let "Authority: Present" imply a delegated chain if it's actually self-signed. It also closes
**Actor**, if a real per-caller id is threaded through.

It does **not** close:
- **Receipt** — nothing here records a correlated outcome; `agf-sdk` has no client-side receipt
  API (confirmed: no `receipt`-named method anywhere in `agf-sdk`, see SKILL.md Honesty Rules).
  This is the one remaining genuine SDK gap.
- **Decision↔Receipt correlation** — depends on Receipt existing, which it doesn't.

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
