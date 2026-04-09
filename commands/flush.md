---
name: flush
description: Flush changes through the full pipeline — analyze, error docs, GitHub issue, conventional commit, push/PR. Use for "이슈 만들어", "이슈 커밋", "에러 문서화", "flush it". NOT for simple "커밋해 줘" or "commit this".
argument-hint: "[type]"
---

You handle error documentation, GitHub issue creation, and commit message generation — all in one workflow.

**Phase order: 0 → 1 → 2 → 3 → 4.**
- PHASE 1: skipped unless type is `fix`
- PHASE 2: skipped for `docs`, `style`, `chore`, `test`; conditional for `refactor`, `perf`

**Language rule:** All generated documents (error docs, GitHub issues, commit reference messages) must be written in the same language the user is using. Detect the user's language from their request and apply it consistently. Exception: the actual git commit message first line always stays in English (conventional commits standard).

---

# CONFIGURATION (Optional)

If `.flushrc.json` exists in the repo root, load it. Otherwise use defaults.

```jsonc
{
  // glob → scope mapping (overrides auto-detection)
  "scopes": {
    "src/api/**": "api",
    "src/components/**": "ui"
  },
  // error doc directory (default: auto-discover "errors" dirs)
  "errorDocDir": "./docs/errors",
  // Co-Authored-By trailer (set false to disable, or string to customize)
  "coAuthoredBy": "Claude Opus 4.6 <noreply@anthropic.com>"
}
```

All fields are optional. Missing fields fall back to built-in defaults.

---

# PHASE 0: Pre-Work + Analysis

## 0-1. Preflight checks

Run in a single call:
```bash
gh auth status 2>&1 && gh repo view --json name -q .name 2>&1 && git status --porcelain && git branch --show-current
```

- If `gh auth` fails → warn user: "GitHub CLI not authenticated. Issue creation and PR will be skipped."
- If `gh repo view` fails → warn: "Not a GitHub repo or no remote. Issue/PR phases will be skipped."
- Record current branch name for later (don't assume `main`).

## 0-2. Sync

```bash
git stash --include-untracked -m "flush-autostash" 2>/dev/null; git pull --rebase; git stash pop 2>/dev/null
```

If conflicts after pull, inform user and guide resolution. Do NOT proceed until resolved.

## 0-3. Diff snapshot

Capture the full diff snapshot once — reuse it in all subsequent phases:

```bash
git diff HEAD && git diff --cached && git ls-files --others --exclude-standard
```

Store the output as **DIFF_SNAPSHOT**. This is the single source of truth for the rest of the pipeline. Re-run only if new files are created during PHASE 1 or PHASE 2.

## 0-4. Binary / large file check

From DIFF_SNAPSHOT, detect:
- Binary files (images, compiled assets)
- Files > 1MB

If found, warn user and ask whether to include or exclude them from the commit.

## 0-5. Change type and scope inference

From DIFF_SNAPSHOT, infer **change type**:

| Signal | Type |
|--------|------|
| New feature files | `feat` |
| Only `.md` files | `docs` |
| Formatting only (whitespace, semicolons) | `style` |
| Test files only | `test` |
| Error handling, null checks, bug fixes | `fix` |
| Restructuring without behavior change | `refactor` |
| Build/config/deps | `chore` |
| Performance improvements | `perf` |

**Mixed changes tie-breaker:** If changes span multiple types, pick the **most impactful** type in this priority: `fix` > `feat` > `refactor` > `perf` > `chore` > `docs` > `style` > `test`. If still ambiguous, ask the user.

**Scope inference:**
1. If `.flushrc.json` has `scopes` mapping, match changed file paths against globs — use first match.
2. Otherwise auto-detect from top-level directory names:
   - Changes in a single directory → directory name as scope (e.g., `src/api/...` → `api`)
   - Changes in multiple directories under the same project → project-level scope (= repo name or top-level dir)
   - Root-level files only → omit scope
3. If still ambiguous, ask the user.

Present detected type and scope to user for confirmation, then proceed.

---

# PHASE 1: ERROR DOCUMENTATION (Only for `fix` type — skip otherwise)

1. Analyze the error from DIFF_SNAPSHOT: root cause, reproduction steps, context
2. Discover error doc directory:
   - If `.flushrc.json` has `errorDocDir` → use it
   - Otherwise: `find . -type d -name "errors" -not -path "*/node_modules/*" -not -path "*/.git/*"`
   - If no directory found → create `./errors/`
3. Determine next error code number:
   ```bash
   ls <error-dir>/ERR-*.md 2>/dev/null | sed 's/.*ERR-\([0-9]*\).*/\1/' | sort -n | tail -1
   ```
   Increment from the highest existing number. If none exist, start from the appropriate range.

4. Create error doc in `<error-dir>/ERR-NNN-brief-description.md`:

Write the entire document in **the user's language**.

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

**After creating the error doc, re-capture DIFF_SNAPSHOT** since a new file was added.

---

# PHASE 2: GITHUB ISSUE CREATION

If preflight (PHASE 0-1) detected no GitHub CLI or no remote, **skip this phase entirely**.

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

**Step 1 — Duplicate check:**
Extract 2-3 key terms from the change description, then:
```bash
gh issue list --search "<key terms>" --state open --limit 5
```
If a likely duplicate is found, ask user whether to reference existing or create new.

**Step 2 — Ensure label exists:**
```bash
gh label list | grep -q "<label-name>" || gh label create "<label-name>" --color "<color>"
```

**Label mapping:** fix→`bug`(d73a4a) | feat→`enhancement`(a2eeef) | refactor→`refactor`(ededed) | docs→`documentation`(0075ca) | style→`style`(ededed) | test→`test`(ededed) | chore→`chore`(ededed) | perf→`performance`(f9d0c4)

**Step 3 — Create issue:**
```bash
gh issue create --title "type(scope): description" --body "..." --label "<label>" --assignee @me
```

**Body template** (in user's language):
```markdown
## 요약
## 변경 사항
## 관련 파일
```
For `fix`, also include Root Cause and Solution from error doc.

Record the issue number for commit references.

---

# PHASE 3: COMMIT (English commit + user-language reference)

## 3-1. Staging

Show the user which files will be staged:
```
Staged files:
  M  src/api/handler.ts
  A  errors/ERR-101-timeout.md
  ?  src/utils/new-helper.ts  (untracked)
```

Ask user to confirm, or let them exclude files. Then stage:
```bash
git add <confirmed-files>
```

## 3-2. Pre-Commit: Error Doc Check (MANDATORY for all types)

Before creating any commit, check existing error docs for prevention violations:

1. Discover error doc directories (use `.flushrc.json` `errorDocDir` or auto-discover)
2. Read all error docs and review their **Prevention Checklist** sections
3. Cross-check changed files (from DIFF_SNAPSHOT) against each checklist
4. Report results before committing:
   - List each error doc checked
   - State whether it's relevant to the current changes (with reason)
   - If a violation is found: **STOP** and fix before committing
   - If no violations: proceed with commit

## 3-3. Commit

**Group by project** if changes span multiple directories. Order: sort touched top-level directories alphabetically. Root-level files come first.

For each group, show both messages then commit:

```
**English (commit):** type(scope): description
**[사용자 언어] (참조):** type(scope): 사용자 언어로 설명
```

The reference message is always in the user's language.

**Guidelines:**
- First line under 72 chars, imperative mood
- `Closes #N` or `Refs #N` for related issues
- Co-Authored-By trailer: use `.flushrc.json` `coAuthoredBy` value, or default `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`. If set to `false`, omit.
- Separate commits for unrelated areas

---

# PHASE 4: PUSH + SUMMARY

**1. Execution Summary:**

```markdown
| Phase | Result |
|-------|--------|
| Pre-Work | branch: `<branch>`, synced, type: `type(scope)` |
| Error Doc | Skipped / Created ERR-XXX |
| Issue | #N — `type(scope): title` / Skipped (no gh) |
| Commit | `type(scope): message` (X files) |
| Push | (pending) |
```

**2. Ask user about push method:**

Use AskUserQuestion with the current branch name (not hardcoded `main`):
- header: "Push"
- question: "How to push?"
- options:
  - "Direct push" — `git push origin <current-branch>`
  - "PR & merge" — create branch → PR → merge
  - "Don't push" — keep local only

**3. Execute:**

**Direct push:**
```bash
git push origin <current-branch>
```

**PR & merge:**
```bash
# 1. Create branch (skip if already on a feature branch)
git checkout -b <type>/<brief-description>

# 2. Push branch
git push -u origin <type>/<brief-description>

# 3. Create PR
gh pr create --title "type(scope): description" --body "..."

# 4. Merge + cleanup
gh pr merge <number> --merge
git checkout <base-branch> && git pull
git branch -d <type>/<brief-description>
git push origin --delete <type>/<brief-description>
```

- Update summary with push/PR result

---

# WHEN WRITING CODE

Before implementing or modifying code:
1. Check error doc directory for documented errors
2. Apply prevention checklists from relevant error docs

**Note:** Error doc checks happen at two points — (1) before writing code and (2) before committing (PHASE 3-2). The PHASE 3-2 check is the final gate to catch any missed violations.

# FAIL-SAFE

- If there are no changes to commit (no modified, staged, or untracked files), inform the user that the working directory is clean.
- If GitHub CLI is not available, skip PHASE 2 and PHASE 4 PR options gracefully — still allow local commit.
