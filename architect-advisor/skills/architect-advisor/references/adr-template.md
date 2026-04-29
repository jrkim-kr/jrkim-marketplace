---
status: "{proposed | accepted | rejected | deprecated | superseded by [ADR-NNNN](NNNN-title.md)}"
date: {YYYY-MM-DD}
decision-makers: "{의사결정 오너 리스트 — 拍板권자}"
consulted: "{자문을 구한 전문가 (two-way)}"
informed: "{결과를 공유할 이해관계자 (one-way)}"
source: "architect-advisor council step"
workflow-state: "architect-advisor/<project>/state/workflow.json"
---

# {ADR 제목 — 동사구, 문제가 아닌 "결정"을 서술}

> MADR 4.0 기반 템플릿. architect-advisor의 council step 확정 직후
> `scripts/new_adr.py`로 이 파일을 채워 생성한다. 본문은 한국어로 작성하되,
> 전문용어는 architect-advisor 횡단 레이어의 인라인 번역 규칙을 따른다
> (예: `멱등성(幂等性/Idempotency /ˌaɪ.dəmˈpoʊ.tən.si/ — 같은 요청을 여러 번
> 보내도 결과가 동일한 성질)`).

## Context and Problem Statement (맥락과 문제)

{decompose 분해 결과와 "왜 지금" 이 결정이 필요한지를 서술한다.
처음 이 ADR을 읽는 에이전트/동료가 추가 질문 없이 배경을 이해할 수 있어야 한다.
가능하면 질문 형태로 프레이밍하고, 관련 이슈/PR/선행 ADR을 링크한다.}

- **트리거(Trigger)**: {무엇이 깨졌는가 / 무엇이 바뀌는가 / 아무것도 하지 않으면 무엇이 깨지는가}
- **관련 ADR**: {선행 ADR 번호와 링크}
- **decompose 토폴로지 링크**: {Mermaid 다이어그램이 저장된 경로}

## Decision Drivers (결정 드라이버)

decompose에서 확인된 제약과 council 비교 테이블의 평가 항목을 그대로 옮긴다.

- {드라이버 1 — 예: 구현 난이도 제약 (2주 이내)}
- {드라이버 2 — 예: 멱등성 보장 필수}
- {드라이버 3 — 예: 분산 트랜잭션 데이터 일관성}

## Considered Options (고려한 방안)

council step에서 비교한 두 방안을 그대로 기재한다. 각 방안의 핵심 트레이드오프 한 줄 요약.

- **방안 A (MVP)** — {한 줄 요약}
- **방안 B (견고한 아키텍처)** — {한 줄 요약}

## Decision Outcome (결정)

**선택**: "{방안 B}", 사유: {핵심 드라이버와 트레이드오프를 근거로 서술}.

> architect-advisor `workflow-state.py`의 `steps.council.decision.reason`
> 필드를 그대로 사용하거나 확장한다.

### Consequences (결과)

- **Good** — {긍정적 결과 — 예: 분산 환경에서 데이터 일관성 확보}
- **Bad** — {부정적 결과 — 예: 운영 복잡도 증가, Saga 패턴 학습 비용}
- **Neutral** — {중립적 결과 — 예: 모니터링 대상 메트릭 증가}

## Implementation Plan (에이전트 구현 계획)

> 이 섹션은 다음 코딩 에이전트가 **추가 질문 없이 바로 구현**할 수 있을 만큼
> 구체적이어야 한다. 추상적인 표현("DB 코드 수정")이 아니라 **파일·패턴·
> 설정**을 명시한다.

- **Affected paths (영향 범위)**: {예: `src/payment/`, `src/db/outbox.ts`, `tests/integration/payment/`}
- **Dependencies (의존성)**: {추가/삭제/업데이트할 패키지와 버전 — 예: `add @sagajs/core@2.x, remove bull`}
- **Patterns to follow (따라야 할 패턴)**: {기존 코드 경로를 참조 — 예: `src/db/repositories/user.ts`의 리포지토리 패턴을 그대로 적용}
- **Patterns to avoid (피해야 할 패턴)**: {명시적으로 금지 — 예: 데이터 액세스 레이어 바깥에서 raw SQL 사용 금지}
- **Configuration (설정 변경)**: {env, config, feature flag — 예: `PAYMENT_SAGA_ENABLED=true`, `config/payment.ts`에 타임아웃 필드 추가}
- **Migration steps (마이그레이션)**: {교체인 경우 점진적 전환 계획 — 예: shadow write → dual read → 구 로직 제거}

### Verification (검증 기준)

에이전트가 테스트나 명령어로 **체크 가능한** 형태로 작성한다. 모호한 표현 금지.

- [ ] {예: `pnpm test:integration src/payment` 전부 pass}
- [ ] {예: `src/` 내부에 `pg` 직접 import가 `src/db/client.ts` 외에 존재하지 않음 (grep으로 검증)}
- [ ] {예: 결제 요청 p95 지연 < 300ms, 동시 요청 100개 기준}
- [ ] {예: 같은 idempotency key로 2회 호출 시 1건만 처리됨 (integration test 통과)}

## Risk Audit (리스크 감사 결과)

> architect-advisor `/arch-audit` 결과를 이 섹션에 append한다. Evaluator-Optimizer
> 루프로 방안이 수정된 경우, 이전 방안과 변경 사유를 함께 기록한다.

- **감지된 도메인**: {결제/실시간통신/재고/인증/범용 — 복합 도메인이면 복수 기재}
- **치명적 시나리오 & 대응**:
  - {시나리오 1 — 예: "PG 타임아웃 후 재시도로 중복 결제"}: {대응 — 예: "idempotency key + outbox 패턴"}
  - {시나리오 2 ...}
- **재검토 결과**: {유지 / 방안 수정 / 보완 설계 추가}

## Pros and Cons of the Options (방안 상세 비교)

### 방안 A (MVP)

{한 줄 설명 또는 council 비교 테이블 링크}

- Good — {argument}
- Bad — {argument}
- Neutral — {argument}

### 방안 B (견고한 아키텍처)

- Good — {argument}
- Bad — {argument}
- Neutral — {argument}

## More Information (더 읽을거리)

- **portfolio 산출물**: {STAR 케이스 스터디 / 면접 요약 링크}
- **누적 용어집**: {term-glossary 산출물 링크 또는 Notion URL}
- **재방문 트리거**: {이 ADR을 다시 열어야 할 조건 — 예: "월 결제 건수 100만 돌파 시 Saga 분리 여부 재검토"}
- **Step 전환 기록**: `architect-advisor/<project>/state/workflow.json`
