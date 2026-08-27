Load this only from SKILL.md Step 5. Never read this file during Steps 1-4, 6-7.

# Plan

Goal: render a concrete, reviewable plan into the target repo and get explicit approval before
any code changes happen. This is the hard gate between "here's what's wrong" (Step 3) and
"here's what changes" (Step 6).

## Governance architecture, first

Before listing individual changes, fill in the template's "Governance architecture" section —
the five questions (where authorization happens, what the Actor identity represents, what
Authority is presented, how existing controls are retained, how the token is supplied). Two
rules that matter most in practice:

- **Never remove or replace an existing authorization/validation mechanism the target repo
  already has** (a role check, a resource allowlist, a path validator, anything). Layer AGF
  alongside or before it — the existing check keeps running unchanged. Removing one is a
  regression the plan would need to justify explicitly and get separate sign-off for, not a
  silent side effect of "adding AGF."
- **Never invent a per-caller/end-user identity that doesn't exist in the codebase.** Many real
  targets (especially single-tenant or stdio-transport services) have no mechanism to
  distinguish individual callers at all — only a service/process identity is available. State
  that plainly: "no per-caller identity exists; the Actor established here represents the
  deployed service itself." That is a legitimate, honest Actor — it's just not a human
  end-user, and the plan must say which one it is rather than leaving it ambiguous.
- **Always include agent enrollment as an explicit plan step, not an assumption.** A
  `guard_tool()`/`authorize()` call with no working chain mechanism doesn't just leave Authority
  unclosed — it 422s on every real invocation (live-confirmed). The plan must propose: (1) a
  one-time enrollment step (`generate_keypair()` + `register_agent()`, written as a small setup
  script, not folded into the guarded server's request path), (2) a `chain_provider=` wired per
  guarded call (never a static `chain=` — self-signed chains expire in 5 minutes), and (3) where
  the persisted private key will live (same secret-mechanism question as the API token — see
  Step 0). See `references/implement-fastapi-mcp.md` for the exact pattern.

## Rendering the plan

Copy `templates/integration-plan.md` into the target repo at `.agf-integrator/integration-plan.md`,
filling in one entry per gap identified in Step 3 that the user wants addressed (not
necessarily every gap — the user may choose to defer some). For each entry:

- The exact gap being closed (reference Step 3's report entry)
- The exact call site: file path and line number
- The exact code change: the real `agf-sdk` call from the matched profile's
  `references/implement-*.md` (`implement-fastapi-mcp.md`, `implement-a2a.md`, or
  `implement-langgraph.md` — whichever Step 4 matched), written out as it will actually appear —
  never a placeholder or pseudocode
- Whether this closes the gap fully or partially (e.g. adding `guard_tool` closes Decision but
  not Receipt or Execution-validation — say so explicitly, don't imply full coverage)

At the top of the rendered plan, include an explicit file-touch boundary section:
```
Files this plan will modify:
  - <file>
  - <file>
Files this plan will NOT touch:
  (everything else in the repo)
```

And an approval marker the user fills in:
```
Approved: <blank — filled in by the user, in chat, not by editing this file>
```

## The approval gate

A rendered plan file existing on disk is **not** approval. Present the plan's contents to the
user directly in the conversation and ask them to explicitly confirm before proceeding to
Step 6. Treat anything short of an explicit "yes, proceed" / "approved" as not approved —
if the user asks questions, answer them and re-present, don't infer approval from silence or
a tangential reply.

## Execution-time validation is not a fallback — include it by default

`validate_execution=True` on `guard_tool()` is a real, live-verified capability (corrected
2026-08-25 — see SKILL.md Honesty Rules). Include it in the plan for every guarded action by
default; there's no reason to omit it now.

## If the user asks for receipts to be included

`agf-sdk` has no client method for this today (the one remaining genuine gap — see SKILL.md
Honesty Rules). If the user, having been told this, still wants it included in the plan anyway,
read `references/sdk-gap-fallback.md` now and add those entries to the plan clearly labeled:

```
NOTE: this entry uses a hand-written HTTP fallback, not a supported agf-sdk client method.
It duplicates auth-header and error-handling logic that lives in agf-sdk internally and will
need to be maintained manually until agf-sdk ships a real client wrapper for this endpoint.
```

Do not add these silently or without this label — the plan must make the tradeoff visible at
approval time, not discover it later.

## After approval

Proceed to Step 6. Do not re-derive or re-render the plan — Step 6 implements exactly what
was approved here.
