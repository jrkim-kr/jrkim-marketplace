---
description: Generate a daily scrum progress summary from git commits across all projects
argument-hint: "[date | range] (e.g. 7/21, 7/22~23, or omit for today)"
---

# Daily Scrum Progress Generator

Generate a scrum progress report from git commits across all project repositories. Output is in Korean, grouped by project, then by **feature**. Written so a **non-developer can read it without asking what anything means**. By default, scan `/Users/jrkim/Projects` so repositories outside `Aisahub` are not missed.

## How it works

1. Scan all git repositories under the requested project root, defaulting to `/Users/jrkim/Projects`
2. Filter commits authored by the user in the requested date window
3. Group by **project**, then by **feature** — never by commit
4. Rewrite each group in plain language, then present in the fixed output format below

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

**This is the core of the report.** Twenty commits on one feature become **one line**, not twenty.

- Group every commit by the **feature or capability it serves**, then write one line per group.
- Never group by commit type (`feat`/`fix`/`refactor`/`docs`). Docs commits belong with the feature they document.
- If several groups within a project are really the same user-facing capability (the feature, its storage, its command, its formatting), collapse them into one.
- A group that spans multiple days in the window is still one line.

Watch for **big words that fuse unrelated work**. "권한", "고도화", "개선" can hide two different systems — check the code before merging groups under one label. Example from a real report: *도구 권한*(GitHub 조회 승인, per-request) and *채널 권한표*(Slack 참여 명단, pre-registered) are different systems despite both being "권한".

### 6. Write in language a non-developer can read

The reader is an executive or a teammate outside engineering. They should never have to ask "what does that mean?"

**Never copy a commit subject verbatim.** Commit messages are written for engineers and use internal shorthand. When a commit's meaning isn't obvious, **open the actual diff** (`git show <hash> --stat`, read the changed file) and describe what it does for a user.

- ❌ `파일 수명 주기별 디렉터리 분리 + 생성 산출물 경로 설정 통합`
- ✅ `매번 새로 생기는 파일을 한곳으로 분리 + git·배포에 딸려가지 않도록 제외 규칙 추가`

- ❌ `citation 조립을 최종 ctx 기준으로 통일`
- ✅ `근거 번호가 어긋나던 것 수정`

Translate jargon; keep terms already common in the business (슬랙, 데이터베이스, 대시보드, 스레드).

**Gloss every bare number and label.** `질의 12,122→23건` alone is meaningless — write `화면 한 번 여는 데 데이터베이스에 1만 2천 번 요청하던 것을 23번으로`.

**Do not claim completion from commits alone.** Commits prove work happened, not that it is finished or live. Write `구축 중` unless the user confirms it's done. Never infer "완료" / "배포됨" from a commit's existence.

### 7. Output format

Output **Korean only**. Use this exact structure — three levels, no date line, no status tags, no extra sections:

```
* 어제 한일
   * energino
      * Railway vs. Hostinger 비교 → Hostinger 채택
      * 이전 실행 준비 완료: 절차서·되돌리기 방안·예행 환경·역할별 운영 매뉴얼까지 완비
      * 코드 구조 전면 재정리: 흩어져 있던 파일 131개를 역할별로 재배치 — 인수인계 및 유지보수 기반 확보
      * 권한 결함 1건 발견·차단: 일반 멤버가 수정·삭제·내보내기 기능에 접근 가능했던 경로 (역할별 매뉴얼 작성 중 발견, 동일 유형 재발 방지 장치까지 적용)
   * ai-pm (Remy)
      * 답변 정확도 개선: 이어 묻기 인식 개선, 근거 조회 범위 확대(8→30건), 재시작 직후 품질 저하 해소
      * 운영 가시성 확보: 사용 현황·권한 승인 이력·조회 결과를 대시보드에서 확인 가능
      * 안정성 강화: 대용량 조회 시 중단·재시도 비용 절감
   * ux-study
      * 기획 단계에서 동작하는 서비스로 전환: 로그인·학습·시험·운영자 화면을 갖춘 사내 학습 사이트 구축 중
      * 학습 콘텐츠: 4개 역량 정의, 문제 32개, 실습 과제까지 집필 완료
      * 수료 판정: 통과 시험 기능 완성 (한 문제씩 진행, 단일 제출)
      * 운영: 참여자 관리·진도 확인 화면 완성, 다국어 지원
```

**Line shape** — each item is a feature group, written one of these ways:

- `묶음명: 세부1, 세부2, 세부3` — the default. Colon, then what it covers.
- `묶음명: 세부 — 효과/결과` — em dash when the *why it matters* is the point.
- `묶음명: 세부 (맥락)` — parentheses for how it was found or a caveat.
- `A vs. B 비교 → C 채택` — arrow for a decision and its outcome.

**Rules:**
- Heading is literally `어제 한일`. No date, no emoji header, no `## 데일리 스크럼` line.
- Exactly three levels: `어제 한일` → project → feature group. Never a fourth level.
- Order projects by **business weight**, not commit count: client delivery first, then internal products, then internal/learning projects.
- Each feature group is one line. If it needs two sentences, compress it.
- **No status tags** (`🟢`/`🟡`), no merge/branch state, no commit hashes, no commit types, no file paths, no `진도` line, no `경영 판단` section. If the user asks for merge status or a progress read, add it that turn only — it does not belong in the default output.
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
