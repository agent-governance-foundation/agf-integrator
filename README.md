# agf-integrator

A [Claude Code](https://claude.com/claude-code) skill that discovers, plans, implements, and
verifies [Agent Governance Foundation](https://agentgovernancefoundation.com) authorization in
an existing AI-agent codebase. It never modifies a target repository without an explicitly
approved plan, and it never claims more coverage than it can actually trace and verify.

**Status: MVP.** Five integration profiles are supported today: Python + MCP (FastAPI optional),
Python + A2A (Agent2Agent protocol), Python + LangGraph, Python + OpenAI Agents SDK, and Python +
AWS Lambda. The first four are each self-tested against a synthetic fixture, live-tested against
a real local `agf-runtime`, and validated end-to-end against a real third-party repository —
[hypercat/PyMCP-FS](https://github.com/hypercat/PyMCP-FS) (FastAPI/MCP),
[yandex-ai-studio/customer-support-chatbot](https://github.com/yandex-ai-studio/customer-support-chatbot)
(A2A),
[wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
(LangGraph), and
[jawwad-ali/ai-customer-support-agent](https://github.com/jawwad-ali/ai-customer-support-agent)
(OpenAI Agents SDK). AWS Lambda is new — it needs no new `agf-sdk` code at all (`guard_tool()`
already works unmodified on a raw handler), and is self-tested against a fixture, but hasn't yet
been live-tested or validated against a real target repo.

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

**As a plugin (recommended)** — this repo is a self-hosted Claude Code plugin marketplace with
one entry, itself:

```
/plugin marketplace add agent-governance-foundation/agf-integrator
/plugin install agf-integrator@agf-integrator
```

This restores `/agf-integrator` as an auto-discovered slash command without cloning anything
manually. *(Not yet verified against a live `claude plugin install` run — if something doesn't
match, please open an issue.)*

**Manually** — this is also just a set of markdown instructions a coding agent can follow
directly. To make it invokable as a `/agf-integrator` slash command without the plugin system,
place (or symlink) this directory under a `.claude/skills/` folder — either your personal one
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

Explicitly out of scope: per-path (vs. per-tool) authorization for a single guarded call. All
five profiles this skill's README has ever named as a target now exist.
