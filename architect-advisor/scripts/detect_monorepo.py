#!/usr/bin/env python3
"""
Monorepo auto-detection for architect-advisor.

Scans a project root for monorepo signals (in priority order):
  1. pnpm-workspace.yaml          (pnpm)
  2. package.json#workspaces       (npm/yarn/bun)
  3. turbo.json                    (Turborepo)
  4. nx.json                       (Nx)
  5. lerna.json                    (Lerna)
  6. Cargo.toml#workspace          (Rust)
  7. go.work                       (Go workspaces)
  8. apps/*/package.json glob      (heuristic fallback)
  9. packages/*/package.json glob  (heuristic fallback)

Outputs:
  - JSON to stdout: { isMonorepo, products, via, detected_at }
  - Optionally writes .architect-advisor.json (when --write is passed and
    user has confirmed via stdin or --yes flag)

Usage:
    python3 scripts/detect_monorepo.py                  # detect & print
    python3 scripts/detect_monorepo.py --root /path     # detect at path
    python3 scripts/detect_monorepo.py --write --yes    # write config without prompt

Design notes:
  - This script is single-shot, idempotent at a syntactic level (re-running
    overwrites the cache only when --write is passed).
  - It NEVER auto-writes the config; the caller / user must confirm.
  - When the cache exists, callers should prefer reading the cache rather
    than re-detecting (run `--reconfigure` to force a re-detect).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob as _glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


CONFIG_FILENAME = ".architect-advisor.json"


def detect_monorepo(root: Path) -> dict:
    """Run detection, return a result dict (no side effects)."""
    root = root.resolve()

    pnpm = _from_pnpm_workspace(root)
    if pnpm is not None:
        return _ok("pnpm-workspace.yaml", pnpm)

    npm = _from_package_json_workspaces(root)
    if npm is not None:
        return _ok("package.json#workspaces", npm)

    if (root / "turbo.json").is_file():
        return _ok("turbo.json", _glob_apps_packages(root))

    if (root / "nx.json").is_file():
        return _ok("nx.json", _glob_apps_packages(root))

    lerna = _from_lerna(root)
    if lerna is not None:
        return _ok("lerna.json", lerna)

    cargo = _from_cargo_workspace(root)
    if cargo is not None:
        return _ok("Cargo.toml#workspace", cargo)

    gowork = _from_go_work(root)
    if gowork is not None:
        return _ok("go.work", gowork)

    apps = _glob_apps_packages(root)
    if len(apps) >= 2:
        return _ok("apps-or-packages-glob", apps)

    return {
        "isMonorepo": False,
        "products": [],
        "via": "no-signal",
        "detected_at": _today(),
    }


def _ok(via: str, products: list[str]) -> dict:
    return {
        "isMonorepo": True,
        "products": sorted(set(products)) or ["app"],
        "via": via,
        "detected_at": _today(),
    }


def _today() -> str:
    return _dt.date.today().isoformat()


def _from_pnpm_workspace(root: Path) -> Optional[list[str]]:
    p = root / "pnpm-workspace.yaml"
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    patterns: list[str] = []
    in_packages = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("packages:"):
            in_packages = True
            continue
        if in_packages:
            if stripped.startswith("- "):
                token = stripped[2:].strip().strip("'\"")
                patterns.append(token)
            elif stripped and not stripped.startswith("#") and not line.startswith(" "):
                in_packages = False
    return _expand_glob_patterns(root, patterns)


def _from_package_json_workspaces(root: Path) -> Optional[list[str]]:
    p = root / "package.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    ws = data.get("workspaces")
    patterns: list[str]
    if isinstance(ws, list):
        patterns = [str(x) for x in ws]
    elif isinstance(ws, dict) and isinstance(ws.get("packages"), list):
        patterns = [str(x) for x in ws["packages"]]
    else:
        return None
    return _expand_glob_patterns(root, patterns)


def _from_lerna(root: Path) -> Optional[list[str]]:
    p = root / "lerna.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    pkgs = data.get("packages")
    if not isinstance(pkgs, list):
        return None
    return _expand_glob_patterns(root, [str(x) for x in pkgs])


def _from_cargo_workspace(root: Path) -> Optional[list[str]]:
    p = root / "Cargo.toml"
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    if "[workspace]" not in text:
        return None
    members: list[str] = []
    in_members = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("members") and "=" in s and "[" in s:
            in_members = True
            after = s.split("[", 1)[1]
            members.extend(_extract_quoted(after))
            if "]" in after:
                in_members = False
            continue
        if in_members:
            members.extend(_extract_quoted(s))
            if "]" in s:
                in_members = False
    return _expand_glob_patterns(root, members) if members else _glob_apps_packages(root)


def _extract_quoted(line: str) -> list[str]:
    return re.findall(r'"([^"]+)"', line) + re.findall(r"'([^']+)'", line)


def _from_go_work(root: Path) -> Optional[list[str]]:
    p = root / "go.work"
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    members: list[str] = []
    in_use = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("use ("):
            in_use = True
            continue
        if in_use:
            if s == ")":
                in_use = False
                continue
            if s and not s.startswith("//"):
                members.append(s)
        elif s.startswith("use ") and not s.endswith("("):
            members.append(s[4:].strip())
    return _expand_glob_patterns(root, members) if members else None


def _glob_apps_packages(root: Path) -> list[str]:
    found: list[str] = []
    for parent in ("apps", "packages"):
        for child in (root / parent).glob("*"):
            if child.is_dir() and not child.name.startswith("."):
                found.append(child.name)
    return sorted(set(found))


def _expand_glob_patterns(root: Path, patterns: list[str]) -> list[str]:
    products: list[str] = []
    for pat in patterns:
        if not pat or pat.startswith("!"):
            continue
        for match in _glob.glob(str(root / pat), recursive=True):
            mp = Path(match)
            if mp.is_dir():
                products.append(mp.name)
    return sorted(set(products))


def load_config(root: Path) -> Optional[dict]:
    p = root / CONFIG_FILENAME
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_config(root: Path, result: dict, default_product: Optional[str] = None) -> Path:
    p = root / CONFIG_FILENAME
    payload = {
        "monorepo": bool(result["isMonorepo"]),
        "products": result["products"],
        "detected_via": result["via"],
        "detected_at": result["detected_at"],
    }
    if default_product:
        payload["default_product"] = default_product
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def main():
    parser = argparse.ArgumentParser(description="Auto-detect monorepo for architect-advisor.")
    parser.add_argument("--root", default=".", help="project root (default: cwd)")
    parser.add_argument("--write", action="store_true", help="write .architect-advisor.json on confirmation")
    parser.add_argument("--yes", action="store_true", help="skip confirmation prompt (CI-friendly)")
    parser.add_argument("--reconfigure", action="store_true", help="force re-detect even if config exists")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    if not args.reconfigure:
        existing = load_config(root)
        if existing is not None:
            print(json.dumps({"cached": True, "config": existing}, ensure_ascii=False, indent=2))
            return

    result = detect_monorepo(root)
    if not args.write:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if not args.yes:
        sys.stderr.write(
            f"Detected: monorepo={result['isMonorepo']}, products={result['products']}, via={result['via']}\n"
            "Write .architect-advisor.json? [y/N] "
        )
        sys.stderr.flush()
        try:
            ans = input().strip().lower()
        except EOFError:
            ans = "n"
        if ans not in ("y", "yes"):
            sys.stderr.write("Aborted; no file written.\n")
            return

    written = write_config(root, result)
    print(json.dumps({"written": str(written), "config": load_config(root)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
