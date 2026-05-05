---
name: arch-portfolio
description: "커리어 자산 자동 생성. 설계 결과를 STAR 케이스 스터디, 30초 면접 요약(한/중), 누적 용어집, 회고로 변환한다. '포트폴리오', '케이스 스터디', '면접 준비', 'STAR', '커리어 자산', '이력서용', '회고' 등의 키워드에 트리거."
argument-hint: "[케이스 스터디로 만들 모듈/기능 설명]"
user-invokable: true
---

# Architect Advisor — 커리어 자산화 (Portfolio Builder)

이 스킬은 완료된 설계를 면접 자산으로 변환하는 단독 도구다. 공통 정책(용어 번역 레이어, 산출물 규약, 톤)은 메인 스킬 `../architect-advisor/SKILL.md`를 따른다.

## 역할

기능 개발 또는 설계 완료 시, 면접에서 바로 활용할 수 있는 **전문가급 케이스 스터디 + 회고**를 자동 생성한다.

## 출력 톤

응답 톤은 `../architect-advisor/references/audience-tone.md`를 따른다. 면접 자산은 면접관 대상이므로 다소 기술적 톤이 허용된다.

## 산출물 1: STAR 케이스 스터디

```markdown
## [모듈명] 아키텍처 설계 케이스

### 배경 (Situation)
[프로젝트명]의 [모듈명] 개발. [비즈니스 맥락 1-2문장].

### 도전 (Challenge)
- [핵심 기술 과제 1: 예) 멱등성 보장]
- [핵심 기술 과제 2: 예) 분산 환경 데이터 일관성]
- [핵심 기술 과제 3: 예) 장애 복구 전략]

### 행동 (Action)
두 가지 아키텍처 방안(MVP vs 견고한 설계)을 비교 분석한 후,
[선택한 방안]을 선택. 그 이유:
1. [아키텍처적 판단 근거 1]
2. [아키텍처적 판단 근거 2]

### 성과 (Result)
- 시스템 견고성(鲁棒性/Robustness) 향상
- 운영 비용 절감
- [구체적 수치나 개선 지표가 있다면 포함]
```

## 산출물 2: 30초 면접 요약 (중한 이중언어)

```markdown
#### 한국어 버전
[30초 분량의 한국어 면접 답변 — STAR 구조 압축]

#### 中文版本
[30秒中文面试回答 — STAR结构压缩]
```

## 산출물 3: 누적 용어집

대화 중 등장한 기술 용어를 모아 정리한다. `/term-glossary`를 자동 호출하거나, 메인 스킬의 "누적 용어집" 형식(한국어 블록 + 中文说明 블록)을 따른다.

## 산출물 4: 회고 (Retrospective)

이번 설계·감사 과정에서 **무엇이 잘 됐고, 무엇을 다음 비슷한 프로젝트에서 바꿀지**를 구조화한다. 미래의 Chloe가 같은 실수를 반복하지 않도록 하는 **설계 자체에 대한 ADR**이다.

```markdown
## [모듈명] 설계 회고

### 🟢 Keep — 다음에도 유지할 것
- {구조·절차·판단 중 효과가 좋았던 것}

### 🔴 Problem — 다음엔 피하거나 바꿀 것
- {이번에 겪은 불편·낭비·놓친 부분}

### 🔵 Try — 다음 프로젝트에서 시도할 실험
- {구체적 액션, 가급적 검증 기준까지}

### ⏰ Revisit — 이 결정을 다시 볼 조건
- {언제·어떤 신호가 오면 이 ADR/설계를 재검토할지}

### 📚 Knowledge Gap — 다음까지 학습할 것
- {이번에 부족했던 지식·스킬·도구}
```

**작성 타이밍**: 감사(`/arch-audit`) 직후, 프로젝트 맥락이 뜨거울 때. 이때 회고해야 가장 구체적이다.

## 산출물 저장 경로

산출물은 **두 위치**에 저장한다:

### 1) 작업 산출물 (intermediate, step별 분리)

`/Users/jrkim/Projects/architect-advisor/<project-slug>/portfolio/` — workflow-state.py가 관리하는 step별 작업 파일 (star-case.md, interview-30s.md, retrospective.md, glossary.md). 다른 architect-advisor skill (decompose/council/adr/audit)과 같은 루트.

**중요**: AA_ROOT는 cwd가 아니라 `/Users/jrkim/Projects/architect-advisor/`로 고정. 프로젝트 디렉토리(예: `/Users/jrkim/Projects/Aisahub/handys/`) 안에 만들지 않는다.

```bash
cat <<'EOF' | python3 scripts/workflow-state.py save portfolio star-case
# STAR 케이스 스터디
...
EOF

cat <<'EOF' | python3 scripts/workflow-state.py save portfolio interview-30s
# 30초 면접 요약 (한/중)
...
EOF

cat <<'EOF' | python3 scripts/workflow-state.py save portfolio retrospective
# 설계 회고 (Keep / Problem / Try / Revisit / Knowledge Gap)
...
EOF

cat <<'EOF' | python3 scripts/workflow-state.py save glossary glossary
# 누적 용어집
...
EOF
```

### 2) 최종 통합 포트폴리오 (single-file, 면접 직접 사용)

`/Users/jrkim/Projects/Portfolio/<descriptive-slug>.md` — 위 4개 산출물을 **하나의 파일로 통합한 면접용 마스터 문서**. 파일명은 도메인을 드러내는 서술적 슬러그(예: `ota-hotel-automation.md`).

**이미 같은 도메인의 통합 포트폴리오가 있으면 새 파일을 만들지 말고 기존 파일에 머지한다**:
- 동일 프로젝트 그룹(같은 비즈니스 도메인)이면 같은 파일을 업데이트
- 새 회고/용어/케이스만 해당 섹션에 추가 (중복은 머지)
- 머지 전 `ls /Users/jrkim/Projects/Portfolio/*.md`로 기존 파일 목록 확인

**통합 파일 구조** (반드시 이 순서):

```markdown
# [도메인 이름] — 커리어 자산

> 생성일: YYYY-MM-DD (또는 최종 업데이트일)
> 프로젝트: project-A + project-B (관련 프로젝트 모두 나열)

---

## 전체 프로젝트 요약
[ASCII 아키텍처 다이어그램 + 프로젝트 비교표 + 총 LOC/플랫폼 등 요약 메트릭]

---

## STAR 케이스 스터디
### 1. project-name — 한 줄 요약
#### 배경 (Situation) / 도전 (Challenge) / 행동 (Action) / 성과 (Result)
[프로젝트별 반복]

---

## 30초 면접 요약
### 전체 에코시스템
#### 한국어 버전 / #### 中文版本

### 프로젝트별 요약
#### A./B./C./D. project-name (한국어 + 中文版)

---

## 설계 회고 (Retrospective)
### 🟢 Keep / ### 🔴 Problem / ### 🔵 Try / ### ⏰ Revisit / ### 📚 Knowledge Gap

---

## 누적 용어집
### 용어명 (中文 / English /발음/)
#### 한국어 설명 (비유/기술 정의/적용 사례)
#### 中文说明 (类比/技术定义/应用案例)
[용어별 반복]
```

## 입력 컨텍스트

이전 step 산출물(`architect-advisor/<project-slug>/decompose/`, `decision/`, `adr/`, `audit/`)이 있으면 그것을 기반으로 STAR 케이스를 풍부하게 작성한다. 없으면 사용자가 설명하는 설계 경험을 바탕으로 작성한다.

## 다중 프로젝트 처리

여러 하위 프로젝트가 있는 경우:
1. **전체 에코시스템 요약**을 먼저 작성 (아키텍처 다이어그램 + 프로젝트 비교표)
2. **프로젝트별 STAR 케이스**를 각각 독립적으로 작성
3. **30초 면접 요약**은 전체 요약 1개 + 프로젝트별 각 1개
4. **용어집**은 전체 프로젝트 통합 정리
5. **회고**는 프로젝트별로 작성하되, 공통된 Knowledge Gap은 상위 수준에서도 요약

## Notion 저장 (선택)

사용자가 요청하면, 케이스 스터디와 용어집을 Notion에 저장한다. DB URL/ID를 확인한 뒤 진행한다.

## 회고의 장기 누적

회고는 한 프로젝트로 끝나지 않는다. **다음 프로젝트 시작 시, `/arch-decompose` 또는 `/architect-advisor`에 진입하기 전에 이전 프로젝트의 `architect-advisor/<prev-project>/portfolio/retrospective.md`의 Try·Revisit·Knowledge Gap을 먼저 읽는다.** 이것이 architect-advisor의 복리 효과(compound learning)다.
