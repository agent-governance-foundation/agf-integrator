Load this only from SKILL.md Step 0. Never read this file during Steps 1-7.

# Step 0 — AGF Readiness

Goal: check whether the target repo (and its eventual runtime environment) has what a real
`agf-sdk` integration needs — before spending effort on discovery, planning, or code. This is
an environment/configuration check, not a code-governance check (that's Steps 1-3). It never
blocks Steps 1-5 (Discover through Plan) — those are static analysis and don't need a live
credential. What it blocks, honestly, is **live verification** in Step 7: Deny-path testing and
Revocation testing both require a real call to a real `agf-runtime`, and this step is where
that gap gets surfaced up front instead of discovered awkwardly at the end.

## What to check (all static/config inspection — never touch a live network call here)

- **AGF SDK**: is `agf-sdk` already a dependency of the target repo (`requirements.txt`,
  `pyproject.toml`, an actual `import agf`)? If not, note that Step 6 will add it.
- **AGF Runtime — base URL**: is there an existing env var or config value for where
  `agf-runtime` lives (commonly `AGF_BASE_URL`, but check for whatever name the repo already
  uses if `agf-sdk` is already partially wired)? Check for the *name* being referenced, not
  a live reachability check — don't attempt to connect to it here.
- **AGF Runtime — client initialized**: does the target repo already construct an
  `AGFClient`/`SyncAGFClient`/`AgentGovernance` instance anywhere? (Overlaps with Step 1's
  discovery, checked again here specifically for readiness purposes.)
- **Agent identity**: is there a determinable `agent_id`/`AGF_AGENT_ID` value or a real
  per-caller identity source (see `references/discover.md`'s Actor guidance)? Phrase a
  negative result as "not established" — describing what the repo's code does — never as "not
  determinable because of transport X" or similar. A transport choice (stdio, HTTP, etc.)
  doesn't inherently preclude an identity concept; the repo simply hasn't built one in the code
  actually inspected. Precision here matters for a governance product: report what's absent,
  not why it's supposedly impossible.
- **Credential source**: is there an env var reference for the AGF API key/token (commonly
  `AGF_TOKEN` or `AGF_API_KEY`) already wired into a client construction call? Check for the
  *variable name* being referenced in code — **never read, print, or log the actual value**,
  even if it happens to be accessible in this environment.
- **Agent private key / enrollment**: is there an env var reference for a persisted agent
  private key (commonly `AGF_AGENT_PRIVATE_KEY`), and evidence the corresponding public key was
  ever registered (a `register_agent(...)` call, or a note that enrollment was done via a
  separate one-time script)? This is a **second, distinct secret from the API token** — required
  for `guard_tool()`/`authorize()` to succeed at all (see `references/implement-fastapi-mcp.md`;
  live-confirmed: without a working chain mechanism, `/v1/decide` returns 422, not a degraded
  decision). Missing this isn't just an Authority gap — it means the Decision call itself cannot
  function. Report that distinction explicitly, don't fold it into a generic "Authority: Missing."
- **Not hardcoded**: grep the target repo for anything that looks like a literal API key/token
  string (e.g. a long random-looking string assigned directly to an `api_key=`/`token=`
  argument instead of an `os.environ[...]`/`os.getenv(...)` call). A hardcoded credential is a
  real vulnerability independent of AGF — flag it immediately and plainly if found, don't wait
  for a later step.
- **Not exposed in git**: check whether the file that would hold the credential (typically
  `.env`) is covered by `.gitignore`. If the repo has no `.env` pattern in `.gitignore` at all
  and no other secret-management convention is evident, flag that as something to fix before
  any credential is added, not after.

## Output format

```
AGF Configuration Check

AGF SDK:
  [check-or-x] Installed | Not installed — Step 6 will add it if a plan is approved

AGF Runtime:
  [check-or-x] Base URL configured (<var name>, or "not found")
  [check-or-x] Client initialized (<file:line>, or "not found — Step 6 would add this")

Agent identity:
  [check-or-x] Determinable (<how>, or "not found")

Credentials:
  [check-or-x] Credential source found (env var name only: <NAME>) | AGF token not configured
  [check-or-x] Agent private key / enrollment found (env var name only, evidence of register_agent) | Not configured — Decision calls will 422 without this
  [check-or-x] Not hardcoded anywhere in source
  [check-or-x] Not exposed via a missing .gitignore entry

Status:
  READY | BLOCKED — <specifically what's blocked: "Step 7 live verification (Deny-path,
  Revocation) cannot run without a configured credential" if only the API token is missing; or
  "guard_tool()/authorize() calls will fail with a 422 on every real invocation, not just be
  unverifiable" if the agent private key/enrollment is also missing — never phrase either as
  blocking Steps 1-6>
```

## If credentials are missing

Do not invent, generate, or provision a token — ever. Tell the user exactly what's needed and
let them configure it. Split the output into two categories, and treat them differently:

**Safe to write** (non-secret — the skill *may* add these to `templates/agf-config.yaml` in
Step 5/6, since that template already exists for exactly this):
```
AGF_BASE_URL=<agf-runtime base URL, e.g. http://localhost:8004 for dev>
AGF_AGENT_ID=<this integration's agent identifier>
```

**Never written by this skill** (two distinct secrets — point at whatever secret mechanism the
target repo already uses, don't assume `.env` if something else is evident: Docker secrets,
CI/CD secret store, a cloud secret manager):
```
AGF_TOKEN=<the user's real AGF API key, configured through the repo's existing secret
mechanism — .env (gitignored), environment variables, Docker secrets, CI/CD secrets, or a
cloud secret manager, whichever this repo already uses or the user prefers>

AGF_AGENT_PRIVATE_KEY=<generated once via agf.generate_keypair(), the public half registered
once via a one-time enrollment step (see references/implement-fastapi-mcp.md) — persisted and
reused across restarts, never regenerated per process start, never hardcoded or committed>
```

## What this does and doesn't gate

- Steps 1-5 (Discover through Plan) proceed regardless of readiness status — static analysis
  and a written plan are useful even with zero live credentials configured, and Step 0 finding
  BLOCKED is not a reason to withhold that value.
- Step 6 (Implement) also proceeds regardless — writing `guard_tool()`/`authorize()` calls into
  source code doesn't require a live credential to exist yet.
- Step 7 (Verify) is where BLOCKED actually bites: if Step 0 found no credential, the Deny-path
  and Revocation-test checklist items must say so plainly, e.g. "BLOCKED — see Step 0: AGF
  token not configured" instead of a vaguer "not tested." This is a clearer, better-attributed
  version of the honesty the skill already required — see `references/verify.md`.
