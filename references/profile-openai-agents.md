Load this only from SKILL.md Step 4. Never read this file during Steps 1-3, 5-7.

# Profile: Python + OpenAI Agents SDK + agf-runtime

**Caution**: `openai-agents` moves fast, same caveat as `a2a-sdk`/`langgraph`. The shapes below
are verified against a real installed `openai-agents` (0.22.0), not just docs — re-check against
the target repo's actual pinned version before writing code.

## Detection signals

Match if **both**:

- `openai-agents` (import name `agents`) appears as a dependency, **and**
- a `@function_tool`-decorated function or an `Agent(...)` construction was found in Step 1's
  discovery.

If neither holds, that's a no-match.

## If it matches

Unlike LangGraph, there is only **one** governance surface here — every tool in this SDK is an
`agents.tool.FunctionTool` (what `@function_tool` builds); there is no separate "graph node"
concept. Use `agf.openai_agents.guard_function_tool` — see `references/implement-openai-agents.md`
for the real signature and a before/after example.

This SDK also ships its own native tool-level hook, `agents.tool_guardrails.ToolInputGuardrail`
(attach via `function_tool(..., tool_input_guardrails=[...])`). `agf-sdk` deliberately does
**not** use it — its `raise_exception()` behavior collapses every DENY/REVIEW_REQUIRED into one
generic `ToolInputGuardrailTripwireTriggered` (the real reason lives in `.output.output_info`,
not as a distinguishable exception type), and there's no output-side hook that sees both success
and exception the way `report_outcome`'s executed/not_executed split needs. `guard_function_tool`
wraps `on_invoke_tool` directly instead — same "wrap the tool object" pattern as
`AGFGuardedTool`/`AGFCrewAITool` — which preserves `AGFDeniedError`/`AGFReviewRequiredError` as
their real, specific types. Do not propose using `tool_input_guardrails=` in a plan; it is not
what this skill's codegen emits.

No Gateway-proxy equivalent exists for this SDK (same direct-call pattern as every other profile).
Call the generic surface directly:

- `agf.openai_agents.guard_function_tool(tool, client, *, agent_id, action_type=None,
  resource=None, audience="agf", chain=None, chain_provider=None, validate_execution=False,
  report_outcome=False) -> FunctionTool` — returns a **new** `FunctionTool`, wrapping an
  already-built one (e.g. from `@function_tool`); never mutates the input. Raises
  `AGFDeniedError` on DENY, `AGFReviewRequiredError` on REVIEW_REQUIRED — live-confirmed a real,
  non-rare outcome for a freshly-enrolled agent under default risk config, same as every other
  profile. Neither is caught internally; both propagate to the caller.
- Build a fresh `chain=` per call via `agf.keys.build_self_signed_chain()`, supplied through
  `chain_provider=` (never a static `chain=` — self-signed chains expire in 5 minutes).
- `validate_execution=True` / `report_outcome=True` — same semantics as `guard_tool()`, include
  both by default per SKILL.md Step 5's standing instruction.

**Real, tested caveat that any plan enabling `report_outcome=True` must state explicitly**:
`@function_tool`'s *default* `failure_error_function` catches the wrapped Python function's own
exception INSIDE `on_invoke_tool` and converts it to a normal string return value (never raises)
— so `guard_function_tool`'s try/except never sees it, and `report_outcome` will accurately-per-
what-happened-at-this-boundary report `"executed"`, not `"not_executed"`, on a tool that
internally failed. If the plan needs accurate `not_executed` reporting on internal tool errors,
it must also change the tool's own `@function_tool(...)` call to add
`failure_error_function=None` — say this in the plan as an explicit, separate line item, not a
silent side effect of adding the guard.

**Receipts here are `gateway="self_reported"`, never a Gateway-observed value** — same reasoning
as every other direct-call profile, say so explicitly in the plan and verification report.

`ToolContext` (the real second positional-equivalent arg `on_invoke_tool` receives, exposed to
`chain_provider=` callers) has no built-in caller-identity concept — `.context` is whatever the
app passed to `Runner.run(..., context=...)`. Confirm what the target repo actually puts there
before claiming Actor: Present on anything beyond a static service-level identity — same caveat
as every other profile.

See `references/implement-openai-agents.md` for concrete before/after code.

## If it doesn't match

Report status **UNSUPPORTED PROFILE**, same as every other profile's no-match handling — tell the
user what was actually detected, mention `agf-sdk`'s standalone adapters (`langchain.py`/
`crewai.py`/`browser.py`) and that AWS Lambda's raw handlers already work via the existing
`guard_tool()` with no adapter needed, if relevant. Do not force this profile's codegen onto a
different shape. Stop here. Do not proceed to Step 5 on a no-match.
