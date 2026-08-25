Load this only when the user, during Step 5's plan review, explicitly asks whether receipt
visibility can be added even after being told `agf-sdk` has no client method for it. Never load
this file proactively.

# Fallback: receipts (the one remaining genuine SDK gap)

**Corrected 2026-08-25**: this file used to also cover execution-time validation, based on a
research finding that turned out to be wrong. `agf-sdk` **does** have a real client method —
`AGFClient.validate_execution()` / `guard_tool(..., validate_execution=True)` — confirmed by
reading `agf-sdk/agf/client.py:361` and `agf-sdk/agf/mcp.py:142-145`, and confirmed live against
a real local `agf-runtime`. Use `references/implement-fastapi-mcp.md`'s real pattern for that —
it is now part of the default codegen, not a fallback. This file covers **only** the one gap
that's still real: receipts.

`agf-runtime` implements receipts server-side (Spec 07 §10 / AAP-Core Spec 00 §3.5), but
`agf-sdk` has no client-callable method for creating or fetching one (confirmed: no
`receipt`-named symbol anywhere in `agf-sdk/agf/*.py`, and no commit history mentioning it —
checked directly, not inferred).

## What to do if the user wants receipt visibility anyway

Do not fabricate a `POST`/`GET` endpoint for this — unlike execution-validation, there is no
confirmed real endpoint to fall back to with a hand-rolled `httpx` call. The honest options:

1. Confirm with `agf-runtime`'s current OpenAPI schema/route list whether a read endpoint for
   fetching a receipt after the fact exists server-side at all (it may, even if `agf-sdk`
   doesn't wrap it) — if so, a hand-rolled `httpx.get(...)` following the auth/error-handling
   pattern in `agf-sdk/agf/client.py`'s internal request helper (`X-AGF-Key` header, not
   `Authorization: Bearer`) is a reasonable, labeled fallback.
2. If no such endpoint is confirmed, tell the user plainly that receipt visibility isn't
   currently exposed for direct client access, and treat it as an open gap in the verification
   report (Step 7) rather than working around it silently.

## Labeling requirement

Any fallback used here must say so explicitly in both the plan and the verification report —
this exists to serve an explicit, informed user request, not to quietly extend this skill's
default claimed coverage.
