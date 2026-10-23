# CLAUDE.md

Public Claude Code skill that discovers, plans, implements and verifies AGF authorization in a third-party agent
repo. `SKILL.md` is the skill itself; `README.md` has status; `references/` holds per-profile and per-step guides
(read only the profile you are working on); `scripts/` and `templates/` support it.

Pipeline: readiness → discover → map to AAP-Core → gap → classify → plan (approval gate) → implement (branch, no
auto-commit) → verify. Profiles: FastMCP, A2A, LangGraph, OpenAI Agents SDK, AWS Lambda — each live-tested against a
local runtime and validated on a real third-party repo.

## Design rules
- Mark an AAP object Present only when a real call is traced at the execution boundary, not because the SDK is imported.
- `guard_tool()` needs agent enrollment and `chain_provider=` building a fresh self-signed chain per call (static
  chains expire in 300 s; bare `agent_id=` gives 422).
- Status words are UNSUPPORTED PROFILE / NOT INTEGRATED / PARTIAL / FULL — never "compliant". Keep "required
  verification" gaps separate from SDK capability gaps.
- Never invent or write credentials; readiness blocks only live checks.
- When the SDK gains an optional extra, update `publish.yml`'s install command too (a past publish failed on this).

## Repo hygiene
- This repo is **public**: no private labels, internal record ids or non-public repo names in files or commit messages.
- Never modify a target repo without an approved plan.
