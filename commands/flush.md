---
name: flush
description: Flush changes through the full pipeline — analyze, error docs, GitHub issue, conventional commit, push/PR. Use for "이슈 만들어", "이슈 커밋", "에러 문서화", "flush it". NOT for simple "커밋해 줘" or "commit this".
argument-hint: "[type]"
---

Full pipeline: error docs → GitHub issue → conventional commit → push/PR.

**Phases:** 0 → 1 (fix only) → 2 (feat/fix always, refactor/perf ask, others skip) → 3 → 4

**Language rule:** All docs, issues, PR bodies in user's language. Commit first line always English.

**Config:** If `.flushrc.json` exists in repo root, load it:
```jsonc
{
  "scopes": { "src/api/**": "api" },   // glob → scope
  "errorDocDir": "./docs/errors",       // default: auto-discover
  "coAuthoredBy": "Claude Opus 4.6 <noreply@anthropic.com>",  // false to disable
  "conflictStrategy": "merge"  // "merge" (default) or "rebase"
}
```

---

# PHASE 0: Pre-Work + Analysis

## 0-1. Preflight + Sync + Diff (ONE bash call)

```bash
GH_OK=true; gh auth status 2>/dev/null && gh repo view --json name -q .name 2>/dev/null || GH_OK=false; echo "---GH:$GH_OK---"; git stash --include-untracked -m "flush-autostash" 2>/dev/null; git pull --rebase 2>&1; git stash pop 2>/dev/null; echo "---SYNC---"; git branch --show-current; echo "---BRANCH---"; git status --porcelain; echo "---STATUS---"; git diff HEAD; echo "---DIFF---"; git ls-files --others --exclude-standard
```

If pull conflicts → stop, guide user. Otherwise parse output into:
- **GH_AVAILABLE**: whether gh CLI + remote are working
- **BRANCH**: current branch name
- **DIFF_SNAPSHOT**: status + diff + untracked files (single source of truth for all phases)

## 0-2. Analyze from DIFF_SNAPSHOT

**Binary / large files:** If detected, warn user inline (don't ask separately — include in the confirmation below).

**Type inference:**

| Signal | Type |
|--------|------|
| New feature files | `feat` |
| Only `.md` | `docs` |
| Formatting only | `style` |
| Test files only | `test` |
| Bug fixes | `fix` |
| Restructuring | `refactor` |
| Build/config/deps | `chore` |
| Performance | `perf` |

**Mixed type tie-breaker:** `fix` > `feat` > `refactor` > `perf` > `chore` > `docs` > `style` > `test`

**Scope:** `.flushrc.json` `scopes` globs → single dir name → repo name → omit. Ask only if truly ambiguous.

**Error doc dir (cache once):** `.flushrc.json` `errorDocDir`, or `find . -type d -name "errors" -not -path "*/node_modules/*" -not -path "*/.git/*"`, or `./errors/`. Store as **ERROR_DIR** — reuse in Phase 1 and 3.

## 0-3. Single confirmation

Present everything at once — ONE AskUserQuestion:
- header: "Flush Plan"
- Show: type, scope, file list, binary warnings (if any)
- question: "Proceed?"
- options: "Yes" / "Change type/scope" / "Cancel"

If user changes type/scope, update and proceed. No re-analysis needed.

---

# PHASE 1: ERROR DOCUMENTATION (fix only — skip otherwise)

1. Determine next error code:
   ```bash
   ls <ERROR_DIR>/ERR-*.md 2>/dev/null | sed 's/.*ERR-\([0-9]*\).*/\1/' | sort -n | tail -1
   ```
   Increment from highest. Ranges: 001-099 DOM | 100-199 Network | 200-299 Data | 300-399 Auth | 400+ Channel.

2. Create `<ERROR_DIR>/ERR-NNN-brief-description.md` in user's language:
   ```markdown
   # [ERROR_CODE] 제목
   ## 요약
   ## 근본 원인
   ## 재현 방법
   ## 해결책
   ## 예방 체크리스트
   ## 관련 파일
   ```
   If incomplete, mark `Status: 조사 중`.

3. **Append** the new filename to DIFF_SNAPSHOT (no git re-run needed).

---

# PHASE 2: GITHUB ISSUE CREATION

Skip entirely if: GH_AVAILABLE is false, or type is `docs`/`style`/`chore`/`test`.
For `refactor`/`perf`: ask user (combine with Phase 0 confirmation if possible).

**Single bash call** — duplicate check + label ensure + create:
```bash
gh issue list --search "<2-3 key terms>" --state open --limit 5; gh label list | grep -q "<label>" || gh label create "<label>" --color "<color>"; gh issue create --title "type(scope): desc" --body "..." --label "<label>" --assignee @me
```

If duplicate found in output → ask user before the create command.

**Labels:** fix→`bug` | feat→`enhancement` | refactor→`refactor` | docs→`documentation` | style→`style` | test→`test` | chore→`chore` | perf→`performance`

**Body** (user's language): 요약 + 변경사항 + 관련파일. For `fix`, add root cause + solution from error doc.

Record issue number.

---

# PHASE 3: COMMIT

## 3-1. Pre-commit error doc check (relevant docs only)

From **ERROR_DIR**, check only error docs whose **관련 파일** section overlaps with DIFF_SNAPSHOT changed files. Skip unrelated docs entirely.

- If violation found → **STOP**, fix first.
- If no relevant docs or no violations → proceed.

## 3-2. Stage + Commit (ONE bash call per commit group)

Group by touched top-level directories (alphabetical, root first). For each group:

```
**English (commit):** type(scope): description
**[사용자 언어] (참조):** type(scope): 설명
```

```bash
git add <files> && git commit -m "$(cat <<'EOF'
type(scope): description

Closes #N

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

- Co-Authored-By: from `.flushrc.json`, or default, or omit if `false`.
- First line < 72 chars, imperative mood.
- Separate commits for unrelated areas only.

---

# PHASE 4: PUSH + SUMMARY

**Summary table:**
```markdown
| Phase | Result |
|-------|--------|
| Pre-Work | branch: `<BRANCH>`, type: `type(scope)` |
| Error Doc | Skipped / Created ERR-XXX |
| Issue | #N / Skipped |
| Commit | `type(scope): msg` (X files) |
| Push | (pending) |
```

**Ask push method** (AskUserQuestion):
- "Direct push" → `git push origin <BRANCH>`
- "PR & merge" → branch + push + PR + merge + cleanup
- "Don't push" → done

**PR flow:**
```bash
git checkout -b <type>/<desc> && git push -u origin <type>/<desc> && gh pr create --title "type(scope): desc" --body "..."
```
After PR created, attempt merge:
```bash
gh pr merge <N> --merge
```

**If merge conflict** — use `.flushrc.json` `conflictStrategy` (default: `merge`):

**merge (default):**
1. Base를 feature에 merge:
   ```bash
   git checkout <type>/<desc> && git fetch origin <BRANCH> && git merge origin/<BRANCH>
   ```
2. Show conflict files, guide resolution
3. `git add <resolved-files> && git commit`
4. `git push origin <type>/<desc>`
5. Retry: `gh pr merge <N> --merge`

**rebase:**
1. Feature 커밋을 base 위로 재배치:
   ```bash
   git checkout <type>/<desc> && git fetch origin <BRANCH> && git rebase origin/<BRANCH>
   ```
2. Rebase 중 충돌 시 — 각 커밋마다 해결:
   - Show conflict files, guide resolution
   - `git add <resolved-files> && git rebase --continue`
   - 모든 커밋 완료될 때까지 반복
3. `git push --force-with-lease origin <type>/<desc>`
4. Retry: `gh pr merge <N> --merge`

**If merge succeeds:**
```bash
git checkout <BRANCH> && git pull && git branch -d <type>/<desc> && git push origin --delete <type>/<desc>
```

---

# FAIL-SAFE

- No changes → inform user, exit.
- No gh CLI → skip Phase 2 + Phase 4 PR option, local commit still works.
