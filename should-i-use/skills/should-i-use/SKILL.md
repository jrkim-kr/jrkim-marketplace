---
name: should-i-use
description: Use when evaluating an external tool, repo, agent collection, MCP server, npm package, or skill against the user's project portfolio and existing Claude Code stack. Triggered by GitHub URLs, "이거 쓸만해?", "X 평가해 줘", "X 도입해야 돼?", "should I install X?", "should I use X", or any first-look assessment of a new external dependency before adoption.
---

# Should I Use

## Overview

Standardize evaluation of external tools against a **user persona profile** and the existing Claude Code stack. Produces a single scannable report with an explicit verdict — INSTALL / TRY-INLINE / SKIP / WAIT-FOR-TRIGGER — instead of a multi-turn conversation.

Every report is generated against the persona profile (see **Persona** below). On first run the skill establishes that profile; later runs load it. Without a structured evaluation, every new tool turns into a 5-turn back-and-forth and the same blind spots recur — especially **hindsight retrofit** (using a known past failure to inflate the tool's apparent prescience).

## Persona — run this first

Before producing any report, resolve the user persona. The persona drives project paths, response language, risk framing, and the Honest Self-Check anchor — nothing in the report is hardcoded to one person.

**Profile location:** `~/.claude/state/should-i-use/profile.md`

**Resolution logic:**

1. **Profile file exists** → read it, skip to evaluation.
2. **Profile file missing** → first run. Check `~/.claude/CLAUDE.md` for substantive role/context:
   - **Present and substantive** → *owner path*: auto-draft the profile from `~/.claude/CLAUDE.md` plus any auto-memory (`~/.claude/projects/*/memory/MEMORY.md` and linked files). Present the draft to the user, let them confirm or edit, then write the profile file.
   - **Absent or sparse** → *new-user path*: ask exactly 3 questions in one message, then build and write the profile:
     1. Identity — your name, role, and work context (one or two sentences).
     2. Project roots — directory glob(s) to scan for portfolio match (e.g. `~/Projects/*`).
     3. Response language — preferred output language, and any format convention to follow.
3. Proceed to evaluation using the resolved persona.

Detection keys on whether `CLAUDE.md` is substantive, not on any name — renaming yourself never breaks it, and a mis-route is caught by the confirm step, so detection only affects UX, not correctness.

**Profile schema** (the file the skill writes — create the directory if needed):

```
# should-i-use — user persona
Last updated: YYYY-MM-DD

- Identity: <name, role, employment/work context>
- Project roots: <glob(s) for the Portfolio Match scan>
- Response language: <output language + any format convention, e.g. ADEPT-T>
- Iteration-loop tooling: <runtime-feedback loop, e.g. flush + ERR + CONFLICT_PATTERNS; or "none">
- Primary adoption risk: <the user's #1 adoption risk, e.g. over-investment / over-engineering>
- Known evaluation blind spots: <anchor for Honest Self-Check; default "hindsight retrofit">
```

For the new-user path, fill Identity / Project roots / Response language from the 3 answers; default Iteration-loop tooling to "none", Primary adoption risk to "over-adoption", Known evaluation blind spots to "hindsight retrofit". To refresh a stale profile, delete the file and re-run.

## When to Use

- User shares a GitHub URL, npm package, MCP server, or new tool name
- User asks "이거 쓸만해?", "X 평가해 줘", "X 도입해야 돼?", "should I install X?", "should I use X"
- Before recommending any external tool/agent/skill in any response
- When a previously-mentioned tool needs re-assessment after time has passed

**Do NOT use for:**
- The user's own existing projects (use `codebase-onboarding` instead)
- Debugging tools already adopted
- "What tool exists for X?" discovery questions (use `find-skills` instead)
- Comparing two tools head-to-head (run this skill twice, separately)

## Inputs Accepted

- GitHub repo URL: `https://github.com/owner/repo`
- npm package name: `@scope/name` or `package-name`
- Local skill/agent path: `~/.claude/skills/foo`, `~/.claude/agents/foo.md`
- MCP server config or installation instructions
- Bare tool name to research (web search permitted within time cap)

## Time Cap: 5 Minutes

Discovery is capped at 5 minutes wall-clock. Do not exhaustively read every file. Sample strategically:
- README only (skip CHANGELOG, CONTRIBUTING, LICENSE)
- Directory listing for shape (counts, not contents)
- 1-2 representative artifact files to feel "the shape of the thing"

If 5 minutes runs out, **stop and write "Discovery incomplete — needs deeper dive on [specific question]" in the Verdict section**. Do not silently truncate.

## Required Report Structure

Output must contain ALL 8 sections in this order. Missing any section = invalid output, restart. Render section labels and prose in the persona's response language; the English template below is the structural scaffold.

```
# 🔎 Should-I-Use REPORT — [tool name]
Date: YYYY-MM-DD  |  Target: [URL or path]

## 🎯 Essence
- Type: [framework | agent-pack | MCP | skill | library | template | tool]
- One-line essence: [one plain-language sentence, no identifiers]
- Maturity: [stars · last-commit · active maintainer count]

## 📦 Inventory
- Concrete artifacts: N [count of agents/commands/files]
- Size estimate: [LOC or file count or package size]
- Dependencies: [core deps only, no full list]

## 💎 Worth Stealing
2-3 non-obvious design patterns worth learning even without adopting. Kept separate from the adoption decision.

## 🎬 Use Cases
2-3 concrete scenarios. Each: trigger → artifact → value.

## 🧩 Portfolio Match
auto-scan the persona's project roots, e.g.:
  for d in <project-roots>/; do git -C "$d" log -1 --format="%ar" 2>/dev/null; done

| Project | Tier (S/A/B/Skip) | Reason (one sentence) |
|---|---|---|
| ... | ... | ... |

Attach one copy-paste-ready starter prompt to each of the Top 3 (Tier S/A).

## 🔗 Stack Integration
auto-scan: `ls ~/.claude/{agents,skills}` + currently active plugins

- **Layer**: where it sits relative to the user's existing stack — derive the stack from the scan plus the persona, do not assume a fixed set
- **Overlap/conflict**: any feature overlap with existing tools (state it if present)
- ❌ **Anti-rec**: a combination that should NOT be used together (mandatory, at least 1)

## 🪞 Honest Self-Check
This section missing = invalid result.

- **Question**: "If I did not already know the user's [past failure / blind spot], would the tool's normal output have produced that insight?"
- ✅ Defect classes caught by upfront specification: [...]
- ❌ Defect classes caught only by iteration: [...]
- **Iteration-loop contact test first**: does the tool take runtime artifacts (logs, errors, test failures, traces, monitoring) as input?
  - Yes → it may overlap the persona's iteration-loop tooling. Name the overlapping area explicitly.
  - No (a pre-iteration tool for design/planning/interview, used before code runs) → the comparison is structurally moot. Close in one line: `iteration-loop overlap: N/A — pre-iteration tool`. No forced paragraph.
  - If the persona's iteration-loop tooling is "none" → skip the overlap analysis and say so in one line.

## 🚀 Verdict
- Decision: **INSTALL** | **TRY-INLINE** | **SKIP** | **WAIT-FOR-TRIGGER**
- First action: [one concrete command or starter prompt]
```

## Enforcement Rules

### 1. Honest Self-Check Gate (Non-Skippable)

Hindsight retrofit is a recurring evaluation failure: using a known past failure to make the tool look prescient. Every evaluation must explicitly answer: "If I did not already know the past failure, would the tool's normal output produce this insight?" Anchor the question on the persona's **Known evaluation blind spots** field (default: hindsight retrofit).

Defect classes the tool catches upfront vs. only via iteration must be separated. Iteration-only defects belong to the persona's iteration-loop tooling — don't claim a new tool covers them. If that field is "none", say the iteration coverage is unowned rather than assigning it.

### 2. Effect-First Language

Lead with the effect in plain language. Identifiers (function names, file paths) trail in backticks. Never open a description with an identifier.

❌ "`workflow-architect` provides handoff contracts"
✅ "Forces data hand-off rules between services to be specified (`workflow-architect`)"

If the persona's response language records a format convention (e.g. ADEPT-T — plain description first, term as a trailing anchor), follow it.

### 3. Anti-Rec Is Mandatory

The Stack Integration section must include ≥1 explicit "don't combine with X" warning — even if minor. Frame the risk against the persona's **Primary adoption risk** field. Empty Anti-rec = invalid report.

### 4. Verdict Is One Word

INSTALL / TRY-INLINE / SKIP / WAIT-FOR-TRIGGER. No "maybe", "depends on", "consider". If genuinely uncertain, use WAIT-FOR-TRIGGER and name the trigger condition explicitly.

### 5. Response Language Rule

Output in the persona's **Response language**, and apply any format convention recorded there. If the user's current turn is clearly in a different language, match that turn instead.

## Discovery Workflow

```
0. Resolve persona (see Persona section) — load or create the profile.
1. Classify input type (URL / npm / local path / name)
2. Inspect (5-min cap):
   - GitHub: gh api repos/owner/repo + curl README + ls top-level dirs
   - npm: npm view <pkg> + check package.json deps
   - Local skill: cat SKILL.md
   - Local agent: cat agent.md
   - MCP: read config + check server source if linked
3. Portfolio scan (parallel) — persona's project roots:
   for d in <project-roots>/; do
     git -C "$d" log -1 --format="%ar" 2>/dev/null
   done
4. Stack scan (parallel):
   ls ~/.claude/agents/ ~/.claude/skills/
5. Apply 8-section template — fill ALL sections
6. Honest Self-Check gate — verify it answers the hindsight question
7. Single-word verdict
```

Steps 2-4 should be parallelized via parallel tool calls — they are independent.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Skipping persona resolution | Load or create the profile before any report. |
| Skipping Honest Self-Check | Section 7 is non-negotiable. Answer the hindsight question explicitly. |
| Using a past failure as "proof" the tool would have caught it | Hindsight retrofit. Restart Section 7 with the proper question. |
| Recommending without Anti-rec | Every report needs ≥1 "don't combine with X". |
| Verdict softened ("maybe install?", "could be useful") | Pick one of 4 verbs. Ambiguous = WAIT-FOR-TRIGGER + name trigger. |
| Identifier-led prose | Plain effect first, identifier in backticks at end. |
| Multi-turn evaluation | One invocation = one complete 8-section report. Don't split. |
| Time uncapped on big repos | 5-minute hard cap. Note "incomplete" in Verdict if hit. |
| Portfolio match skipped | Auto-scan the persona's project roots even if the user named no specific project. |

## Red Flags — STOP and Restart

- About to produce a report without resolving the persona profile
- About to recommend without a project-portfolio cross-reference
- About to cite a past failure as evidence the tool would have prevented it
- Verdict contains "consider", "might be useful", "could help", "depends"
- Anti-rec section is empty
- More than one identifier appears before any plain-language sentence
- Section count ≠ 8
- "I think" or "probably" appears in Verdict line

All of these mean: stop, restart with the template, fill every section.

## Cross-Reference

- `find-skills` (skill) — use when the user wants discovery, not evaluation
- `codebase-onboarding` (skill) — use for the user's own existing projects
- `superpowers:brainstorming` — use AFTER this skill if Verdict is INSTALL and the tool needs design integration work
- Persona profile: `~/.claude/state/should-i-use/profile.md` — delete it to refresh
