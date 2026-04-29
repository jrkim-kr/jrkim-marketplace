---
name: arch-err-pattern
description: "architect-advisor 횡단 도구. `<ERR_DIR>/ERR-*.md`를 가로로 훑어 재발 충돌 패턴을 추출해 `CONFLICT_PATTERNS.md`를 생성한다. ERR_DIR은 `.flushrc.json` → `find errors/` → `./errors/` 3단계로 자동 해석된다. 다음 `writing-plans`가 자동 참조. 트리거: '패턴 추출', 'CONFLICT_PATTERNS', '冲突模式', 'extract conflict patterns'."
argument-hint: "[ERR 디렉토리 경로 (생략 시 자동 해석)] 또는 [프로젝트 슬러그]"
user-invokable: true
---

# Arch Err Pattern — 에러 문서 횡단 패턴 추출

**정체성**: architect-advisor 횡단 도구. 단일 step에 속하지 않으며 수동 호출 전용. `term-glossary`와 같은 위치. portfolio의 회고가 "이번 프로젝트" 회고라면, 이 스킬은 **여러 에러를 가로질러 반복 패턴**을 뽑는다.

> 의사가 진료 기록 하나씩 봐선 안 보이던 병이, 100장을 한꺼번에 늘어놓으면 "다 수요일 저녁에 발병했다"가 보이는 것 — 이 스킬이 하는 일.

## 언제 호출

| 상황 | 효과 |
|---|---|
| `<ERR_DIR>`에 ERR-*.md **5개 이상** 쌓였을 때 | 첫 패턴 추출, 기준선 확립 |
| 신규 ERR 5건 추가 또는 월 1회 | 증분 업데이트 |
| `writing-plans` 시작 전 | `CONFLICT_PATTERNS.md`를 읽어 task 수락 기준에 주입 (글로벌 CLAUDE.md §6 연동) |
| 고위험 모듈 리팩터링 직전 | 해당 모듈 관련 과거 패턴 pre-flight 브리핑 |

> **ERR_DIR 해석 규칙 (W0.1 단일 진실)**
> 1. `.flushrc.json` 의 `errorDocDir` 필드
> 2. `find . -type d -name "errors"` (node_modules/.git 제외)
> 3. `./errors/` (기본값)
>
> `flush` 플러그인과 동일한 규칙. 이 스킬에서 `docs/errors/` 같은 경로를 하드코딩하지 말 것.

## 자동 누적 모드 (W3.1)

수동 호출 외에도, **PostToolUse hook**으로 ERR 작성 시점에 자동으로 candidate를 누적할 수 있다.

### Hook 등록 (1회 설정)

`~/.claude/settings.json`의 `hooks` 섹션에 다음을 추가:

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "python3 /Users/jrkim/Projects/jrkim-marketplace/architect-advisor/scripts/err_pattern_observe.py 2>/dev/null || true",
        "async": true,
        "timeout": 10
      }
    ]
  }
]
```

훅 안전 특성:
- **fire-and-forget**: 어떤 실패도 main thread를 막지 않음 (`2>/dev/null || true`)
- **async**: 백그라운드 실행 → 편집 응답 시간 영향 없음
- **filter**: ERR-*.md가 `<ERR_DIR>` 안에 있을 때만 작동, 아니면 즉시 silent exit

### 누적 흐름

```
flush /flush 명령 → errors/ERR-NNN-*.md 작성
        │
        ▼ (PostToolUse hook 발동)
err_pattern_observe.py
        │
        ├─ ERR doc 파싱 (Affected Modules + Root Cause)
        ├─ architect-advisor/observations.jsonl 에 기록
        └─ candidate 누적
              │
              ├─ confidence < 0.7 또는 1번만 관측 → patterns/candidates.jsonl 만 기록
              └─ confidence ≥ 0.7 AND 동일 module pair가 2개 이상 ERR에서 출현
                    → patterns/CONFLICT_PATTERNS.md 자동 promote
```

### 산출물

```
architect-advisor/
├── observations.jsonl           ← 모든 ERR 관측 로그 (감사용)
└── patterns/
    ├── candidates.jsonl         ← 낮은 confidence pattern (대기열)
    └── CONFLICT_PATTERNS.md     ← 정식 패턴 (writing-plans가 자동 참조)
```

monorepo 모드에서는 `architect-advisor/_shared/patterns/CONFLICT_PATTERNS.md` (모든 product 공유).

### 수동과 자동 혼용

수동 `/arch-err-pattern` 호출은 자동 hook을 끄지 않는다. 수동은 한 번에 전체 횡단 분석으로 더 정교한 패턴(병합·승격)을 수행하고, 자동 hook은 incremental observation만 한다.

**Early exit**: ERR이 **5건 미만**이면 패턴 귀납 보류. "샘플 부족 — 최소 5건 누적 후 재실행" 안내만 출력하고 저장하지 않는다.

## 실행 흐름 (4단계)

### 1. 스캔 (스크립트 위임)

파싱은 Claude가 하지 않는다. 헬퍼 스크립트가 대신한다:

```bash
# ERR_DIR을 별도 지정하지 않으면 .flushrc.json -> find errors/ -> ./errors/ 순으로 자동 해석.
python3 scripts/err_scan.py --summary           # 요약 먼저
python3 scripts/err_scan.py                     # 전체 JSON
python3 scripts/err_scan.py --explain           # 어느 tier에서 해석됐는지만 확인

# 강제 지정이 필요하면:
python3 scripts/err_scan.py --dir custom/path/errors/
```

스크립트 출력은 각 ERR의 구조화된 JSON + 모듈 공현 행렬 + 빈도 맵. 별칭 매핑(`근본 원인 ↔ Root Cause` 등)은 스크립트 내부에서 처리.

**에이전트가 수동 파싱 금지** — 토큰 낭비 + 일관성 저하. 항상 스크립트 출력을 입력으로 쓴다.

### 2. 횡단 귀납 (에이전트 본업)

JSON을 받아 아래 규칙으로 패턴 도출:

- **정식 패턴 기준**: 같은 근본 원인이 **서로 다른 모듈 조합**에서 **2건 이상** 반복
- **단일 사례(Singletons)**: 1건뿐이면 정식 패턴 아님. 별도 블록에 적재
- **Singleton 자동 승격**: 이전 세대의 `CONFLICT_PATTERNS.md`에 singleton이었던 근본 원인이 이번 스캔에서 1건 더 발견되면 → 정식 패턴으로 승격하고 Changelog 기록
- **패턴 병합**: 모듈·원인 둘 다 80% 이상 겹치면 1개로 병합 제안

### 3. 문서 생성

`architect-advisor/<project>/patterns/CONFLICT_PATTERNS.md`에 저장. 구조:

```markdown
# 충돌 패턴 분석 (Conflict Patterns)

> 기반: <ERR_DIR>/ 하위 N개 ERR 문서 횡단 귀납
> 생성: YYYY-MM-DDThh:mm:ssZ | 모드: [신규 | 증분]

## Changelog
- YYYY-MM-DD: (새 변경 요약 1줄)
- (이전 이력 유지)

## 개요
- 총 ERR: N · 식별 패턴: M · 단일 사례: K

---

<!-- pattern-id: M1 -->
## 모드 1: [패턴 이름]

**범주**: [상태 관리 / 경쟁 조건 / 에러 처리 / 스키마 호환성 / ...]
**고위험 모듈 조합**: `module-a` ↔ `module-b`
**전형적 증상**: 1-2문장 (트리거 + 증상)
**과거 사례 (N건)**:
- `ERR-XXX` — 한 줄 요약
- `ERR-YYY` — 한 줄 요약

**예방 규칙** (writing-plans 수락 기준):
- [ ] 구체·검증 가능한 항목
- [ ] 검증 방법

---

<!-- pattern-id: M2 -->
## 모드 2: ...

---

## 高危模块组合 Top 5

| 순위 | 모듈 조합 | 공현 | 주요 리스크 |
|---|---|---|---|
| 1 | ... | ... | ... |

## writing-plans용 빠른 체크리스트

신규/수정이 다음 모듈을 건드릴 때 **반드시** 해당 예방 규칙 주입:
- **[모듈 카테고리]** → M1 + M3
- ...

---

## 단일 사례 (Singletons)
재발 시 자동 승격 후보.
- `ERR-ZZZ` — 한 줄 요약 (근본 원인 카테고리: "상태 손실")

## 데이터 품질 비고
파싱 누락·스키마 편차 기록 (ERR 문서 규범화용).
- `ERR-NNN`: `## 영향 모듈` 헤더 누락
```

**Pattern ID 규약**:
- 각 패턴 블록 직전에 `<!-- pattern-id: M<n> -->` HTML 주석 필수
- 증분 업데이트 시 이 ID로 기존 패턴 추적. 사용자가 예방 규칙을 수동 보완했을 수 있으므로 **예방 규칙은 기계적으로 덮어쓰지 말 것** — 새 항목은 append, 기존 항목은 보존
- ID는 한번 부여되면 재사용 금지. 패턴이 삭제되어도 번호는 건너뜀

### 4. 저장 & 상태 기록

```bash
# 파일 저장
cat <<'EOF' | python3 scripts/workflow-state.py save patterns CONFLICT_PATTERNS
# 충돌 패턴 분석 (Conflict Patterns)
...
EOF
# → architect-advisor/<project>/patterns/CONFLICT_PATTERNS.md

# 통계 갱신 (state.patterns에 정확한 수치 기록)
python3 scripts/workflow-state.py patterns-stat \
  --source-errors 12 --pattern-count 5 --singletons 4
```

두 명령 모두 실행해야 `state/workflow.json`의 `patterns` 필드가 완전히 최신화됨.

## 증분 업데이트 규칙

`CONFLICT_PATTERNS.md`가 이미 존재하면:

1. 기존 문서 읽기 → `<!-- pattern-id: M<n> -->` 주석으로 블록 분할
2. 각 블록에서 **과거 사례 리스트**와 **예방 규칙**을 추출
3. 새 ERR 스캔 결과와 대조:
   - 기존 패턴에 신규 사례 → "과거 사례" 리스트에 append
   - 신규 패턴 발견 → 다음 번호(M<max+1>)로 추가
   - Singleton 승격 → 새 pattern-id 부여, Changelog에 기록
4. 예방 규칙: 기존 항목 전부 보존 + 신규 항목만 append (중복 체크는 문자열 정규화 후 비교)
5. Changelog에 이번 변경 1줄 추가, 이전 이력은 유지

## 완료 보고 포맷 (4단 구조)

```
🎯 지금 뭘 했나
<ERR_DIR>/ 12개 ERR을 횡단 분석했습니다.

📌 핵심 결과
- 정식 패턴 5개 (신규 3, 업데이트 2)
- 고위험 조합 Top 3: `scheduler` ↔ `queue` (4건), ...
- 단일 사례 4건 (모니터링)
- Singleton 승격 1건: "상태 손실" 카테고리

📊 Top 패턴
| 모드 | 이름 | 사례 | 주요 모듈 |
| M1  | 스케줄러-큐 레이스 | 3 | scheduler, queue |
| ... |

👉 다음 한 걸음
- 저장: `architect-advisor/<project>/patterns/CONFLICT_PATTERNS.md`
- `/superpowers:writing-plans` 실행 시 자동 참조 (글로벌 CLAUDE.md §6)
```

## 출력 톤

`../architect-advisor/references/audience-tone.md`를 따른다 (비유 먼저, 전문용어는 괄호로).

## 가드레일

- **ERR < 5건**: 저장 없이 early exit
- **빈 디렉토리**: "<ERR_DIR>/ 없음 또는 ERR-*.md 없음" 안내만
- **파일명 계약**: 저장 파일명은 반드시 `CONFLICT_PATTERNS.md` — 글로벌 CLAUDE.md §6이 이 이름으로 검색한다. 소비자 계약을 따른다. 소문자/변형 금지.
- **파싱 실패 ERR**: `missing_fields`가 있으면 "데이터 품질 비고" 섹션에 기록. 무시하지 말 것.

## 참조

- **입력 규격**: 글로벌 `~/.claude/CLAUDE.md §5` "Fix Tasks — Lightweight Error Documentation" (ERR-NNN 템플릿)
- **소비자**: 글로벌 `~/.claude/CLAUDE.md §6` "Writing Plans — Conflict Pattern Check"
- **관련 스킬**: `/architect-advisor:arch-portfolio` (단일 프로젝트 회고), `/superpowers:writing-plans` (주 소비자)
- **헬퍼 스크립트**: `scripts/err_scan.py`, `scripts/workflow-state.py patterns-stat`
