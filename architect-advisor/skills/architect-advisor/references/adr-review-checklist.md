# ADR Agent-Readiness Checklist (adr 게이트)

> architect-advisor council에서 방안이 확정(拍板)된 직후, `new_adr.py`로
> 생성한 ADR 초안이 **다음 코딩 에이전트가 질문 없이 바로 구현할 수 있는
> 상태**인지 검증한다. audit(리스크 감사)로 진입하기 전의 마지막 게이트다.
>
> 출처: `skillrecordings/adr-skill`의 `review-checklist.md`를 architect-advisor
> 워크플로우에 맞게 각색.

## 사용 방법

1. `new_adr.py`로 ADR 초안 생성
2. 이 체크리스트를 순서대로 훑으며 `[ ]` → `[x]` 표시
3. **Present the review as a summary**, not a raw checkbox dump. 형식:

   ```
   ✅ 통과: {견고한 항목 — 예: "context 자기완결적, affected paths 명시, verification 실행 가능"}

   ⚠️ 갭:
   - {구체적 갭 1 — 예: "Verification에 테스트 파일 경로 없음. 어느 테스트 슈트를 써야 하나?"}
   - {구체적 갭 2}

   권고: {Ship / 갭 먼저 보완 / decompose로 돌아가 재분해}
   ```

4. 갭이 있으면 Chloe에게 구체적 수정안을 제안한다. 문제만 나열하지 않는다.
5. 체크리스트 통과 또는 Chloe가 갭을 명시적으로 수용할 때까지 audit로 진입하지 않는다.

---

## Context & Problem (맥락)

- [ ] 사전 지식 없는 독자(에이전트 포함)가 왜 이 결정이 필요한지 이해할 수 있는가
- [ ] 트리거가 명확한가 (무엇이 깨졌는지 / 무엇이 바뀌는지)
- [ ] 부족지식(tribal knowledge) 없이 서술되었는가 — 약어 정의, 시스템 명시
- [ ] 관련 이슈/PR/선행 ADR 링크가 포함되었는가
- [ ] decompose 토폴로지 다이어그램 경로가 링크되어 있는가

## Decision (결정)

- [ ] "더 나은 방식을 쓴다"가 아니라 "X를 Y 용도로 쓴다"처럼 실행 가능한가
- [ ] 스코프 경계가 명확한가 — 포함/제외(non-goals) 모두
- [ ] 제약이 가능하면 측정 가능한 수치로 표현되었는가 (예: "< 200ms p95")
- [ ] council 비교 테이블의 드라이버가 사유에 반영되었는가

## Consequences (결과)

- [ ] 각 결과가 구체적이고 실행 가능한가 (희망사항이 아님)
- [ ] 후속 과제가 식별되었는가 (마이그레이션, 설정 변경, 문서, 신규 테스트)
- [ ] 리스크가 **완화 전략과 함께** 명시되었는가
- [ ] 결정을 위장한 재진술이 아닌가 ("Saga를 도입한다"가 Good에 반복되고 있지 않은가)

## Implementation Plan (핵심 — 에이전트가 바로 구현 가능한가)

- [ ] Affected paths가 **파일·디렉토리 단위**로 명시되었는가 (예: `src/db/client.ts`)
- [ ] 추가/삭제할 의존성과 버전이 지정되었는가 (예: `add @sagajs/core@2.x`)
- [ ] 따라야 할 패턴이 **기존 코드 경로를 참조**하는가 (추상 표현 금지)
- [ ] 피해야 할 패턴이 명시되었는가 (금지사항)
- [ ] 환경변수·feature flag·config 변경이 전부 나열되었는가
- [ ] 교체 결정인 경우 **점진적 마이그레이션 단계**가 서술되었는가

## Verification (검증 기준)

- [ ] 체크박스 형태인가 (산문 서술 금지)
- [ ] 각 항목이 테스트 가능한가 — 에이전트가 실행할 명령 또는 테스트를 떠올릴 수 있는가
- [ ] 기능 관점(works)과 구조 관점(it's done right) 모두 커버하는가
- [ ] 모호한 항목이 없는가 (예: "잘 동작함" → "p95 < 200ms 조건하에 100 동시 요청 통과")
- [ ] **멱등성 검증** 항목이 포함되었는가 (결제/재고 도메인은 필수)

## Options 비교 (MADR 섹션)

- [ ] 최소 2개 방안이 실질적으로 비교되었는가 (straw man 금지)
- [ ] 각 방안에 real pros AND cons가 있는가
- [ ] 선택된 방안의 사유가 드라이버/트레이드오프를 참조하는가
- [ ] 기각된 방안이 **왜** 기각되었는지 서술되었는가

## architect-advisor 횡단 연동

- [ ] 전문용어가 인라인 번역 규칙을 따르는가 (`한국어(中文/English /발음/ — 비유)`)
- [ ] decompose 토폴로지·상태 머신 결과가 Context/Decision Drivers에 반영되었는가
- [ ] `workflow-state.json`의 `steps.council.decision.reason`이 Decision Outcome에 반영되었는가
- [ ] Risk Audit 섹션이 비어있거나 플레이스홀더 상태로 준비되었는가 (audit 이후 append)
- [ ] portfolio 산출물 링크 자리(More Information)가 준비되었는가

## 메타

- [ ] Status가 올바른가 (신규 ADR은 보통 `proposed`, council 확정 직후라면 `accepted`도 가능)
- [ ] Date가 채워졌는가
- [ ] decision-makers가 기재되었는가 (Chloe 외 필요한 오너 포함)
- [ ] 제목이 **동사구**인가 (문제 서술 아님 — "결제 시스템" X, "Saga 패턴으로 결제 정합성 확보" O)
- [ ] 파일명이 repo 관례를 따르는가

---

## Quick Scoring

체크된 항목 수로 대화 방향을 정한다. 자동 게이트가 아니라 **합의 도구**다.

- **전부 체크**: audit(리스크 감사)로 진입.
- **1–3개 미체크**: Chloe와 갭 논의. 대부분 1분 내 보완 가능.
- **4개 이상 미체크**: decompose 또는 council로 되돌아가 fuzzy 영역을 재분해한다.

## Common Failure Modes (자주 발견되는 문제)

| 증상 | 근본 원인 | 수정 방향 |
|------|---------|---------|
| "성능 향상"이 Consequence | 모호한 의도 | "어떤 지표를 얼마나, 무엇으로 측정?"을 물어 수치화 |
| 방안이 1개뿐 | 이미 결정된 상태의 사후 문서화 | "무엇을 기각했고 왜?"를 council 비교로 되돌려 받음 |
| Context가 솔루션 피치처럼 읽힘 | 문제 프레이밍 생략 | Context는 문제만, 해결책은 Decision으로 이동 |
| Consequences가 긍정 일색 | 체리피킹 | "뭐가 어려워지나? 운영 비용은?"을 물어 Bad/Neutral 추가 |
| "X를 쓴다"에 사유 없음 | 비교 없는 선정 | "왜 Y 대신 X?"로 비교 강제 |
| Implementation Plan이 "코드 수정" | 추상 표현 | "어느 파일·함수·패턴?"까지 구체화 |
| Verification이 "잘 동작함" | 검증 불가 | "어떤 명령으로 증명?"을 답하게 함 |
| affected paths 없음 | 코드베이스 스캔 누락 | decompose 토폴로지로 돌아가 경로 식별 |
| 전문용어 번역 누락 | 횡단 레이어 우회 | `/term-glossary`로 즉시 보완 |
