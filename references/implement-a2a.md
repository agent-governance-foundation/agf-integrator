Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about `agf-sdk` call signatures beyond what's written here — confirm against
`agf-sdk/agf/govern.py`/`agf-sdk/agf/client.py`/`agf-sdk/agf/keys.py` directly. For the A2A
side (`a2a-sdk`), this file's shapes come from current public docs, not a real installed
package read — confirm against the target repo's actual installed `a2a-sdk` source before
writing code, per `references/profile-a2a.md`'s honesty caveat.

# Implement (Python + A2A profile)

## Real agf-sdk API surface (same calls as the MCP profile, used directly instead of via a decorator)

```python
# agf-sdk/agf/govern.py
class AgentGovernance:
    def __init__(self, private_key_pem: str, base_url: str, audience: str = "agf") -> None: ...
    def authorize(
        self, agent_id: str, action: str, resource: str, *,
        chain: list[str] | None = None, audience: str = "agf", context: dict[str, Any] | None = None,
    ) -> AuthResult: ...

# agf-sdk/agf/client.py
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...
    async def validate_execution(self, artifact_id: str) -> ExecutionValidationResult: ...
    async def report_outcome(self, artifact_id: str, outcome: str, *, upstream_status: int | None = None) -> str | None: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...    # -> (private_key_pem, public_key_pem)
```

`AgentGovernance(private_key_pem=...)` self-signs its own chain per call — no separate
`chain_provider=` to wire for this direct-call style (that machinery exists specifically for
`guard_tool()`'s decorator use case, which doesn't apply here — see `profile-a2a.md`).

## One-time agent enrollment (identical prerequisite to the MCP profile)

Same as `references/implement-fastapi-mcp.md`'s enrollment section — read it, don't duplicate a
second, possibly-drifting copy of the same instructions. Same persistence/re-enrollment/sandbox
caveats apply unchanged: this is a service identity, not per-task.

## Wiring an AgentExecutor's execute() (the common case)

Before:
```python
from a2a.server.agent_execution import AgentExecutor

class RefundAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        result = process_refund_task(context)
        await event_queue.enqueue_event(result)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        ...
```

After:
```python
from agf import AgentGovernance
from agf.client import AGFClient

governance = AgentGovernance(private_key_pem=AGF_PRIVATE_KEY_PEM, base_url=AGF_BASE_URL)
client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=AGF_BASE_URL)

class RefundAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Confirm against the target's actual installed a2a-sdk what RequestContext really
        # exposes for a caller/task identity before claiming Actor: Present on anything beyond
        # a static service-level identity -- do not guess an attribute name here.
        result = governance.authorize(
            agent_id=AGF_AGENT_ID,
            action="task:process_refund",
            resource="RefundAgentExecutor.execute",
        )
        if result.decision not in ("ALLOW", "ALLOW_WITH_CAUTION"):
            raise PermissionError(f"AGF denied this task: {result.decision}")

        validation = await client.validate_execution(result.artifact_id)
        if validation.outcome == "invalid":
            raise PermissionError("AGF execution-time validation failed between decision and dispatch")

        outcome = "executed"
        try:
            task_result = process_refund_task(context)
            await event_queue.enqueue_event(task_result)
        except Exception:
            outcome = "not_executed"
            raise
        finally:
            # Best-effort, matches guard_tool()'s report_outcome contract -- never mask the
            # real result/exception above, never raise from this call.
            try:
                await client.report_outcome(result.artifact_id, outcome)
            except Exception:
                logger.warning("AGF report_outcome failed", exc_info=True)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        ...
```

This is illustrative shape, not a literal template — `action`/`resource` strings, the real
`RequestContext` attribute for caller identity, and whether `cancel()` also needs a Decision
gate all depend on the specific target repo. Say explicitly in the plan and verification report
that Receipts here are self-reported (`gateway="self_reported"`, per `profile-a2a.md`), not
Gateway-observed.

## Git workflow while implementing

Same as `references/implement-fastapi-mcp.md`'s Step 6 git workflow (new branch, one file at a
time with a diff shown, no commit) — not repeated here.
