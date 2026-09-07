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

**Binary / large files:** If detected, note in the plan log (no separate prompt).

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

## 0-3. Log plan (no confirmation)

Print the analysis result inline (type, scope, file list, binary warnings if any) so the user can see what was detected, then proceed immediately. Do NOT ask for confirmation here.

---

# PHASE 1: ERROR DOCUMENTATION (fix only — skip otherwise)

1. Determine next error code. **Count the remote, not just your local directory.**

   ```bash
   BASE=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
   git fetch -q origin 2>/dev/null
   { git ls-tree -r --name-only "$BASE" -- <ERROR_DIR> 2>/dev/null
     gh pr list --state open --json files --jq '.[].files[].path' 2>/dev/null
     ls <ERROR_DIR>/ERR-*.md 2>/dev/null
   } | grep -oE 'ERR-[0-9]+' | sort -u -t- -k2 -n | tail -1
   ```

   Increment from highest. Ranges: 001-099 DOM | 100-199 Network | 200-299 Data | 300-399 Auth | 400+ Channel.

   **Why three sources, not one.** The numbering rule ("count the highest, take the
   next, no gaps") *forces* every concurrently-open branch to pick the same number.
   Collisions are the default, not the exception. A local `ls` sees neither the
   branches other people have open nor what landed on the base branch since you last
   pulled — and the colliding file **is not in your checkout**, so local tests stay
   green and only CI goes red, ten minutes after you push.

   In one repo this happened **fifteen times**. Five of those, the number was held by
   an open PR that `ls` could never have shown.

   **Do not trim the inputs.** No `head -N` on the branch or PR listing. Truncating
   the input to a max-finding computation makes the answer silently smaller, and a
   too-small answer looks exactly like a correct one. (One incident: `head -60` cut
   off the branch holding the number — its name literally contained `err-364`.)

   Each source degrades on its own: no remote, no `gh`, not a git repo — that source
   contributes nothing and the others still count. **Say which sources answered**, so
   "checked, it's free" is never confused with "couldn't check."

   **Count again right before merging.** Merging does not re-run CI, so if someone
   takes your number between your green check and your merge, both PRs stay green and
   the base branch goes red. This is the one moment no file-creation hook can cover.

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
For `refactor`/`perf`: create issue automatically (no confirmation needed).

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
