---
description: Generate a daily scrum progress summary from today's git commits across all projects
argument-hint: "[project-root]"
---

# Daily Scrum Progress Generator

Generate a concise daily scrum progress report by analyzing today's git commits across all project repositories. Output is in Korean, grouped by page/feature — not by commit type.

## How it works

1. Scan all git repositories under the user's project root directories
2. Filter commits authored by the user today (check multiple git emails)
3. Group commits by **page or feature area** (not by commit type like feat/fix/refactor)
4. Present in a "Done (한 일)" result-oriented format, ready to copy-paste into standup

## Step-by-step

### 1. Discover repositories and collect commits

Find all git repos and gather today's commits. Check **all known git emails** for the user — they may commit under different emails in different repos.

```bash
# Known git emails for this user
GIT_EMAILS=("chloe@aisahub.com" "jeongrankim99@gmail.com")

# Also check the global config in case a new email was added
GLOBAL_EMAIL=$(git config --global user.email 2>/dev/null)

# Find all git repos under ~/Projects (adjust depth as needed)
find ~/Projects -maxdepth 4 -name ".git" -type d 2>/dev/null
```

For each discovered repo, run git log for **each email** and combine results (dedup by hash):
```bash
git -C <repo-path> log --since="midnight" --author="<email>" --no-merges --format="%h %s" --all
```

Skip repos with no commits today — don't mention them in the output.

### 2. Group by page/feature area

**Do NOT group by commit type (feat/fix/refactor/docs).** Instead, analyze commit scopes and messages to identify logical feature areas, then group commits by those areas.

How to identify feature areas:
- Use the conventional commit **scope** as the primary signal: `feat(settings):`, `fix(admin):`, `refactor(products):` → group by scope
- Combine related scopes into a single area when they clearly belong together (e.g., `settings` scope commits all go under "관리자 설정 페이지")
- If a commit touches multiple areas, place it under the most relevant one
- Group docs commits with the feature they document, not in a separate "Docs" section

Example feature area groupings:
- "관리자 설정 페이지" — includes feat(settings), fix(settings), refactor(settings), related docs
- "상품 수정 스펙 테이블" — includes feat(admin) for spec table, fix(admin) for related modals
- "공개 상품/홈 페이지" — includes fix(home), fix(products) for public-facing pages

### 3. Summarize as results, not commits

The audience is your team at standup. They want to know **what was accomplished**, not the git history.

Principles:
- **Result-oriented**: "설정 페이지 뼈대 + 회사 정보 / 공지 바 / 영업 시간 / 배송 정책 섹션 4종 구현 완료" (not a list of 5 separate feat commits)
- **Combine related commits** into single bullets aggressively — if 3 commits all build the same feature, that's 1 bullet
- **Include the "so what"**: "`site_settings` 스키마 확장, 조회/저장 서버 액션, 한국어 유효성 검증 적용" tells the team what's actually usable now
- **Keep technical details that matter**, drop ones that don't: "미들웨어에서 super_admin으로 제한" is useful context; "extract shared SectionProps type" is not
- Keep each bullet to 1 line (2 lines max)

### 4. Output format

Output **Korean only**. Use this exact structure:

```
## 📋 데일리 스크럼 — {YYYY-MM-DD}

### Done (한 일)

**{기능 영역 1}**
- {결과 요약}
- {결과 요약}

**{기능 영역 2}**
- {결과 요약}

**{기능 영역 3 & 기타 수정}**
- {결과 요약}
```

Rules:
- Feature area names should be descriptive Korean labels (e.g., "관리자 설정 페이지 (Phase 1)", "메뉴 관리자 권한 분리")
- Order feature areas by significance — biggest work chunk first
- If a feature area has only 1 bullet, still use the bold header for consistency
- Combine small, scattered fixes under a single "공개 페이지 & 기타 수정" area at the end
- Date format: use ISO date (YYYY-MM-DD)
- If there are no commits today across all repos, say: "오늘 커밋 내역이 없습니다."

### 5. Edge cases

- **No commits today**: Output "오늘 커밋 내역이 없습니다."
- **Non-conventional commits**: Infer the feature area from the message content; if unclear, group under "기타"
- **Merge commits**: Skip them — they don't represent actual work
- **Repos requiring auth or failing**: Skip silently and mention at the end if any repos couldn't be read
- **Multiple emails with no results**: Try all known emails before reporting no commits
