Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about `agf-sdk` call signatures beyond what's written here — confirm against
`agf-sdk/agf/client.py`/`agf-sdk/agf/keys.py` directly. For the A2A side (`a2a-sdk`), the
import paths and `AgentExecutor`/`RequestContext` shapes below are verified against a real
installed `a2a-sdk` (1.1.2) — `a2a-sdk` still moves fast (0.2.x → 1.1.x across its release
history), so re-check against the target's actual pinned version, don't assume this file stays
accurate forever.

**Corrected 2026-08-26, before this file was ever used**: the original version of this file
used the sync `AgentGovernance` facade with an invented signature
(`AgentGovernance(private_key_pem=..., base_url=...)` — missing the required `api_key` arg) and
checked a nonexistent `result.decision` field on `AuthResult` (which is actually a boolean-flag
result: `.allowed`/`.denied`/`.review_required`). Caught by installing `agf-sdk` and reading
`agf/govern.py` directly before building a fixture on top of it, not by anyone hitting the bug
first. Also: `AgentGovernance` wraps the *sync* client — blocking every call inside `execute()`,
which is `async def` by contract, is a real correctness problem for a server handling concurrent
tasks. Fixed below by using the *async* `AGFClient` directly, the same object the MCP profile's
`guard_tool()` already uses internally — one real async surface, not two.

# Implement (Python + A2A profile)

## Real API surface (verified against installed agf-sdk + a2a-sdk source, do not deviate)

```python
# agf-sdk/agf/client.py
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...
    async def decide(
        self, action_type: str, resource: str, *, chain: list[str] | None = None,
        audience: str = "agf", context: dict[str, Any] | None = None, policy_version: str | None = None,
    ) -> DecisionResult: ...    # raises AGFDeniedError on DENY; DecisionResult has .decision/.artifact_id on success
    async def validate_execution(self, artifact_id: str) -> ExecutionValidationResult: ...   # .result is "valid"|"invalid", never raises
    async def report_outcome(self, artifact_id: str, outcome: str, *, upstream_status: int | None = None) -> str | None: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...    # -> (private_key_pem, public_key_pem)
def build_self_signed_chain(private_key_pem: str, agent_id: str, action: str, audience: str = "agf") -> list[str]: ...  # 1-element list, JWT expires in 300s

# a2a-sdk (real, verified against the installed package)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue

class AgentExecutor(ABC):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None: ...
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None: ...

# RequestContext real properties (agf's own auth model, distinct from A2A's own ServerCallContext.user):
#   context.call_context.user -> User (.is_authenticated: bool, .user_name: str), default UnauthenticatedUser()
#   context.get_user_input(), context.task_id, context.context_id, context.current_task
```

Build a fresh `chain=` per call via `build_self_signed_chain()` — same reason as the MCP
profile: a chain built once at module load expires in 5 minutes. No `chain_provider=` machinery
to wire here (that's specific to `guard_tool()`'s decorator use case); a plain per-call function
call to `build_self_signed_chain()` inside `execute()` is enough for direct calls like this.

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
import logging
from agf.client import AGFClient
from agf.exceptions import AGFDeniedError
from agf.keys import build_self_signed_chain

logger = logging.getLogger(__name__)
client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=AGF_BASE_URL)

class RefundAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        action = "task:process_refund"
        chain = build_self_signed_chain(AGF_PRIVATE_KEY_PEM, AGF_AGENT_ID, action, "agf")
        try:
            result = await client.decide(
                action_type=action,
                resource="RefundAgentExecutor.execute",
                chain=chain,
                # context.call_context.user is A2A's own auth model (may be UnauthenticatedUser
                # if the caller wasn't authenticated at the transport layer) -- confirm what the
                # target repo actually populates before claiming Actor: Present on anything
                # beyond a static service-level identity.
                context={"caller": context.call_context.user.user_name},
            )
        except AGFDeniedError as exc:
            raise PermissionError(f"AGF denied this task: {exc}") from exc

        validation = await client.validate_execution(result.artifact_id)
        if validation.result == "invalid":
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
