# Architect Advisor — 포괄적 사용 가이드

## 목차

1. [개요](#1-개요)
2. [플러그인 구조](#2-플러그인-구조)
3. [빠른 시작](#3-빠른-시작)
4. [메인 워크플로우: /architect-advisor](#4-메인-워크플로우)
5. [독립 스킬: /term-glossary](#5-독립-스킬-term-glossary)
6. [워크플로우 상태 추적](#6-워크플로우-상태-추적)
7. [Notion 연동](#7-notion-연동)
8. [실전 시나리오별 사용법](#8-실전-시나리오별-사용법)
9. [산출물 활용법](#9-산출물-활용법)
10. [트러블슈팅](#10-트러블슈팅)

---

## 1. 개요

### 이 스킬은 누구를 위한 것인가

Chloe처럼 **AI 아키텍트/시니어 PM으로 성장하려는 개발자**를 위한 스킬이다. 비즈니스 기능 모듈을 제안하면, 시니어 아키텍트가 옆에 앉아 함께 설계하듯 5가지를 자동으로 해준다:

1. 시스템을 쪼개고 시각화
2. 두 가지 방안을 비교해서 의사결정 지원
3. 극단적 상황을 미리 시뮬레이션
4. 기술 용어를 한/중/영 3개 국어로 정리
5. 면접에서 바로 쓸 수 있는 포트폴리오 케이스 자동 생성

### 설계 패턴 (Anthropic Agent Patterns)

```
┌───────────────────────────────────────────────────────────────┐
│  🔄 용어 번역 레이어 (Parallelization — 항상 활성)            │
└───────────────────────────────────────────────────────────────┘
         ↕            ↕           ↕           ↕            ↕
   ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
   │ decompose  │→│ council  │→│adr│→│ audit  │→│ portfolio  │
   │시스템 분해│ │의사결정   │ │ADR 기록 │ │리스크 감사│ │커리어 자산│
   └──────────┘ └──────────┘ └─────────┘ └──────────┘ └──────────┘
   Chaining      Evaluator-   Persistence Routing      Chaining
                 Optimizer    (agent spec) (6 domains)
                      ↑___________________|
                      (재검토 루프 시 council으로 회귀)
```

| 패턴 | 적용 위치 | 역할 |
|------|----------|------|
| **Prompt Chaining** | decompose → council → adr → audit → portfolio | 순차 실행 + 체크포인트 게이트 |
| **Parallelization** | 용어 횡단 레이어 | 모든 step에서 용어를 병렬 수집/번역 |
| **Evaluator-Optimizer** | council ↔ 3 | 리스크가 방안을 뒤집을 수 있는 피드백 루프 |
| **Persistence** | adr (ADR) | 결정을 "에이전트가 읽어 실행할 수 있는 스펙"으로 고정 |
| **Routing** | audit 도메인 감사 | 결제/실시간/재고/인증/통합/범용별 맞춤 시나리오 |

---

## 2. 플러그인 구조

```
architect-advisor/
├── SKILL.md                          # 메인 스킬 (5단계 하이브리드 워크플로우)
├── skills/
│   ├── arch-decompose/SKILL.md       # decompose 독립 호출
│   ├── arch-council/SKILL.md        # council 독립 호출
│   ├── arch-audit/SKILL.md           # audit 독립 호출
│   ├── arch-portfolio/SKILL.md       # portfolio 독립 호출
│   └── term-glossary/SKILL.md        # /term-glossary 독립 호출
├── scripts/
│   ├── workflow-state.py             # step 상태 + 용어 수집 추적
│   ├── new_adr.py                    # adr 파일 생성기
│   └── notion-term-sync.py           # Notion DB 동기화
├── hooks/                            # (향후 자동 훅 추가 가능)
├── evals/                            # 평가 데이터
└── references/
    ├── adr-template.md               # adr 템플릿 (MADR 4.0 기반)
    └── usage-guide.md                # 이 파일
```

### 산출물 디렉터리 레이아웃

모든 step 산출물은 프로젝트 루트의 `architect-advisor/<project>/` 트리에 저장된다.

```
[프로젝트 루트]/
└── architect-advisor/
    └── <project>/                    # 프로젝트명(예: payment-system)
        ├── state/
        │   └── workflow.json         # step 전환/결정/용어 누적 기록
        ├── decompose/         # 토폴로지, 상태 머신, Blast Radius
        ├── council/          # 방안 비교 테이블, 추천 근거
        ├── adr/             # NNNN-title.md ADR 파일 (MADR 4.0)
        ├── audit/             # 도메인별 리스크 시나리오 & 대응
        ├── portfolio/         # STAR 케이스, 면접 요약, 회고
        └── glossary/                 # 누적 용어집 (한/중/영)
```

### 컴포넌트 관계도

```
사용자 입력
    │
    ├─── "/architect-advisor 결제 시스템 설계해 줘"
    │         │
    │         ▼
    │    ┌─────────────────┐
    │    │ SKILL.md (메인)      │──→ workflow-state.py (상태 기록)
    │    │ decompose → council → adr → audit → portfolio   │──→ new_adr.py (adr 생성)
    │    │                     │──→ 용어 횡단 레이어 (인라인)
    │    └─────────────────────┘
    │         │ portfolio 완료 시
    │         ▼
    │    누적 용어집 자동 생성 ──→ notion-term-sync.py (선택)
    │
    ├─── "/term-glossary 멱등성, Saga 패턴"
    │         │
    │         ▼
    │    ┌──────────────────┐
    │    │ term-glossary     │──→ 즉시 용어 카드 생성
    │    │ (독립 스킬)       │──→ notion-term-sync.py (선택)
    │    └──────────────────┘
    │
    └─── "현재 진행 상태 보여줘"
              │
              ▼
         workflow-state.py show ──→ JSON 상태 출력
```

---

## 3. 빠른 시작

### 가장 기본: 한 줄로 시작

```
/architect-advisor 우리 쇼핑몰에 결제 시스템 만들어야 해
```

이것만으로 5단계 워크플로우가 자동 시작된다. 자연어로도 트리거된다:

```
결제 모듈 아키텍처 리뷰해 줘
실시간 채팅 시스템 설계 도와줘
재고 관리에서 동시성 버그가 있는데 아키텍처를 다시 잡아줘
```

### 용어만 빠르게 정리

```
/term-glossary 멱등성, 서킷브레이커, Saga 패턴, CQRS
```

### 대화에서 나온 용어 자동 추출

```
/term-glossary
```
(인자 없이 호출하면 현재 대화에서 기술 용어를 자동 추출)

---

## 4. 메인 워크플로우

### decompose: 시스템 분해 & 토폴로지

**트리거**: 워크플로우 시작 시 자동

**산출물 4가지**:
1. Mermaid 토폴로지 다이어그램
2. 노드 간 데이터 프로토콜(입력/출력/검증 규칙)
3. 핵심 엔티티 상태 머신(가능/불가능 전이 명시)
4. 모듈 결합 관계 + Blast Radius 분석

**체크포인트에서 할 수 있는 것**:
- "노드 X를 분리해 줘" → 토폴로지 수정
- "상태 Y를 추가해 줘" → 상태 머신 수정
- "괜찮아, 다음으로" → council 진행

### council: 의사결정 & 트레이드오프

**산출물**:
- 방안 A(MVP) vs 방안 B(견고한 아키텍처) 비교 테이블
- 아키텍트 추천 + 근거
- 멱등성/데이터 일관성 필수 감사

**체크포인트에서 할 수 있는 것**:
- "방안 B로 갈게" → 확정(拍板), audit 진행
- "방안 A인데 X만 보강하고 싶어" → 하이브리드 방안 설계
- "아직 모르겠어, 좀 더 설명해 줘" → 추가 분석

**중요**: 방안 확정 전까지 구체적인 비즈니스 코드가 출력되지 않는다. 의사코드/다이어그램만 허용.

### adr: ADR 기록 (에이전트 가독 스펙)

**트리거**: council 확정(拍板) 직후 자동

**역할**: council의 결정을 **코딩 에이전트가 추가 질문 없이 바로 구현**할 수 있는 실행 스펙(executable spec)으로 고정한다. MADR 4.0 기반 ADR 파일을 `architect-advisor/<project>/adr/NNNN-title.md` 형식으로 생성한다.

**산출물**:
- ADR 파일 (status / council-makers / consulted / informed 메타데이터 포함)
- Implementation Plan (영향 경로, 의존성, 따라야 할 패턴, 피해야 할 패턴, 설정 변경, 마이그레이션 절차)
- Verification (에이전트가 테스트·grep·명령어로 확인 가능한 체크리스트)

**생성 방법**:

```bash
python3 scripts/new_adr.py "결제 시스템에 Saga 패턴 도입"
```

**왜 필요한가**: "방안 B로 가자"는 합의만으로는 다음 에이전트가 일할 수 없다. 영향 파일, 금지 패턴, 검증 기준까지 명시해야 구현 중 드리프트가 생기지 않는다.

### audit: 이상 경로 감사

**도메인 라우팅 자동 적용**:

| 도메인 | 자동 감지 키워드 | 핵심 시나리오 |
|--------|-----------------|-------------|
| 결제/정산 | 결제, 환불, PG, 정산 | 중복 결제, 금액 위변조, PG 장애 |
| 실시간 통신 | 채팅, WebSocket, 메시지 | 연결 끊김, 메시지 유실, 순서 역전 |
| 재고/자원 | 재고, 주문, 동시성 | 음수 재고, 데드락, 캐시-DB 불일치 |
| 인증/권한 | 로그인, 토큰, 권한 | 토큰 탈취, 권한 상승, 세션 고정 |
| **모듈 통합(Integration)** | 모듈 간 의존, 계약, 마이그레이션 | 계약 위반, 순환 의존, 부분 배포, 블래스트 레이디어스 전파 |
| 범용 | (위 도메인 미감지 시 폴백) | SPOF, 백프레셔, 재시도 폭주, 관측성 누락 |

**Evaluator-Optimizer 루프**:

감사 중 선택한 방안에 구조적 한계가 발견되면, 자동으로 방안 재검토를 제안한다:

```
⚠️ 방안 재검토 제안
audit 결과, 방안 A가 [시나리오 X]를 구조적으로 해결하지 못합니다.
council으로 돌아가서 재검토할까요?
```

- "council으로 돌아가자" → 방안 재선택
- "이대로 가되 보완해 줘" → 보완 설계 추가 후 portfolio 진행

### portfolio: 커리어 자산 자동화

**자동 생성되는 4가지**:
1. **STAR 케이스 스터디** — 면접에서 바로 사용 가능한 아키텍처 의사결정 사례
2. **30초 면접 요약** — 한국어 + 中文 이중언어
3. **누적 용어집** — 워크플로우 전체에서 수집된 모든 기술 용어
4. **회고(Retrospective)** — Keep / Problem / Try / Revisit / Knowledge Gap 5축 회고. 다음 프로젝트로 이전할 교훈과 재방문이 필요한 결정을 명시한다.

---

## 5. 독립 스킬: /term-glossary

architect-advisor 워크플로우 없이도 용어 정리만 독립적으로 사용할 수 있다.

### 사용법

```bash
# 특정 용어 즉시 정리
/term-glossary 멱등성, 서킷브레이커, Saga 패턴

# 현재 대화에서 자동 추출
/term-glossary

# 중국어로 질문해도 OK
/term-glossary 幂等性, 断路器, 分布式锁
```

### 용어 카드 출력 형식

각 용어는 **한국어 블록 + 中文 블록**으로 출력된다:

```
### 서킷 브레이커 (断路器 / Circuit Breaker /ˈsɜːrkɪt ˈbreɪkər/)

#### 한국어 설명
**비유**: 전기 과부하 시 자동으로 내려가는 두꺼비집과 같다.
**기술 정의**: 외부 서비스 장애를 감지하면 호출을 차단하여 전체 장애 확산을 방지하는 패턴.
**적용 사례**: 결제 PG 서버가 응답하지 않을 때, 일정 횟수 실패 후 자동으로 차단하고 폴백 처리.

#### 中文说明
**类比**：就像电路过载时保险丝自动断开，防止火灾蔓延。
**技术定义**：检测到外部服务故障后自动中断调用，防止故障扩散到整个系统的模式。
**应用案例**：当支付PG服务器无响应时，失败达到阈值后自动熔断并执行降级方案。
```

### 출력 옵션

| 옵션 | 사용법 |
|------|--------|
| 대화 내 출력 (기본) | `/term-glossary Saga 패턴` |
| 파일 저장 | "파일로 저장해 줘" 추가 요청 → `architect-advisor/<project>/glossary/` 하위 |
| Notion 동기화 | "노션에도 저장해 줘" 추가 요청 |

---

## 6. 워크플로우 상태 추적

### 왜 필요한가

긴 워크플로우에서 대화가 끊기거나, 다음 날 이어서 작업할 때, 어디까지 했는지 추적할 수 있다.

### 자동 추적 (워크플로우 중)

architect-advisor 워크플로우 실행 시, 각 step 전환마다 자동으로 상태를 기록한다:

```json
{
  "project": "결제시스템",
  "current_step": "council",
  "steps": {
    "decompose": { "status": "completed", "started_at": "...", "completed_at": "..." },
    "council": { "status": "in_progress", "decision": null },
    "audit": { "status": "pending", "domain": null, "feedback_loop_count": 0 },
    "portfolio": { "status": "pending" }
  },
  "terms": [
    { "korean": "멱등성", "english": "Idempotency", "chinese": "幂等性", "steps": ["decompose", "council"] }
  ]
}
```

### 수동 명령어

| 명령 | 용도 |
|------|------|
| `python3 scripts/workflow-state.py init "프로젝트명"` | 새 워크플로우 시작 |
| `python3 scripts/workflow-state.py show` | 현재 상태 전체 출력 |
| `python3 scripts/workflow-state.py terms` | 수집된 용어 목록만 출력 |
| `python3 scripts/workflow-state.py step <name> completed` | step 수동 완료 처리 |
| `python3 scripts/workflow-state.py council b "이유"` | 방안 확정 기록 |
| `python3 scripts/workflow-state.py reset` | 상태 초기화 |

### 상태 파일 위치

```
[프로젝트 루트]/architect-advisor/<project>/state/workflow.json
```

---

## 7. Notion 연동

### 초기 설정

1. Chloe의 기술 용어 Notion DB URL을 확인한다
2. URL에서 DB ID를 추출한다 (예: `307ffa74a2ce80d192dce...`)

### 사용법

**워크플로우 완료 후 동기화**:
```
워크플로우 끝났으니 노션에 용어 정리해 줘
```
→ Claude가 DB ID를 확인하고, `notion-term-sync.py`를 실행하여 MCP 도구로 페이지 생성

**미리보기 (실제 저장 없이)**:
```bash
python3 scripts/notion-term-sync.py --db-id <DB_ID> --dry-run
```

**특정 step 용어만 동기화**:
```bash
python3 scripts/notion-term-sync.py --db-id <DB_ID> --step <name>
```

### Notion 페이지 형식

각 용어가 하나의 페이지로 생성된다:

```
제목: 멱등성 (Idempotency)

본문:
## 멱등성 (幂等性 / Idempotency)
**발음**: /ˌaɪ.dəmˈpoʊ.tən.si/

### 한국어 설명
**비유**: ...
**기술 정의**: ...

### 中文说明
**类比**: ...
**技术定义**: ...

**등장 Step**: decompose, council
```

---

## 8. 실전 시나리오별 사용법

### 시나리오 1: 새 기능 모듈 처음부터 설계

```
/architect-advisor 우리 앱에 실시간 채팅 기능을 추가하려고 해. 
그룹 채팅, 읽음 확인, 메시지 철회 지원하고 DAU 10만 정도.
```

→ decompose~4 전체 실행. 각 체크포인트에서 확인/수정 요청 가능.

### 시나리오 2: 기존 시스템 아키텍처 리뷰

```
/architect-advisor 지금 재고 관리에서 동시 주문 처리할 때 
재고가 마이너스로 가는 버그가 있어. 아키텍처를 다시 잡아줘.
```

→ decompose에서 현재 문제의 토폴로지를 분석하고, council에서 해결 방안 비교, audit에서 Race Condition 등 동시성 시나리오 집중 감사.

### 시나리오 3: 면접 준비만 하고 싶을 때

이전에 워크플로우를 실행한 적이 있다면:
```
이전에 했던 결제 시스템 설계를 기반으로 면접 케이스만 다시 만들어 줘
```

### 시나리오 4: 용어만 빠르게 공부

```
/term-glossary CAP 정리, BASE, ACID, 2PC, Saga, CQRS, 이벤트 소싱
```

→ 7개 용어를 한/중 이중 언어 카드로 즉시 정리.

### 시나리오 5: 대화 중간에 용어 추출

설계 논의가 끝난 뒤:
```
/term-glossary
```

→ 지금까지 대화에서 나온 기술 용어를 자동 추출하여 정리.

### 시나리오 6: 중국어로 질문

```
实时聊天功能需要设计一下。要支持群聊、已读回执和消息撤回。
```

→ 중국어 입력이지만 한국어로 출력. 전문용어는 한/중/영 3개 국어 병기.

### 시나리오 7: council에서 결정을 못 내리겠을 때

```
두 방안의 차이가 잘 안 와닿아. 좀 더 구체적으로 설명해 줘.
```

→ 추가 분석과 비유를 제공. 확정할 때까지 기다린다.

### 시나리오 8: audit에서 방안을 바꾸고 싶을 때

```
방안 A를 선택했는데, 감사 결과를 보니 방안 B가 나을 것 같아. 돌아가자.
```

→ Evaluator-Optimizer 루프 작동. council으로 돌아가서 방안 B 기준으로 재설계.

---

## 9. 산출물 활용법

### 면접 활용

| 산출물 | 면접 활용 |
|--------|----------|
| STAR 케이스 | "가장 어려웠던 기술적 의사결정을 설명해주세요" 대답 |
| 30초 한국어 요약 | 한국 회사 면접 엘리베이터 피치 |
| 30초 중문 요약 | 중국 회사 면접 엘리베이터 피치 |
| 비교 테이블 | "왜 그 기술을 선택했나요?" 근거 제시 |
| 리스크 감사 | "예상 가능한 장애 상황에 어떻게 대비했나요?" 대답 |

### 기술 문서 활용

| 산출물 | 문서 활용 |
|--------|----------|
| Mermaid 토폴로지 | README, 설계 문서의 아키텍처 다이어그램 |
| 상태 머신 | API 문서의 상태 전이 설명 |
| 데이터 프로토콜 | API 스펙 문서 |
| 결합 관계 분석 | 온보딩 문서, 팀 핸드오프 문서 |
| 누적 용어집 | 팀 위키, 신규 입사자 온보딩 |

### Notion 활용

- 용어 DB가 쌓이면 → 기술 면접 단어장으로 활용
- Step별 등장 태그로 → 도메인별 핵심 용어 필터링

---

## 10. 트러블슈팅

### Q: 워크플로우 중간에 대화가 끊겼어요

```
python3 scripts/workflow-state.py show
```
→ 현재 step와 수집된 용어를 확인하고, 이어서 진행 요청:
```
council까지 했었어. 결제 시스템 설계 이어서 해줘.
```

### Q: audit 시나리오가 내 도메인과 안 맞아요

```
이건 결제 시스템이 아니라 IoT 디바이스 관리 시스템이야.
센서 데이터 유실, 디바이스 오프라인, 펌웨어 업데이트 실패 같은 시나리오를 봐줘.
```
→ 도메인 라우팅이 "범용"으로 감지한 경우, 수동으로 도메인 힌트를 줄 수 있다.

### Q: 코드를 먼저 보여줘

```
코드 금지 해제해 줘. 의사코드가 아니라 실제 코드로 보여줘.
```
→ council 확정 후에는 코드 출력 가능. 확정 전이라면 왜 로직 우선인지 설명 후, 강하게 요청하면 해제.

### Q: 용어 정리가 너무 길어요

```
핵심 용어 5개만 골라서 정리해 줘
```
→ 가장 중요한 용어만 선별하여 정리.

### Q: Notion 동기화가 안 돼요

1. MCP Notion 도구가 활성화되어 있는지 확인
2. DB ID가 올바른지 확인 (URL에서 추출)
3. `--dry-run`으로 미리보기 후 문제 파악:
```bash
python3 scripts/notion-term-sync.py --db-id <DB_ID> --dry-run
```

### Q: 영어/중국어로 출력하고 싶어요

```
이번에는 전체를 중국어로 출력해 줘
```
→ 기본은 한국어이지만, 명시적으로 요청하면 출력 언어 변경 가능.
