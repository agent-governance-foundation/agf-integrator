Load this only from SKILL.md Step 2. Never read this file during Steps 1, 3-7.

# Map to AAP-Core

Goal: for each item discovered in Step 1, label what's present against the six AAP-Core
objects, faithfully to `agf-profile/specifications/00-aap-core.md` §3.1–3.6. This step labels
only — no Present/Missing/Partial verdict yet (that's Step 3). Here you're answering "what did
we find, if anything" for each object, per discovered action.

If the target repo isn't checked out alongside `agf-profile`, use the definitions below —
they are copied faithfully from the spec's intent, not reworded loosely. If in doubt, read the
actual spec file rather than relying on this summary.

## The six objects, and what to look for per discovered action

**Actor** (spec §3.1) — the identity performing the action.
Look for: a resolvable agent/user id passed into or derivable at the call site (from Step 1's
"actor signal" note). A static process-level API key is NOT an Actor — it identifies the
process, not who's acting through it.

**Authority** (spec §3.2) — the scoped, attributable grant that lets the Actor act.
Look for: any delegation chain, JWT, or expiring/scoped credential specific to this action.
A blanket "the process has an API key so anything it does is allowed" is NOT Authority — it's
the absence of scoping.

**Action** (spec §3.3) — the verb + target being performed.
Usually the easiest to map: it's the function name / route + its parameters. Note it plainly;
this rarely reveals a gap on its own, but Step 3 needs a clean Action label to reference.

**Decision** (spec §3.4) — an explicit allow/deny/review point before the Action executes.
Look for: a real call to an authorization check (AGF or ad-hoc) that gates execution, not just
a log line after the fact. An `if user.role == "admin"` check IS a Decision, just not an AGF
one — note it as "ad-hoc Decision present, not AGF-backed."

**Receipt** (spec §3.5) — recorded evidence of what happened, correlated back to the Decision.
Look for: anything that records the *outcome* of the action in a way traceable to a specific
authorization event, not just generic app logging. Generic logging without that correlation is
NOT a Receipt in the AAP-Core sense — note it as "logging present, not a correlated Receipt."

**Invalidation** (spec §3.6) — the ability to revoke or expire access mid-session, not just at
grant time.
Look for: any mechanism that could stop this Actor from continuing to act (session expiry tied
to a checkable authority, a revocation list, a kill switch). A JWT with only a long, fixed TTL
and no revocation path is weak Invalidation — note it as such rather than rounding up to "has it."

## Output

For each action from Step 1, produce a mapping entry:

```
<action_name>:
  Actor:        <what was found, or "none">
  Authority:    <what was found, or "none">
  Action:       <the verb+target, always fillable>
  Decision:     <what was found — AGF / ad-hoc / none>
  Receipt:      <what was found — correlated / generic logging / none>
  Invalidation: <what was found, or "none">
```

This is intermediate output, feeding Step 3 directly — you can summarize it briefly to the
user in passing, but the real deliverable is Step 3's gap-analysis report, not this mapping.
