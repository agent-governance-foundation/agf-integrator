#!/usr/bin/env python3
"""Diff a generated gap-analysis report against expected-gaps.md's structured verdicts.

Used by .github/workflows/self-test.yml for both the pre-implementation comparison (after
invocation 1's Steps 0-3) and the post-implementation regression check (after invocation 2's
Steps 6-7, self-test.md item 6).

Usage:
    diff_gap_analysis.py --expected-section pre|post --actual <path>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gap_report_parser import REQUIRED_TOOLS, diff_reports, parse_gap_report

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "assets" / "fixtures" / "support-agent-fastapi-mcp"
)


def load_expected(section: str) -> dict[str, dict[str, str]]:
    text = (FIXTURE_DIR / "expected-gaps.md").read_text(encoding="utf-8")
    parts = text.split("## After Step 6")
    if len(parts) != 2:
        raise SystemExit("expected-gaps.md must have exactly one '## After Step 6' section")
    chosen = parts[0] if section == "pre" else ("## After Step 6" + parts[1])
    return parse_gap_report(chosen)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-section", choices=["pre", "post"], required=True)
    parser.add_argument("--actual", type=Path, required=True)
    args = parser.parse_args()

    if not args.actual.exists():
        print(f"FAIL: expected agent output file does not exist: {args.actual}")
        return 1

    expected = load_expected(args.expected_section)
    actual = parse_gap_report(args.actual.read_text(encoding="utf-8"))

    missing_tools = REQUIRED_TOOLS - actual.keys()
    if missing_tools:
        print(f"FAIL: actual output missing tools entirely: {sorted(missing_tools)}")
        return 1

    mismatches = diff_reports(expected, actual)
    if mismatches:
        print(
            f"FAIL: {len(mismatches)} verdict mismatch(es) vs expected-gaps.md "
            f"({args.expected_section}-implementation section):"
        )
        for m in mismatches:
            print(f"  - {m}")
        return 1

    print(
        f"OK: actual output matches expected-gaps.md "
        f"({args.expected_section}-implementation section) for all tools/objects."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
