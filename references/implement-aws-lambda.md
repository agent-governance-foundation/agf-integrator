Load this only from SKILL.md Step 6 (and referenced from Step 4/5 for real signatures). Never
speculate about `agf-sdk` call signatures beyond what's written here — confirm against
`agf-sdk/agf/mcp.py` directly. Verified against the real `awslambdaric` runtime's invocation
contract (a plain sync positional `handler(event, context)` call) — see
`agf-sdk/tests/test_lambda_handler_guard.py`.

# Implement (Python + AWS Lambda profile)

## Real API surface (identical to the FastAPI/MCP profile — no Lambda-specific function exists)

```python
# agf-sdk/agf/mcp.py
def guard_tool(
    client: AGFClient | SyncAGFClient,
    *,
    agent_id: str,
    action_type: str | None = None,       # default f"tool:{func.__name__}"
    resource: str | None = None,          # default func.__name__
    audience: str = "agf",
    chain: list[str] | None = None,
    chain_provider: ChainProvider | None = None,
    validate_execution: bool = False,
    report_outcome: bool = False,
) -> Callable[[F], F]: ...
    # Decorator, fully generic over (*args, **kwargs) -- applies unchanged to a
    # def handler(event, context) Lambda entrypoint. Raises AGFDeniedError on DENY;
    # AGFReviewRequiredError on REVIEW_REQUIRED.

# agf-sdk/agf/client.py -- same as every other profile
class AGFClient:
    async def register_agent(self, name: str, did: str, public_key_pem: str, metadata=None) -> Agent: ...

# agf-sdk/agf/keys.py
def generate_keypair() -> tuple[str, str]: ...
def build_self_signed_chain(private_key_pem: str, agent_id: str, action: str, audience: str = "agf") -> list[str]: ...
```

`agf-sdk >= 0.7.0` is a **hard requirement** for this profile, not just a version floor to note —
the sync/async bridge `guard_tool()` uses to call the async `AGFClient` from a Lambda handler's
sync call site was broken before 0.7.0 (`_run_async_from_sync` created a fresh event loop per
call, breaking a shared client's pooled connections on the second call — live-confirmed this
session). A warm Lambda container reusing one module-level `AGFClient` across many invocations is
exactly this shape. Check the target's pinned `agf-sdk` version and flag it explicitly in the
plan if it predates 0.7.0 — do not propose this recipe against an older pin without saying so.

## One-time agent enrollment (identical prerequisite to every other profile)

Same as `references/implement-fastapi-mcp.md`'s enrollment section — read it, don't duplicate a
second, possibly-drifting copy. Run it as its own separate script/process with its own
`AGFClient` instance, discarded after — never the handler module's own long-lived client (same
loop-affinity reason as every other profile).

## Wiring a Lambda handler (the common case)

Before:
```python
def handler(event, context):
    order_id = event["order_id"]
    amount = event["amount"]
    result = process_refund(order_id, amount)
    return {"statusCode": 200, "body": result}
```

After:
```python
import os
from agf.client import AGFClient
from agf.exceptions import AGFDeniedError, AGFReviewRequiredError
from agf.keys import build_self_signed_chain
from agf.mcp import guard_tool

AGF_AGENT_ID = "did:agf:my-lambda-fn"
# Module-level -- reused across warm-container invocations, which is exactly why
# agf-sdk >= 0.7.0 matters here (see above).
client = AGFClient(api_key=os.environ["AGF_TOKEN"], base_url=os.environ["AGF_BASE_URL"])


def _chain_provider(event, context):
    # Built fresh per call -- a chain built once at cold-start expires in 5 minutes,
    # and a warm container can sit idle between invocations well past that.
    return build_self_signed_chain(os.environ["AGF_PRIVATE_KEY_PEM"], AGF_AGENT_ID, "lambda:issue_refund", "agf")


@guard_tool(
    client,
    agent_id=AGF_AGENT_ID,
    action_type="lambda:issue_refund",
    chain_provider=_chain_provider,
    validate_execution=True,
    report_outcome=True,
)
def handler(event, context):
    order_id = event["order_id"]
    amount = event["amount"]
    result = process_refund(order_id, amount)
    return {"statusCode": 200, "body": result}
```

`AGFDeniedError`/`AGFReviewRequiredError` propagate out of the guarded handler like any other
exception. **Say explicitly in the plan and verification report** what the target's own Lambda
runtime does with an uncaught handler exception (the real, default AWS behavior: the invocation
is recorded as a Lambda `Error` — visible in CloudWatch/whatever error-handling the target's own
deployment already has, e.g. a DLQ or `on_failure` destination) — this skill does not invent a
Lambda-native "requires auth" mapping, there isn't one.

## If the handler already has other decorators

Real, common — not a hypothetical (found validating this profile against a real target repo
using AWS Lambda Powertools' observability decorators). Apply `guard_tool()` **innermost,
immediately above `def handler`**, same side of the stack the FastAPI/MCP profile already uses
for `@mcp.tool()` (apply `guard_tool()` closer to `def`) — so the target's own outer decorators
(logging context, tracing, metrics) wrap AGF's own `decide()`/`validate_execution()` call too,
and a DENY/REVIEW_REQUIRED shows up correlated in the target's existing observability instead of
bypassing it:

```python
@init_environment_variables(model=HandlerEnvVars)      # target's own decorators, outermost —
@logger.inject_lambda_context(...)                      # unchanged, still wrap everything
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
@guard_tool(client, agent_id=AGF_AGENT_ID, action_type="lambda:issue_refund",
            chain_provider=_chain_provider, validate_execution=True, report_outcome=True)
def handler(event, context):
    ...
```

Verified directly against a real target's actual decorator stack (AWS Lambda Powertools'
`Tracer`/`Logger`/`Metrics` plus `aws_lambda_env_modeler`'s `init_environment_variables`) before
writing this guidance — both the ALLOW and DENY paths compose and propagate correctly through the
full real stack, not just in isolation.

## Git workflow while implementing

Same as `references/implement-fastapi-mcp.md`'s Step 6 git workflow (new branch, one file at a
time with a diff shown, no commit) — not repeated here.
