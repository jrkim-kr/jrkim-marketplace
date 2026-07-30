---
description: Generate a daily scrum progress summary from git commits across all projects
argument-hint: "[date | range] (e.g. 7/21, 7/22~23, or omit for today)"
---

# Daily Scrum Progress Generator

Generate a scrum progress report from git commits across all project repositories. Output is in Korean, grouped by project, then by **feature group**, with only the core outcomes under each feature. Written so a **non-developer can read it without asking what anything means**. By default, scan `/Users/jrkim/Projects` so repositories outside `Aisahub` are not missed.

## How it works

1. Scan all git repositories under the requested project root, defaulting to `/Users/jrkim/Projects`
2. Filter commits authored by the user in the requested date window
3. Group by **project**, then by **feature group** — never by commit
4. Rewrite each group in plain language with industry-standard terms, then present in the fixed dated format below

## Step-by-step

### 1. Resolve the date window

The argument may be a single date (`7/21`), a range (`7/22~23`, `7/17~7/19`), or absent (= today). Convert to an explicit window and use it for every repo:

```bash
SINCE="2026-07-22 00:00"   # start of first day
UNTIL="2026-07-24 00:00"   # start of day AFTER the last day
```

Always use `--since`/`--until` together. Do not use `--since="midnight"` for anything but a plain "today" request.

### 2. Discover repositories and collect commits

```bash
# The ONLY git emails for this user
GIT_EMAILS=("chloe@aisahub.com" "jeongrankim99@gmail.com")

PROJECT_ROOT="${1:-/Users/jrkim/Projects}"
find "$PROJECT_ROOT" -maxdepth 6 -name ".git" -type d 2>/dev/null
```

**Do NOT add other emails.** `jordan@aisahub.com` is the user's login/work address but is **not** a git author identity — including it risks pulling a colleague's commits into the user's report. Only add an email if the user says to.

Collect in one pass per repo, then filter by author, so ordering survives:

```bash
git -C <repo> log --all --since="$SINCE" --until="$UNTIL" --no-merges \
    --format="%ct|%H|%h|%ae|%s"
```

Pitfall: never pass a multi-line list of hashes as one shell argument (`$(echo $hashes)`) — git fails with "File name too long". Iterate line by line.

Skip repos with no commits in the window — don't mention them.

### 3. Drop noise before summarizing

These appear in `--all` but are not work. Exclude them silently:

- **Merge commits** (`--no-merges` already handles it)
- **git stash entries** — subjects starting `index on `, `untracked files on `, `On <branch>:`
- **Automated commits** — e.g. `auto: 2026-07-20T07:27:28Z` timestamp commits
- **Duplicate commits** across branches (same subject, different hash after rebase/cherry-pick) — count the work once

### 4. Identify projects

- For repos under `/Users/jrkim/Projects/Aisahub`, the project is the direct child folder of `Aisahub`
  - `/Users/jrkim/Projects/Aisahub/ai-cos/apps/web` → `ai-cos`
- For repos outside `Aisahub`, the project is the first folder below `/Users/jrkim/Projects`
- Keep the folder name; add a human alias in parentheses when it helps — never replace the folder name:
  - `ai-cos` → `ai-cos (Alex)`
  - `ai-pm` → `ai-pm (Remy)`
  - `enertec` / `enertec-*` → `{folder-name} (에너텍)`

### 5. Group by feature, not by commit

**This is the core of the report.** Twenty commits on one feature become **one feature group**, not twenty commit lines.

- Group every commit by the **feature or capability it serves**, then write one feature group per meaningful capability.
- Never group by commit type (`feat`/`fix`/`refactor`/`docs`). Docs commits belong with the feature they document.
- If several groups within a project are really the same user-facing capability (the feature, its storage, its command, its formatting), collapse them into one.
- A group that spans multiple days in the window is still one line.
- Under each feature group, include **1-3 core outcome bullets**. Keep only what the team needs for standup.
- Prefer the shape: project -> feature group -> concrete outcomes. Do not flatten back to project -> many commit-sized bullets.

Watch for **big words that fuse unrelated work**. "권한", "고도화", "개선" can hide two different systems — check the code before merging groups under one label. Example from a real report: *도구 권한*(GitHub 조회 승인, per-request) and *채널 권한표*(Slack 참여 명단, pre-registered) are different systems despite both being "권한".

### 6. Write in language a non-developer can read

The reader is an executive or a teammate outside engineering. They should never have to ask "what does that mean?"

**Never copy a commit subject verbatim.** Commit messages are written for engineers and use internal shorthand. When a commit's meaning isn't obvious, **open the actual diff** (`git show <hash> --stat`, read the changed file) and describe what it does for a user.

- ❌ `파일 수명 주기별 디렉터리 분리 + 생성 산출물 경로 설정 통합`
- ✅ `매번 새로 생기는 파일을 한곳으로 분리 + git·배포에 딸려가지 않도록 제외 규칙 추가`

- ❌ `citation 조립을 최종 ctx 기준으로 통일`
- ✅ `근거 번호가 어긋나던 것 수정`

Translate jargon; keep terms already common in the business (Slack, LINE WORKS, 데이터베이스, 대시보드, 스레드, API, VPS, CI, E2E).

Prefer industry-standard terms over internal metaphors:

- `원장` -> `운영 DB` / `프로덕션 DB`
- `접수기` -> `콜백 서버` / `웹훅 수신기`
- `같은 기계` -> `동일 VPS 네트워크`
- `정기 작업` -> `배치 작업`
- `자가 점검` -> `헬스 체크`
- `저장소` when used technically -> `스토어` or the specific storage name, e.g. `메시지 스토어`
- `증거 각주` -> `근거 표시`

Keep the summary **핵심만**. If a detail explains an implementation path rather than the value, drop it.

**Gloss every bare number and label.** `질의 12,122→23건` alone is meaningless — write `화면 한 번 여는 데 데이터베이스에 1만 2천 번 요청하던 것을 23번으로`.

**Do not claim completion from commits alone.** Commits prove work happened, not that it is finished or live. Write `구축 중` unless the user confirms it's done. Never infer "완료" / "배포됨" from a commit's existence.

### 7. Output format

Output **Korean only**. Use this exact structure — dated title, `한 일`, project, feature group, core outcomes:

```
## 📋 데일리 스크럼 — 2026-07-28

### 한 일
- energino
  - VPS 마이그레이션 준비
    - 운영 DB·앱·배치 작업을 Hostinger VPS 기준으로 재구성
  - LINE WORKS 운영 안정화
    - 존재하지 않는 API 경로 제거 및 재유입 방지
    - 영업방 멤버십 검증을 실제 API 기준으로 보강
- ai-pm (Remy)
  - Q&A 응답 UX 개선
    - 근거 표시를 최신순으로 정렬
    - 비공개 답변에 `나만 보기` 공유 옵션 추가
- ux-study
  - 반응형 UI 개선
    - 플랫폼을 모바일·iPad에서 사용할 수 있도록 화면 구조 조정
  - 학습 흐름 정리
    - Competency 페이지를 실제 학습 순서 기준으로 재구성
```

For a range, use an ISO range in the title:

```
## 📋 데일리 스크럼 — 2026-07-29~2026-07-30
```

**Line shape**:

- Project bullet: folder name first, optional alias in parentheses.
- Feature group bullet: short noun phrase using product or industry terms.
- Outcome bullet: one core result per line, usually 1-3 bullets per feature group.
- Use arrows only for explicit decisions, e.g. `Railway vs. Hostinger 비교 → Hostinger 채택`.

**Rules:**
- Heading is exactly `## 📋 데일리 스크럼 — {date-or-range}`.
- The second heading is exactly `### 한 일`.
- Use exactly this hierarchy: `한 일` -> project -> feature group -> core outcome.
- Order projects by **business weight**, not commit count: client delivery first, then internal products, then internal/learning projects.
- Keep each outcome short. If a feature needs many details, keep the 1-3 most important and drop the rest.
- **No status tags** (`🟢`/`🟡`), no merge/branch state, no commit hashes, no commit types, no file paths, no `진도` line, no `경영 판단` section.
- If nothing in the window: `해당 기간 커밋 내역이 없습니다.`

### 8. Report what git cannot show

`git log` only sees committed code. After the report, mention (outside the pasteable block) anything that materially affects accuracy:

- **Uncommitted changes** — run `git status --porcelain`; if a repo has substantial modified files, say so. Check file mtimes to tell whether they belong to this window.
- **Work with no commits** — debugging, investigations, and decisions leave no git trace. If the user names such work, include it; don't silently drop it because it isn't in git.
- **Scan timing** — commits made after the scan won't appear. If the window includes today, note that late work may be missing.
- **Repos that couldn't be read** — mention them at the end.

### 9. Edge cases

- **No commits in window**: `해당 기간 커밋 내역이 없습니다.`
- **Non-conventional commit messages**: infer the result from the diff; if still unclear, `기타 작업`
- **Scattered small fixes**: fold them into the relevant feature group, not an `기타` project
- **A commit touching several areas**: place it under the feature it most serves
