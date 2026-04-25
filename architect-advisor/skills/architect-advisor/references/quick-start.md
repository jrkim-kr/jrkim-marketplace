# architect-advisor Quick Start

> `/architect-advisor` 첫 실행 시 Chloe가 바로 참고할 수 있는 통합 사용 가이드.
> 상세한 Step별 로직은 메인 SKILL.md를, ADR 작성은 `adr-template.md`와
> `adr-review-checklist.md`를, 톤은 `audience-tone.md`를 참조한다.

---

## 1. 스킬 철학 한 줄

> **"로직이 먼저, 코드는 나중에"** — 비즈니스 결정을 에이전트가 바로 구현할 수 있는 **실행 가능 스펙(executable spec)** 으로 고정하고, 모든 산출물을 `architect-advisor/<project>/` 아래에 누적해 다음 프로젝트에 **복리 효과(compound learning)** 를 만든다.

아키텍처 패턴 3종 조합 (Anthropic Agent Patterns):
- **Prompt Chaining**: decompose → decision → adr → audit → portfolio 순차 체인
- **Parallelization**: 용어 번역 레이어(횡단 관심사)가 모든 step와 동시 동작
- **Evaluator-Optimizer**: adr ↔ audit 피드백 루프

---

## 2. 언제 어떤 명령을 쓰나

| 상황 | 명령 | 소요 시간 | 산출물 |
|---|---|---|---|
| 새 기능·도메인 처음부터 설계 | `/architect-advisor:architect-advisor` | 40~60분 | 권장 순서 전체 |
| 요구사항만 있고 구조만 먼저 쪼개고 싶음 | `/architect-advisor:arch-decompose` | 10~15분 | 토폴로지·상태머신·결합관계 |
| 두 방안 중 하나 고르는 비교만 필요 | `/architect-advisor:arch-decision` | 10~20분 | 비교표 + 추천안 (+ ADR 초안) |
| 기존 설계 리스크만 점검 | `/architect-advisor:arch-audit` | 15~25분 | 도메인별 감사서 + Integration Risk |
| 완료된 설계를 커리어 자산화 | `/architect-advisor:arch-portfolio` | 10~15분 | STAR + 면접 요약 + 회고 |
| 기술 용어만 한/중/영 정리 | `/architect-advisor:term-glossary` | ~5분 | 누적 용어집 (Notion 동기화 선택) |

**Proactive 자동 감지 신호** (Chloe가 명시 호출 안 해도 에이전트가 먼저 제안):
- "A 쓸까 B 쓸까?" (새 의존성·패턴 선택)
- "결제/인증/정산 흐름 설계"
- "왜 예전에 이렇게 했지?" (ADR 고고학)
- 코드 주석이 3줄 넘게 설계 이유 설명 중

---

## 3. Step별 상세

### decompose — 시스템 분해 (Decomposition)

| 항목 | 내용 |
|---|---|
| **목적** | 요구사항을 독립적인 비즈니스 노드로 쪼개고 전체 흐름을 **시각화** |
| **목표** | Chloe가 "이 모듈 바꾸면 저기 괜찮나?"에 즉답 가능한 상태 |
| **핵심 로직** | 노드 분해 → 데이터 계약 → 상태 머신 → 결합 관계(Blast Radius) |
| **입력** | 자연어 요구사항, 비즈니스 목표, (선택) 기존 코드 링크 |
| **산출물** | `decompose/topology.md` (Mermaid), `state-machine.md`, `coupling.md` |
| **체크포인트** | 노드 구성·상태 전이·결합 관계 3가지를 Chloe가 확인 |
| **Chloe 개입 빈도** | **높음** (도메인 지식 필요) |
| **스킵 가능?** | ❌ — 이후 모든 step의 기반 |

### decision — 의사결정 & 트레이드오프 (Decision)

| 항목 | 내용 |
|---|---|
| **목적** | 핵심 로직에 대해 **MVP vs 견고한 아키텍처** 두 방안을 정량 비교 |
| **목표** | Chloe가 수치 기반으로 "拍板(확정)"할 수 있게 함 |
| **핵심 로직** | 두 방안 제시 → 평가 항목별 비교표 → 아키텍트 추천 → 필수 감사(멱등성·데이터 일관성) |
| **입력** | decompose 산출물 + 비즈니스 제약(시간·팀·예산) |
| **산출물** | `decision/comparison.md` (비교표 + 추천 근거) |
| **체크포인트** | Chloe의 명시적 확정(拍板). **확정 전까지 코드 금지** |
| **Chloe 개입 빈도** | **매우 높음** (결정권자) |
| **스킵 가능?** | ❌ — 핵심 단계 |

### adr — ADR 기록 (Decision Record)

| 항목 | 내용 |
|---|---|
| **목적** | decision 결정을 **에이전트가 바로 구현 가능한 실행 스펙**으로 고정 |
| **목표** | 다음 코딩 에이전트가 추가 질문 없이 Implementation Plan 따라 코드 작성 가능 |
| **핵심 로직** | MADR 4.0 템플릿 + Implementation Plan(affected paths·deps·patterns·verification) + 양방향 링크 |
| **입력** | decision 확정안, `workflow.json`의 `steps.decision.decision.reason` |
| **산출물** | `adr/NNNN-<슬러그>.md` + `README.md` 인덱스. state의 `steps.adr.adr_path`에 back-ref |
| **체크포인트** | `adr-review-checklist.md` 통과(✅ 통과 / ⚠️ 갭 / 권고 3줄 요약) |
| **Chloe 개입 빈도** | 낮음 (체크리스트 승인만) |
| **스킵 가능?** | ⚠️ — 핵심 로직(결제·인증·정산)은 생략 금지. 사소한 리팩터링은 생략 가능 |
| **실행 명령** | `python3 scripts/new_adr.py --title "..." --status accepted` |

### audit — 이상 경로 감사 (Risk Audit)

| 항목 | 내용 |
|---|---|
| **목적** | 극단적 상황을 시뮬레이션하여 **런타임 취약점**을 사전 발견 |
| **목표** | 방안이 구조적 리스크를 해결하는지 검증. 안 되면 decision으로 복귀 (Evaluator-Optimizer 루프) |
| **핵심 로직** | 도메인 라우팅(6종) → 시나리오별 Self-Q&A → 방안 검증 → 보완 설계 제안 |
| **입력** | adr + decompose의 결합 관계 |
| **산출물** | `audit/<도메인>-audit.md`, `integration-risk.md` + ADR의 `## Risk Audit` 섹션 append |
| **도메인 6종** | 결제/정산 · 실시간 통신 · 재고/자원 · 인증/권한 · **모듈 통합(Integration)** · 범용 |
| **체크포인트** | 치명 시나리오 대응 완료 또는 방안 재검토 제안 |
| **스킵 가능?** | ⚠️ — 결제·인증·정산은 필수 |

**Integration Risk 상세** (모듈간 충돌·영향도):
API 계약 깨짐 · 이벤트 순서·중복·유실 · 공유 리소스 경합 · 버전 호환성 · 배포 순서 · 순환 의존 · 스키마 마이그레이션 · 트랜잭션 경계 · 백프레셔 전파

### portfolio — 커리어 자산 자동화 (Portfolio)

| 항목 | 내용 |
|---|---|
| **목적** | 설계 과정을 **면접 즉시 활용 가능한 자산**으로 변환 + 다음 프로젝트를 위한 회고 |
| **목표** | 5년 뒤 Chloe가 이 결정을 3분 안에 재설명 가능한 상태 |
| **핵심 로직** | STAR 구조 추출 → 30초 중한 면접 요약 → 누적 용어집 → **회고(Keep/Problem/Try/Revisit/Knowledge Gap)** |
| **입력** | decompose~3 전체 산출물 + Chloe 회고 인풋 |
| **산출물** | `portfolio/{star-case,interview-30s,retrospective}.md` + `glossary/glossary.md` |
| **스킵 가능?** | ✅ — 커리어/면접 목적 없으면 스킵 가능 (설계 품질에는 영향 없음) |

**회고 5-섹션** (다음 프로젝트 decompose 진입 전 필수 독서):
🟢 Keep · 🔴 Problem · 🔵 Try · ⏰ Revisit · 📚 Knowledge Gap

---

## 4. 횡단 레이어 — 용어 번역

**동작**: 모든 step에서 새 전문용어 등장 시 **즉시 인라인 번역**. portfolio 끝에 누적 용어집 자동 생성.

**포맷**: `일상 비유 (용어/中文·English /발음/ — 한 줄 정의)`

예시:
```
같은 결제 요청을 여러 번 눌러도 한 번만 처리되게 한다
(멱등성/幂等性·Idempotency /ˌaɪ.dəmˈpoʊ.tən.si/ — 엘리베이터
버튼 10번 눌러도 한 번만 호출되는 성질).
```

**Notion 동기화** (선택): `python3 scripts/notion-term-sync.py --db-id <ID>` — MCP 미감지 시 `glossary/notion-sync-*.json`로 자동 덤프.

---

## 5. Best Practices

### ✅ Do

| 원칙 | 이유 |
|---|---|
| decompose부터 시작 | 요구사항 모호할 때 decision 직행하면 비교가 straw man 됨 |
| 확정 전 코드 금지 | decision 체크포인트 뚫리면 되돌리기 비용 10배 |
| ADR은 핵심 로직만 | 스타일·리팩터링까지 ADR 쓰면 피로도 폭증 |
| 전문용어는 비유 먼저 | 비전공자 독자가 이해 못하면 ADR이 executable spec 역할 못함 |
| 다중 모듈 시스템은 Integration Risk 항상 | 정적 결합 분석으론 동적 충돌 못 잡음 |
| 다음 프로젝트 decompose 전에 이전 회고 읽기 | 복리 효과의 핵심 |
| 산출물을 `workflow-state.py save`로 저장 | 버전관리에 커밋되어 PR 리뷰·팀 공유 가능 |
| Proactive 신호 존중 | "A 쓸까 B 쓸까"는 되돌리기 힘든 결정 확률 높음 |

### ❌ Don't

| 안티패턴 | 대안 |
|---|---|
| decision에서 방안 1개만 제시 | 최소 2개 비교 (straw man 금지) |
| "성능 향상" 같은 모호한 Verification | "p95 < 200ms, 100 concurrent requests" 수치화 |
| ADR Implementation Plan에 "DB 코드 수정" | 실제 파일 경로(`src/db/client.ts`)까지 명시 |
| audit 스킵하고 portfolio로 점프 | 감사 없는 포트폴리오는 면접에서 역풍 |
| 회고에 Keep만 적기 | Problem·Try가 복리 효과의 진짜 엔진 |
| 동일 프로젝트에 여러 번 init | `--project <name>` 플래그로 분리 |
| Chloe 체크포인트 없이 자동 진행 | 각 step 끝에 "✅/⚠️ 요약"으로 확인 |
| 코드 주석으로 설계 이유 길게 | "이 설명은 ADR로"라며 Proactive 트리거 |

### 🎯 톤 정책 (비전공자 친화)

- **비유 먼저, 용어는 괄호로**
- **한 문장 한 개념** (복문 금지)
- **3개 이상 비교는 표**, 흐름은 Mermaid
- **4단 응답 구조**: `🎯 지금 뭘 하나 / 📌 핵심 포인트 / 📊 비교·다이어그램 / 👉 Chloe가 할 일`
- 상세: `audience-tone.md`

---

## 6. 치트시트

### 디렉토리 레이아웃

```
[프로젝트 루트]/
└── architect-advisor/
    ├── .active                    # 현재 활성 프로젝트 포인터
    └── <project-slug>/
        ├── state/workflow.json    # step 전환·결정·용어
        ├── decompose/      # 토폴로지, 상태머신, 결합
        ├── decision/       # 비교표, 추천
        ├── adr/          # NNNN-*.md + README 인덱스
        ├── audit/          # 도메인별 감사, integration-risk
        ├── portfolio/      # STAR, 면접, 회고
        └── glossary/              # 누적 용어집, notion-sync-*.json
```

### 명령어

```bash
# 프로젝트 시작
python3 scripts/workflow-state.py init "결제시스템"

# step 상태 전환
python3 scripts/workflow-state.py step <name> completed

# 방안 확정 기록
python3 scripts/workflow-state.py decision b "Saga로 정합성 확보"

# ADR 생성 (adr)
python3 scripts/new_adr.py --title "Saga로 결제 정합성 확보" --status accepted

# 산출물 저장 (stdin 파이프)
echo "# 토폴로지" | python3 scripts/workflow-state.py save decompose topology

# 용어 추가 (stdin/파일)
cat term.json | python3 scripts/workflow-state.py term -
python3 scripts/workflow-state.py term --file term.json

# 상태 확인
python3 scripts/workflow-state.py show
python3 scripts/workflow-state.py paths
python3 scripts/workflow-state.py list-projects

# 다중 프로젝트
python3 scripts/workflow-state.py --project "정산시스템" init "정산시스템"

# 리셋 (산출물까지 삭제)
python3 scripts/workflow-state.py reset --purge-artifacts

# Notion 동기화
python3 scripts/notion-term-sync.py --check-mcp
python3 scripts/notion-term-sync.py --db-id <ID> --export-only
```

### step 종료 자문 체크리스트

- **decompose**: 노드·상태·결합 3가지 Chloe 확인?
- **decision**: 방안 2개 + 평가 항목별 비교 + 수치 근거?
- **adr**: agent-readiness 체크리스트 통과? 갭은 보완 or decompose/2 복귀
- **audit**: 도메인 판별 + 치명 시나리오 대응 + Integration Risk 커버?
- **portfolio**: STAR·면접·용어집·회고 4종 + 재방문 트리거 명시?

---

## 7. 참고 문서 맵

| 문서 | 용도 |
|---|---|
| `SKILL.md` | 메인 스킬 정의 (권장 순서 전체 상세) |
| `references/adr-template.md` | adr MADR 4.0 템플릿 |
| `references/adr-review-checklist.md` | adr agent-readiness 게이트 |
| `references/audience-tone.md` | 비전공자 친화 톤 정책·비유 사전 |
| `references/portfolio-templates.md` | STAR/면접/회고 템플릿 상세 |
| `references/usage-guide.md` | 포괄 사용 가이드 (긴 버전) |
| `references/quick-start.md` | 이 문서 (빠른 참조) |
