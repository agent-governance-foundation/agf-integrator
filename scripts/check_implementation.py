#!/usr/bin/env python3
"""Assert Step 6's git invariants inside the throwaway fixture copy, per SKILL.md's Step 6
contract and references/self-test.md item 4: a new branch was created, only planned files were
touched, no commit was made, and the fixture's golden file was never edited by the skill.

Run with CWD set to the throwaway fixture's own git repo (self-test.yml's `work/` checkout).
"""
from __future__ import annotations

import subprocess
import sys

BASELINE_BRANCH_NAMES = {"main", "master", "baseline", "HEAD"}
FORBIDDEN_PATHS = {"expected-gaps.md"}


def run(*args: str) -> str:
    # rstrip only -- `git status --porcelain` lines start with a meaningful leading space
    # (the staged/unstaged status column), which a plain .strip() would corrupt on the first
    # line by eating into the actual filename.
    return subprocess.check_output(["git", *args], text=True).rstrip("\n")


def main() -> int:
    errors: list[str] = []

    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    if branch in BASELINE_BRANCH_NAMES:
        errors.append(f"Step 6 must create a new branch, but HEAD is still {branch!r}")

    commit_count = int(run("rev-list", "--count", "HEAD"))
    if commit_count != 1:
        errors.append(
            "expected exactly 1 commit (the throwaway baseline, no auto-commit by the "
            f"skill), found {commit_count}"
        )

    changed_lines = [line for line in run("status", "--porcelain").splitlines() if line.strip()]
    if not changed_lines:
        errors.append("Step 6 produced no changes at all -- nothing was implemented")

    changed_paths = {line[3:].strip() for line in changed_lines}
    forbidden_touched = FORBIDDEN_PATHS & changed_paths
    if forbidden_touched:
        errors.append(f"Step 6 must never touch the fixture's golden file(s): {sorted(forbidden_touched)}")

    if errors:
        print("FAIL: Step 6 git invariants violated:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"OK: branch={branch!r}, {len(changed_paths)} file(s) changed, "
        "no commit made, golden file untouched."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
