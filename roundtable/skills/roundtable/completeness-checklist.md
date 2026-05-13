# PRD/Spec 완결성 체크리스트 (Synthesizer 전용)

Synthesizer 가 Round 3 합성 시 transcript 를 이 체크리스트로 평가.
각 항목에 **✅ 충분 / ⚠️ 부분 / ❌ 안 다룸** 으로 표기.

❌ 또는 ⚠️ 가 많은 카테고리 → `decisions.md` 의 "**5. 커버되지 않은 영역**" 섹션에 명시 + 다음 회의에서 召唤할 페르소나 추천.

이 체크리스트의 목적은 **detector** 이지 generator 가 아님. transcript 에 없는 내용을 만들어내지 말 것 — 단지 "이 영역은 안 다뤄졌으니 다음 라운드에 X 페르소나 召唤 필요" 만 표시.

---

## 비즈니스 (Growth/CMO·CEO 가 주로 다룸)
- [ ] TAM/SAM (시장 규모 추정)
- [ ] CAC / LTV / Payback (단위 경제)
- [ ] GTM (Go-to-Market) 가설 — 첫 N명 어떻게 모을지
- [ ] 경쟁 포지셔닝 — 누구 vs 누구, 차별화 무엇
- [ ] 수익 모델 / 가격 구조 (구체적 숫자)
- [ ] BM 확장 옵션 (1-3년 후 인접 시장 / 데이터 자산화)
- [ ] 리텐션 / 바이럴 메커니즘

## 기술 (CTO 가 주로 다룸)
- [ ] 아키텍처 — ASCII 다이어그램 그릴 수 있는 수준
- [ ] 데이터 흐름 — 생성→변환→저장→소비
- [ ] 비용 모델 — 사용자 100·1k·10k·100k 단계별
- [ ] 장애 시나리오 + blast radius
- [ ] Innovation token 회계 — 새 기술 도입 정당화
- [ ] 외부 의존성 리스크 (SaaS·API)
- [ ] 가정 가시화 — 암묵적 사용량·동시성·트래픽

## UX / 디자인 (Designer 가 주로 다룸)
- [ ] 사용자 여정 완결성 — onboarding → 핵심 가치 → 리텐션
- [ ] Empty / Error / Loading state
- [ ] 모바일 적합성 — 한 손·세로
- [ ] 인지 부담 — 한 화면 결정 수 (Hick's law)
- [ ] 접근성 — WCAG AA 이상
- [ ] 첫 5초 first-glance 이해
- [ ] AI slop 검출 — generic 디자인 아닌가

## 데이터
- [ ] 데이터 모델 — 핵심 entity·관계
- [ ] 소유권 — 사용자 vs 제공자 vs 학원 등
- [ ] 격리 / 멀티테넌시 boundary
- [ ] 보관 / 파기 정책
- [ ] Export / portability

## 보안 / 컴플라이언스 (CSO 가 주로 다룸)
- [ ] 인증 / 인가 — RBAC·ABAC
- [ ] PII / 미성년자 / 결제 처리
- [ ] STRIDE 위협 모델
- [ ] Audit trail
- [ ] 법규 (KISA, ISMS-P, GDPR 등)
- [ ] AI/LLM 보안 (prompt injection 등) — AI 기능 있을 때

## 법무
- [ ] 약관 — 소유권·IP·이용 범위
- [ ] 책임 소재 — 사고 시 누가
- [ ] 데이터 이전 / 폐업 시 처리

## 운영
- [ ] 온보딩 흐름
- [ ] 고객 지원 / 문의 채널
- [ ] 모니터링·관측 (observability)
- [ ] 운영 인계 — 6개월 후 새 엔지니어가 받을 수 있는가

## 도메인 현장
- [ ] 실 사용자가 기존 워크플로우와 충돌 없이 도입 가능한가
- [ ] 결제 결정자와 사용자가 분리된 경우 결제 모델 적합한가
- [ ] 학부모·상사·규제 기관 등 외부 이해관계자 영향

---

## Synthesizer 작성 패턴

`decisions.md` 마지막 섹션:

```markdown
## 5. 커버되지 않은 영역 (Completeness Gaps)

| 카테고리 | 상태 | 누락 항목 | 다음 회의 추천 |
|---|---|---|---|
| 비즈니스 | ❌ | TAM/CAC/GTM 전혀 안 다룸 | Growth/CMO 召唤 |
| UX | ⚠️ | Empty/Error state 누락 | Designer 召唤 (E 원형 아니어도) |
| 법무 | ❌ | 약관·IP 미논의 | 사용자 직접 또는 법무 검토 |

**권장 후속 액션**: Round 4 로 위 페르소나 召唤하여 추가 회의, 또는 사용자 직접 검토.
```
