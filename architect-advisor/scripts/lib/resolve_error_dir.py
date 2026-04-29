"""
Unified errorDocDir resolution.

Reused by both `flush` (producer of ERR docs) and `architect-advisor` (consumer).
Single source of truth — never hardcode paths to docs/errors anywhere else.

Resolution order:
  1. .flushrc.json -> errorDocDir
  2. find . -type d -name "errors" (excluding node_modules / .git)
  3. ./errors/ (default)

Usage:
    from scripts.lib.resolve_error_dir import resolve_error_dir
    err_dir = resolve_error_dir(project_root)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


_EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", ".next", "target"}


def resolve_error_dir(project_root: str | Path = ".") -> Path:
    """Return the absolute Path to the directory containing ERR-*.md docs.

    Falls back through three tiers; never raises. Always returns a Path.
    The directory is not guaranteed to exist — callers must check.
    """
    root = Path(project_root).resolve()

    explicit = _from_flushrc(root)
    if explicit is not None:
        return explicit

    discovered = _find_errors_dir(root)
    if discovered is not None:
        return discovered

    return root / "errors"


def _from_flushrc(root: Path) -> Optional[Path]:
    cfg_path = root / ".flushrc.json"
    if not cfg_path.is_file():
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    raw = cfg.get("errorDocDir")
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = (root / raw).resolve() if not os.path.isabs(raw) else Path(raw)
    return candidate


def _find_errors_dir(root: Path) -> Optional[Path]:
    """Walk the tree shallow-first looking for a directory literally named 'errors'."""
    candidates: list[Path] = []
    for current_root, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS and not d.startswith(".")]
        for d in dirnames:
            if d == "errors":
                candidates.append(Path(current_root) / d)
        if Path(current_root).resolve() != root and len(Path(current_root).resolve().relative_to(root).parts) >= 3:
            dirnames[:] = []

    if not candidates:
        return None

    candidates.sort(key=lambda p: len(p.relative_to(root).parts))
    return candidates[0].resolve()


def describe_resolution(project_root: str | Path = ".") -> dict:
    """Return a debug record showing which tier resolved and the final path."""
    root = Path(project_root).resolve()
    explicit = _from_flushrc(root)
    if explicit is not None:
        return {"tier": "flushrc", "path": str(explicit), "exists": explicit.is_dir()}
    discovered = _find_errors_dir(root)
    if discovered is not None:
        return {"tier": "discovered", "path": str(discovered), "exists": discovered.is_dir()}
    fallback = root / "errors"
    return {"tier": "default", "path": str(fallback), "exists": fallback.is_dir()}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(describe_resolution(target), indent=2, ensure_ascii=False))
