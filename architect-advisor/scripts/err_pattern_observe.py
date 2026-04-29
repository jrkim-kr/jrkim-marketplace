#!/usr/bin/env python3
"""
Background ERR-pattern observer (W3.1).

Invoked by a PostToolUse hook every time Claude Code writes/edits a file.
If the file is an ERR-*.md inside the resolved errorDocDir, we:

  1. Parse out Affected Modules and Root Cause
  2. Append an observation record to architect-advisor/observations.jsonl
  3. Spawn a background analysis stub (Haiku call placeholder for now —
     callable from the harness later) that writes a candidate pattern with
     a confidence score into architect-advisor/patterns/candidates.jsonl
  4. If a candidate has accumulated ≥ 2 distinct ERR sources AND confidence
     ≥ 0.7, promote it into CONFLICT_PATTERNS.md (project-scoped).

Design constraints:
  - Fire-and-forget: never raise to the caller, never block the editor
  - project-scoped only — never auto-write into a global location
  - All paths via lib/resolve_error_dir.py (W0.1) and lib/advisor_paths.py (W0.3)

Hook context (env vars from Claude Code's PostToolUse):
  - CLAUDE_PROJECT_DIR    project root
  - CLAUDE_TOOL_INPUT     JSON string with the tool call's input

If those env vars are absent, the script reads stdin / argv as a manual
debug entry point.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from lib.resolve_error_dir import resolve_error_dir  # noqa: E402
from lib.advisor_paths import resolve_layout  # noqa: E402


PROMOTE_CONFIDENCE = 0.7
PROMOTE_MIN_OCCURRENCES = 2


def main() -> int:
    try:
        return _run()
    except Exception as e:
        # Fire-and-forget — never propagate
        sys.stderr.write(f"[err-pattern-observe] silent fail: {e}\n")
        return 0


def _run() -> int:
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
    file_path = _extract_file_path()

    if not file_path:
        return 0

    err_dir = resolve_error_dir(project_root)
    target = Path(file_path).resolve()

    # Filter: only act on ERR-*.md inside the resolved errorDocDir
    if not _is_inside(target, err_dir):
        return 0
    if not re.match(r"^ERR-\d+", target.name, re.IGNORECASE):
        return 0
    if target.suffix.lower() != ".md":
        return 0
    if not target.is_file():
        return 0

    layout = resolve_layout(project_root)

    # Parse the ERR doc
    parsed = _parse_err_doc(target)
    if not parsed:
        return 0

    # Observation log
    observations_file = layout.observations_file()
    observations_file.parent.mkdir(parents=True, exist_ok=True)
    obs_record = {
        "ts": int(time.time()),
        "err_id": parsed["err_id"],
        "err_path": str(target.relative_to(project_root)) if target.is_relative_to(project_root) else str(target),
        "modules": parsed["modules"],
        "root_cause_first_line": parsed["root_cause_first_line"],
    }
    with observations_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obs_record, ensure_ascii=False) + "\n")

    # Candidate accumulation (offline lightweight analyzer)
    candidate = _build_candidate(parsed)
    if candidate is not None:
        candidates_file = layout.candidates_file()
        candidates_file.parent.mkdir(parents=True, exist_ok=True)
        _upsert_candidate(candidates_file, candidate)

        # Promotion check
        if _should_promote(candidates_file, candidate["pattern_key"]):
            _promote_to_conflict_patterns(layout, candidates_file, candidate["pattern_key"])

    return 0


def _extract_file_path() -> str | None:
    raw = os.environ.get("CLAUDE_TOOL_INPUT")
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload.get("file_path") or payload.get("path")
    if len(sys.argv) >= 2:
        return sys.argv[1]
    return None


def _is_inside(target: Path, parent: Path) -> bool:
    try:
        target.relative_to(parent)
        return True
    except ValueError:
        return False


def _parse_err_doc(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    err_id_match = re.search(r"ERR-(\d+)", path.name, re.IGNORECASE)
    if not err_id_match:
        return None
    err_id = f"ERR-{int(err_id_match.group(1)):03d}"

    modules = _extract_modules(text)
    root_cause = _extract_section(text, ["근본 원인", "Root Cause", "원인", "Cause"])
    if not modules and not root_cause:
        return None

    first_line = (root_cause.splitlines()[0].strip() if root_cause else "")[:120]

    return {
        "err_id": err_id,
        "modules": modules,
        "root_cause_first_line": first_line,
    }


def _extract_modules(text: str) -> list[str]:
    section = _extract_section(text, ["영향 모듈", "Affected Modules", "Affected", "Impact", "영향 범위"])
    if not section:
        return []
    paths: list[str] = []
    for line in section.splitlines():
        for token in re.findall(r"`([^`\n]+)`", line):
            if "/" in token or token.endswith((".py", ".ts", ".js", ".go", ".java", ".rs")):
                paths.append(token)
    seen: set[str] = set()
    deduped: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def _extract_section(text: str, header_aliases: list[str]) -> str:
    for alias in header_aliases:
        pattern = re.compile(rf"^##\s+{re.escape(alias)}.*?$", re.MULTILINE)
        m = pattern.search(text)
        if m:
            start = m.end()
            next_h = re.search(r"^##\s", text[start:], re.MULTILINE)
            if next_h:
                return text[start:start + next_h.start()].strip()
            return text[start:].strip()
    return ""


def _build_candidate(parsed: dict) -> dict | None:
    if not parsed["modules"]:
        return None
    # Pattern key = sorted module pair (stable across orderings)
    if len(parsed["modules"]) < 2:
        return None
    key = "::".join(sorted(parsed["modules"][:3]))
    return {
        "pattern_key": key,
        "modules": sorted(parsed["modules"]),
        "err_id": parsed["err_id"],
        "first_seen_root_cause": parsed["root_cause_first_line"],
    }


def _upsert_candidate(candidates_file: Path, candidate: dict) -> None:
    """Append candidate observation, dedup by (pattern_key, err_id)."""
    seen_pairs: set[tuple[str, str]] = set()
    if candidates_file.is_file():
        for line in candidates_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            seen_pairs.add((rec.get("pattern_key", ""), rec.get("err_id", "")))

    pair = (candidate["pattern_key"], candidate["err_id"])
    if pair in seen_pairs:
        return

    record = {
        **candidate,
        "ts": int(time.time()),
        "confidence": _compute_confidence(candidates_file, candidate["pattern_key"]),
    }
    with candidates_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _compute_confidence(candidates_file: Path, pattern_key: str) -> float:
    """Heuristic confidence: 0.3 baseline + 0.2 per distinct ERR seen, capped at 0.95."""
    if not candidates_file.is_file():
        return 0.3
    distinct_errs: set[str] = set()
    for line in candidates_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("pattern_key") == pattern_key:
            distinct_errs.add(rec.get("err_id", ""))
    return min(0.3 + 0.2 * (len(distinct_errs) + 1), 0.95)


def _should_promote(candidates_file: Path, pattern_key: str) -> bool:
    if not candidates_file.is_file():
        return False
    distinct_errs: set[str] = set()
    max_conf = 0.0
    for line in candidates_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("pattern_key") != pattern_key:
            continue
        distinct_errs.add(rec.get("err_id", ""))
        max_conf = max(max_conf, float(rec.get("confidence", 0)))
    return len(distinct_errs) >= PROMOTE_MIN_OCCURRENCES and max_conf >= PROMOTE_CONFIDENCE


def _promote_to_conflict_patterns(layout, candidates_file: Path, pattern_key: str) -> None:
    cp_file = layout.conflict_patterns_file()
    cp_file.parent.mkdir(parents=True, exist_ok=True)

    # Don't double-write if already promoted
    existing = cp_file.read_text(encoding="utf-8") if cp_file.is_file() else ""
    if f"<!-- pattern_key: {pattern_key} -->" in existing:
        return

    # Gather all candidate records for this key
    records: list[dict] = []
    for line in candidates_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("pattern_key") == pattern_key:
            records.append(rec)
    if not records:
        return

    err_ids = sorted({r["err_id"] for r in records})
    modules = records[0]["modules"]
    cause = records[0].get("first_seen_root_cause", "")

    if not existing:
        existing = (
            "# 충돌 패턴 분석 (Conflict Patterns)\n\n"
            "> 자동 누적: `arch-err-pattern` PostToolUse hook이 ERR 문서 작성 시점에 갱신.\n\n"
            "## Changelog\n\n"
            "## 자동 추출 패턴\n\n"
        )
    else:
        if "## 자동 추출 패턴" not in existing:
            existing += "\n## 자동 추출 패턴\n\n"

    pattern_md = (
        f"### {' + '.join(modules)} 결합 충돌\n"
        f"<!-- pattern_key: {pattern_key} -->\n\n"
        f"- **추출 시각**: {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        f"- **근거 ERR**: {', '.join(err_ids)}\n"
        f"- **공통 모듈**: {', '.join(modules)}\n"
        f"- **공통 근본 원인 단서**: {cause or '(미파싱)'}\n"
        f"- **상태**: candidate → promoted (confidence ≥ {PROMOTE_CONFIDENCE}, occurrences ≥ {PROMOTE_MIN_OCCURRENCES})\n\n"
        f"**예방 규칙 (Prevention Checklist)** — 다음 writing-plans에서 자동 주입:\n"
        f"- [ ] {modules[0]} 와 {modules[-1]} 에 동시 작용하는 step은 동일 트랜잭션 경계 안에 둘 것\n"
        f"- [ ] 두 모듈을 함께 변경하는 PR은 통합 테스트 필수\n\n"
    )

    cp_file.write_text(existing + pattern_md, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
