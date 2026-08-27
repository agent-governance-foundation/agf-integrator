#!/usr/bin/env python3
"""Tier 1 mechanical fixture checks for agf-integrator's self-test CI
(.github/workflows/self-test.yml). Fast, deterministic, no LLM involved -- catches "someone
broke the fixture" before the expensive Tier 2 agent-based self-test even starts.

Checks:
  - server.py imports cleanly against the dependencies installed from requirements.txt
  - requirements.txt pins agf-sdk>=0.6.0 (report_outcome= needs it -- see RR-0005)
  - expected-gaps.md has exactly one pre-implementation and one post-implementation section,
    and both cover all three fixture tools and all five baseline AAP-Core objects
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gap_report_parser import REQUIRED_OBJECTS, REQUIRED_TOOLS, parse_gap_report

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "assets" / "fixtures" / "support-agent-fastapi-mcp"
)


def check_imports() -> list[str]:
    sys.path.insert(0, str(FIXTURE_DIR))
    try:
        import server  # noqa: F401
    except Exception as exc:  # noqa: BLE001 -- report any import failure, not just specific ones
        return [f"server.py failed to import: {exc!r}"]
    return []


def check_requirements_pin() -> list[str]:
    text = (FIXTURE_DIR / "requirements.txt").read_text(encoding="utf-8")
    if not re.search(r"agf-sdk\s*>=\s*0\.6\.0", text):
        return ["requirements.txt must pin agf-sdk>=0.6.0 (report_outcome= needs it, RR-0005)"]
    return []


def check_expected_gaps() -> list[str]:
    text = (FIXTURE_DIR / "expected-gaps.md").read_text(encoding="utf-8")
    sections = text.split("## After Step 6")
    if len(sections) != 2:
        return ["expected-gaps.md must have exactly one '## After Step 6' section"]

    errors: list[str] = []
    pre = parse_gap_report(sections[0])
    post = parse_gap_report("## After Step 6" + sections[1])
    for label, report in (("pre-implementation", pre), ("post-implementation", post)):
        missing_tools = REQUIRED_TOOLS - report.keys()
        if missing_tools:
            errors.append(f"{label} section missing tools: {sorted(missing_tools)}")
        for tool, objects in report.items():
            missing_objects = REQUIRED_OBJECTS - objects.keys()
            if missing_objects:
                errors.append(f"{label}/{tool} missing objects: {sorted(missing_objects)}")
    return errors


def main() -> int:
    errors = [*check_imports(), *check_requirements_pin(), *check_expected_gaps()]
    if errors:
        print("FAIL: fixture-check found problems:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: fixture is well-formed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
