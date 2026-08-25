Load this only when the user, during Step 5's plan review, explicitly asks for
execution-validation or receipt calls to be included even after being told `agf-sdk` has no
client method for them. Never load this file proactively, and never use its pattern as the
default codegen path in Step 6 — the default is to report the gap honestly (SKILL.md Honesty
Rules), not to paper over it.

# Fallback: raw HTTP for execution-validation / receipts

This exists because `agf-runtime` implements these server-side (Spec 30:
`agf-profile/specifications/30-execution-time-authorization-validation.md`) but `agf-sdk` has
never wrapped them in a client method (confirmed by direct grep of `agf-sdk/agf/` — zero hits
for `validate-execution`/`validate_execution`/`receipt`). If you're reading this, the user has
explicitly opted into a hand-maintained call against an otherwise-unwrapped endpoint, with the
tradeoffs already disclosed in the plan (`references/plan-format.md`).

## What `agf-sdk`'s real client already handles internally (and this fallback must replicate)

Look at `agf-sdk/agf/client.py`'s internal request helper before writing this by hand — it
already centralizes: base URL resolution, the `X-AGF-Key` auth header (not
`Authorization: Bearer` — this workspace's auth convention), timeout handling, and mapping
HTTP error codes to `AGFAuthError`/`AGFConnectionError`/etc. Mirror that behavior rather than
writing a naive `httpx.post(...)` with no error mapping — a fallback that silently swallows a
401 or a network error is worse than no fallback.

## Execution-validation call (illustrative shape — verify path/payload against the live spec before use)

```python
import httpx

async def validate_execution(base_url: str, api_key: str, artifact_id: str) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        resp = await client.post(
            f"/v1/decisions/{artifact_id}/validate-execution",
            headers={"X-AGF-Key": api_key},
        )
        resp.raise_for_status()
        return resp.json()
```

Call this immediately before dispatching the actual side-effecting action, after the
`authorize()`/`guard_tool()` decision already returned `allowed`, to re-check
revocation/expiry drift between decision time and dispatch time — that's what Spec 30 actually
validates (per `execution_validation_service.py`'s own scope note: revocation/expiry/platform-halt
only, deliberately not re-checking signature/scope/policy).

## Receipts

No documented client-callable receipt-creation endpoint was found during this skill's own
research pass — receipts are described as server-emitted only (Spec 07 §10 / AAP-Core Spec 00
§3.5), inside the runtime's own gateways. Do not fabricate a `POST` endpoint for this. If the
user wants receipt visibility, the honest options are: (a) confirm with `agf-runtime`'s current
API docs/OpenAPI schema whether a read endpoint exists to fetch a receipt after the fact, or
(b) tell the user this is not currently exposed for direct client creation and treat it as an
open gap in the verification report (Step 7) rather than working around it silently.

## Labeling requirement

Every plan entry and every verification-report line that uses this fallback must say so
explicitly (see `references/plan-format.md`'s NOTE format) — this fallback exists to serve an
explicit, informed user request, not to quietly extend this skill's default claimed coverage.
