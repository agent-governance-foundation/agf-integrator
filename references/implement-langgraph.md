Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about `agf-sdk` call signatures beyond what's written here — confirm against
`agf-sdk/agf/langgraph.py` directly. Verified against a real installed `langgraph` (1.2.11) and
`langchain-core` (1.4.9) — re-check against the target's actual pinned version, don't assume this
file stays accurate forever, same caveat as every other profile.

# Implement (Python + LangGraph profile)

## Real API surface (verified against installed agf-sdk + langgraph source, do not deviate)

```python
# agf-sdk/agf/langgraph.py
def guard_node(
    client: AGFClient | SyncAGFClient,
    *,
    agent_id: str,
    action_type: str | None = None,       # default f"node:{func.__name__}"
    resource: str | None = None,          # default func.__name__
    audience: str = "agf",
    chain: list[str] | None = None,
    chain_provider: Callable[..., list[str] | None] | None = None,
    validate_execution: bool = False,
    report_outcome: bool = False,
) -> Callable[[F], F]: ...
    # Decorator. Wraps ANY real StateNode shape (state-only, or state + keyword-only
    # config/writer/store/runtime) via *args, **kwargs forwarding -- never assumes a fixed arity.
    # Sync or async node functions both supported (LangGraph allows either).
    # Raises AGFDeniedError on DENY; AGFReviewRequiredError on REVIEW_REQUIRED (does NOT catch
    # it -- propagates to the caller, no LangGraph-native "requires auth" primitive exists).

# agf-sdk/agf/client.py -- same as every other profile
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...
    async def validate_execution(self, artifact_id: str) -> ExecutionValidationResult: ...
    async def report_outcome(self, artifact_id: str, outcome: str, *, upstream_status: int | None = None) -> str | None: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...
def build_self_signed_chain(private_key_pem: str, agent_id: str, action: str, audience: str = "agf") -> list[str]: ...

# langgraph.graph.StateGraph -- the real node-registration entrypoint this profile targets
class StateGraph:
    def add_node(self, name: str, action: StateNode, **kwargs) -> Self: ...
```

`chain_provider=` is called with the guarded node's own call arguments (state, and any
config/writer/store/runtime kwargs the node's real signature declares) — same "non-`None` wins, a
`None` return raises immediately before calling `decide()`" contract as `guard_tool()`.

## One-time agent enrollment (identical prerequisite to every other profile)

Same as `references/implement-fastapi-mcp.md`'s enrollment section — read it, don't duplicate a
second, possibly-drifting copy of the same instructions. Same persistence/re-enrollment/sandbox
caveats apply unchanged: this is a service identity, not per-task, not per-graph-invocation.

## Wiring a StateGraph node (the common case)

Before:
```python
from langgraph.graph import StateGraph

def issue_refund(state: RefundState) -> dict:
    result = process_refund(state["order_id"])
    return {"result": result}

graph = StateGraph(RefundState)
graph.add_node("issue_refund", issue_refund)
```

After:
```python
import logging
from agf.client import AGFClient
from agf.exceptions import AGFDeniedError, AGFReviewRequiredError
from agf.keys import build_self_signed_chain
from agf.langgraph import guard_node
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)
client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=AGF_BASE_URL)


def _refund_chain_provider(state: RefundState) -> list[str]:
    # Built fresh per call -- a chain built once at module load expires in 5 minutes.
    return build_self_signed_chain(AGF_PRIVATE_KEY_PEM, AGF_AGENT_ID, "node:issue_refund", "agf")


@guard_node(
    client,
    agent_id=AGF_AGENT_ID,
    action_type="node:issue_refund",
    chain_provider=_refund_chain_provider,
    validate_execution=True,
    report_outcome=True,
)
def issue_refund(state: RefundState) -> dict:
    result = process_refund(state["order_id"])
    return {"result": result}


graph = StateGraph(RefundState)
graph.add_node("issue_refund", issue_refund)
```

The wrapped node still raises on DENY/REVIEW_REQUIRED — same as any other exception a node body
might raise. **Say explicitly in the plan and verification report** what the target repo's own
graph invocation does with an uncaught exception from a node (most commonly: `.invoke()`/
`.ainvoke()` raises out to the caller, unless the target has its own node-level try/except or
`error_handler=` wired on `add_node()` — check the target's actual code, don't assume). There is
no LangGraph-native mapping for `AGFReviewRequiredError` the way A2A's `TaskUpdater
.requires_auth()` is a real framework primitive — don't invent one.

**If the node is a bound instance method, not a plain function** — real, common (a class holding
graph nodes as methods, e.g. `self._chat`), found validating this profile against a real target
repo: `guard_node` wraps the plain function *before* binding, so the actual call carries a
leading `self` positional arg the method's own declared signature doesn't show — and so does
`chain_provider`'s. A `chain_provider` written to the method's own `(state, config)` signature
raises `TypeError: takes 2 positional arguments but 3 were given` at runtime, live-confirmed.
Always write `chain_provider=lambda *args, **kwargs: ...` for a guarded method, never assume its
declared parameter list is what the decorator's inner call actually receives.

## Tool-calling nodes (ToolNode / create_react_agent) — different recipe, not this one

If Step 1 discovery instead finds the target's tools wired via `ToolNode`/`create_react_agent`,
this is the FastAPI/MCP profile's `AGFGuardedTool` recipe, not `guard_node` — see
`references/implement-fastapi-mcp.md`. `AGFGuardedTool` already works unmodified inside a real
`ToolNode` (verified). Do not wrap an already-`AGFGuardedTool`-wrapped tool with `guard_node` too
— that double-guards the same call for no reason.

## A single generic dispatcher node — direct calls, not guard_node

Real, common shape (found validating this profile against a real target repo): a lone `"tool_call"`
node that loops over `state.messages[-1].tool_calls` and invokes each by dynamic name lookup
(`self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])`). `guard_node` can't gate this
per-tool — its `action_type=`/`resource=` are fixed at decoration time, and one decorator on the
whole dispatcher node only expresses "may this agent invoke *some* tool," not "gate this specific
tool." Call `AGFClient.decide()` directly inside the per-call closure instead, parameterized by
the tool's real runtime name — same direct-call pattern `implement-a2a.md` uses for per-instance/
dynamic `resource=`:

Before:
```python
async def _execute_tool(tool_call: dict) -> ToolMessage:
    tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
    return ToolMessage(content=tool_result, name=tool_call["name"], tool_call_id=tool_call["id"])
```

After:
```python
async def _execute_tool(tool_call: dict) -> ToolMessage:
    action_type = f"tool:{tool_call['name']}"
    try:
        decision = await agf_client.decide(
            action_type,
            tool_call["name"],
            chain=build_self_signed_chain(AGF_PRIVATE_KEY_PEM, AGF_AGENT_ID, action_type, "agf"),
            context={"agent_id": AGF_AGENT_ID},
        )
        validation = await agf_client.validate_execution(decision.artifact_id)
        if validation.result == "invalid":
            raise AGFDeniedError("AGF execution-time validation failed between decision and dispatch")
    except (AGFDeniedError, AGFReviewRequiredError) as exc:
        # Surfaced to the LLM as a tool error, not a raised exception that would crash the
        # whole node/turn -- no report_outcome() here, the tool was never dispatched.
        return ToolMessage(content=f"Action denied by policy: {exc}", name=tool_call["name"], tool_call_id=tool_call["id"])

    try:
        tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
    except Exception:
        await agf_client.report_outcome(decision.artifact_id, "not_executed")
        raise
    await agf_client.report_outcome(decision.artifact_id, "executed")
    return ToolMessage(content=tool_result, name=tool_call["name"], tool_call_id=tool_call["id"])
```

Illustrative shape, not a literal template — wrap the `report_outcome()` calls in their own
best-effort try/except (matching every other profile's contract: a reporting failure must never
mask the tool's own result), and confirm the target's real tool-call dict shape (`tool_call["name"]`/
`["args"]`/`["id"]`) against its actual `langchain_core` message types before writing this.

## Git workflow while implementing

Same as `references/implement-fastapi-mcp.md`'s Step 6 git workflow (new branch, one file at a
time with a diff shown, no commit) — not repeated here.
