#!/usr/bin/env python3
"""
PreToolUse hook for Skill tool: enforce brainstorm-router gate before
`superpowers:writing-plans` (or `writing-plans`) is invoked.

If the brainstorming skill recently produced a design doc (state file
written by mark_brainstorm_done.py), and the router hasn't run yet, we
block writing-plans and prompt the user to run brainstorm-router first.

The user can clear the gate by either:
  - Running /arch-advisor flow (which uses brainstorm-router)
  - Manually deleting ~/.claude/state/brainstorm-pending-router.json

Reads:
  CLAUDE_TOOL_INPUT  JSON, e.g. {"skill": "superpowers:writing-plans"}

Exit codes:
  0 — allow tool call
  1 — block (state shows pending router) — message goes to stderr
  Any unexpected error → exit 0 (fail-open)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


STATE_FILE = Path.home() / ".claude" / "state" / "brainstorm-pending-router.json"

# Match writing-plans skill across naming variations
WRITING_PLANS_NAMES = {
    "writing-plans",
    "superpowers:writing-plans",
    "execute-plan",
    "superpowers:execute-plan",
}

# State stale threshold (24h) — older than this, we let it through
STALE_AFTER_SECONDS = 24 * 3600


def main() -> int:
    try:
        return _run()
    except Exception as e:
        sys.stderr.write(f"[gate_writing_plans] unexpected error, allowing call: {e}\n")
        return 0


def _run() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    skill_name = (payload.get("skill") or "").strip()
    if skill_name not in WRITING_PLANS_NAMES:
        return 0

    if not STATE_FILE.is_file():
        return 0

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    ts = state.get("ts")
    if isinstance(ts, (int, float)) and (time.time() - ts) > STALE_AFTER_SECONDS:
        # Stale state — clean up and let through
        try:
            STATE_FILE.unlink()
        except OSError:
            pass
        return 0

    sys.stderr.write(_block_message(state))
    return 1


def _block_message(state: dict) -> str:
    return (
        "\n"
        "🛑 writing-plans blocked — brainstorming finished but brainstorm-router hasn't run (CLAUDE.md §7).\n"
        "\n"
        f"Recent design doc: {state.get('design_path', '(unknown)')}\n"
        "\n"
        "Run the router first (it scores the brainstorm output and recommends a path):\n"
        "  - Dispatch the `brainstorm-router` subagent at ~/.claude/agents/brainstorm-router.md\n"
        "  - Or run /architect-advisor (which routes through it automatically)\n"
        "\n"
        "If you've already run the router and want to skip this gate:\n"
        f"  rm {STATE_FILE}\n"
    )


if __name__ == "__main__":
    sys.exit(main())
