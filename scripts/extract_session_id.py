#!/usr/bin/env python3
"""Extract the session id from a `claude -p --output-format json` invocation's output, so a
second invocation can resume it via `--resume <id>` (self-test.yml's approval-gate handoff).

The exact field name isn't pinned by this repo's own docs, so this tries the plausible options
rather than assuming one -- if Claude Code's JSON schema changes, this fails loudly instead of
silently resuming the wrong (or no) session.

Usage: extract_session_id.py <path-to-invocation-json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CANDIDATE_KEYS = ("session_id", "sessionId", "session")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_session_id.py <path-to-invocation-json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))

    for key in CANDIDATE_KEYS:
        if key in data and data[key]:
            print(data[key])
            return 0

    print(
        f"ERROR: no session id found under any of {CANDIDATE_KEYS} in {path}; "
        f"top-level keys were: {sorted(data.keys())}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
