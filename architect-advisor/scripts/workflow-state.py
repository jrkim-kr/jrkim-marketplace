#!/usr/bin/env python3
# Requires Python 3.10+
"""
architect-advisor 워크플로우 상태 관리 스크립트.

각 skill 단계의 진행 상태, 수집된 용어, 선택된 방안 등을 JSON으로 추적한다.
모든 산출물은 프로젝트 루트의 `architect-advisor/<project-slug>/` 하위에
**skill 이름 디렉토리**로 저장된다 (멀티 프로젝트 지원). Phase 번호는 사용하지
않으며, skill은 독립 호출 가능한 단위다 — 다만 권장 작업 순서는
`decompose → council → adr → audit → portfolio`.

사용법:
    python3 workflow-state.py init <project-name>            # 새 워크플로우 시작
    python3 workflow-state.py [--project X] step <name> <st> # step 상태 업데이트
    python3 workflow-state.py [--project X] term <json|->    # 용어 추가 (- = stdin)
    python3 workflow-state.py [--project X] term --file <p>  # 용어 JSON 파일
    python3 workflow-state.py [--project X] council <a|b> [reason]   # (alias: decision)
    python3 workflow-state.py [--project X] save <step> <filename>  # stdin → md
    python3 workflow-state.py [--project X] paths            # 산출물 경로
    python3 workflow-state.py [--project X] show
    python3 workflow-state.py [--project X] terms
    python3 workflow-state.py [--project X] reset [--purge-artifacts]
    python3 workflow-state.py list-projects                  # 등록된 프로젝트 목록

멀티 프로젝트 경로 스키마:
    architect-advisor/<slug>/state/workflow.json   — 워크플로우 상태
    architect-advisor/<slug>/decompose/            — 토폴로지, 상태머신, 결합관계
    architect-advisor/<slug>/council/              — 4-voice 비교표, 추천 근거
    architect-advisor/<slug>/adr/NNNN-*.md         — ADR (new_adr.py가 저장)
    architect-advisor/<slug>/audit/                — 리스크 감사 결과
    architect-advisor/<slug>/portfolio/            — STAR 케이스, 면접 요약
    architect-advisor/<slug>/glossary/             — 누적 용어집
    architect-advisor/<slug>/patterns/             — CONFLICT_PATTERNS 등 횡단 산출물

자동 마이그레이션:
    1. 평면 레이아웃 (architect-advisor/{state,decompose,...}) → 슬러그 하위로 이동
    2. 구 디렉토리·키 → 신 step 이름으로 이름 변경
       - decision → council (arch-council 도입에 따른 일관화)
       - phase1-decompose → decompose, phase2-decision → council,
         phase2.5-adr/phase3-adr → adr, phase3-audit/phase4-audit → audit,
         phase4-portfolio/phase5-portfolio → portfolio
       - state.phases.{phase1..phase5,phase2.5} → state.steps.{name}
       - state.steps.decision → state.steps.council
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone


AA_ROOT = os.path.join(os.getcwd(), "architect-advisor")

# step 이름 → 산출물 디렉토리 이름 (슬러그 하위에 공통으로 붙음)
# glossary/patterns는 단독 step이 아니라 횡단 산출물이지만 저장 목표로 허용.
STEP_SUBDIRS = {
    "decompose": "decompose",
    "council": "council",
    "adr": "adr",
    "audit": "audit",
    "portfolio": "portfolio",
    "glossary": "glossary",
    "patterns": "patterns",
}

# 권장 진행 순서 (강제 아님). step 완료 시 다음 step을 current_step으로 자동 설정.
STEP_ORDER = ["decompose", "council", "adr", "audit", "portfolio"]

# 평면 레이아웃 마이그레이션 대상 (슬러그 하위로 이동) — 신키 + 구키 모두 포함
FLAT_MIGRATE_DIRS = [
    "state",
    # 신 step 디렉토리
    "decompose",
    "council",
    "adr",
    "audit",
    "portfolio",
    "glossary",
    "patterns",
    # 구 step / phase 디렉토리 (이름 변경 대상)
    "decision",
    "phase1-decompose",
    "phase2-decision",
    "phase2.5-adr",
    "phase3-adr",
    "phase3-audit",
    "phase4-audit",
    "phase4-portfolio",
    "phase5-portfolio",
]

# 구 step/phase 디렉토리 → 신 step 디렉토리 매핑 (이름 변경)
LEGACY_DIR_RENAME = {
    "decision": "council",
    "phase1-decompose": "decompose",
    "phase2-decision": "council",
    "phase2.5-adr": "adr",
    "phase3-adr": "adr",
    "phase3-audit": "audit",
    "phase4-audit": "audit",
    "phase4-portfolio": "portfolio",
    "phase5-portfolio": "portfolio",
}

# 구 phase / step 키 → 신 step 키
LEGACY_PHASE_KEY_MAP = {
    "phase1": "decompose",
    "phase2": "council",
    "phase2.5": "adr",
    # phase3는 ADR이었던 적과 audit이었던 적 둘 다 있다 — 모양으로 판별 후 매핑
    # phase4는 audit이었던 적과 portfolio였던 적 둘 다 있다 — 모양으로 판별
    # phase5는 portfolio
    "phase5": "portfolio",
    # 구 step 이름 (arch-council 도입 이전)
    "decision": "council",
}


def slugify(title: str) -> str:
    """한국어/영어 혼용 제목을 안전한 파일/디렉토리 슬러그로 변환."""
    slug = (title or "").strip().lower()
    slug = re.sub(r"[\s/\\]+", "-", slug)
    slug = re.sub(r"[^\w\-가-힣]+", "", slug, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def legacy_state_path() -> str:
    """구버전(`docs/plan/workflow-state.json`) 경로 — 마이그레이션용."""
    return os.path.join(os.getcwd(), "docs", "plan", "workflow-state.json")


# ---------------------------------------------------------------------------
# 프로젝트 해상도
# ---------------------------------------------------------------------------

def project_root(slug: str) -> str:
    return os.path.join(AA_ROOT, slug)


def state_file_for(slug: str) -> str:
    return os.path.join(project_root(slug), "state", "workflow.json")


def step_dir_for(slug: str, step: str) -> str:
    key = normalize_step_key(step)
    if key not in STEP_SUBDIRS:
        raise KeyError(step)
    return os.path.join(project_root(slug), STEP_SUBDIRS[key])


def normalize_step_key(step: str) -> str:
    if step in STEP_SUBDIRS:
        return step
    # 구버전 phase 키 호환
    if step in LEGACY_PHASE_KEY_MAP:
        return LEGACY_PHASE_KEY_MAP[step]
    if step in ("phase2_5", "phase25"):
        return "adr"
    if step in ("phase3", "phase4"):
        # 모호 — 호출자가 명시적인 step 이름을 쓰도록 유도. 보수적으로 KeyError 트리거.
        raise KeyError(f"ambiguous legacy phase key '{step}' — use explicit step name (decompose|decision|adr|audit|portfolio)")
    return step


ACTIVE_POINTER = os.path.join(AA_ROOT, ".active")


def read_active_slug() -> str | None:
    try:
        with open(ACTIVE_POINTER, "r", encoding="utf-8") as f:
            s = f.read().strip()
            return s or None
    except OSError:
        return None


def write_active_slug(slug: str) -> None:
    try:
        os.makedirs(AA_ROOT, exist_ok=True)
        with open(ACTIVE_POINTER, "w", encoding="utf-8") as f:
            f.write(slug)
    except OSError:
        pass


def list_project_slugs() -> list[str]:
    """`architect-advisor/*/state/workflow.json`이 존재하는 모든 프로젝트."""
    if not os.path.isdir(AA_ROOT):
        return []
    slugs = []
    for name in sorted(os.listdir(AA_ROOT)):
        full = os.path.join(AA_ROOT, name)
        if not os.path.isdir(full):
            continue
        # 평면 레이아웃의 step/phase 디렉토리는 스킵
        if name in FLAT_MIGRATE_DIRS:
            continue
        if os.path.isfile(os.path.join(full, "state", "workflow.json")):
            slugs.append(name)
    return slugs


def migrate_flat_layout_if_any(preferred_slug: str | None = None) -> str | None:
    """`architect-advisor/{state,...}/…`가 평면으로 남아 있으면 프로젝트 슬러그
    아래로 이동시킨다. 마이그레이션된 경우 슬러그를 반환, 아니면 None."""
    if not os.path.isdir(AA_ROOT):
        return None

    flat_state = os.path.join(AA_ROOT, "state", "workflow.json")
    flat_dirs_present = [
        d for d in FLAT_MIGRATE_DIRS
        if os.path.isdir(os.path.join(AA_ROOT, d))
    ]
    if not flat_dirs_present:
        return None

    # 슬러그 결정
    slug = preferred_slug
    if not slug and os.path.isfile(flat_state):
        try:
            with open(flat_state, "r", encoding="utf-8") as f:
                data = json.load(f)
            project = data.get("project")
            if project:
                slug = slugify(project)
            stored = data.get("project_slug")
            if stored:
                slug = stored
        except Exception:
            pass
    if not slug:
        slug = slugify(os.path.basename(os.getcwd()))

    dest_root = project_root(slug)
    if os.path.isdir(dest_root) and not flat_dirs_present:
        return None

    os.makedirs(dest_root, exist_ok=True)
    moved_any = False
    for d in flat_dirs_present:
        src = os.path.join(AA_ROOT, d)
        # 구 phase 디렉토리는 신 step 이름으로 변경하면서 이동
        target_name = LEGACY_DIR_RENAME.get(d, d)
        dst = os.path.join(dest_root, target_name)
        if os.path.isdir(dst):
            for root, _dirs, files in os.walk(src):
                rel = os.path.relpath(root, src)
                target_dir = os.path.join(dst, rel) if rel != "." else dst
                os.makedirs(target_dir, exist_ok=True)
                for fn in files:
                    s = os.path.join(root, fn)
                    t = os.path.join(target_dir, fn)
                    if not os.path.exists(t):
                        shutil.move(s, t)
            shutil.rmtree(src, ignore_errors=True)
        else:
            shutil.move(src, dst)
        moved_any = True

    if moved_any:
        sf = state_file_for(slug)
        if os.path.isfile(sf):
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    st = json.load(f)
                if not st.get("project_slug"):
                    st["project_slug"] = slug
                    with open(sf, "w", encoding="utf-8") as f:
                        json.dump(st, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        sys.stderr.write(
            f"[workflow-state] migrated flat layout -> architect-advisor/{slug}/...\n"
        )
        return slug
    return None


def migrate_per_slug_legacy_dirs(slug: str) -> bool:
    """슬러그 하위에 남아 있는 구 phase 디렉토리를 신 step 이름으로 변경."""
    root = project_root(slug)
    if not os.path.isdir(root):
        return False
    moved = False
    for old, new in LEGACY_DIR_RENAME.items():
        src = os.path.join(root, old)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(root, new)
        if os.path.isdir(dst):
            for r, _ds, fs in os.walk(src):
                rel = os.path.relpath(r, src)
                td = os.path.join(dst, rel) if rel != "." else dst
                os.makedirs(td, exist_ok=True)
                for fn in fs:
                    s = os.path.join(r, fn)
                    t = os.path.join(td, fn)
                    if not os.path.exists(t):
                        shutil.move(s, t)
            shutil.rmtree(src, ignore_errors=True)
        else:
            shutil.move(src, dst)
        moved = True
    if moved:
        sys.stderr.write(f"[workflow-state] renamed legacy phase dirs in {slug}/\n")
    return moved


def migrate_legacy_docs_plan(slug: str) -> bool:
    """`docs/plan/workflow-state.json` → `architect-advisor/<slug>/state/workflow.json`."""
    legacy = legacy_state_path()
    target = state_file_for(slug)
    if os.path.isfile(target):
        return False
    if not os.path.isfile(legacy):
        return False
    with open(legacy, "r", encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    sys.stderr.write(f"[workflow-state] migrated {legacy} -> {target}\n")
    return True


def resolve_project(override: str | None, allow_auto_init: bool = True) -> str:
    """명령 단위로 활성 프로젝트 슬러그를 해상한다."""
    if override:
        return slugify(override)

    migrated = migrate_flat_layout_if_any()
    if migrated:
        return migrated

    active = read_active_slug()
    if active and os.path.isfile(state_file_for(active)):
        return active

    slugs = list_project_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if len(slugs) > 1:
        def mtime(s: str) -> float:
            try:
                return os.path.getmtime(state_file_for(s))
            except OSError:
                return 0.0
        slugs.sort(key=mtime, reverse=True)
        return slugs[0]

    if os.path.isfile(legacy_state_path()):
        slug = slugify(os.path.basename(os.getcwd()))
        migrate_legacy_docs_plan(slug)
        return slug

    if allow_auto_init:
        slug = slugify(os.path.basename(os.getcwd()))
        return slug
    return ""


# ---------------------------------------------------------------------------
# 상태 I/O
# ---------------------------------------------------------------------------

STEP_ADR_DEFAULT = {
    "status": "pending",
    "started_at": None,
    "completed_at": None,
    "adr_path": None,
    "artifacts": [],
}

STEP_AUDIT_DEFAULT = {
    "status": "pending",
    "started_at": None,
    "completed_at": None,
    "domain": None,
    "feedback_loop_count": 0,
}

STEP_DEFAULT = {
    "status": "pending",
    "started_at": None,
    "completed_at": None,
}

PATTERNS_DEFAULT = {
    "status": "pending",
    "last_generated_at": None,
    "source_error_count": 0,
    "pattern_count": 0,
    "output_path": None,
    "artifacts": [],
}


def ensure_step_keys(state: dict) -> bool:
    """state.steps에 필수 키를 보장. 변경되면 True."""
    changed = False
    steps = state.setdefault("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        state["steps"] = steps
        changed = True
    # 구 step 키 'decision' → 신 키 'council'로 이관 (arch-council 도입 이전 상태 호환)
    if "decision" in steps and "council" not in steps:
        steps["council"] = steps.pop("decision")
        changed = True
    elif "decision" in steps and "council" in steps:
        # 둘 다 있으면 council 유지, 구 키는 폐기
        steps.pop("decision")
        changed = True
    # current_step 포인터도 동시 이관
    if state.get("current_step") == "decision":
        state["current_step"] = "council"
        changed = True
    if "decompose" not in steps:
        steps["decompose"] = dict(STEP_DEFAULT)
        changed = True
    if "council" not in steps:
        steps["council"] = dict(STEP_DEFAULT)
        steps["council"]["decision"] = None
        changed = True
    if "adr" not in steps:
        steps["adr"] = dict(STEP_ADR_DEFAULT)
        changed = True
    if "audit" not in steps:
        steps["audit"] = dict(STEP_AUDIT_DEFAULT)
        changed = True
    if "portfolio" not in steps:
        steps["portfolio"] = dict(STEP_DEFAULT)
        changed = True
    return changed


def ensure_patterns(state: dict) -> bool:
    if "patterns" not in state:
        state["patterns"] = dict(PATTERNS_DEFAULT)
        return True
    return False


def migrate_legacy_state_to_steps(state: dict) -> bool:
    """state.phases.* (구버전) → state.steps.* (신버전). 이미 신 키만 있으면 no-op."""
    if "phases" not in state:
        return False
    phases = state.get("phases") or {}
    if not isinstance(phases, dict):
        del state["phases"]
        return True

    steps = state.setdefault("steps", {})

    def take(key: str, default: dict) -> dict:
        v = phases.get(key)
        return v if isinstance(v, dict) else dict(default)

    # phase3는 audit이었거나 ADR이었음 — 모양으로 판별
    legacy_p3 = phases.get("phase3") or {}
    p3_is_audit = isinstance(legacy_p3, dict) and "domain" in legacy_p3
    legacy_p4 = phases.get("phase4") or {}
    p4_is_portfolio = isinstance(legacy_p4, dict) and "domain" not in legacy_p4 and "adr_path" not in legacy_p4

    if "decompose" not in steps:
        steps["decompose"] = take("phase1", STEP_DEFAULT)
    if "council" not in steps:
        d = take("phase2", STEP_DEFAULT)
        d.setdefault("decision", None)
        steps["council"] = d
    if "adr" not in steps:
        if "phase2.5" in phases:
            steps["adr"] = take("phase2.5", STEP_ADR_DEFAULT)
        elif not p3_is_audit and "phase3" in phases:
            steps["adr"] = take("phase3", STEP_ADR_DEFAULT)
        else:
            steps["adr"] = dict(STEP_ADR_DEFAULT)
    if "audit" not in steps:
        if p3_is_audit:
            steps["audit"] = legacy_p3
        elif "phase4" in phases and not p4_is_portfolio:
            steps["audit"] = take("phase4", STEP_AUDIT_DEFAULT)
        else:
            steps["audit"] = dict(STEP_AUDIT_DEFAULT)
    if "portfolio" not in steps:
        if p4_is_portfolio:
            steps["portfolio"] = legacy_p4
        elif "phase5" in phases:
            steps["portfolio"] = take("phase5", STEP_DEFAULT)
        else:
            steps["portfolio"] = dict(STEP_DEFAULT)

    # current_phase → current_step
    current_phase = state.pop("current_phase", None)
    if current_phase and "current_step" not in state:
        try:
            state["current_step"] = normalize_step_key(current_phase)
        except KeyError:
            state["current_step"] = "decompose"

    del state["phases"]
    return True


def default_state(project_name: str, slug: str) -> dict:
    state = {
        "project": project_name,
        "project_slug": slug,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "current_step": "decompose",
        "steps": {},
        "terms": [],
        "patterns": dict(PATTERNS_DEFAULT),
        "notion_sync": False,
        "notion_db_id": None,
    }
    ensure_step_keys(state)
    return state


def load_state(slug: str) -> dict:
    sf = state_file_for(slug)
    if os.path.isfile(sf):
        with open(sf, "r", encoding="utf-8") as f:
            state = json.load(f)
        changed = False
        changed |= migrate_legacy_state_to_steps(state)
        changed |= ensure_step_keys(state)
        changed |= ensure_patterns(state)
        if not state.get("project_slug"):
            state["project_slug"] = slug
            changed = True
        if changed:
            save_state(slug, state)
        # 슬러그 하위 디렉토리도 함께 정규화
        if migrate_per_slug_legacy_dirs(slug):
            pass
        return state

    if migrate_legacy_docs_plan(slug):
        with open(sf, "r", encoding="utf-8") as f:
            state = json.load(f)
        migrate_legacy_state_to_steps(state)
        ensure_step_keys(state)
        ensure_patterns(state)
        if not state.get("project_slug"):
            state["project_slug"] = slug
        save_state(slug, state)
        return state
    return {}


def save_state(slug: str, state: dict):
    sf = state_file_for(slug)
    os.makedirs(os.path.dirname(sf), exist_ok=True)
    with open(sf, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def auto_init_if_needed(slug: str, project_name: str | None = None, set_active: bool = True) -> dict:
    state = load_state(slug)
    if state:
        return state
    name = project_name or os.path.basename(os.getcwd()) or slug
    state = default_state(name, slug)
    save_state(slug, state)
    if set_active and not read_active_slug():
        write_active_slug(slug)
    sys.stderr.write(f"[workflow-state] auto-init project={slug}\n")
    return state


# ---------------------------------------------------------------------------
# 명령어
# ---------------------------------------------------------------------------

def cmd_init(project_name: str, override_slug: str | None = None):
    slug = slugify(override_slug) if override_slug else slugify(project_name)
    state = default_state(project_name, slug)
    save_state(slug, state)
    if not override_slug:
        write_active_slug(slug)
    print(json.dumps({
        "ok": True,
        "message": f"Workflow initialized for '{project_name}'",
        "project_slug": slug,
        "path": os.path.relpath(state_file_for(slug), os.getcwd()),
    }, ensure_ascii=False))


def cmd_step(slug: str, step: str, status: str):
    state = auto_init_if_needed(slug)
    try:
        key = normalize_step_key(step)
    except KeyError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
    if key not in state.get("steps", {}):
        print(json.dumps({"ok": False, "error": f"Unknown step: {key}"}))
        sys.exit(1)

    state["steps"][key]["status"] = status
    state["updated_at"] = now_iso()

    if status == "in_progress" and not state["steps"][key].get("started_at"):
        state["steps"][key]["started_at"] = now_iso()
        state["current_step"] = key
    elif status == "completed":
        state["steps"][key]["completed_at"] = now_iso()
        if key in STEP_ORDER:
            idx = STEP_ORDER.index(key)
            if idx + 1 < len(STEP_ORDER):
                state["current_step"] = STEP_ORDER[idx + 1]

    save_state(slug, state)
    print(json.dumps({"ok": True, "step": key, "status": status}, ensure_ascii=False))


def _read_term_payload(arg: str | None, file_path: str | None) -> str:
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    if arg == "-" or arg is None:
        return sys.stdin.read()
    return arg


def cmd_term(slug: str, payload: str):
    state = auto_init_if_needed(slug)
    term = json.loads(payload)
    term["added_at"] = now_iso()
    term["step"] = state.get("current_step", "unknown")

    def _k(v) -> str:
        return (v or "").strip().lower()

    new_key = _k(term.get("english"))
    existing = [t for t in state["terms"] if _k(t.get("english")) == new_key]
    if existing:
        existing[0].setdefault("steps", []).append(term["step"])
        print(json.dumps({"ok": True, "action": "updated", "term": existing[0].get("english")}, ensure_ascii=False))
    else:
        term["steps"] = [term["step"]]
        state["terms"].append(term)
        print(json.dumps({"ok": True, "action": "added", "term": term.get("english")}, ensure_ascii=False))

    state["updated_at"] = now_iso()
    save_state(slug, state)


def cmd_decision(slug: str, choice: str, reason: str = ""):
    """council step에서 확정된 plan을 기록한다.

    CLI는 `decision` / `council` 두 alias 모두 받는다. 내부 데이터 필드명은
    'decision'을 유지한다 — 'council이 내린 decision'이라는 의미상의 분리.
    """
    state = auto_init_if_needed(slug)
    state["steps"]["council"]["decision"] = {
        "choice": f"plan_{choice.upper()}",
        "reason": reason,
        "decided_at": now_iso(),
    }
    state["updated_at"] = now_iso()
    save_state(slug, state)
    print(json.dumps({"ok": True, "decision": f"Plan {choice.upper()}", "reason": reason}, ensure_ascii=False))


def cmd_show(slug: str):
    state = load_state(slug)
    if not state:
        print(json.dumps({"ok": False, "error": "No workflow state found."}))
        sys.exit(1)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_terms(slug: str):
    state = load_state(slug)
    if not state:
        print(json.dumps({"ok": False, "error": "No workflow state found."}))
        sys.exit(1)
    print(json.dumps(
        {"terms": state.get("terms", []), "count": len(state.get("terms", []))},
        ensure_ascii=False,
        indent=2,
    ))


def cmd_reset(slug: str, purge_artifacts: bool = False):
    sf = state_file_for(slug)
    removed_state = False
    if os.path.isfile(sf):
        os.remove(sf)
        removed_state = True
    removed_tree = False
    if purge_artifacts:
        root = project_root(slug)
        if os.path.isdir(root):
            shutil.rmtree(root)
            removed_tree = True
    print(json.dumps({
        "ok": True,
        "message": "Workflow state reset.",
        "project_slug": slug,
        "state_removed": removed_state,
        "artifacts_purged": removed_tree,
    }, ensure_ascii=False))


def cmd_save(slug: str, step: str, filename: str):
    content = sys.stdin.read()
    if not content.strip():
        print(json.dumps({"ok": False, "error": "stdin is empty"}))
        sys.exit(1)
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    try:
        key = normalize_step_key(step)
    except KeyError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
    if key not in STEP_SUBDIRS:
        print(json.dumps({"ok": False, "error": f"Unknown step dir: {step}"}))
        sys.exit(1)
    target_dir = step_dir_for(slug, key)
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, filename)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)

    state = auto_init_if_needed(slug)
    rel_path = os.path.relpath(target, os.getcwd())
    saved_at = now_iso()

    step_state = state.get("steps", {}).get(key)
    if step_state is not None:
        step_state.setdefault("artifacts", []).append({"path": rel_path, "saved_at": saved_at})
        state["updated_at"] = saved_at
        save_state(slug, state)
    elif key == "patterns":
        ensure_patterns(state)
        patterns = state["patterns"]
        patterns["status"] = "generated"
        patterns["last_generated_at"] = saved_at
        patterns["output_path"] = rel_path
        patterns.setdefault("artifacts", []).append({"path": rel_path, "saved_at": saved_at})
        state["updated_at"] = saved_at
        save_state(slug, state)

    print(json.dumps({
        "ok": True,
        "path": rel_path,
        "step": key,
        "project_slug": slug,
    }, ensure_ascii=False))


def cmd_patterns_stat(slug: str, kv: dict):
    """arch-err-pattern skill이 호출해서 state.patterns의 통계 필드를 갱신."""
    state = auto_init_if_needed(slug)
    ensure_patterns(state)
    patterns = state["patterns"]
    if "source_errors" in kv:
        patterns["source_error_count"] = kv["source_errors"]
    if "pattern_count" in kv:
        patterns["pattern_count"] = kv["pattern_count"]
    if "singletons" in kv:
        patterns["singleton_count"] = kv["singletons"]
    patterns["last_generated_at"] = now_iso()
    if patterns.get("status") == "pending":
        patterns["status"] = "generated"
    state["updated_at"] = now_iso()
    save_state(slug, state)
    print(json.dumps({"ok": True, "project_slug": slug, "patterns": patterns}, ensure_ascii=False))


def cmd_paths(slug: str):
    root = project_root(slug)
    info = {
        "project_slug": slug,
        "root": os.path.relpath(root, os.getcwd()),
        "state": os.path.relpath(state_file_for(slug), os.getcwd()),
        "steps": {
            k: os.path.relpath(os.path.join(root, v), os.getcwd())
            for k, v in STEP_SUBDIRS.items()
        },
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))


def cmd_list_projects():
    migrate_flat_layout_if_any()
    slugs = list_project_slugs()
    projects = []
    for slug in slugs:
        sf = state_file_for(slug)
        name = slug
        current_step = None
        try:
            with open(sf, "r", encoding="utf-8") as f:
                st = json.load(f)
            name = st.get("project", slug)
            current_step = st.get("current_step") or st.get("current_phase")
        except Exception:
            pass
        projects.append({
            "project_slug": slug,
            "project": name,
            "current_step": current_step,
            "state": os.path.relpath(sf, os.getcwd()),
        })
    print(json.dumps({"projects": projects, "count": len(projects)}, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 엔트리포인트
# ---------------------------------------------------------------------------

def _extract_project_flag(argv: list[str]) -> tuple[str | None, list[str]]:
    """argv에서 --project/-p <값> 또는 --project=<값> 플래그를 뽑아낸다."""
    override = None
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--project", "-p"):
            if i + 1 >= len(argv):
                print("--project requires a value", file=sys.stderr)
                sys.exit(2)
            override = argv[i + 1]
            i += 2
            continue
        if a.startswith("--project="):
            override = a.split("=", 1)[1]
            i += 1
            continue
        out.append(a)
        i += 1
    return override, out


def main():
    argv = sys.argv[1:]
    override, argv = _extract_project_flag(argv)

    if not argv:
        print(__doc__)
        sys.exit(1)

    cmd = argv[0]
    rest = argv[1:]

    # 구버전 alias: phase → step
    if cmd == "phase":
        cmd = "step"

    if cmd == "list-projects":
        cmd_list_projects()
        return

    if cmd == "init":
        project_name = rest[0] if rest else "untitled"
        cmd_init(project_name, override_slug=override)
        return

    slug = resolve_project(override)

    if cmd == "step":
        if not rest:
            print("Usage: workflow-state.py step <step> <status>", file=sys.stderr)
            sys.exit(1)
        cmd_step(slug, rest[0], rest[1] if len(rest) > 1 else "in_progress")

    elif cmd == "term":
        payload = None
        if rest and rest[0] == "--file":
            if len(rest) < 2:
                print("Usage: workflow-state.py term --file <path>", file=sys.stderr)
                sys.exit(1)
            payload = _read_term_payload(None, rest[1])
        elif rest and rest[0] == "-":
            payload = _read_term_payload("-", None)
        elif rest:
            payload = rest[0]
        else:
            payload = _read_term_payload("-", None)
        cmd_term(slug, payload)

    elif cmd in ("council", "decision"):
        if not rest:
            print("Usage: workflow-state.py council <a|b> [reason]", file=sys.stderr)
            sys.exit(1)
        cmd_decision(slug, rest[0], " ".join(rest[1:]) if len(rest) > 1 else "")

    elif cmd == "show":
        cmd_show(slug)

    elif cmd == "terms":
        cmd_terms(slug)

    elif cmd == "reset":
        purge = "--purge-artifacts" in rest
        cmd_reset(slug, purge_artifacts=purge)

    elif cmd == "save":
        if len(rest) < 2:
            print("Usage: workflow-state.py save <step> <filename>  (stdin으로 컨텐츠 전달)", file=sys.stderr)
            sys.exit(1)
        cmd_save(slug, rest[0], rest[1])

    elif cmd == "paths":
        cmd_paths(slug)

    elif cmd == "patterns-stat":
        kv: dict[str, int] = {}
        i = 0
        while i < len(rest):
            if rest[i].startswith("--") and i + 1 < len(rest):
                key = rest[i][2:].replace("-", "_")
                try:
                    kv[key] = int(rest[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        cmd_patterns_stat(slug, kv)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
