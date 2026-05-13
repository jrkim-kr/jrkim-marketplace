---
name: roundtable
description: Use when a PRD/design spec/RFC needs critique from a multi-role roundtable before implementation. Convenes 4-6 personas (backbone PM+CTO+Growth, domain 1-2, optional triggers CSO/Designer/CEO) for 3 rounds (opinion → rebuttal → synthesis). Output is transcript.md, decisions.md, spec_v2.md. Trigger on '라운드 테이블', 'roundtable', 'PRD 회의', '스펙 평가 회의', 'multi-persona review'.
---

# Roundtable

PRD·spec·RFC 를 다역할 라운드테이블이 **3 라운드 회의**로 비평·개선하는 스킬. 평등한 다자 참여, 순차 발언, anchoring-rich(서로 듣고 반박). `arch-council`(추상 4-voice 병렬)과 구분.

## When to Use

- ✅ `superpowers:brainstorming` 이 design spec 만든 후, `writing-plans` 직전
- ✅ PRD 가 도메인 특화 sanity check 필요할 때
- ❌ 단일 기술 결정 → `architect-advisor:arch-council`
- ❌ 코드 리뷰 → `superpowers:requesting-code-review`

## Inputs

- PRD/spec 파일 경로 (기본: 최신 `docs/superpowers/specs/YYYY-MM-DD-*-design.md`)
- (선택) 도메인 힌트 (예: "education", "fintech")

## Outputs

```
roundtable-output/<YYYY-MM-DD-HHmm>/
├── transcript.md      # 회의 전문 (R1·R2 + R3 합성 노트)
├── decisions.md       # 합의 / 미해결 / 검증 / Phase / §5 verification
└── spec_v2.md         # 합의 적용된 개선판
```

## 회의 인원

- **Backbone (3 인 고정)**: PM · CTO · Growth — 모든 PRD 에 가치 있음
- **Domain (1-2 인)**: 사용자 구조 기반
- **Trigger (0-3 인)**: critical 시 자동 추가 (CSO·Designer·CEO)
- **실제 범위**: 4-6 인 (극단 7-8 인)

## Process

### Step 1: Persona Plan (메인 Claude, subagent 미사용)

메인 Claude가 PRD 읽고 다음 4 개 질문에 답해 persona list 도출:

```python
backbone = [PM, CTO, Growth]    # 항상 3 인

# Q1: 사용자 구조 → domain 인원
if 단边 SaaS or 내부도구:
    domains = pick(1, "주 사용자")
elif 다 stakeholder B2B SaaS (사용자 ≠ 결정자):  # clinic·학원·미용실 등 SMB 운영 도구
    domains = pick(2, "주 사용자 + 결정자/구매자")
else:  # 양면 / 다중 생태계 / 개발자 대상
    domains = pick(2, "양측 대표")

# Q2-Q4: Critical trigger (자동 추가, 인원 제한 없음)
triggers = []
if PII 다량 or 미성년 or 결제 or 의료/금융:    triggers += [CSO]
if toC and 가치 핵심 = UX:                    triggers += [Designer]
if PRD 에 "or/vs/미정/검토중" 5+회:           triggers += [CEO]

# Follow-up flags (persona 召唤 안 함, 사용자에게 알림)
if IP·약관·미성년 동의 critical:    flag("法务 자문 follow-up")
if 다 팀·24/7·SLA critical:        flag("운영 ADR/인계 문서 권장")

main = backbone + domains + triggers
```

**도메인 매핑**:

| 사용자 구조 | domain | 매핑 |
|---|---|---|
| 단일 사용자 층 | 1 | 주 사용자 |
| 내부 도구 | 1 | 주 사용자 |
| 다 stakeholder B2B SaaS (clinic·학원·미용실 등) | 2 | 주 사용자 + 결정자/구매자 |
| 양면 플랫폼 | 2 | 판매측 + 구매측 |
| 다중 역할 생태계 | 2 | 핵심 생산자 + 핵심 소비자 |
| 개발자 대상 | 2 | 타깃 개발자 + 통합 파트너 |

**인원 시나리오**:

| 사용자 구조 | trigger 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 단边/내부 | 4 인 | 5 | 6 | 7 |
| 양면/생태계/개발자 | 5 인 | 6 | 7 | 8 |

대부분 프로젝트 **4-6 인**.

**사용자에게 제시 형식**:

```
## Roundtable Plan

- Backbone: PM·CTO·Growth (3 인)
- Domain: <역할들> (<n> 인, 사용자 구조: <구조>)
- Trigger: <CSO/Designer/CEO if any> (<n> 인)
- 총 <N> 인

## 사용자 follow-up (회의 후)
- 법무: <항목 if critical>
- 운영: <항목 if critical>

진행 / 수정 / 취소?
```

### Step 2: User Confirmation

Step 1 plan 제시 후 진행 승인. 사용자가 토큰 절약 이유로 페르소나 빼면 누락 영역을 명시적으로 confirm (예: "Designer 빼면 UX critical 누락 — OK?").

### Step 3: 도메인 페르소나 로드/생성

- `personas/domains/<domain>/<role>.md` 존재 시 → 로드
- 없으면 → 메인 Claude가 PRD 읽고 즉석 생성 + 동일 경로 저장 (재사용 캐시)
- 포맷: `정체성·배경·말투·가치관·관심 영역·약점·토론 스타일`

### Step 4: 3-Round 회의 실행

**원칙**: 메인 Claude는 transcript 본문을 직접 읽지 않음. 각 서브에이전트 호출 후 한 줄 요약만 받음.

#### Round 1 — 개진 (Opening)
- N 명 순차 호출 (general-purpose subagent)
- 각자 PRD + 본인 soul.md + 현재까지 transcript 읽고 핵심 우려·개선점 3-5 개 발언
- 발언 후 transcript.md 에 append
- 분량: 200-350 단어
- 발언 순서: PM → CTO → Growth → (trigger persona) → 도메인1 → 도메인2

#### Round 2 — 반박 (Cross-examination)
- 역순 호출
- 각자 Round 1 transcript 전체 읽고 동의·반박·질문
- **메인 Claude가 어떤 충돌이 중요한지 사전 선별하지 않음**
- 각 페르소나가 자기 판단으로 반박할 지점 선택

#### Round 3 — 합성 (Synthesis)
- Synthesizer 서브에이전트 1 회 호출
- 입력:
  - transcript 전체
  - 원본 spec
  - **`~/.claude/skills/roundtable/completeness-checklist.md`** (필수 — 7 类別 verifier)
  - (있으면) `architect-advisor/*/patterns/CONFLICT_PATTERNS.md`
- 출력 3 종:
  - `decisions.md`: 합의 / 미해결 충돌 / 추가 검증 / Phase 재배치 / **§5 Category Coverage Verification** (7 类別 plan vs actual 비교, 누락 시 회의 결함으로 표시)
  - `spec_v2.md`: 합의 적용된 개선판 (원본 보존)
  - transcript 에 "Round 3 합성 노트" append
- **금지**: transcript 에 없는 내용 만들지 말 것. checklist 는 detector 이지 generator 가 아님.

### Step 5: User Review

3 산출물 제시 후 사용자 결정:
- 수용 → `superpowers:writing-plans`
- 미해결 기술 결정 → `architect-advisor:arch-council`
- 미해결 가치 판단 → 사용자 직접 결정 후 `arch-adr` 로 기록

## Persona Pool

### 고정 페르소나 (`personas/fixed/`)

| 파일 | 페르소나 | 역할 |
|---|---|---|
| `pm.md` | 김프로 (PM) | Backbone — 완결성·MVP·엣지케이스·YC forcing questions |
| `cto.md` | 이테크 (CTO) | Backbone — 아키텍처·실현성·가정 가시화·ADR·DDD |
| `growth.md` | 박그로 (Growth) | Backbone — 시장·CAC·LTV·GTM·BM·K-factor |
| `cso.md` | 정세큐 (CSO) | Trigger (보안 critical) — STRIDE·CVSS·ISMS-P |
| `designer.md` | 윤디자 (Designer) | Trigger (UX critical) — IA·0-10 점수·AI slop |
| `ceo.md` | 강대표 (CEO) | Trigger (방향 unstable) — 10x·scope 4-mode |

### 도메인 페르소나 (`personas/domains/<domain>/`)

프로젝트별 동적 생성·재사용. 예시:
- `domains/education/teacher-exam-author.md`
- `domains/education/academy-director.md`

## 원칙

- **충돌 사전 선별 금지**: 메인 Claude가 어떤 발언이 중요한지 미리 판단하지 않음. Synthesizer 가 transcript 전체 읽고 판단
- **3 라운드 완주**: Round 2 생략 금지. 첫 라운드 발언자는 자기가 뭘 놓쳤는지 모름
- **도메인 > 추상**: 도메인 페르소나 발언이 가장 큰 가치를 만들 때가 많음. 토큰 절약 이유로 빼지 말 것
- **분류는 召唤 전에**: 잘못된 페르소나 = 라운드 낭비. Step 1 의 4 개 질문 답하면 끝

## 관련 스킬

- **선행**: `superpowers:brainstorming` (요구사항 추출)
- **후행**: `superpowers:writing-plans` (구현 계획)
- **보완**: 
  - `architect-advisor:arch-council` (단일 기술 결정의 4-voice anchoring-free 비교)
  - `architect-advisor:arch-adr` (미해결 충돌의 결정 기록)
- **참조**: `architect-advisor:arch-err-pattern` (CONFLICT_PATTERNS.md 생성)
