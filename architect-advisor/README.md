# architect-advisor

Chloe의 수석 AI 아키텍트 & 시니어 PM 어드바이저 플러그인 (Claude Code).

---

## English

A senior-architect assistant plugin for Claude Code. Provides five independent
skills (`decompose → decision → adr → audit → portfolio`) and persists every
artifact under `architect-advisor/<project>/` at the repo root, so decisions
survive across sessions and projects. Each skill is callable on its own; phase
numbering was deliberately dropped because most invocations are one-off.

**Key properties**
- **`/arch-adr` produces an agent-readable executable spec** —
  every decision becomes MADR 4.0 + Implementation Plan + Verification checklist.
  The next coding agent can implement directly from the ADR without clarifying questions.
- **Six audit domains** — payment, realtime, inventory, auth, **module
  integration** (API contracts, event ordering, shared resources, migration
  order, circular deps), and a generic fallback.
- **Portfolio includes a retrospective** (Keep / Problem / Try / Revisit /
  Knowledge Gap). The next project reads previous `retrospective.md` before
  decompose — compound learning across projects.
- **Non-engineer tone** — analogies first, jargon in parentheses with
  Korean/Chinese/English tri-lingual terms.

**Quick start**
```bash
# Initialize a project workspace
python3 scripts/workflow-state.py init "payment-system"

# Run the recommended sequence end-to-end (in Claude Code)
/architect-advisor:architect-advisor

# Or call any skill on its own
/architect-advisor:arch-decompose
/architect-advisor:arch-decision
/architect-advisor:arch-adr
/architect-advisor:arch-audit
/architect-advisor:arch-portfolio

# List registered projects
python3 scripts/workflow-state.py list-projects
```

**Requirements**: Python 3.10+. Notion MCP is optional (for glossary sync).

> **TL;DR** — decompose → decision → adr → audit → portfolio, all
> persisted under `architect-advisor/<project>/`. No phase numbers — skills
> are independent tools with a recommended order.

---

## Skills (8)

**5개 단독 skill (권장 순서: decompose → decision → adr → audit → portfolio)**
- `architect-advisor` — 5개 skill을 권장 순서대로 연속 실행하는 메인 오케스트레이터.
- `arch-decompose` — 시스템 분해 & 토폴로지 (Mermaid + 결합 관계).
- `arch-decision` — MVP vs 견고한 아키텍처 비교 & 추천.
- `arch-adr` — ADR 기록 (MADR 4.0 + Implementation Plan + Verification, agent-readiness 게이트).
- `arch-audit` — 도메인별 이상 경로·리스크 감사.
- `arch-portfolio` — 커리어 자산 (STAR/면접/용어/회고) 자동 생성.

**횡단 도구 (수동 호출)**
- `term-glossary` — 기술 용어 한/중/영 3개 국어 정리 & Notion DB 동기화.
- `arch-err-pattern` — `<ERR_DIR>/ERR-*.md` 횡단 분석으로 재발 충돌 패턴 추출 → `writing-plans`가 자동 참조하는 `CONFLICT_PATTERNS.md` 생성. ERR_DIR은 `.flushrc.json` → `find errors/` → `./errors/` 3단계 자동 해석 (W0.1, flush 플러그인과 동일 규칙).

## 워크플로우

```
decompose → decision → adr → audit → portfolio
  분해       의사결정    ADR    리스크    커리어
                     (agent spec)  감사     자산
                         ↑__________|
                     (Evaluator-Optimizer 루프)
```

각 skill은 단독 호출 가능하다. **권장 순서**일 뿐 강제는 아니다.

- **decompose**: Mermaid 토폴로지, 데이터 프로토콜, 상태 머신, Blast Radius.
- **decision**: 방안 A(MVP) vs 방안 B(견고) 비교 + 추천 근거.
- **adr**: decision 결정을 MADR 4.0 기반 ADR로 고정. 코딩 에이전트가 추가 질문 없이 바로 구현할 수 있는 **"agent-readable executable spec"** (영향 경로, 따라야/피해야 할 패턴, 검증 체크리스트 포함).
- **audit**: 6개 도메인 라우팅 기반 이상 경로 시뮬레이션.
  - 결제/정산, 실시간 통신, 재고/자원, 인증/권한, **모듈 통합(Integration — 모듈간 충돌·영향도)**, 범용
- **portfolio** (4가지 산출물):
  - STAR 케이스 스터디
  - 30초 면접 요약 (한/중 이중언어)
  - 누적 용어집
  - **회고(Retrospective)** — Keep / Problem / Try / Revisit / Knowledge Gap

## Directory Layout

모든 산출물은 프로젝트 루트의 `architect-advisor/<project>/`에 skill별로 저장된다.

```
[프로젝트 루트]/
└── architect-advisor/
    └── <project>/
        ├── state/
        │   └── workflow.json     # step 전환·결정·용어 누적
        ├── decompose/            # 토폴로지, 상태 머신, Blast Radius
        ├── decision/             # 방안 비교 테이블, 추천 근거
        ├── adr/                  # NNNN-title.md (MADR 4.0 ADR)
        ├── audit/                # 도메인별 리스크 & 대응
        ├── portfolio/            # STAR, 면접 요약, 회고
        ├── glossary/             # 누적 용어집 (한/중/영)
        └── patterns/             # CONFLICT_PATTERNS.md (arch-err-pattern)
```

구버전 디렉토리(`phase1-decompose/`, `phase2.5-adr/` 등)는 첫 실행 시 자동으로 새 이름으로 이동된다.

## Scripts

- `workflow-state.py` — step 전환·결정·용어 상태를 `state/workflow.json`에 기록.
- `new_adr.py` — `/arch-adr`용 ADR 파일을 템플릿으로부터 생성(번호 자동 증가).
- `notion-term-sync.py` — 누적 용어집을 Notion DB에 동기화.

## Requirements

- Python 3.10+
- (선택) Notion MCP — 용어집 동기화 시

## 더 읽을거리

- `skills/architect-advisor/references/usage-guide.md` — 포괄적 사용 가이드.
- `skills/architect-advisor/references/adr-template.md` — ADR 템플릿 (MADR 4.0).
- `skills/architect-advisor/references/portfolio-templates.md` — STAR/면접/회고 템플릿.
