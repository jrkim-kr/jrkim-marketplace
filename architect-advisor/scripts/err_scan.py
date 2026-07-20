#!/usr/bin/env python3
# Requires Python 3.10+
"""
ERR 문서 스캐너 — architect-advisor / arch-err-pattern skill 전용 파싱 헬퍼.

`<ERR_DIR>/` (자동 해석) 하위의 `ERR-*.md` 문서를 재귀 탐색하고 헤더 별칭 매핑으로
필드를 추출해 JSON으로 출력한다. 에이전트(arch-err-pattern)는 이 JSON을
입력으로 받아 횡단 귀납만 수행한다 — 문서 파싱 부담을 스크립트로 위임해
토큰·일관성 문제를 해소한다.

사용법:
    python3 scripts/err_scan.py                   # ERR_DIR 자동 해석
    python3 scripts/err_scan.py --dir some/path
    python3 scripts/err_scan.py --json            # 전체 JSON 덤프
    python3 scripts/err_scan.py --summary         # 요약만 (개수, 모듈 빈도)

출력 스키마:
{
  "scanned": 12,
  "parse_errors": 0,
  "dir": "errors",
  "errors": [
    {
      "error_id": "ERR-001",
      "file": "errors/ERR-001-foo.md",
      "title": "...",
      "root_cause": "...",
      "affected_modules": ["src/a.py", "src/b.py"],
      "solution": "...",
      "prevention": ["item 1", "item 2"],
      "missing_fields": []
    }
  ],
  "module_cooccurrence": {"src/a.py::src/b.py": 3, ...},
  "module_frequency": {"src/a.py": 5, ...}
}
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.resolve_error_dir import resolve_error_dir, describe_resolution

# 별칭 매핑 — architect-advisor arch-err-pattern skill과 동기화 유지
#
# 헤더는 정확히 일치해야 잡힌다(뒤 괄호 보충만 허용). 실측 이유로 세 갈래를 추가:
#   ① 중국어 헤더 — 대화 언어가 중국어인 저장소는 ERR 헤더도 중국어로 쓴다
#      (ai-pm 46건 중 `## 根因` 30건. 이게 빠져 43건이 통째로 미파싱이었다)
#   ② 한국어 축약형 — `근인`/`처방`/`해결`. 규범은 `근본 원인`이지만 실제로는 축약이 다수
#   ③ 복합 헤더 — `재발 방지 / 패턴` 처럼 두 절을 한 헤더에 합친 형태
FIELD_ALIASES = {
    "root_cause": ["근본 원인", "Root Cause", "원인", "Cause", "분석",
                   "근인", "根因", "根本原因"],
    "affected_modules": ["영향 모듈", "Affected Modules", "Affected", "Impact",
                         "영향 범위", "관련 파일", "Related Files",
                         "영향 파일", "影响模块", "影响范围"],
    "solution": ["해결책", "Solution", "Fix", "해결 방법",
                 "해결", "처방", "修复", "解决", "解决方案"],
    "prevention": ["재발 방지 체크리스트", "Prevention", "Prevention Checklist",
                   "재발 방지 / 패턴", "재발 방지", "예방 체크리스트", "예방",
                   "재사용 가능 패턴", "可复用 패턴", "교훈", "复发防止", "预防"],
}

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
ERR_ID_RE = re.compile(r"ERR-(\d+)", re.IGNORECASE)
DATE_ID_RE = re.compile(r"^(ERR-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._]+)*)$", re.IGNORECASE)
# YAML frontmatter 의 `component:` — `## 영향 모듈` 섹션 대신 여기에 모듈을 적는
# ERR 규범(flush 플러그인 산출물)이 있다. 섹션이 우선이고 이건 폴백.
FM_COMPONENT_RE = re.compile(r"^component:\s*(.+?)\s*$", re.MULTILINE)
# 코드블록 내 경로 또는 리스트 항목의 경로 추출
PATH_RE = re.compile(r"`([^`\n]+?)`|(?:^|\s)([A-Za-z0-9_\-./]+/[A-Za-z0-9_\-./]+)")


def extract_error_id(path: Path, body: str) -> str:
    # 날짜식 ID(`ERR-2026-05-28-slug`)를 일련번호식(`ERR-001`)보다 먼저 본다.
    # 순서를 바꾸면 `ERR-(\d+)` 가 앞 4자리만 물어 `ERR-2026` 으로 잘리고,
    # 같은 해의 ERR 이 전부 한 ID 로 뭉개져 패턴 귀납이 무의미해진다.
    m_date = DATE_ID_RE.match(path.stem)
    if m_date:
        return m_date.group(1)
    m = ERR_ID_RE.search(path.name)
    if m:
        return f"ERR-{int(m.group(1)):03d}"
    # H1에서라도 추출 시도
    h1 = H1_RE.search(body)
    if h1:
        m2 = ERR_ID_RE.search(h1.group(1))
        if m2:
            return f"ERR-{int(m2.group(1)):03d}"
    return path.stem


def extract_title(body: str) -> str:
    m = H1_RE.search(body)
    if not m:
        return ""
    # [ERR-NNN] 접두사 제거
    title = m.group(1).strip()
    title = re.sub(r"^\s*\[?ERR-\d+\]?\s*", "", title, flags=re.IGNORECASE)
    return title.strip()


def extract_section(body: str, aliases: list[str]) -> str | None:
    """주어진 별칭 중 하나에 해당하는 ## 섹션 본문을 추출. 없으면 None."""
    for alias in aliases:
        # ## 헤더 탐색 (부가 텍스트 허용: "## 근본 원인 (Root Cause)")
        pattern = re.compile(
            rf"^##\s+{re.escape(alias)}(?:\s*\([^)]*\))?\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        m = pattern.search(body)
        if not m:
            continue
        # 다음 ## 또는 문서 끝까지
        start = m.end()
        next_h = re.search(r"^##\s+", body[start:], re.MULTILINE)
        end = start + next_h.start() if next_h else len(body)
        return body[start:end].strip()
    return None


def parse_modules(section: str) -> list[str]:
    """영향 모듈 섹션에서 파일 경로/모듈명을 집합으로 추출."""
    if not section:
        return []
    mods: set[str] = set()
    # 백틱 코드
    for code in re.findall(r"`([^`\n]+)`", section):
        s = code.strip()
        if s and s not in {"-", "*"} and len(s) < 200:
            mods.add(s)
    # 리스트 항목 중 경로 형태
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith(("-", "*")):
            continue
        stripped = line.lstrip("-* ").strip()
        # `path` 형태가 이미 있으면 이미 추출됨
        if "`" in stripped:
            continue
        # "Trigger: src/a.py" 같은 prefix 제거
        after_colon = stripped.split(":", 1)[-1].strip() if ":" in stripped else stripped
        # 쉼표로 여러 개
        for candidate in re.split(r"[,،、]", after_colon):
            c = candidate.strip()
            if re.match(r"^[A-Za-z0-9_\-./]+/[A-Za-z0-9_\-./]+$", c):
                mods.add(c)
    return sorted(mods)


def parse_checklist(section: str) -> list[str]:
    if not section:
        return []
    items = []
    for line in section.splitlines():
        line = line.strip()
        m = re.match(r"^[-*]\s+\[[ xX]\]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
        elif line.startswith(("-", "*")):
            items.append(line.lstrip("-* ").strip())
    return items


def parse_frontmatter_modules(body: str) -> list[str]:
    """YAML frontmatter 의 `component:` 에서 모듈 목록을 회수한다.

    `component: a.py, b.py` 처럼 콤마 또는 ` · ` 로 나열하는 관행을 모두 받는다.
    frontmatter 블록(문서 선두의 `---` 쌍) 안에 있을 때만 인정 — 본문에 우연히
    나온 `component:` 줄을 모듈로 오인하지 않기 위해서다.
    """
    if not body.startswith("---"):
        return []
    end = body.find("\n---", 3)
    if end == -1:
        return []
    fm = body[3:end]
    m = FM_COMPONENT_RE.search(fm)
    if not m:
        return []
    raw = m.group(1)
    parts = re.split(r"[,·]|\s{2,}", raw)
    mods = []
    for p in parts:
        p = p.strip().strip("`").strip()
        # `(_build_prompt 커밋 절 지시문)` 같은 괄호 보충은 떼고 경로만 남긴다
        p = re.sub(r"\s*\(.*?\)\s*$", "", p).strip()
        if p and p not in mods:
            mods.append(p)
    return mods


def parse_err_file(path: Path) -> dict:
    body = path.read_text(encoding="utf-8", errors="replace")
    missing = []
    entry = {
        "error_id": extract_error_id(path, body),
        "file": str(path),
        "title": extract_title(body) or "",
    }

    for field, aliases in FIELD_ALIASES.items():
        section = extract_section(body, aliases)
        if section is None:
            missing.append(field)
            entry[field] = [] if field in ("affected_modules", "prevention") else ""
            continue
        if field == "affected_modules":
            entry[field] = parse_modules(section)
        elif field == "prevention":
            entry[field] = parse_checklist(section)
        else:
            # 첫 문단만 요약용으로 (너무 길면 잘림)
            para = section.split("\n\n", 1)[0].strip()
            entry[field] = para[:500]

    # 모듈 폴백 — 섹션이 없어도 frontmatter 의 `component:` 가 있으면 그걸 쓴다.
    # 모듈 정보가 비면 공현 행렬이 통째로 비고, hook 의 모듈쌍 그룹핑도 죽는다.
    if not entry.get("affected_modules"):
        fm = parse_frontmatter_modules(body)
        if fm:
            entry["affected_modules"] = fm
            if "affected_modules" in missing:
                missing.remove("affected_modules")

    entry["missing_fields"] = missing
    return entry


def scan_dir(dir_path: Path) -> dict:
    if not dir_path.is_dir():
        return {
            "scanned": 0,
            "parse_errors": 0,
            "dir": str(dir_path),
            "errors": [],
            "module_cooccurrence": {},
            "module_frequency": {},
            "note": f"directory not found: {dir_path}",
        }

    errors = []
    parse_errors = 0
    for p in sorted(dir_path.rglob("ERR-*.md")):
        try:
            errors.append(parse_err_file(p))
        except Exception as e:
            parse_errors += 1
            sys.stderr.write(f"[err_scan] parse failed: {p} — {e}\n")

    # 모듈 공현 / 빈도
    freq: Counter[str] = Counter()
    cooc: Counter[str] = Counter()
    for e in errors:
        mods = sorted(set(e.get("affected_modules") or []))
        freq.update(mods)
        for i, a in enumerate(mods):
            for b in mods[i + 1:]:
                cooc[f"{a}::{b}"] += 1

    return {
        "scanned": len(errors),
        "parse_errors": parse_errors,
        "dir": str(dir_path),
        "errors": errors,
        "module_cooccurrence": dict(cooc.most_common()),
        "module_frequency": dict(freq.most_common()),
    }


def main():
    p = argparse.ArgumentParser(description="Scan ERR-*.md files for arch-err-pattern skill.")
    p.add_argument("--dir", default=None, help="ERR 문서 디렉토리 (미지정 시 .flushrc.json -> find errors/ -> ./errors/ 자동 해석)")
    p.add_argument("--root", default=".", help="프로젝트 루트 (기본 현재 디렉토리)")
    p.add_argument("--json", action="store_true", help="전체 JSON 덤프")
    p.add_argument("--summary", action="store_true", help="개수·모듈 빈도 요약만")
    p.add_argument("--explain", action="store_true", help="해석된 errorDocDir의 출처(tier)만 출력")
    args = p.parse_args()

    if args.explain:
        print(json.dumps(describe_resolution(args.root), ensure_ascii=False, indent=2))
        return

    err_dir = Path(args.dir) if args.dir else resolve_error_dir(args.root)
    result = scan_dir(err_dir)

    if args.summary:
        summary = {
            "scanned": result["scanned"],
            "parse_errors": result["parse_errors"],
            "top_modules": list(result["module_frequency"].items())[:10],
            "top_cooccurrence": list(result["module_cooccurrence"].items())[:10],
            "missing_fields_count": sum(
                len(e.get("missing_fields", [])) for e in result["errors"]
            ),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        # 기본: JSON 덤프 (--json도 같은 동작)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
