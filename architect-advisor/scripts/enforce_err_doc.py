#!/usr/bin/env python3
"""
PreToolUse hook for Bash: block fix commits without an ERR doc.

Triggered by Claude Code on every Bash tool call. We only act on commands
that look like `git commit ... -m "fix..."`. If such a commit lacks any new
ERR-*.md in the resolved errorDocDir, we exit non-zero to block the call
and print a hint pointing the user at /flush.

Reads:
  CLAUDE_TOOL_INPUT  JSON, e.g. {"command": "git commit -m 'fix: ...'"}
  CLAUDE_PROJECT_DIR project root (if missing, falls back to cwd)

Exit codes:
  0 — allow tool call (not a fix commit, or fix WITH ERR doc)
  1 — block tool call (fix without ERR doc) — error message goes to stderr
  Any unexpected error → exit 0 (fail-open, never silently break user's flow)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from lib.resolve_error_dir import resolve_error_dir  # noqa: E402


FIX_MESSAGE_RE = re.compile(
    r"""(?:^|[\s'"])fix(?:\([^)]*\))?\s*:""",
    re.IGNORECASE,
)


def main() -> int:
    try:
        return _run()
    except Exception as e:
        sys.stderr.write(f"[enforce_err_doc] unexpected error, allowing call: {e}\n")
        return 0


def _run() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    command = (payload.get("command") or "").strip()
    if not command:
        return 0

    if not _is_fix_commit(command):
        return 0

    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    if not (project_root / ".git").exists():
        return 0  # not a git repo — nothing to enforce

    err_dir = resolve_error_dir(project_root)
    new_err_files = _staged_err_files(project_root, err_dir)
    if new_err_files:
        return 0  # fix commit AND ERR doc staged → allow

    sys.stderr.write(_block_message(err_dir))
    return 1


def _is_fix_commit(command: str) -> bool:
    if "git commit" not in command:
        return False
    # Tokenize and look for `-m "fix..."` or `-m 'fix...'`
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False

    # Find -m / --message flags and check the message
    for i, tok in enumerate(tokens):
        if tok in ("-m", "--message") and i + 1 < len(tokens):
            if FIX_MESSAGE_RE.search(tokens[i + 1]):
                return True
        elif tok.startswith("--message="):
            if FIX_MESSAGE_RE.search(tok[len("--message="):]):
                return True
        elif tok.startswith("-m") and len(tok) > 2:
            # -m"fix..." or -mfix:... (rare but possible)
            if FIX_MESSAGE_RE.search(tok[2:]):
                return True

    # Heredoc / multi-line commit messages also work — check entire command
    if FIX_MESSAGE_RE.search(command):
        # Conservative: only flag if -F or -m present too, otherwise it's likely commentary
        if "-m" in tokens or "-F" in tokens or "--message" in command:
            return True
    return False


def _staged_err_files(project_root: Path, err_dir: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []

    err_files: list[str] = []
    for line in result.stdout.splitlines():
        path = (project_root / line).resolve()
        if path.suffix.lower() != ".md":
            continue
        if not re.match(r"^ERR-\d+", path.name, re.IGNORECASE):
            continue
        try:
            path.relative_to(err_dir)
            err_files.append(line)
        except ValueError:
            continue
    return err_files


def _block_message(err_dir: Path) -> str:
    return (
        "\n"
        "❌ Fix commit blocked — no ERR doc staged (CLAUDE.md §5 enforcement).\n"
        "\n"
        f"Expected a new ERR-*.md inside {err_dir} to be staged with this commit.\n"
        "\n"
        "How to fix:\n"
        "  1. Run /flush — this generates the ERR doc and runs the commit pipeline\n"
        "  2. Or manually create <ERR_DIR>/ERR-NNN-*.md and `git add` it\n"
        "\n"
        "(See `flush` plugin for the canonical doc structure.)\n"
    )


if __name__ == "__main__":
    sys.exit(main())
