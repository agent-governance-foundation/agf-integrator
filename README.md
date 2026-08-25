# agf-integrator

A [Claude Code](https://claude.com/claude-code) skill that discovers, plans, implements, and
verifies [Agent Governance Foundation](https://agentgovernancefoundation.com) authorization in
an existing AI-agent codebase. It never modifies a target repository without an explicitly
approved plan, and it never claims more coverage than it can actually trace and verify.

**Status: MVP, not distributed as a package.** One integration profile is supported today
(Python + MCP, FastAPI optional). Self-tested against a synthetic fixture and validated
end-to-end against a real third-party repository ([hypercat/PyMCP-FS](https://github.com/hypercat/PyMCP-FS)).

## What it does

Given a target AI-agent codebase, `agf-integrator` runs an 8-step pipeline:

| Step | What it does |
|---|---|
| 0 — Readiness | Checks whether `agf-sdk`, a runtime URL, an agent identity, and a credential source are available — without ever inventing or writing a secret |
| 1 — Discover | Finds agent/tool entrypoints, existing auth logic, side effects, and audit trails |
| 2 — Map | Labels what's present against the AAP-Core object model (Actor, Authority, Action, Decision, Receipt, Invalidation) |
| 3 — Gap Analysis | Reports Present/Partial/Missing per action, per object |
| 4 — Classify | Confirms the repo matches a supported integration profile |
| 5 — Plan | Proposes exact file:line changes and real `agf-sdk` calls — **stops for explicit approval** |
| 6 — Implement | Applies the approved plan on a dedicated branch, one file at a time, with a diff shown for each — no commit made |
| 7 — Verify | Reports what was actually wired, with evidence — not a claim |

## Core principle

> Never claim AGF compliance merely because AGF libraries are installed. Compliance requires
> identifying governed actions, enforcing authorization at the execution boundary, producing
> evidence, and passing verification.

Every status this skill reports uses one of four words — **UNSUPPORTED PROFILE**, **NOT
INTEGRATED**, **PARTIAL**, or **FULL** — never "compliant." Given a real, fixed limitation in
`agf-sdk` today (no client method for execution-time validation or receipts — see
`references/sdk-gap-fallback.md`), **PARTIAL is the expected, honest outcome** for this MVP,
not a shortfall to apologize for.

## Using it

This is a set of markdown instructions for a coding agent, not an installable package. To make
it invokable as a `/agf-integrator` slash command in Claude Code, place (or symlink) this
directory under a `.claude/skills/` folder — either your personal one
(`~/.claude/skills/agf-integrator`) or a specific project's
(`<project>/.claude/skills/agf-integrator`). See
[`SKILL.md`](SKILL.md) for the full pipeline definition.

## Layout

```
SKILL.md              Entry point — the 8-step pipeline, hard rules, status vocabulary
references/            Lazy-loaded detail for each step (only read when that step runs)
templates/              Artifacts the skill writes into a target repo (plan, config, verification report)
assets/fixtures/        Synthetic target repo used for self-testing this skill's own instructions
```

## Scope

Explicitly out of scope for this MVP: adapters for LangGraph, A2A, OpenAI Agents SDK, or AWS
Lambda; a multi-profile classifier; extending `agf-sdk` with the missing execution-validation/
receipt client methods; per-path (vs. per-tool) authorization; automated CI.
