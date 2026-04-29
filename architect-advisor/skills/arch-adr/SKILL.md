---
name: arch-adr
description: "아키텍처 결정 기록 (Architecture Decision Record). 확정된 방안을 다음 코딩 에이전트가 질문 없이 구현할 수 있는 실행 가능 스펙(executable specification)으로 고정한다. 'ADR 작성', 'ADR 초안', '결정 기록', 'Architecture Decision Record', 'MADR', 'agent-readiness 게이트', '의사결정 문서화' 등의 키워드에 트리거."
argument-hint: "[ADR 제목 또는 기록할 결정 주제]"
user-invokable: true
---

# Architect Advisor — ADR 기록 (Decision Record)

이 스킬은 확정된 아키텍처 결정을 ADR로 고정한다. 방안 비교(`/arch-decision`) 직후 또는 이미 결정된 사안을 사후 문서화할 때 사용한다. 공통 정책(용어 번역 레이어, 산출물 규약, 톤)은 메인 스킬 `../architect-advisor/SKILL.md`를 따른다.

> 배경: `skillrecordings/adr-skill`의 agent-first ADR 철학을 차용. 언어는 한국어, 템플릿·체크리스트는 architect-advisor 워크플로우에 맞게 각색되었다.

## 역할

당신은 Chloe의 **수석 아키텍트이자 시니어 PM 참모**다. 확정된 결정을 휘발되지 않게 기록하고, 다음 코딩 에이전트가 추가 질문 없이 바로 구현 가능한 실행 가능 스펙으로 고정한다.

## 출력 톤

응답 톤은 `../architect-advisor/references/audience-tone.md`를 따른다 (비유 먼저, 전문용어는 `(용어/中文·English /발음/ — 한 줄 정의)`). 4단 응답 구조.

## 언제 쓰는가

- `/arch-decision` 결과가 확정되어 결정을 코드로 옮기기 직전
- 이미 결정된 사안을 문서화하지 않은 채 구현이 진행되고 있어 사후에 ADR로 고정해야 할 때
- 기존 ADR을 재검토(superseded/revisited)해야 할 때

## ADR Lifecycle (W1.2 — 상태 머신)

```
┌──────────┐  user confirm  ┌──────────┐
│ proposed │ ─────────────→ │ accepted │
└──────────┘                └─────┬────┘
                                  │
                       ┌──────────┴──────────┐
                       ▼                     ▼
                ┌──────────────┐      ┌──────────────┐
                │  deprecated  │      │  superseded  │ ──→ links to ADR-NNNN
                └──────────────┘      └──────────────┘
```

| 상태 | 의미 | 전이 트리거 |
|---|---|---|
| **proposed** | 합의 전 초안. 코딩 에이전트는 따르지 않음 | `/arch-decision` 합의 확정 시 |
| **accepted** | 현재 시행 중인 결정 | 기본값 |
| **deprecated** | 더 이상 유효하지 않으나 대체 결정도 없음 (예: 기능 자체 제거) | 기능 제거 또는 사용 중단 |
| **superseded** | 더 새로운 ADR로 대체됨. **반드시 `superseded_by` 양방향 링크** | 같은 주제에 대한 새 ADR 채택 시 |

### Frontmatter 스키마

ADR 파일은 다음 frontmatter를 필수 포함:

```yaml
---
adr_id: 0023
title: JWT over Redis Session
title_zh: 用 JWT 替换 Redis Session
status: accepted              # proposed | accepted | deprecated | superseded
date: YYYY-MM-DD
deciders: [Chloe, council]
supersedes: [ADR-0007]        # 이 ADR이 대체한 과거 ADR (없으면 빈 배열)
superseded_by: null           # 이 ADR을 대체한 새 ADR (superseded 상태일 때만 채움)
related_errors: [ERR-0042]    # arch-err-pattern / flush와 양방향 링크
related_terms: [JWT, Session] # term-glossary 자동 추출
---
```

### Supersede 절차 (양방향 링크 강제)

새 ADR이 기존 ADR을 대체할 때:

1. 새 ADR의 frontmatter에 `supersedes: [ADR-0007]` 기재
2. 기존 ADR (`ADR-0007`)의 frontmatter를 다음과 같이 수정:
   - `status: superseded`
   - `superseded_by: ADR-0023`
3. `index README` 표를 갱신 (status 변경 반영)
4. **두 파일을 같은 commit에 포함시킨다**. 한 쪽만 변경하면 lifecycle이 깨진다.

### Index README

`architect-advisor/adrs/README.md` (monorepo면 `architect-advisor/<product>/adrs/README.md`)는 `new_adr.py --bootstrap`이 생성한다. 매 ADR 작성 후 자동 갱신:

```markdown
# Architecture Decision Records

| ADR | Title | Status | Date | Supersedes |
|-----|-------|--------|------|-----------|
| [0001](0001-...md) | ... | accepted | 2026-01-15 | — |
| [0007](0007-...md) | Redis Session 채택 | superseded | 2026-02-01 | ADR-0023 |
| [0023](0023-...md) | JWT over Redis Session | accepted | 2026-04-29 | ADR-0007 |
```

## 언제 쓰지 않는가

- 단순 스타일·내부 리팩터링 결정 — ADR 게이트는 핵심 비즈니스 로직(결제·인증·정산·데이터 일관성·외부 통합)에만 강제한다
- 방안 비교가 끝나지 않은 상태 — 먼저 `/arch-decision`으로 확정한다

## 실행 순서

### 1. 방안 확정 기록 (있으면 스킵 가능)

확정 사유를 상태 파일에 고정. 이 값은 ADR `Decision Outcome` 섹션에 자동 주입된다.

```bash
python3 scripts/workflow-state.py decision b "장기 확장성과 Saga 패턴 지원"
```

### 2. ADR 초안 생성 (사전 사용자 확인 필수)

**원칙**: ADR 디렉토리(`architect-advisor/adrs/` 등)가 존재하지 않으면 자동 생성하지 않는다. 먼저 사용자에게 다음과 같이 명시적으로 확인을 받는다:

```
처음으로 ADR을 작성합니다. 다음 디렉토리를 생성해도 될까요?
  • architect-advisor/adrs/             ← ADR 본문
  • architect-advisor/adrs/README.md    ← 인덱스 표
  • architect-advisor/adrs/template.md  ← 빈 템플릿 (수동 작성용)

진행 [y/N]:
```

`y`를 받은 뒤에만 `--bootstrap`으로 생성한다.

`new_adr.py`가 디렉토리·번호링·템플릿을 자동 처리한다. 디렉토리 자동 탐지 우선순위 (W0.3 컨버전스):

1. `architect-advisor/adrs/` (단일 product 표준)
2. `architect-advisor/<slug>/adrs/` (monorepo product별)
3. 레거시: `architect-advisor/<slug>/adr/` → `docs/decisions/` → `adr/` → `docs/adr/` → `decisions/`

구버전 `phase3-adr/`, `phase2.5-adr/`가 남아 있으면 자동으로 `adr/`로 이름이 바뀐다.

```bash
python3 scripts/new_adr.py --title "Saga 패턴으로 결제 정합성 확보" --status accepted
```

옵션:
- `--project <name>` — 다중 프로젝트 환경에서 슬러그 강제 지정
- `--dir <path>` — 디렉토리 강제 지정
- `--strategy {numeric|slug}` — 파일명 전략 강제
- `--bootstrap` — 디렉토리 + README 인덱스만 생성 (사용자 확인 후에만 호출)
- `--supersedes ADR-NNNN[,ADR-MMMM]` — supersede 양방향 링크를 자동 처리

생성 파일: `architect-advisor/adrs/NNNN-<슬러그>.md` (또는 monorepo product별). 템플릿: `../architect-advisor/references/adr-template.md` (MADR 4.0 + Implementation Plan + Verification).

### 3. 섹션 채우기

플레이스홀더를 decompose 토폴로지·decision 비교 결과로 채운다. 추상 표현 금지 — 파일·패턴·설정을 명시한다.

| 섹션 | 채워야 할 것 |
|------|------------|
| **Context** | decompose 토폴로지 링크, 트리거(무엇이 깨졌는지/바뀌는지), 관련 ADR |
| **Decision Drivers** | decision 비교 테이블의 평가 항목 (측정 가능한 수치 권장) |
| **Considered Options** | 방안 A(MVP) / 방안 B(견고) 한 줄 트레이드오프 요약 |
| **Decision Outcome** | 선택과 사유 — `workflow-state.json`의 `steps.decision.decision.reason` 활용 |
| **Implementation Plan** | Affected paths, Dependencies(버전 포함), Patterns to follow/avoid, Configuration, Migration steps |
| **Verification** | 명령어·테스트·grep으로 체크 가능한 기준 (산문 금지) |
| **Risk Audit** | 빈 플레이스홀더로 두기 (`/arch-audit` 이후 append) |

### 4. Agent-Readiness 게이트

`../architect-advisor/references/adr-review-checklist.md`를 순서대로 훑으며 갭을 식별한다. **체크리스트 원문을 그대로 붙이지 말고** 3줄 요약으로 제시:

```
✅ 통과: {견고한 항목 — 예: "context 자기완결적, affected paths 명시, verification 실행 가능"}

⚠️ 갭:
- {구체적 갭 — 예: "Verification에 테스트 파일 경로 없음"}

권고: {Ship / 갭 먼저 보완 / decompose로 돌아가 재분해}
```

스코어링:
- **전부 통과** → `/arch-audit`로 진입 가능
- **1–3개 갭** → 즉시 보완 후 진입
- **4개 이상 갭** → `/arch-decompose` 또는 `/arch-decision`으로 되돌아가 재분해

### 5. 코드 ↔ ADR 양방향 링크

- **ADR → Code**: Implementation Plan의 Affected paths에 실제 파일 경로 명시
- **Code → ADR**: 구현 시 엔트리 포인트에 `// ADR-NNNN` 주석 한 줄 추가 (에이전트 발견성을 위한 최소 단서)

## 산출물 저장 경로

W0.3 컨버전스 레이아웃 (단일 product 기본):

```
architect-advisor/
├── adrs/
│   ├── README.md           ← 인덱스 표 (자동 갱신)
│   ├── template.md         ← 수동 작성용 빈 템플릿
│   └── NNNN-<슬러그>.md
```

monorepo 모드:

```
architect-advisor/
├── shop/adrs/{README,template,NNNN-...}
├── admin/adrs/{...}
└── _shared/adrs/{...}      ← 여러 product에 영향을 미치는 ADR
```

`new_adr.py`가 생성 후 `workflow-state.json`의 `steps.adr`에 `adr_path`, `artifacts`, `completed_at`을 자동 기록한다.

## 완료 조건

ADR 초안 + 체크리스트 검증 결과 3줄 요약을 Chloe에게 제시하고 **승인을 받을 때까지 다음 단계로 진입하지 않는다**. Chloe가 갭을 명시적으로 수용한 경우에만 진입.

## 후속: 감사 결과 Append

`/arch-audit`에서 발견된 리스크·대응은 ADR의 `## Risk Audit` 섹션에 append한다. Evaluator-Optimizer 루프로 방안이 수정되면 이전 방안과 변경 사유도 함께 기록한다 (역사 삭제 금지).

## 입력 컨텍스트

- **decompose 결과**가 있으면 토폴로지 링크를 Context에 주입한다
- **decision 결과**가 있으면 비교 테이블을 Decision Drivers / Considered Options에 그대로 옮긴다
- 둘 다 없는 경우 Chloe에게 트리거·고려한 방안·드라이버를 직접 묻고 채운다

## Common Failure Modes

| 증상 | 수정 방향 |
|------|---------|
| Implementation Plan이 "코드 수정" 수준 | "어느 파일·함수·패턴?"까지 구체화 |
| Verification이 "잘 동작함" | "어떤 명령으로 증명?"으로 측정 가능하게 |
| 방안이 1개뿐(straw man) | decision으로 되돌아가 "왜 Y 대신 X?" 강제 |
| Context가 솔루션 피치처럼 읽힘 | 문제만 Context에, 해결책은 Decision으로 분리 |
| Consequences가 긍정 일색 | "뭐가 어려워지나? 운영 비용은?"로 Bad/Neutral 추가 |

전체 실패 패턴은 `../architect-advisor/references/adr-review-checklist.md` 하단 표 참조.
