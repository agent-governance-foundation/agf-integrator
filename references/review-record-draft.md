Load this only from SKILL.md Step 5, and only when Step 3's gap analysis concludes a gap is
caused by AGF itself lacking a capability — not by the target repo simply not using AGF yet.
Never load this proactively; most integrations never hit this.

# Drafting a Review Record proposal for a genuine AGF-itself gap

## When this actually applies (read carefully — it's narrower than it sounds)

This is **not** for every Missing/Partial verdict Step 3 finds. Almost every gap this skill
finds is a target-repo gap: the target simply hasn't wired `agf-sdk` yet. That's the normal
case Step 5's plan already handles — it needs no escalation, just the standard recipe in
`references/implement-fastapi-mcp.md`.

This file is for the rarer case: Step 3/5 concludes that `agf-sdk`/`agf-runtime` **itself**
has no real client method, server endpoint, or mechanism for something the integration
genuinely needs — confirmed by actually checking current source (grep the real files, don't
assume from a comment or an older doc — see
[[feedback-verify-docstrings-against-callsites]]), not inferred from "this would be nice."

**As of this file being written (2026-08-26), there is no currently-live example** — RR-0003
(execution-time validation) and RR-0005 (Receipt emission from `guard_tool()`) closed the two
real gaps that existed. All six AAP-Core objects have a real `agf-sdk` client method today for
this skill's supported profile. A candidate that looks like a gap but usually isn't:
`guard_tool`'s per-tool (not per-argument/per-path) resource scoping — this is **not** an
AGF-itself gap, since `AgentGovernance.authorize()` already supports a dynamic `resource=`
built at call time; it's a bigger target-repo implementation pattern, handled as a larger plan
item (see `references/implement-fastapi-mcp.md`'s note on this), not this file.

This mechanism exists so that **if** a genuine gap resurfaces (the way Receipt did before
RR-0005), there's already a documented way to escalate it, instead of just adding a `NOTE:` in
the plan and letting the finding evaporate once the integration ends.

## What to do when it genuinely applies

1. Confirm it's real: grep the actual current `agf-sdk`/`agf-runtime` source for the
   capability you think is missing. Quote the exact absence (function that doesn't exist,
   endpoint that doesn't exist) — not a docstring, not a comment, not an assumption.
2. Offer, as part of Step 5's plan approval (not silently): "This integration also surfaced a
   real AGF capability gap: <one line>. I can draft an unnumbered Review Record proposal for
   it, written into this target repo's `.agf-integrator/` directory — not filed anywhere in
   AGF's own repos. Want that?"
3. If yes, render `templates/review-record-draft.md` into
   `.agf-integrator/review-record-draft-<slug>.md` in the target repo, filled in from what was
   actually found in step 1.
4. Say plainly, in both the plan and the verification report, that this is a proposal for a
   human to review and manually file (with a real assigned number) into
   `agf-profile/implementation/review-records/` themselves — this skill never does that step.
