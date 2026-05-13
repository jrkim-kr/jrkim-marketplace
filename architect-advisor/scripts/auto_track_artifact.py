#!/usr/bin/env python3
"""PostToolUse hook: keep workflow.json in sync with Write|Edit landing in architect-advisor/.

Reads PostToolUse JSON on stdin. If the written file is under
`<project>/architect-advisor[/<slug>]/<step-dir>/...`, append `{path, saved_at}`
to `steps[step].artifacts[]` (dedup by path) and bump `updated_at`.

Silent no-op on any mismatch — this hook must never block tool use.

Dir → step mapping (uses advisor_paths.py canonical plural forms):
  decompositions/  → decompose
  council/         → council        (legacy/transitional: comparison.md)
  decisions/       → council        (DECISION-*.md records the council outcome)
  adrs/            → adr            (also sets steps.adr.adr_path if NNNN-*.md and currently null)
  audits/, audit/  → audit
  portfolio/       → portfolio
  glossary/        → glossary
  patterns/        → updates state.patterns.{output_path,artifacts,last_generated_at}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DIR_TO_STEP = {
    "decompositions": "decompose",
    "decompose": "decompose",
    "council": "council",
    "decisions": "council",
    "adrs": "adr",
    "adr": "adr",
    "audits": "audit",
    "audit": "audit",
    "portfolio": "portfolio",
    "glossary": "glossary",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_workflow_root(file_path: Path) -> tuple[Path, str] | None:
    """Walk up from file_path; return (advisor_root, step_dir_name) or None.

    advisor_root is the dir that contains state/workflow.json (single-product:
    .../architect-advisor; monorepo: .../architect-advisor/<slug>).
    """
    parts = file_path.parts
    for i in range(len(parts) - 2, -1, -1):
        if parts[i] != "architect-advisor":
            continue
        # parts[i+1] is either <step-dir> (single) or <slug> (monorepo)
        remaining = parts[i + 1 :]
        if not remaining:
            return None
        # Try single-product: architect-advisor/<step>/...
        single_root = Path(*parts[: i + 1])
        if (single_root / "state" / "workflow.json").is_file():
            return single_root, remaining[0]
        # Try monorepo: architect-advisor/<slug>/<step>/...
        if len(remaining) >= 2:
            mono_root = Path(*parts[: i + 2])
            if (mono_root / "state" / "workflow.json").is_file():
                return mono_root, remaining[1]
        return None
    return None


def update_state(advisor_root: Path, step_dir: str, file_path: Path) -> dict | None:
    state_file = advisor_root / "state" / "workflow.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    saved_at = now_iso()
    # Path stored as relative to project_root (parent of architect-advisor)
    project_root = advisor_root.parent if advisor_root.name != "architect-advisor" else advisor_root.parent
    try:
        rel = str(file_path.resolve().relative_to(project_root))
    except ValueError:
        rel = str(file_path)

    if step_dir == "patterns":
        patterns = state.setdefault("patterns", {})
        artifacts = patterns.setdefault("artifacts", [])
        if any(a.get("path") == rel for a in artifacts):
            return None
        artifacts.append({"path": rel, "saved_at": saved_at})
        if file_path.name == "CONFLICT_PATTERNS.md":
            patterns["output_path"] = rel
            patterns["last_generated_at"] = saved_at
        state["updated_at"] = saved_at
    else:
        step = DIR_TO_STEP.get(step_dir)
        if step is None:
            return None
        steps = state.get("steps", {})
        if step not in steps:
            return None
        artifacts = steps[step].setdefault("artifacts", [])
        if any(a.get("path") == rel for a in artifacts):
            return None
        artifacts.append({"path": rel, "saved_at": saved_at})
        # Backfill adr_path on first ADR write (NNNN-*.md naming)
        if step == "adr" and not steps[step].get("adr_path"):
            name = file_path.name
            if len(name) >= 5 and name[:4].isdigit() and name[4] == "-" and name.endswith(".md"):
                steps[step]["adr_path"] = rel
        state["updated_at"] = saved_at

    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"step_dir": step_dir, "path": rel}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if payload.get("tool_name") not in {"Write", "Edit"}:
        return
    tool_input = payload.get("tool_input") or {}
    fp = tool_input.get("file_path")
    if not fp:
        return
    path = Path(fp)
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    found = find_workflow_root(path)
    if not found:
        return
    advisor_root, step_dir = found
    if step_dir == "state":
        return  # Don't track state file edits as artifacts
    update_state(advisor_root, step_dir, path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block tool use
        pass
