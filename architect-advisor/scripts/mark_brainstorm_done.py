#!/usr/bin/env python3
"""
PostToolUse hook for Write: detect when superpowers `brainstorming` skill
finishes and writes its design doc, then mark a state file so the next
`writing-plans` invocation knows to gate on `brainstorm-router` first.

The brainstorming skill writes its final design to:
    docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md

This hook fires on every Write/Edit, but only acts when the path matches.

Reads:
  CLAUDE_TOOL_INPUT  JSON, e.g. {"file_path": "/abs/path/to/design.md"}
  CLAUDE_PROJECT_DIR project root (if missing, falls back to cwd)

Writes:
  ~/.claude/state/brainstorm-pending-router.json
    {"design_path": "...", "ts": 1234567890, "project_root": "..."}

This is fire-and-forget — never raises, never blocks.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path


STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "brainstorm-pending-router.json"

DESIGN_PATH_RE = re.compile(
    r"docs/superpowers/specs/\d{4}-\d{2}-\d{2}-[^/]+-design\.md$"
)


def main() -> int:
    try:
        return _run()
    except Exception as e:
        sys.stderr.write(f"[mark_brainstorm_done] silent fail: {e}\n")
        return 0


def _run() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    file_path = payload.get("file_path") or payload.get("path") or ""
    if not file_path:
        return 0

    if not DESIGN_PATH_RE.search(file_path):
        return 0

    project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "design_path": file_path,
        "ts": int(time.time()),
        "project_root": str(Path(project_root).resolve()),
    }
    STATE_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
