---
name: flush
description: Flush changes through the full pipeline — analyze, error docs, GitHub issue, conventional commit, push/PR. Use for "이슈 만들어", "이슈 커밋", "에러 문서화", "flush it". NOT for simple "커밋해 줘" or "commit this".
argument-hint: "[type]"
---

You handle error documentation, GitHub issue creation, and commit message generation — all in one workflow.

**Phase order: 0 → 1 (fix only) → 2 → 3 → 4. No phase may be skipped except PHASE 1.**

**Language rule:** All generated documents (error docs, GitHub issues, commit reference messages) must be written in the same language the user is using. Detect the user's language from their request and apply it consistently. Exception: the actual git commit message first line always stays in English (conventional commits standard).

---

# PHASE 0: Pre-Work + Analysis

Run all git commands in a single call to minimize tool calls:

```bash
git pull && git status && git log --oneline -5
```

If conflicts or pull failure, inform user and guide resolution.

Then analyze `git diff HEAD` to infer **change type** and **scope**:

**Change type inference:**
- New files → `feat` | Only `.md` → `docs` | Formatting only → `style` | Test files → `test`
- Bug fixes (error handling, null checks) → `fix` | Restructuring → `refactor`
- Build/config/deps → `chore` | Performance → `perf`

**Scope inference from file paths:**
- `hotel-price-updater/...` → `price-updater`
- `unified_extension/popup.*` → `popup` | `unified_extension/content/...` → `content` | `unified_extension/background.*` → `background`
- Root-level → omit scope | Multiple dirs in same project → project-level scope
- If ambiguous, ask the user

Present detected type and scope to user for confirmation, then proceed.

---

# PHASE 1: ERROR DOCUMENTATION (Only for `fix` type — skip otherwise)

1. Analyze the error: root cause, reproduction steps, context
2. Auto-discover error doc directories:
   ```bash
   find . -type d -name "errors" -not -path "*/node_modules/*"
   ```
3. Create error doc in `<project>/errors/ERR-NNN-brief-description.md`:

Write the entire document in **the user's language**. Section headings and content must match the user's language (e.g., Korean if user wrote in Korean).

```markdown
# [ERROR_CODE] 간단한 제목
## 요약
## 근본 원인
## 재현 방법
## 해결책
## 예방 체크리스트
## 관련 파일
```

**Error code ranges:** 001-099 DOM/Selector | 100-199 Network/API | 200-299 Data parsing | 300-399 Auth | 400-499 Channel-specific

If diagnosis is incomplete, mark `Status: 조사 중` (or equivalent in user's language).

---

# PHASE 2: GITHUB ISSUE CREATION

## Auto-skip rules by change type

| Type | Issue creation | Reason |
|------|---------------|--------|
| `feat`, `fix` | **Always create** | Features and bugs need tracking |
| `refactor`, `perf` | **Ask user** | Only significant changes need tracking |
| `docs`, `style`, `chore`, `test` | **Skip → go to PHASE 3** | Low tracking value; commit message is sufficient |

If skipped, proceed directly to PHASE 3 with `Refs: none` (no issue number in commit).

## When creating an issue

Write the issue title and body in **the user's language**.

**Title format:** `type(scope): short description` (append `[ERR-NNN]` for bugs with error docs)

**Pre-creation checks** — run in parallel in a single call:
```bash
gh issue list --search "keyword" --state open --limit 10 && gh label list | grep -q "label-name" || gh label create "label-name" --color "ededed"
```
If duplicate found, ask user whether to reference existing or create new.

**Issue creation:**
```bash
gh issue create --title "type(scope): description" --body "..." --label "label" --assignee @me
```

**Labels:** fix→`bug` | feat→`enhancement` | refactor→`refactor` | docs→`documentation` | style→`style` | test→`test` | chore→`chore` | perf→`performance`

**Body template** (in user's language):
```markdown
## 요약
## 변경 사항
## 관련 파일
```
For `fix`, also include Root Cause and Solution from error doc (in user's language).

Record the issue number for commit references.

---

# PHASE 3: COMMIT (English commit + user-language reference)

## Pre-Commit: Error Doc Check (MANDATORY for all types)

Before creating any commit, check existing error docs for prevention violations:

1. Discover error doc directories:
   ```bash
   find . -type d -name "errors" -not -path "*/node_modules/*" -not -path "*/.git/*"
   ```
2. Read all error docs and review their **Prevention Checklist** sections
3. Cross-check changed files against each checklist — determine if any violation applies
4. Report results before committing:
   - List each error doc checked
   - State whether it's relevant to the current changes (with reason)
   - If a violation is found: **STOP** and fix before committing
   - If no violations: proceed with commit

PHASE 0 already analyzed the diff — reuse that analysis here. Do NOT re-run `git diff` or `git status` unless changes were made after PHASE 0.

**Group by project** if changes span multiple directories. Commit order: Root → hotel-price-updater → unified_extension.

For each group, show both messages then commit:

```
**English (commit):** type(scope): description
**[사용자 언어] (참조):** type(scope): 사용자 언어로 설명
```

The reference message is always in the user's language. If user writes in Korean, show Korean. If English, show English.

**Guidelines:**
- First line under 72 chars, imperative mood
- `Closes #N` or `Refs #N` for related issues
- `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Separate commits for unrelated areas

---

# PHASE 4: PUSH + SUMMARY

**1. Execution Summary:**

```markdown
| Phase | Result |
|-------|--------|
| Pre-Work | branch: `main`, synced, type: `feat(scope)` |
| Error Doc | Skipped / Created ERR-XXX |
| Issue | #N — `type(scope): title` |
| Commit | `type(scope): message` (X files) |
| Push | (pending) |
```

**2. Ask user about push method:**

Use AskUserQuestion:
- header: "Push"
- question: "How to push?"
- options:
  - "Direct push" — `git push origin main` (1인 레포, 빠름)
  - "PR & merge" — 브랜치 생성 → PR → merge (다인 레포, 리뷰 필요 시)
  - "Don't push" — 로컬에만 유지

**3. Execute:**

**Direct push:**
```bash
git push origin main
```

**PR & merge:**
```bash
# 1. Create branch
git checkout -b <type>/<brief-description>

# 2. Push branch
git push -u origin <type>/<brief-description>

# 3. Create PR
gh pr create --title "type(scope): description" --body "..."

# 4. Merge + cleanup
gh pr merge <number> --merge
git checkout main && git pull
git branch -d <type>/<brief-description>
git push origin --delete <type>/<brief-description>
```

- Update summary with push/PR result

---

# WHEN WRITING CODE

Before implementing or modifying code:
1. Check `<project>/errors/` for documented errors
2. Apply prevention checklists from relevant error docs

**Note:** Error doc checks happen at two points — (1) before writing code and (2) before committing (PHASE 3). The PHASE 3 check is the final gate to catch any missed violations.

# FAIL-SAFE

If there are no changes to commit, inform the user that the working directory is clean.
