Load this only from SKILL.md Step 4. Never read this file during Steps 1-3, 5-7.

# Profile: Python + AWS Lambda + agf-runtime

**No new `agf-sdk` code exists for this profile, and none is needed.** `agf.mcp.guard_tool()` —
the same primitive the FastAPI/MCP profile uses — already works unmodified on a raw Lambda
handler, verified against the real `awslambdaric` (the open-source AWS Lambda Python Runtime
Interface Client) invocation contract: `response = handler(event, context)` — a plain,
**synchronous, positional** call, never `await`ed. Python Lambda handlers are always sync at the
runtime boundary; an `async def` handler is never awaited by AWS's own runtime and fails to
marshal. `guard_tool()`'s wrapping is already fully generic over `(*args, **kwargs)`, so it
applies unchanged — see `agf-sdk/tests/test_lambda_handler_guard.py` for the regression test that
pins this against a real `awslambdaric.lambda_context.LambdaContext`.

## Detection signals

Match if **any** of:

- A `serverless.yml`, SAM `template.yaml`, or CDK `lambda.Function(...)`/`PythonFunction(...)`
  declaration whose `handler:`/`Handler:` (or `handler=`) points at a Python module function.
- A function matching the real Lambda contract found in Step 1's discovery: exactly two
  positional params (conventionally `event, context`), **not** `async def` — a real runtime
  never awaits this, so an `async def` "handler" either isn't actually the deployed entrypoint or
  is being invoked through some other wrapper Step 1 needs to trace, not assume.

If neither holds, that's a no-match.

## If it matches

Use `agf.mcp.guard_tool()` directly on the handler function — the same primitive and the same
recipe as the FastAPI/MCP profile, not a new profile-specific function. See
`references/implement-fastapi-mcp.md` for `guard_tool()`'s real signature (confirm against
`agf-sdk/agf/mcp.py` directly, don't re-derive) and `references/implement-aws-lambda.md` for a
concrete before/after wiring a real `(event, context)` handler — different enough in shape from a
FastAPI route or an MCP tool to warrant its own example, even though the underlying call is
identical.

**Lambda-specific things to get right that the FastAPI/MCP profile's own examples don't have to
think about**:

- **Warm-start reuse.** A Lambda execution environment commonly stays warm and handles many
  invocations against the same module-level `AGFClient` instance — this is exactly the repeated-
  sync-bridged-call shape the `agf-sdk` 0.7.0 `_sync_bridge.run_sync` fix (this session) made
  safe. `agf-sdk >= 0.7.0` is a **real, hard requirement** for this profile, not just a version
  floor to mention — anything older breaks on a warm container's second invocation with
  `RuntimeError: Event loop is closed`. Check the target's pinned `agf-sdk` version explicitly
  and flag it in the plan if it predates 0.7.0.
- **Enrollment must use its own, separate, discarded client** — never the handler module's own
  long-lived `AGFClient`. Same `httpx.AsyncClient`-is-loop-affine reason as every other profile's
  enrollment section, but worth restating here since a Lambda deployment's "one-time setup" step
  is often run from a local machine or a separate CI job, not obviously a "different process"
  the way a systemd service's setup script is — don't let that ambiguity lead to accidentally
  reusing the handler's client for enrollment.
- **`chain_provider=`, not a static `chain=`**, same reason as every other profile (self-signed
  chains expire in 5 minutes) — doubly relevant here since a warm Lambda container can sit idle
  between invocations for well over 5 minutes.

No Gateway proxy applies here — same direct-call-primitive pattern as every other profile,
`guard_tool()` calling `agf-runtime` directly, not through an intermediary.

## If it doesn't match

Report status **UNSUPPORTED PROFILE**, same as every other profile's no-match handling — tell the
user what was actually detected, mention `agf-sdk`'s standalone adapters if relevant, and do not
force this profile's codegen onto a different shape. Stop here. Do not proceed to Step 5 on a
no-match.
