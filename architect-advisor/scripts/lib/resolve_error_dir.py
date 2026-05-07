"""
Unified errorDocDir resolution.

Reused by both `flush` (producer of ERR docs) and `architect-advisor` (consumer).
Single source of truth — never hardcode paths to docs/errors anywhere else.

Resolution order (singular — first match wins):
  1. .flushrc.json -> errorDocDir (string) or first of errorDocDirs (list)
  2. find . -type d -name "errors" (excluding node_modules / .git)
  3. ./errors/ (default)

Plural mode (resolve_error_dirs) returns ALL matches:
  1. .flushrc.json -> errorDocDirs (list) — explicit set
  2. .flushrc.json -> errorDocDir (string) — single, returned as 1-element list
  3. find . -type d -name "errors" — every match (for multi-package repos)
  4. [./errors/] (default)

Usage:
    from scripts.lib.resolve_error_dir import resolve_error_dir, resolve_error_dirs
    err_dir = resolve_error_dir(project_root)        # first match
    err_dirs = resolve_error_dirs(project_root)      # all matches
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


_EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", ".next", "target"}


def resolve_error_dir(project_root: str | Path = ".") -> Path:
    """Return the first errorDocDir; backward-compatible singular API."""
    return resolve_error_dirs(project_root)[0]


def resolve_error_dirs(project_root: str | Path = ".") -> list[Path]:
    """Return all errorDocDirs (deduped, in stable order). Always non-empty."""
    root = Path(project_root).resolve()

    explicit = _from_flushrc_multi(root)
    if explicit:
        return _dedup(explicit)

    discovered = _find_errors_dirs(root)
    if discovered:
        return _dedup(discovered)

    return [root / "errors"]


def _from_flushrc_multi(root: Path) -> list[Path]:
    cfg_path = root / ".flushrc.json"
    if not cfg_path.is_file():
        return []
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    out: list[Path] = []
    raw_list = cfg.get("errorDocDirs")
    if isinstance(raw_list, list):
        for item in raw_list:
            p = _coerce_path(root, item)
            if p is not None:
                out.append(p)
    if not out:
        raw = cfg.get("errorDocDir")
        p = _coerce_path(root, raw)
        if p is not None:
            out.append(p)
    return out


def _coerce_path(root: Path, raw) -> Optional[Path]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    return Path(raw) if os.path.isabs(raw) else (root / raw).resolve()


def _find_errors_dirs(root: Path) -> list[Path]:
    """Walk the tree returning every directory literally named 'errors'."""
    candidates: list[Path] = []
    for current_root, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS and not d.startswith(".")]
        for d in dirnames:
            if d == "errors":
                candidates.append((Path(current_root) / d).resolve())
        if Path(current_root).resolve() != root and len(Path(current_root).resolve().relative_to(root).parts) >= 3:
            dirnames[:] = []

    candidates.sort(key=lambda p: (len(p.relative_to(root).parts), str(p)))
    return candidates


def _dedup(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(rp)
    return out


def describe_resolution(project_root: str | Path = ".") -> dict:
    """Return a debug record showing which tier resolved and the final paths."""
    root = Path(project_root).resolve()
    explicit = _from_flushrc_multi(root)
    if explicit:
        return {
            "tier": "flushrc",
            "paths": [str(p) for p in _dedup(explicit)],
            "exists": [p.is_dir() for p in _dedup(explicit)],
        }
    discovered = _find_errors_dirs(root)
    if discovered:
        return {
            "tier": "discovered",
            "paths": [str(p) for p in _dedup(discovered)],
            "exists": [p.is_dir() for p in _dedup(discovered)],
        }
    fallback = root / "errors"
    return {"tier": "default", "paths": [str(fallback)], "exists": [fallback.is_dir()]}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(describe_resolution(target), indent=2, ensure_ascii=False))
