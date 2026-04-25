#!/usr/bin/env python3
# Requires Python 3.10+
"""
Notion 기술 용어 동기화 스크립트 (MCP 선택 의존).

workflow.json에서 수집된 용어를 읽어 Notion DB에 페이지로 생성한다.
Claude가 이 스크립트 출력을 파싱 후 `mcp__notion__notion-create-pages`로
실제 페이지를 만드는 **간접 파이프라인**이다 — 이 스크립트 자체는
Notion API를 직접 호출하지 않는다.

사용법:
    python3 notion-term-sync.py --db-id <NOTION_DB_ID>
    python3 notion-term-sync.py --db-id <NOTION_DB_ID> --project <slug>
    python3 notion-term-sync.py --db-id <NOTION_DB_ID> --step adr
    python3 notion-term-sync.py --db-id <NOTION_DB_ID> --dry-run
    python3 notion-term-sync.py --check-mcp        # MCP 설치 상태만 확인

Graceful degradation (MCP 미설치 시):
    - `--check-mcp`: ok=false와 설치 안내를 JSON으로 반환 (exit 0)
    - 일반 실행: 여전히 JSON 명령 목록을 출력하되 stderr에 "MCP 미감지,
      로컬 파일 export만 수행" 경고. Claude가 받을 수 있으면 페이지 생성,
      아니면 `architect-advisor/<slug>/glossary/notion-sync.json`으로
      명령 목록을 dump만 하도록 `--export-only` 제공.

멀티 프로젝트 경로:
    state JSON은 `architect-advisor/<slug>/state/workflow.json`에서 탐색.
    `--project` 미지정 시 `architect-advisor/.active` 파인터 → 단일 프로젝트
    → cwd basename 순으로 해상한다.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

AA_ROOT = os.path.join(os.getcwd(), "architect-advisor")
ACTIVE_POINTER = os.path.join(AA_ROOT, ".active")
LEGACY_STATE = os.path.join(os.getcwd(), "docs", "plan", "workflow-state.json")

FLAT_LAYOUT_DIRS = {
    "state", "decompose", "decision", "adr", "audit", "portfolio",
    "glossary", "patterns",
    # 구버전 호환
    "phase1-decompose", "phase2-decision", "phase2.5-adr",
    "phase3-adr", "phase3-audit", "phase4-audit",
    "phase4-portfolio", "phase5-portfolio",
}


def slugify(title: str) -> str:
    slug = (title or "").strip().lower()
    slug = re.sub(r"[\s/\\]+", "-", slug)
    slug = re.sub(r"[^\w\-가-힣]+", "", slug, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def list_project_slugs() -> list[str]:
    if not os.path.isdir(AA_ROOT):
        return []
    out = []
    for name in sorted(os.listdir(AA_ROOT)):
        full = os.path.join(AA_ROOT, name)
        if not os.path.isdir(full) or name in FLAT_LAYOUT_DIRS:
            continue
        if os.path.isfile(os.path.join(full, "state", "workflow.json")):
            out.append(name)
    return out


def resolve_project(override: str | None) -> str:
    if override:
        return slugify(override)
    # .active pointer
    try:
        with open(ACTIVE_POINTER, "r", encoding="utf-8") as f:
            slug = f.read().strip()
            if slug:
                return slug
    except OSError:
        pass
    slugs = list_project_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if len(slugs) > 1:
        # 가장 최근에 수정된 것
        slugs.sort(
            key=lambda s: os.path.getmtime(
                os.path.join(AA_ROOT, s, "state", "workflow.json")
            ),
            reverse=True,
        )
        return slugs[0]
    return slugify(os.path.basename(os.getcwd()))


def state_file_for(slug: str) -> str:
    return os.path.join(AA_ROOT, slug, "state", "workflow.json")


def glossary_dir_for(slug: str) -> str:
    return os.path.join(AA_ROOT, slug, "glossary")


def load_state(slug: str) -> dict:
    sf = state_file_for(slug)
    if os.path.isfile(sf):
        with open(sf, "r", encoding="utf-8") as f:
            return json.load(f)
    # legacy fallback
    if os.path.isfile(LEGACY_STATE):
        with open(LEGACY_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def detect_mcp_available() -> dict:
    """MCP Notion 도구가 현재 Claude 세션에서 사용 가능한지 감지.

    스크립트 단독으로는 MCP 런타임에 접근할 수 없으므로, 외부 신호로
    판단한다:
      - 환경변수 `CLAUDE_MCP_NOTION_AVAILABLE=1`이 있으면 사용 가능
      - `ANTHROPIC_MCP_SERVERS`가 `notion`을 포함하면 사용 가능
      - `~/.claude/mcp.json` 또는 프로젝트 `.claude/mcp.json`에 notion
        엔트리가 있으면 가능성 있음
      - 위 전부 해당 없으면 미감지 상태로 간주
    """
    if os.environ.get("CLAUDE_MCP_NOTION_AVAILABLE") == "1":
        return {"ok": True, "source": "env:CLAUDE_MCP_NOTION_AVAILABLE"}
    servers = os.environ.get("ANTHROPIC_MCP_SERVERS", "")
    if "notion" in servers.lower():
        return {"ok": True, "source": "env:ANTHROPIC_MCP_SERVERS"}
    for candidate in [
        os.path.expanduser("~/.claude/mcp.json"),
        os.path.join(os.getcwd(), ".claude", "mcp.json"),
    ]:
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                servers = (cfg.get("mcpServers") or {})
                if any("notion" in k.lower() for k in servers):
                    return {"ok": True, "source": candidate}
            except Exception:
                continue
    return {
        "ok": False,
        "hint": (
            "Notion MCP 미감지. Claude Code에서 Notion MCP 서버를 설정하거나, "
            "`--export-only`로 JSON 명령만 로컬 파일로 덤프하세요. "
            "docs: https://docs.claude.com/en/docs/claude-code/mcp"
        ),
    }


def cmd_check_mcp():
    result = detect_mcp_available()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # check-mcp는 항상 exit 0 — graceful 원칙
    sys.exit(0)


def build_notion_page(term: dict, db_id: str) -> dict:
    """용어 하나를 Notion 페이지 생성 명령으로 변환"""
    korean = term.get("korean", "")
    english = term.get("english", "")
    chinese = term.get("chinese", "")
    pronunciation = term.get("pronunciation", "")
    analogy_kr = term.get("analogy_kr", "")
    analogy_cn = term.get("analogy_cn", "")
    definition_kr = term.get("definition_kr", "")
    definition_cn = term.get("definition_cn", "")
    application_kr = term.get("application_kr", "")
    application_cn = term.get("application_cn", "")
    # 구버전(phases)/신버전(steps) 둘 다 허용
    steps = term.get("steps") or term.get("phases", [])

    title = f"{korean} ({english})"

    # Notion rich text body
    body_lines = [
        f"## {korean} ({chinese} / {english})",
        f"**발음**: {pronunciation}" if pronunciation else "",
        "",
        "### 한국어 설명",
        f"**비유**: {analogy_kr}" if analogy_kr else "",
        f"**기술 정의**: {definition_kr}" if definition_kr else "",
        f"**적용 사례**: {application_kr}" if application_kr else "",
        "",
        "### 中文说明",
        f"**类比**: {analogy_cn}" if analogy_cn else "",
        f"**技术定义**: {definition_cn}" if definition_cn else "",
        f"**应用案例**: {application_cn}" if application_cn else "",
        "",
        f"**등장 Step**: {', '.join(steps)}" if steps else "",
    ]

    return {
        "action": "create_page",
        "database_id": db_id,
        "title": title,
        "body_markdown": "\n".join(line for line in body_lines if line is not None),
        "properties": {
            "Korean": korean,
            "English": english,
            "Chinese": chinese,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Notion 기술 용어 동기화 (MCP 선택 의존)")
    parser.add_argument("--db-id", help="Notion Database ID (check-mcp 외에는 필수)")
    parser.add_argument("--dry-run", action="store_true", help="실제 동기화 없이 미리보기만")
    parser.add_argument("--step", help="특정 step 용어만 동기화 (decompose/decision/adr/audit/portfolio)")
    parser.add_argument("--phase", help=argparse.SUPPRESS)  # 구버전 호환
    parser.add_argument("--project", "-p", help="대상 프로젝트 슬러그 (미지정 시 자동 해상)")
    parser.add_argument("--state-file", help="workflow.json 직접 경로 override")
    parser.add_argument("--check-mcp", action="store_true", help="MCP Notion 설치 상태만 확인")
    parser.add_argument("--export-only", action="store_true", help="MCP 호출 시도 없이 JSON 명령만 glossary 폴더로 덤프")
    args = parser.parse_args()

    if args.check_mcp:
        cmd_check_mcp()
        return

    if not args.db_id:
        print(json.dumps({"ok": False, "error": "--db-id is required (unless --check-mcp)"}, ensure_ascii=False))
        sys.exit(2)

    slug = resolve_project(args.project)

    if args.state_file:
        sf = args.state_file
        state = (json.load(open(sf, encoding="utf-8")) if os.path.isfile(sf) else {})
    else:
        state = load_state(slug)

    if not state:
        print(json.dumps(
            {"ok": False, "error": f"No workflow state found for project '{slug}'. Run `workflow-state.py init {slug}` first."},
            ensure_ascii=False,
        ))
        sys.exit(1)

    terms = state.get("terms", [])
    if not terms:
        print(json.dumps({"ok": True, "message": "No terms to sync.", "project_slug": slug, "count": 0}, ensure_ascii=False))
        return

    step_filter = args.step or args.phase
    if step_filter:
        # 구버전 phase 키도 입력으로 받아 step으로 매핑
        legacy_map = {"phase1": "decompose", "phase2": "decision", "phase2.5": "adr", "phase3": "adr", "phase4": "audit", "phase5": "portfolio"}
        step_filter = legacy_map.get(step_filter, step_filter)
        terms = [t for t in terms if step_filter in (t.get("steps") or t.get("phases", []))]

    commands = [build_notion_page(t, args.db_id) for t in terms]

    mcp = detect_mcp_available()
    mode = "dry_run" if args.dry_run else ("export_only" if args.export_only else "sync")

    result = {
        "ok": True,
        "mode": mode,
        "project_slug": slug,
        "database_id": args.db_id,
        "term_count": len(commands),
        "mcp_available": mcp.get("ok", False),
        "commands": commands,
    }
    if not mcp.get("ok"):
        result["mcp_hint"] = mcp.get("hint")

    # export-only 또는 MCP 미감지 시: glossary/ 폴더에 JSON 명령 dump
    if args.export_only or (not args.dry_run and not mcp.get("ok")):
        gdir = glossary_dir_for(slug)
        os.makedirs(gdir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dump_path = os.path.join(gdir, f"notion-sync-{ts}.json")
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result["export_path"] = os.path.relpath(dump_path, os.getcwd())
        if not args.export_only:
            sys.stderr.write(
                f"[notion-term-sync] MCP 미감지 — 명령을 {result['export_path']}에 덤프함. "
                "나중에 Notion MCP 설정 후 재실행하거나, Claude 세션에서 이 파일을 읽고 수동 생성하세요.\n"
            )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.dry_run:
        print(f"\n--- Dry run: {len(commands)} terms would be synced to DB {args.db_id} ---", file=sys.stderr)
    elif args.export_only:
        print(f"\n--- Export only: {len(commands)} commands saved to {result.get('export_path')} ---", file=sys.stderr)
    elif mcp.get("ok"):
        print(f"\n--- {len(commands)} sync commands generated. Claude will execute via MCP. ---", file=sys.stderr)


if __name__ == "__main__":
    main()
