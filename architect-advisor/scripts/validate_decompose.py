#!/usr/bin/env python3
"""
Validate a decompose Step YAML for cold-start safety (W2.2).

Checks:
  1. Required fields present on every step
  2. files_to_read paths exist
  3. Dependency graph is a DAG (no cycles)
  4. parallel_with groups don't write the same files
  5. context_brief.problem doesn't reference other steps ("앞에서", "이전 step", etc.)
  6. verification entries look executable (not prose)

Usage:
    python3 scripts/validate_decompose.py architect-advisor/decompositions/DECOMP-*.yaml
    python3 scripts/validate_decompose.py path/to/file.yaml --root /project/root
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_TOP = {"step_id", "title", "deps", "parallel_with", "model_tier",
                "context_brief", "acceptance_criteria", "verification", "rollback"}
REQUIRED_BRIEF = {"problem", "hard_constraints", "files_to_read"}

AMBIENT_REFS_RE = re.compile(
    r"(앞에서|이전 step|이전 단계|위에서 언급|previously|as discussed|"
    r"the prior step|前面提到|上一步|先前)",
    re.IGNORECASE,
)

VERIFICATION_PROSE_RE = re.compile(r"^[A-Za-zㄱ-ㆎ가-힣一-鿿].*[^`)]$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate decompose Step YAML")
    parser.add_argument("file", help="Path to Step YAML file")
    parser.add_argument("--root", default=".", help="Project root for files_to_read existence check")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    yaml_path = Path(args.file)
    if not yaml_path.is_file():
        sys.stderr.write(f"ERROR: File not found: {yaml_path}\n")
        return 2

    root = Path(args.root).resolve()
    raw = yaml_path.read_text(encoding="utf-8")

    steps = _parse_steps(raw, yaml_path.suffix.lower())
    if steps is None:
        return 2

    if not isinstance(steps, list):
        sys.stderr.write("ERROR: Top level must be a list of steps\n")
        return 2

    errors: list[str] = []

    # 1. Required fields
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"step[{i}]: must be a mapping")
            continue
        missing_top = REQUIRED_TOP - set(step.keys())
        if missing_top:
            errors.append(f"step[{i}] (id={step.get('step_id')}): missing fields {sorted(missing_top)}")
        cb = step.get("context_brief", {}) or {}
        missing_brief = REQUIRED_BRIEF - set(cb.keys())
        if missing_brief:
            errors.append(f"step[{i}].context_brief: missing fields {sorted(missing_brief)}")

    # 2. files_to_read existence
    for step in steps:
        if not isinstance(step, dict):
            continue
        cb = step.get("context_brief") or {}
        for f in cb.get("files_to_read") or []:
            target = (root / f).resolve()
            if not target.exists():
                errors.append(f"step {step.get('step_id')}: files_to_read missing: {f}")

    # 3. DAG
    graph = {step["step_id"]: list(step.get("deps") or []) for step in steps if isinstance(step, dict) and "step_id" in step}
    cycle = _find_cycle(graph)
    if cycle:
        errors.append(f"dependency cycle detected: {' -> '.join(str(x) for x in cycle)}")

    # 4. parallel_with write-collision (heuristic — same files_to_read implies probable write conflict)
    parallel_groups = _build_parallel_groups(steps)
    for group in parallel_groups:
        files_by_step: dict[int, set[str]] = {}
        for sid in group:
            for s in steps:
                if isinstance(s, dict) and s.get("step_id") == sid:
                    cb = s.get("context_brief") or {}
                    files_by_step[sid] = set(cb.get("files_to_read") or [])
        ids = list(files_by_step.keys())
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                shared = files_by_step[a] & files_by_step[b]
                if shared:
                    errors.append(f"parallel_with group {sorted(group)}: steps {a} and {b} share files {sorted(shared)} — possible write conflict")

    # 5. ambient references
    for step in steps:
        if not isinstance(step, dict):
            continue
        problem = ((step.get("context_brief") or {}).get("problem") or "")
        if AMBIENT_REFS_RE.search(problem):
            errors.append(f"step {step.get('step_id')}: context_brief.problem contains ambient reference (cold-start unsafe)")

    # 6. verification looks executable
    for step in steps:
        if not isinstance(step, dict):
            continue
        for v in step.get("verification") or []:
            if isinstance(v, str) and not _looks_executable(v):
                errors.append(f"step {step.get('step_id')}: verification line not executable: '{v[:60]}'")

    result = {
        "file": str(yaml_path),
        "step_count": sum(1 for s in steps if isinstance(s, dict)),
        "errors": errors,
        "ok": not errors,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"📋 {yaml_path.name}: {result['step_count']} steps")
        if errors:
            print(f"❌ {len(errors)} validation error(s):")
            for e in errors:
                print(f"  - {e}")
        else:
            print("✅ all checks passed (cold-start safe)")

    return 0 if result["ok"] else 1


def _find_cycle(graph: dict) -> list:
    color: dict = {}  # 0=white, 1=gray, 2=black
    parent: dict = {}

    def dfs(node, path):
        color[node] = 1
        for dep in graph.get(node, []):
            if color.get(dep, 0) == 1:
                cycle_start = path.index(dep) if dep in path else 0
                return path[cycle_start:] + [dep]
            if color.get(dep, 0) == 0:
                result = dfs(dep, path + [dep])
                if result:
                    return result
        color[node] = 2
        return None

    for n in graph:
        if color.get(n, 0) == 0:
            r = dfs(n, [n])
            if r:
                return r
    return []


def _build_parallel_groups(steps: list) -> list[set]:
    groups: list[set] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        sid = s.get("step_id")
        pw = s.get("parallel_with") or []
        if pw:
            grp = {sid, *pw}
            merged = False
            for g in groups:
                if g & grp:
                    g |= grp
                    merged = True
                    break
            if not merged:
                groups.append(grp)
    return groups


def _looks_executable(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    # Common command starts
    if line.startswith(("npm ", "yarn ", "pnpm ", "bun ", "python ", "python3 ",
                       "pytest ", "go ", "cargo ", "make ", "bash ", "sh ",
                       "grep ", "find ", "ls ", "cat ", "test ", "./",
                       "docker ", "kubectl ", "curl ", "git ")):
        return True
    if "|" in line or "&&" in line or " > " in line:
        return True
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]+\s+", line):
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
