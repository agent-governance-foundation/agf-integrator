"""Shared parser for the structured Present/Partial/Missing gap-analysis format used
throughout agf-integrator (expected-gaps.md, and any Step 3 output CI asks Claude Code to
produce in the same shape, for machine diffing).

Format (see assets/fixtures/support-agent-fastapi-mcp/expected-gaps.md for the real example):

    tool_name() -- file:line
      Object:      Verdict -- reason text (may wrap to further indented lines)
      ...

Object names and verdicts are the only structured fields deliberately compared -- reason prose
is not (references/self-test.md: "prose may differ, verdict must not").
"""
from __future__ import annotations

import re

TOOL_HEADER_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s*[—-]")
OBJECT_LINE_RE = re.compile(
    r"^\s*(Actor|Authority|Decision↔Receipt correlation|Decision|Receipt|Execution-validation)"
    r":\s+(Present|Partial|Missing)\b"
)

REQUIRED_TOOLS = {"search_customer", "update_ticket", "issue_refund"}
REQUIRED_OBJECTS = {"Actor", "Authority", "Decision", "Receipt", "Execution-validation"}


def parse_gap_report(text: str) -> dict[str, dict[str, str]]:
    """Parse a structured gap-analysis report into {tool: {object: verdict}}.

    Only lines inside a fenced ``` code block are considered, if the text contains any fence at
    all -- this keeps surrounding prose (which may itself mention "Present"/"Missing" in
    explanatory sentences) from being mistaken for structured data.
    """
    has_fence = "```" in text
    report: dict[str, dict[str, str]] = {}
    current_tool: str | None = None
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if has_fence and not in_fence:
            continue
        header = TOOL_HEADER_RE.match(line)
        if header:
            current_tool = header.group(1)
            report.setdefault(current_tool, {})
            continue
        obj = OBJECT_LINE_RE.match(line)
        if obj and current_tool:
            report[current_tool][obj.group(1)] = obj.group(2)
    return report


def diff_reports(
    expected: dict[str, dict[str, str]], actual: dict[str, dict[str, str]]
) -> list[str]:
    """Return human-readable mismatch descriptions; an empty list means a full match."""
    mismatches: list[str] = []
    for tool, objects in expected.items():
        actual_objects = actual.get(tool)
        if actual_objects is None:
            mismatches.append(f"{tool}: missing entirely from actual output")
            continue
        for obj, verdict in objects.items():
            actual_verdict = actual_objects.get(obj)
            if actual_verdict != verdict:
                mismatches.append(f"{tool}/{obj}: expected {verdict!r}, got {actual_verdict!r}")
    extra_tools = sorted(set(actual) - set(expected))
    if extra_tools:
        mismatches.append(f"actual output has unexpected extra tools: {extra_tools}")
    return mismatches
