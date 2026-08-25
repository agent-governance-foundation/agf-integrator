Load this only from SKILL.md Step 5, if the target repo's `agf-sdk` version predates 0.6.0 and
the user explicitly wants a receipt-visibility workaround anyway. Never load this file
proactively — for `agf-sdk >= 0.6.0`, use `references/implement-fastapi-mcp.md`'s real
`report_outcome=True` pattern instead, not this fallback.

# Historical: receipts before RR-0005 (agf-sdk < 0.6.0)

**RR-0005 (2026-08-25, `agf-sdk >= 0.6.0`) closed this gap for real** —
`guard_tool(..., report_outcome=True)` now produces a genuine, live-verified Receipt for a
`guard_tool()`-based integration (marked `gateway="self_reported"`). This file used to document
two successive wrong beliefs (that execution-time validation had no SDK method, then that
Receipt could never be produced by `guard_tool()` at all) — both corrected. It's kept only for
the case where a target repo is pinned to `agf-sdk < 0.6.0` and can't upgrade.

## If the target repo can't upgrade past agf-sdk < 0.6.0

`emit_execution_receipt()` — the server-side function that creates a Receipt row — was, before
RR-0005, only ever called from AGF's three Gateway proxies (MCP/A2A/HTTP). A `guard_tool()`-based
integration on an old `agf-sdk` genuinely cannot produce a Receipt: recommend upgrading `agf-sdk`
first (it's a backward-compatible minor bump) rather than working around this. If upgrading is
truly not an option, the honest choices are: (a) route through a Gateway proxy instead (a
materially larger, different integration than this profile's default pattern), or (b) report
Receipt as Missing in the verification report and move on — do not hand-rolled `httpx` a
`report-outcome` call against an old runtime that may not have the endpoint either.

## Labeling requirement

Any workaround used here must say so explicitly in both the plan and the verification report —
this is a documented exception for an outdated dependency, not this skill's normal path.
