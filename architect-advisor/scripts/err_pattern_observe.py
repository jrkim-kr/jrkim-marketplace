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

from lib.resolve_error_dir import resolve_error_dirs  # noqa: E402
from lib.advisor_paths import resolve_layout  # noqa: E402


PROMOTE_CONFIDENCE = 0.7
PROMOTE_MIN_OCCURRENCES = 2
# 근거 ERR이 이 수 이상이면 '확립', 미만이면 '잠정'. skills/arch-err-pattern/SKILL.md와 같은 기준.
ESTABLISHED_MIN_ERRS = 5


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

    target = Path(file_path).resolve()

    # Quick syntax filters (don't need anchor for these)
    if not re.match(r"^ERR-\d+", target.name, re.IGNORECASE):
        return 0
    if target.suffix.lower() != ".md":
        return 0
    if not target.is_file():
        return 0

    # Anchor project_root to the ERR file's repo, not the cwd. This keeps
    # data per-repo regardless of where Claude Code was started.
    # Priority: existing architect-advisor/ (respect prior setup) → .git → cwd.
    anchor = _find_advisor_anchor(target.parent)
    if anchor is not None:
        project_root = anchor

    # Resolve err_dirs against the anchored project_root, then verify the
    # ERR file actually lives inside one of them.
    err_dirs = resolve_error_dirs(project_root)
    if not any(_is_inside(target, d) for d in err_dirs):
        return 0

    # Within-repo monorepo support (e.g. ota-admin-scraper declaring
    # 3 sub-products in its own .architect-advisor.json).
    product = _derive_product(target, project_root)
    layout = resolve_layout(project_root, product=product)

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

    # Emit a same-turn reminder so the active Claude Code session runs the
    # arch-err-pattern skill in-session (no separate process, no API key).
    _emit_session_reminder(parsed)

    # Candidate accumulation kept for audit/debug only.
    # CONFLICT_PATTERNS.md is now owned by the arch-err-pattern skill (triggered above)
    # which performs LLM-driven root-cause induction beyond simple pair coupling.
    candidate = _build_candidate(parsed)
    if candidate is not None:
        candidates_file = layout.candidates_file()
        candidates_file.parent.mkdir(parents=True, exist_ok=True)
        _upsert_candidate(candidates_file, candidate)

    return 0


def _find_advisor_anchor(start: Path) -> Path | None:
    """Walk up from `start` looking for the canonical project root for this
    ERR file. Priority:
      1. Existing `architect-advisor/` directory (respects user's prior setup)
      2. `.git/` directory (canonical repo root)
    Returns None if neither found at any ancestor (caller falls back to cwd).
    """
    current = start.resolve()
    while True:
        if (current / "architect-advisor").is_dir():
            return current
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _derive_product(target: Path, project_root: Path) -> str | None:
    """Monorepo product attribution.

    Reads `.architect-advisor.json` from project_root. If `monorepo: true` and a
    `products` list is declared, walks the ERR file's path segments (relative to
    project_root) and returns the first segment that matches a declared product
    slug. Returns None in single-product mode or if no match.
    """
    cfg_path = project_root / ".architect-advisor.json"
    if not cfg_path.is_file():
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not cfg.get("monorepo"):
        return None
    products = cfg.get("products") or []
    if not products:
        return None
    try:
        rel = target.relative_to(project_root)
    except ValueError:
        return None
    products_set = set(products)
    for part in rel.parts:
        if part in products_set:
            return part
    return None


def _emit_session_reminder(parsed: dict) -> None:
    """Inject an additionalContext system reminder so the active agent runs
    pattern extraction inline (same turn, no API key, with active notification)."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[arch-err-pattern auto-accumulation] "
                f"{parsed['err_id']} 관측이 architect-advisor/observations.jsonl 에 기록되었습니다. "
                f"이번 응답이 끝나기 전에 다음을 수행하세요:\n"
                f"1. Skill 도구로 'architect-advisor:arch-err-pattern' 호출 "
                f"(누적된 모든 ERR을 LLM으로 횡단 귀납하여 CONFLICT_PATTERNS.md 갱신)\n"
                f"2. 신규/승격된 패턴이 있으면 사용자에게 1-3줄로 능동 보고. "
                f"변화가 없으면 'pattern 변화 없음'만 한 줄.\n"
                f"3. 사용자가 명시적으로 다른 작업 중이라도, 이 보고는 응답 마지막에 반드시 포함."
            ),
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


def _extract_file_path() -> str | None:
    # 1) Claude Code's documented PostToolUse contract: full event JSON on stdin
    if not sys.stdin.isatty():
        try:
            raw_stdin = sys.stdin.read()
        except Exception:
            raw_stdin = ""
        if raw_stdin:
            try:
                payload = json.loads(raw_stdin)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                tool_input = payload.get("tool_input") or {}
                if isinstance(tool_input, dict):
                    fp = tool_input.get("file_path") or tool_input.get("path")
                    if fp:
                        return fp
                fp = payload.get("file_path") or payload.get("path")
                if fp:
                    return fp

    # 2) Legacy env-var contract (kept for back-compat)
    raw = os.environ.get("CLAUDE_TOOL_INPUT")
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload.get("file_path") or payload.get("path")

    # 3) argv (manual debug entry point)
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
    section = _extract_section(text, [
        "영향 모듈", "Affected Modules", "Affected", "Impact", "영향 범위",
        "관련 파일", "Related Files",
    ])
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

    # 증거 등급 — SKILL.md와 같은 기준. hook 승격은 보통 근거 2건이므로 대개 잠정이다.
    # 등급이 없으면 소비자가 잠정을 확립으로 오인해 강제 수락 기준으로 주입한다.
    established = len(err_ids) >= ESTABLISHED_MIN_ERRS
    grade = "확립" if established else "잠정"
    # 확립만 체크박스(=충족해야 완료). 잠정은 평범한 불릿으로 두어 완료를 막지 않는다.
    bullet = "- [ ]" if established else "-"
    grade_note = (
        "to-tickets가 필수 수락 기준으로 주입"
        if established
        else f"to-tickets가 참고로만 주입. 근거 {ESTABLISHED_MIN_ERRS}건이 되면 확립으로 승격"
    )

    pattern_md = (
        f"### {' + '.join(modules)} 결합 충돌 `[{grade}]`\n"
        f"<!-- pattern_key: {pattern_key} -->\n"
        f"<!-- evidence: {grade} | ERR 근거 {len(err_ids)}건 -->\n\n"
        f"- **추출 시각**: {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        f"- **증거 등급**: {grade} (근거 {len(err_ids)}건) — {grade_note}\n"
        f"- **근거 ERR**: {', '.join(err_ids)}\n"
        f"- **공통 모듈**: {', '.join(modules)}\n"
        f"- **공통 근본 원인 단서**: {cause or '(미파싱)'}\n"
        f"- **상태**: candidate → promoted (confidence ≥ {PROMOTE_CONFIDENCE}, occurrences ≥ {PROMOTE_MIN_OCCURRENCES})\n\n"
        f"**예방 규칙 (Prevention Checklist)** — 다음 to-tickets에서 자동 주입:\n"
        f"{bullet} {modules[0]} 와 {modules[-1]} 에 동시 작용하는 step은 동일 트랜잭션 경계 안에 둘 것\n"
        f"{bullet} 두 모듈을 함께 변경하는 PR은 통합 테스트 필수\n\n"
    )

    cp_file.write_text(existing + pattern_md, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
