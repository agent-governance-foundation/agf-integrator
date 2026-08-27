Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about `agf-sdk` call signatures beyond what's written here — confirm against
`agf-sdk/agf/openai_agents.py` directly. Verified against a real installed `openai-agents`
(0.22.0) — re-check against the target's actual pinned version, don't assume this file stays
accurate forever, same caveat as every other profile.

# Implement (Python + OpenAI Agents SDK profile)

## Real API surface (verified against installed agf-sdk + openai-agents source, do not deviate)

```python
# agf-sdk/agf/openai_agents.py
def guard_function_tool(
    tool: FunctionTool,
    client: AGFClient | SyncAGFClient,
    *,
    agent_id: str,
    action_type: str | None = None,       # default f"tool:{tool.name}"
    resource: str | None = None,          # default tool.name
    audience: str = "agf",
    chain: list[str] | None = None,
    chain_provider: Callable[[ToolContext], list[str] | None] | None = None,
    validate_execution: bool = False,
    report_outcome: bool = False,
) -> FunctionTool: ...
    # Returns a NEW FunctionTool (dataclasses.replace) -- never mutates the input `tool`.
    # Wraps FunctionTool.on_invoke_tool (always async by contract). Raises AGFDeniedError on
    # DENY; AGFReviewRequiredError on REVIEW_REQUIRED (does NOT catch it -- propagates to caller).

# agf-sdk/agf/client.py -- same as every other profile
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...
    async def validate_execution(self, artifact_id: str) -> ExecutionValidationResult: ...
    async def report_outcome(self, artifact_id: str, outcome: str, *, upstream_status: int | None = None) -> str | None: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...
def build_self_signed_chain(private_key_pem: str, agent_id: str, action: str, audience: str = "agf") -> list[str]: ...

# agents.tool -- the real tool-building entrypoint this profile targets
@function_tool
def my_tool(...) -> ...: ...   # -> FunctionTool

# agents.tool_context -- what chain_provider= actually receives
class ToolContext:
    tool_name: str
    tool_call_id: str
    tool_arguments: str   # raw JSON string
    context: Any           # whatever the app passed to Runner.run(..., context=...)
```

`chain_provider=`, when set, is called with the real `ToolContext` for that invocation — same
"non-`None` wins, a `None` return raises immediately before calling `decide()`" contract as every
other profile.

## One-time agent enrollment (identical prerequisite to every other profile)

Same as `references/implement-fastapi-mcp.md`'s enrollment section — read it, don't duplicate a
second, possibly-drifting copy of the same instructions.

## Wiring a FunctionTool (the common case)

Before:
```python
from agents import Agent, function_tool

@function_tool
def issue_refund(order_id: str) -> str:
    return process_refund(order_id)

agent = Agent(name="support-agent", tools=[issue_refund])
```

After:
```python
import os
from agents import Agent, function_tool
from agf.client import AGFClient
from agf.keys import build_self_signed_chain
from agf.openai_agents import guard_function_tool

client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=AGF_BASE_URL)


def _refund_chain_provider(ctx) -> list[str]:
    # Built fresh per call -- a chain built once at module load expires in 5 minutes.
    return build_self_signed_chain(AGF_PRIVATE_KEY_PEM, AGF_AGENT_ID, "tool:issue_refund", "agf")


@function_tool
def issue_refund(order_id: str) -> str:
    return process_refund(order_id)


guarded_issue_refund = guard_function_tool(
    issue_refund,
    client,
    agent_id=AGF_AGENT_ID,
    action_type="tool:issue_refund",
    chain_provider=_refund_chain_provider,
    validate_execution=True,
    report_outcome=True,
)

agent = Agent(name="support-agent", tools=[guarded_issue_refund])
```

**If `report_outcome=True` is included** (the default per SKILL.md Step 5), the plan must also
state whether the wrapped tool needs `@function_tool(failure_error_function=None)` added. Without
it, the SDK's own default error handling catches the tool's internal exceptions and converts them
to a string return value before `guard_function_tool` ever sees them — so `report_outcome` will
report `"executed"`, not `"not_executed"`, on an internally-failed call. This is a real, tested
behavior of the underlying SDK, not a bug in the guard — say so plainly in the plan rather than
letting `report_outcome=True` imply more accuracy than it has for that specific tool's error path.

`AGFReviewRequiredError` is not caught by `guard_function_tool` — it propagates out of
`on_invoke_tool` the same as any other tool exception. Say explicitly in the plan and
verification report what the target's own `Runner.run()`/agent-loop error handling does with an
uncaught tool exception (most commonly: it becomes a tool-call error the agent sees, unless the
target has its own handling) — do not invent a "requires auth" mapping this SDK doesn't define.

## Git workflow while implementing

Same as `references/implement-fastapi-mcp.md`'s Step 6 git workflow (new branch, one file at a
time with a diff shown, no commit) — not repeated here.
