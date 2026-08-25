Load this only from SKILL.md Step 5, if the user asks whether receipts can be closed for this
integration. Never load this file proactively.

# Receipts: fetchable now, but still not producible via guard_tool()

**Corrected 2026-08-25 (twice)**: this file originally covered a fallback for both
execution-time validation and receipts, believing `agf-sdk` had no client method for either.
That was wrong for execution-time validation (see `references/implement-fastapi-mcp.md` — it's
real, live-verified, part of default codegen now). It is also now **partially** wrong for
receipts: `agf-sdk` 0.5.0+ ships `AGFClient.list_receipts()`/`get_receipt()` — a real client
method exists (confirmed: `agf-sdk/agf/client.py`, live-verified against a real local
`agf-runtime`). **But this does not close the gap for what this skill actually generates.**

## Why fetching doesn't help a guard_tool()-based integration

`emit_execution_receipt()` — the server-side function that actually creates a Receipt row — is
only ever called from AGF's three Gateway proxies (MCP/A2A/HTTP), confirmed by direct grep of
every call site in `agf-runtime`. A `guard_tool()`-based integration (what this skill's default
codegen produces) calls `decide()`/`validate_execution()` directly, with no Gateway proxy
involved. **No Receipt is ever created for those calls, so `list_receipts()` will correctly
return an empty list — there's nothing to fetch, not an error.**

Concretely: after Step 6 wires `guard_tool()` per `references/implement-fastapi-mcp.md`, do
**not** report Receipt as Present just because `list_receipts()` exists in the SDK now. Trace
whether a Receipt would actually be produced for this integration's call pattern — for the
default MCP-tool profile, it won't be, and Step 7 must say so.

## What would actually close it

Making `guard_tool()`-based calls produce a Receipt requires a real runtime change (a new
endpoint for the client to self-report its execution outcome, since AGF never observes a
non-Gateway-proxied action's real result) — proposed and pending review as
`agf-profile/implementation/review-records/RR-0005-guard-tool-execution-receipts.md`. Do not
implement anything toward this without that RR reaching `Approved` — this skill only ever
writes into target repos, never into `agf-runtime`/`agf-sdk`, so this is out of scope for
`agf-integrator` regardless, but worth knowing about when explaining to a user why Receipt
still can't be closed even though a fetch method now exists.

## If the user asks for receipt visibility anyway

There is no confirmed real create/report endpoint to fall back to for a `guard_tool()`-based
integration today (that's exactly RR-0005's subject). Tell the user plainly: receipts require
routing through an AGF Gateway proxy instead of/in addition to `guard_tool()` — a materially
different, larger integration than this profile's default pattern, not something to fold in
silently. Treat Receipt as an open gap in the verification report (Step 7).

## Labeling requirement

If a target repo's integration is later extended to also use a Gateway proxy path (out of
scope for this skill's default codegen), any resulting Receipt-related claim must say so
explicitly in both the plan and the verification report.
