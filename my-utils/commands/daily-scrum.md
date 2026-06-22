---
description: Generate a daily scrum progress summary from today's git commits across all projects
argument-hint: "[project-root]"
---

# Daily Scrum Progress Generator

Generate a concise daily scrum progress report by analyzing today's git commits across all project repositories. Output is in Korean, grouped by human-readable project name. By default, scan `/Users/jrkim/Projects` so repositories outside `Aisahub` are not missed.

## How it works

1. Scan all git repositories under the requested project root, defaulting to `/Users/jrkim/Projects`
2. Filter commits authored by the user today (check multiple git emails)
3. Group commits by **project**, using known project aliases where possible
4. Present in a short "한 일" standup format, ready to copy-paste into chat

## Step-by-step

### 1. Discover repositories and collect commits

Find all git repos and gather today's commits. Check **all known git emails** for the user — they may commit under different emails in different repos.

```bash
# Known git emails for this user
GIT_EMAILS=("chloe@aisahub.com" "jeongrankim99@gmail.com")

# Also check the global config in case a new email was added
GLOBAL_EMAIL=$(git config --global user.email 2>/dev/null)

# Default project root
PROJECT_ROOT="${1:-/Users/jrkim/Projects}"

# Find all git repos under the project root (adjust depth as needed)
find "$PROJECT_ROOT" -maxdepth 6 -name ".git" -type d 2>/dev/null
```

For each discovered repo, run git log for **each email** and combine results (dedup by hash):
```bash
git -C <repo-path> log --since="midnight" --author="<email>" --no-merges --format="%h %s" --all
```

Skip repos with no commits today — don't mention them in the output.

### 2. Group by project and optional sub-area

**Do NOT group by commit type (feat/fix/refactor/docs).** First group all commits by the project they belong to, then add a sub-area only when it makes the report easier to read.

How to identify project folders:
- Default scan root is `/Users/jrkim/Projects`, unless the user passes a different `[project-root]`.
- For repos under `/Users/jrkim/Projects/Aisahub`, treat each direct child folder under `Aisahub` as one project.
  - Example: `/Users/jrkim/Projects/Aisahub/ai-cos/apps/web` → project `ai-cos`
- For repos outside `Aisahub`, map them to the first folder below `/Users/jrkim/Projects`.
  - Example: `/Users/jrkim/Projects/jrkim-marketplace/my-utils` → project `jrkim-marketplace`
- If the user passes a different `[project-root]`, use that root and apply the same direct-child-folder rule without the `Aisahub` special case unless the path is inside `/Users/jrkim/Projects/Aisahub`.
- Keep the folder name as the project name. If a human-readable alias helps, put it in parentheses after the folder name:
  - `ai-cos` -> `ai-cos (Alex)`
  - `ai-pm` -> `ai-pm (Remy)`
  - `enertec` -> `enertec (에너텍)`
  - `enertec-*` -> `{folder-name} (에너텍)`

Within each project:
- Use direct bullets when the work fits one clear project area.
- Use one nested sub-area when the project has a natural workstream or feature area such as `안드로이드 앱`, `웹`, `자동화`, `주간 보고서 생성 기능`, or `참조문서 SSoT`.
- When several commits belong to the same feature, create a feature-area parent bullet and place the concrete outcomes underneath it.
  - Example:
    - `주간 보고서 생성 기능`
      - `주간 보고서 제품 영역별 소제목 적용`
      - `보고서 프로젝트 자기등록 구현 → /remy report add/list`
      - `Notion 레지스트리 연동`
- Do not add a sub-area just to mirror commit scopes.
- Combine related commits into one feature-area group when they clearly belong together.
- Group docs commits with the feature they document, not in a separate "Docs" section.
- If a commit touches multiple areas, place the result under the most relevant project.

### 3. Summarize as results, not commits

The audience is your team at standup. They want to know **which project moved and what changed**, not the git history.

Principles:
- **Standup-short**: prefer short noun phrases like "QA SSoT 구현" or "실기기 검증".
- **Human first**: use product names and user-visible outcomes before internal implementation details.
- **Keep useful anchors**: if a command or entrypoint is the point of the work, keep it after an arrow, e.g. `Agents R&R 기능 고도화 → \`/alex agents\``.
- **Avoid duplicate feature bullets**: do not split a user-facing feature, its storage/registry integration, and its helper commands into separate sibling bullets. Put them under one feature-area parent when that makes the relationship clearer.
- **Allow next-state bullets**: short status items like "고도화 필요" are allowed when they are the honest project state after today's work.
- **Drop technical noise**: do not mention schema names, middleware, refactors, helper types, or commit scopes unless that is the thing the team needs to know.
- Keep each bullet to 1 short line. If it needs a full sentence, compress it.

### 4. Output format

Output **Korean only**. Use this exact structure:

```
## 📋 데일리 스크럼 — {YYYY-MM-DD}

### 한 일
- ai-cos (Alex)
  - Agents R&R 기능 고도화 → `/alex agents`
- ai-pm (Remy)
  - 주간 보고서 생성 기능
    - 주간 보고서 제품 영역별 소제목 적용
    - 보고서 프로젝트 자기등록 구현 → `/remy report add/list`
    - Notion 레지스트리 연동
  - QA SSoT 구현
- enertec (에너텍)
  - 안드로이드 앱
    - 실기기 검증
    - 고도화 필요
```

Rules:
- Project names should come from folders directly under `/Users/jrkim/Projects/Aisahub` for Aisahub repos, or directly under `/Users/jrkim/Projects` for non-Aisahub repos. If the user supplies `[project-root]`, use direct children of that root.
- If using an alias, never replace the folder name with the alias. Write `{folder-name} ({alias})`.
- Order projects by significance — biggest work chunk first.
- Each project must be a top-level bullet. Do not use bold project headers.
- Put short result or status bullets under each project.
- Use a third bullet level only for a real sub-area or feature area such as `안드로이드 앱` or `주간 보고서 생성 기능`; otherwise stay at two levels.
- If a project has only 1 result bullet, still keep it under the project bullet for consistency.
- Combine small, scattered fixes inside the relevant project or feature-area bullet instead of creating an "기타" project unless the project itself is unclear.
- If multiple sibling bullets describe the same feature's user command, registry/storage, formatting, or generated output, collapse them under one feature-area parent.
- Do not add feature headers, commit hashes, commit types, or implementation-heavy explanations.
- Date format: use ISO date (YYYY-MM-DD)
- If there are no commits today across all repos, say: "오늘 커밋 내역이 없습니다."

### 5. Edge cases

- **No commits today**: Output "오늘 커밋 내역이 없습니다."
- **Non-conventional commits**: Keep them under the correct project folder and infer the result summary from the message content; if unclear, summarize as "기타 작업"
- **Merge commits**: Skip them — they don't represent actual work
- **Repos requiring auth or failing**: Skip silently and mention at the end if any repos couldn't be read
- **Multiple emails with no results**: Try all known emails before reporting no commits
