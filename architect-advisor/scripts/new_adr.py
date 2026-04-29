#!/usr/bin/env python3
# Requires Python 3.10+
"""
architect-advisor — ADR 자동 생성 스크립트.

`/arch-adr` skill이 호출하여 프로젝트별 `architect-advisor/<slug>/adr/`
아래에 한국어 ADR 파일을 생성한다. `workflow-state.json`의
`steps.decision.decision`과 `terms`, decompose 산출물을 주입해 초안을 채우고,
생성 후에는 `steps.adr`에 `adr_path`, `artifacts`, `completed_at`을 기록한다.

사용법:
    python3 scripts/new_adr.py --title "Saga 패턴으로 결제 정합성 확보"
    python3 scripts/new_adr.py --project "결제시스템" --title "..." --status accepted --json
    python3 scripts/new_adr.py --title "..." --dir docs/decisions --strategy numeric
    python3 scripts/new_adr.py --bootstrap     # 디렉토리 + 인덱스만 생성

프로젝트 해상도 (우선순위):
    1. --project <name> 플래그
    2. architect-advisor/<slug>/state/workflow.json 존재하는 단일 프로젝트
    3. cwd basename 기반 auto-init

디렉토리 자동 탐지:
    architect-advisor/<slug>/adr → docs/decisions → adr → docs/adr → decisions
    없으면 --dir (기본 architect-advisor/<slug>/adr) 에 새로 생성.
    구버전 phase3-adr/phase2.5-adr가 남아 있으면 자동으로 adr/로 이름 변경한다.

파일명 전략:
    기존 ADR이 있으면 관례를 따른다.
    - `0001-*.md` 형태가 있으면 numeric 전략으로 다음 번호 사용.
    - 슬러그만 쓰는 경우 slug 전략.
    --strategy {numeric|slug} 로 강제 가능.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(os.getcwd())
AA_ROOT = REPO_ROOT / "architect-advisor"
LEGACY_WORKFLOW_STATE = REPO_ROOT / "docs" / "plan" / "workflow-state.json"

# 이 스크립트는 플러그인 scripts/ 하위에 위치한다. 템플릿은 스킬 references/ 아래.
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = (
    SCRIPT_DIR.parent / "skills" / "architect-advisor" / "references" / "adr-template.md"
)

INDEX_NAMES = ["README.md", "index.md"]

FLAT_LAYOUT_DIRS = {
    "state",
    "decompose",
    "council",
    "adr",
    "audit",
    "portfolio",
    "glossary",
    "patterns",
    # 구버전 호환
    "decision",
    "phase1-decompose",
    "phase2-decision",
    "phase2.5-adr",
    "phase3-adr",
    "phase3-audit",
    "phase4-audit",
    "phase4-portfolio",
    "phase5-portfolio",
}

STEP_ADR_DEFAULT = {
    "status": "pending",
    "started_at": None,
    "completed_at": None,
    "adr_path": None,
    "artifacts": [],
}

LEGACY_ADR_DIRS = ["phase3-adr", "phase2.5-adr"]


def slugify(title: str) -> str:
    """한국어/영어 혼용 제목을 안전한 파일명 슬러그로 변환."""
    slug = (title or "").strip().lower()
    slug = re.sub(r"[\s/\\]+", "-", slug)
    slug = re.sub(r"[^\w\-가-힣]+", "", slug, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 프로젝트 해상도
# ---------------------------------------------------------------------------

def list_project_slugs() -> list[str]:
    if not AA_ROOT.is_dir():
        return []
    slugs = []
    for p in sorted(AA_ROOT.iterdir()):
        if not p.is_dir():
            continue
        if p.name in FLAT_LAYOUT_DIRS:
            continue
        if (p / "state" / "workflow.json").is_file():
            slugs.append(p.name)
    return slugs


def resolve_project(override: str | None) -> str:
    if override:
        return slugify(override)
    slugs = list_project_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if len(slugs) > 1:
        def mtime(s: str) -> float:
            try:
                return (AA_ROOT / s / "state" / "workflow.json").stat().st_mtime
            except OSError:
                return 0.0
        slugs.sort(key=mtime, reverse=True)
        return slugs[0]
    # 평면 레이아웃에 state가 있다면 cwd basename을 슬러그로 가정
    if (AA_ROOT / "state" / "workflow.json").is_file():
        return slugify(REPO_ROOT.name)
    # 아무것도 없으면 cwd basename을 반환 (auto-init용)
    return slugify(REPO_ROOT.name)


def project_root(slug: str) -> Path:
    return AA_ROOT / slug


def state_file_for(slug: str) -> Path:
    return project_root(slug) / "state" / "workflow.json"


# ---------------------------------------------------------------------------
# 경로/상태
# ---------------------------------------------------------------------------

def adr_dir_candidates(slug: str) -> list[str]:
    """ADR directory candidates, ordered by preference (new layout first).

    The W0.3 layout convergence prefers:
      - single-product: architect-advisor/adrs/
      - monorepo:       architect-advisor/<product>/adrs/

    Legacy paths (architect-advisor/<slug>/adr, docs/adr, ...) are kept for
    backward compatibility — if a project already uses one of them, we honour
    it rather than forcing migration.
    """
    return [
        # W0.3 canonical layout
        "architect-advisor/adrs",
        f"architect-advisor/{slug}/adrs",
        # Legacy / backward compatible
        f"architect-advisor/{slug}/adr",
        "docs/decisions",
        "adr",
        "docs/adr",
        "decisions",
    ]


def migrate_legacy_adr_dir(slug: str) -> None:
    """슬러그 하위에 phase3-adr/phase2.5-adr가 남아 있으면 adr/로 이름 변경."""
    target = project_root(slug) / "adr"
    for legacy in LEGACY_ADR_DIRS:
        src = project_root(slug) / legacy
        if not src.is_dir():
            continue
        if target.is_dir():
            for f in src.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src)
                    dst = target / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        f.rename(dst)
            try:
                src.rmdir()
            except OSError:
                pass
        else:
            src.rename(target)
        sys.stderr.write(f"[new_adr] renamed {legacy}/ -> adr/ in {slug}/\n")


def detect_adr_dir(slug: str, override: str | None) -> Path:
    if override:
        return REPO_ROOT / override
    migrate_legacy_adr_dir(slug)
    for candidate in adr_dir_candidates(slug):
        p = REPO_ROOT / candidate
        if p.is_dir():
            return p
    # No existing ADR directory — default to the W0.3 canonical layout
    cfg_path = REPO_ROOT / ".architect-advisor.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("monorepo"):
                product = cfg.get("default_product") or (cfg.get("products") or [slug])[0]
                return REPO_ROOT / "architect-advisor" / product / "adrs"
        except (json.JSONDecodeError, OSError):
            pass
    return REPO_ROOT / "architect-advisor" / "adrs"


def detect_strategy(adr_dir: Path, override: str | None) -> str:
    if override:
        return override
    if adr_dir.is_dir():
        for f in adr_dir.glob("*.md"):
            if re.match(r"^\d{4}-", f.name):
                return "numeric"
    return "numeric"


def next_number(adr_dir: Path) -> int:
    n = 0
    if adr_dir.is_dir():
        for f in adr_dir.glob("*.md"):
            m = re.match(r"^(\d{4})-", f.name)
            if m:
                n = max(n, int(m.group(1)))
    return n + 1


def _migrate_phases_to_steps(state: dict) -> None:
    """구버전 phases.* → steps.* 즉석 이관 (workflow-state.py와 동일 로직의 축약본)."""
    if "phases" not in state:
        return
    phases = state.pop("phases", {}) or {}
    steps = state.setdefault("steps", {})

    def _take(key: str, default: dict) -> dict:
        v = phases.get(key)
        return v if isinstance(v, dict) else dict(default)

    legacy_p3 = phases.get("phase3") or {}
    p3_is_audit = isinstance(legacy_p3, dict) and "domain" in legacy_p3
    legacy_p4 = phases.get("phase4") or {}
    p4_is_portfolio = isinstance(legacy_p4, dict) and "domain" not in legacy_p4 and "adr_path" not in legacy_p4

    if "decompose" not in steps:
        steps["decompose"] = _take("phase1", {"status": "pending"})
    if "council" not in steps:
        d = _take("phase2", {"status": "pending"})
        d.setdefault("decision", None)
        steps["council"] = d
    if "adr" not in steps:
        if "phase2.5" in phases:
            steps["adr"] = _take("phase2.5", STEP_ADR_DEFAULT)
        elif "phase3" in phases and not p3_is_audit:
            steps["adr"] = _take("phase3", STEP_ADR_DEFAULT)
        else:
            steps["adr"] = dict(STEP_ADR_DEFAULT)
    if "audit" not in steps:
        if p3_is_audit:
            steps["audit"] = legacy_p3
        elif "phase4" in phases and not p4_is_portfolio:
            steps["audit"] = _take("phase4", {"status": "pending"})
        else:
            steps["audit"] = {"status": "pending"}
    if "portfolio" not in steps:
        if p4_is_portfolio:
            steps["portfolio"] = legacy_p4
        elif "phase5" in phases:
            steps["portfolio"] = _take("phase5", {"status": "pending"})
        else:
            steps["portfolio"] = {"status": "pending"}

    cp = state.pop("current_phase", None)
    if cp and "current_step" not in state:
        state["current_step"] = {"phase1": "decompose", "phase2": "council", "phase2.5": "adr", "phase3": "adr" if not p3_is_audit else "audit", "phase4": "audit" if not p4_is_portfolio else "portfolio", "phase5": "portfolio"}.get(cp, "decompose")


def _migrate_decision_to_council(state: dict) -> None:
    """구 step 키 'decision' → 신 키 'council'. arch-council 도입 이전 상태 호환."""
    steps = state.setdefault("steps", {})
    if "decision" in steps and "council" not in steps:
        steps["council"] = steps.pop("decision")
    elif "decision" in steps and "council" in steps:
        steps.pop("decision")


def load_workflow_state(slug: str) -> dict:
    sf = state_file_for(slug)
    if sf.is_file():
        with sf.open("r", encoding="utf-8") as f:
            state = json.load(f)
        _migrate_phases_to_steps(state)
        _migrate_decision_to_council(state)
        steps = state.setdefault("steps", {})
        if "adr" not in steps:
            steps["adr"] = dict(STEP_ADR_DEFAULT)
        if not state.get("project_slug"):
            state["project_slug"] = slug
        return state
    if LEGACY_WORKFLOW_STATE.is_file():
        with LEGACY_WORKFLOW_STATE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        _migrate_phases_to_steps(state)
        _migrate_decision_to_council(state)
        state.setdefault("steps", {}).setdefault("adr", dict(STEP_ADR_DEFAULT))
        return state
    return {}


def save_workflow_state(slug: str, state: dict) -> None:
    sf = state_file_for(slug)
    sf.parent.mkdir(parents=True, exist_ok=True)
    with sf.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_template() -> str:
    if not TEMPLATE_PATH.is_file():
        sys.stderr.write(f"[new_adr] template not found at {TEMPLATE_PATH}\n")
        sys.exit(2)
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def fill_template(
    template: str,
    title: str,
    status: str,
    state: dict,
) -> str:
    """템플릿의 `{placeholder}`를 workflow-state와 CLI 인자로 채운다."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    decision = (state.get("steps", {}).get("council", {}) or {}).get("decision") or {}
    reason = decision.get("reason", "")
    choice = decision.get("choice", "")

    template = re.sub(
        r"^# \{[^}]+\}\s*$",
        f"# {title}\n",
        template,
        count=1,
        flags=re.MULTILINE,
    )

    template = template.replace(
        'status: "{proposed | accepted | rejected | deprecated | superseded by [ADR-NNNN](NNNN-title.md)}"',
        f'status: "{status}"',
        1,
    )
    template = template.replace("{YYYY-MM-DD}", today, 1)

    if reason or choice:
        seed = f"> (auto-seeded from workflow-state) 선택: {choice}, 사유: {reason}"
        template = template.replace(
            "> architect-advisor `workflow-state.py`의 `steps.decision.decision.reason`",
            f"{seed}\n>\n> architect-advisor `workflow-state.py`의 `steps.decision.decision.reason`",
            1,
        )

    project = state.get("project")
    if project:
        template = template.replace(
            "source: \"architect-advisor decision step\"",
            f'source: "architect-advisor decision step"\nproject: "{project}"',
            1,
        )

    return template


def update_index(adr_dir: Path, filename: str, title: str, status: str) -> Path | None:
    for name in INDEX_NAMES:
        idx = adr_dir / name
        if idx.is_file():
            entry = f"- [{title}]({filename}) — {status}\n"
            content = idx.read_text(encoding="utf-8")
            if filename in content:
                return idx
            with idx.open("a", encoding="utf-8") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(entry)
            return idx
    return None


def bootstrap_index(adr_dir: Path) -> Path:
    idx = adr_dir / "README.md"
    if idx.is_file():
        return idx
    idx.write_text(
        "# Architecture Decision Records\n\n"
        "architect-advisor `/arch-adr` 산출물. 각 ADR은 MADR 4.0 + Implementation Plan + Verification 구조.\n\n"
        "## Index\n\n",
        encoding="utf-8",
    )
    return idx


def record_adr_in_state(slug: str, state: dict, adr_path: Path) -> None:
    """steps.adr에 ADR 경로를 back-reference로 기록."""
    if not state:
        return
    steps = state.setdefault("steps", {})
    ph = steps.setdefault("adr", dict(STEP_ADR_DEFAULT))
    try:
        rel = str(adr_path.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(adr_path)
    ph["adr_path"] = rel
    ph["created_at"] = now_iso()
    ph["completed_at"] = ph.get("completed_at") or now_iso()
    if not ph.get("status") or ph.get("status") == "pending":
        ph["status"] = "completed"
    artifacts = ph.setdefault("artifacts", [])
    if not any(a.get("path") == rel for a in artifacts if isinstance(a, dict)):
        artifacts.append({"path": rel, "saved_at": now_iso()})
    state["updated_at"] = now_iso()
    save_workflow_state(slug, state)


def cmd_create(args, slug: str) -> dict:
    adr_dir = detect_adr_dir(slug, args.dir)
    adr_dir.mkdir(parents=True, exist_ok=True)

    strategy = detect_strategy(adr_dir, args.strategy)
    slug_title = slugify(args.title)

    if strategy == "numeric":
        num = next_number(adr_dir)
        filename = f"{num:04d}-{slug_title}.md"
    else:
        filename = f"{slug_title}.md"

    target = adr_dir / filename
    if target.exists() and not args.force:
        return {"ok": False, "error": f"{target} already exists. Use --force to overwrite."}

    state = load_workflow_state(slug)
    template = load_template()
    filled = fill_template(template, args.title, args.status, state)
    target.write_text(filled, encoding="utf-8")

    if not (adr_dir / "README.md").is_file() and not (adr_dir / "index.md").is_file():
        bootstrap_index(adr_dir)
    index_path = update_index(adr_dir, filename, args.title, args.status)

    # state.steps.adr에 back-reference 기록
    record_adr_in_state(slug, state, target)

    # supersede 양방향 링크 처리 (W1.2 lifecycle)
    superseded_targets: list[str] = []
    if args.supersedes:
        new_adr_id = f"ADR-{num:04d}" if strategy == "numeric" else f"ADR-{slug_title}"
        new_filename = filename
        for raw in args.supersedes.split(","):
            old_id = raw.strip()
            if not old_id:
                continue
            if not old_id.upper().startswith("ADR-"):
                old_id = f"ADR-{old_id}"
            old_id = old_id.upper()
            if mark_superseded(adr_dir, old_id, new_adr_id, new_filename):
                superseded_targets.append(old_id)
        if superseded_targets:
            inject_supersedes_field(target, superseded_targets)
            for old_id in superseded_targets:
                old_filename = find_adr_filename(adr_dir, old_id)
                if old_filename:
                    update_index(adr_dir, old_filename, _read_adr_title(adr_dir / old_filename) or old_id, "superseded")

    return {
        "ok": True,
        "path": str(target.relative_to(REPO_ROOT)) if target.is_relative_to(REPO_ROOT) else str(target),
        "strategy": strategy,
        "title": args.title,
        "status": args.status,
        "project_slug": slug,
        "index": str(index_path.relative_to(REPO_ROOT)) if index_path else None,
        "workflow_seed": bool((state.get("steps", {}).get("council") or {}).get("decision")),
        "supersedes": superseded_targets,
    }


# ---------------------------------------------------------------------------
# Supersede helpers (W1.2)
# ---------------------------------------------------------------------------

def find_adr_filename(adr_dir: Path, adr_id: str) -> str | None:
    """Find the filename of an ADR by id (e.g. ADR-0007 -> 0007-foo.md)."""
    m = re.match(r"ADR-(\d+)", adr_id, re.IGNORECASE)
    if not m:
        return None
    num = int(m.group(1))
    pattern = f"{num:04d}-*.md"
    matches = sorted(adr_dir.glob(pattern))
    if matches:
        return matches[0].name
    return None


def _read_adr_title(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            title = re.sub(r"^ADR-\d+:\s*", "", title)
            return title
    return None


def mark_superseded(adr_dir: Path, old_adr_id: str, new_adr_id: str, new_filename: str) -> bool:
    """Open the old ADR and set status: superseded + superseded_by link."""
    fname = find_adr_filename(adr_dir, old_adr_id)
    if fname is None:
        sys.stderr.write(f"[new_adr] ⚠️  cannot find {old_adr_id} in {adr_dir} — skipping supersede link\n")
        return False
    target = adr_dir / fname
    text = target.read_text(encoding="utf-8")

    # Replace status line
    text = re.sub(
        r'^(\s*status:\s*)"?[^"\n]*"?',
        rf'\1"superseded by [{new_adr_id}]({new_filename})"',
        text,
        count=1,
        flags=re.MULTILINE,
    )

    # Insert/update superseded_by line in frontmatter (within first --- ... --- block)
    fm_match = re.match(r"(---\n)([\s\S]*?)(\n---\n)", text)
    if fm_match:
        fm_body = fm_match.group(2)
        if re.search(r"^superseded_by:", fm_body, re.MULTILINE):
            fm_body = re.sub(
                r"^superseded_by:.*$",
                f"superseded_by: {new_adr_id}",
                fm_body,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            fm_body = fm_body.rstrip() + f"\nsuperseded_by: {new_adr_id}"
        text = fm_match.group(1) + fm_body + fm_match.group(3) + text[fm_match.end():]

    target.write_text(text, encoding="utf-8")
    sys.stderr.write(f"[new_adr] 🔗 marked {old_adr_id} superseded_by {new_adr_id}\n")
    return True


def inject_supersedes_field(new_adr_path: Path, old_adr_ids: list[str]) -> None:
    """Add `supersedes: [...]` to the new ADR's frontmatter."""
    text = new_adr_path.read_text(encoding="utf-8")
    fm_match = re.match(r"(---\n)([\s\S]*?)(\n---\n)", text)
    if not fm_match:
        return
    fm_body = fm_match.group(2)
    line = f"supersedes: [{', '.join(old_adr_ids)}]"
    if re.search(r"^supersedes:", fm_body, re.MULTILINE):
        fm_body = re.sub(r"^supersedes:.*$", line, fm_body, count=1, flags=re.MULTILINE)
    else:
        fm_body = fm_body.rstrip() + f"\n{line}"
    text = fm_match.group(1) + fm_body + fm_match.group(3) + text[fm_match.end():]
    new_adr_path.write_text(text, encoding="utf-8")


def cmd_bootstrap(args, slug: str) -> dict:
    adr_dir = detect_adr_dir(slug, args.dir)
    adr_dir.mkdir(parents=True, exist_ok=True)
    idx = bootstrap_index(adr_dir)
    return {
        "ok": True,
        "project_slug": slug,
        "dir": str(adr_dir.relative_to(REPO_ROOT)),
        "index": str(idx.relative_to(REPO_ROOT)),
    }


def main():
    p = argparse.ArgumentParser(description="Create an architect-advisor-flavored ADR.")
    p.add_argument("--project", "-p", help="프로젝트 이름/슬러그 (미지정 시 자동 해상)")
    p.add_argument("--title", help="ADR 제목 (동사구 권장)")
    p.add_argument("--status", default="proposed", help="proposed | accepted | rejected | deprecated")
    p.add_argument("--dir", help="ADR 디렉토리 (미지정 시 자동 탐지)")
    p.add_argument("--strategy", choices=["numeric", "slug"], help="파일명 전략")
    p.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    p.add_argument("--bootstrap", action="store_true", help="디렉토리 + 인덱스만 생성")
    p.add_argument(
        "--supersedes",
        help="이 ADR이 대체하는 기존 ADR ID (콤마로 여러 개). 예: ADR-0007,ADR-0011. 양방향 링크 자동 처리",
    )
    p.add_argument("--json", action="store_true", help="JSON 출력")
    args = p.parse_args()

    slug = resolve_project(args.project)

    if args.bootstrap:
        result = cmd_bootstrap(args, slug)
    else:
        if not args.title:
            p.error("--title is required (or use --bootstrap)")
        result = cmd_create(args, slug)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result.get("ok"):
            if "path" in result:
                print(f"✅ ADR 생성: {result['path']}")
                if result.get("index"):
                    print(f"   인덱스 업데이트: {result['index']}")
                if result.get("workflow_seed"):
                    print("   workflow-state.json의 decision step 사유를 주입함.")
            else:
                print(f"✅ ADR 디렉토리 준비: {result['dir']}")
                print(f"   인덱스: {result['index']}")
        else:
            print(f"❌ {result.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
