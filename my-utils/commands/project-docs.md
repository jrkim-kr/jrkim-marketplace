---
description: Analyze the latest codebase and update all project documentation (.md, .sql) under docs/. Validates structure, naming, and keeps docs in sync with code
---

# Project Documentation Updater

Analyze the codebase → validate docs structure → update all documents → verify quality → generate changelog.

---

## Phase 0: User Preferences

Ask the user via a single `AskUserQuestion` with two questions:

**Q1 — Language:** English (Recommended) / Korean / Other
**Q2 — Diagram Style:** Mermaid (Recommended) / ASCII

Store as `DOC_LANG` and `DIAGRAM_STYLE`.

- **English**: Clear, concise technical writing.
- **Korean**: Technical terms with English annotations (e.g., State Management)
- **Mermaid**: Fenced code blocks with `mermaid` tag (`flowchart`, `sequenceDiagram`, `erDiagram`, `stateDiagram-v2`)
- **ASCII**: Box-drawing characters (`─│┌┐└┘├┤┬┴┼`, `→←↑↓`)

---

## Docs Folder Convention

Core documents live directly under `docs/` (flat). Subdirectories are only used for multi-file collections.

```
project-root/
├── README.md
└── docs/
    ├── mvp-prd.md              # Product Requirements Document
    ├── spec.md                 # Feature Specification
    ├── system-design.md        # System Design + ADRs
    ├── checklist.md            # Unified Implementation Checklist
    ├── workflow-state.md       # Workflow State (auto-generated)
    ├── schema/                 # DB definitions (.sql), ERD, data models
    │   ├── schema-overview.md
    │   └── migrations/
    ├── test/                   # Test reports and manual test cases
    │   ├── test-report.md
    │   └── manual-test-case.md
    ├── guides/                 # Setup and user guides
    │   ├── setup-guide-developer.md
    │   └── setup-guide-end-user.md
    └── errors/                 # Error documentation
        └── ERR-NNN-description.md
```

**Naming**: `lowercase-kebab-case.md/.sql`. No underscores. Exception: root `README.md`.

**New document template:**
```markdown
# {Title}
> **Version**: v1.0 | **Last modified**: {date} | **Language**: {DOC_LANG}
---
```

**Required sections by type:**

| Type | Sections |
|------|----------|
| PRD (mvp-prd.md) | Executive Summary, User Experience, Functional Requirements, Non-Functional, Risks |
| Spec (spec.md) | System Overview, State Flows, Per-Feature Specs, Page Map |
| Design (system-design.md) | Architecture Diagram, Tech Stack, Data Flow, ADRs, Security |
| Checklist (checklist.md) | Phase-by-phase tasks with checkboxes, Completion Criteria |
| Schema | Table Definitions, ENUMs, Relationships, Indexes |
| Guide | Prerequisites, Step-by-Step Instructions, Troubleshooting |
| Error Doc | Summary, Root Cause, Reproduction Steps, Solution, Prevention |

---

## Phase 1: Codebase Analysis

Use Agent tool with Explore agents to parallelize.

1. **Project scan** — Read `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` etc. Scan source dirs. Extract routes.
2. **Git diff** — `git log --oneline -20`. Identify added/deleted/moved files.
3. **Doc inventory** — List and read all files under `docs/` and root `README.md`.
4. **Find discrepancies** — Code without docs, docs without code, changed APIs/models/env vars.

## Phase 2: Structure Validation

1. Verify core docs are flat under `docs/` (not in unnecessary subdirectories)
2. Verify multi-file collections use subdirectories (schema/, test/, guides/, errors/)
3. Fix naming: underscores → hyphens, enforce kebab-case
4. Report corrections to user

## Phase 3: Document Updates

**Diff preview**: Collect all changes, present as a single grouped diff via `AskUserQuestion`. Options: **Apply all** / **Select files to skip** / **Cancel**. One interaction, not per-file.

**Update rules per document type:**

| Document | Key Checks |
|----------|------------|
| **spec.md** | Pages/features match code, API paths/methods/formats match, state flows match, page map matches routing |
| **checklist.md** | Mark completed items, update altered approaches, add new phases |
| **setup-guide-developer.md** | Env var list matches code, integration steps current, new integrations added |
| **schema (migrations)** | Matches DB state, type definitions align with columns, new tables/columns reflected |
| **system-design.md** | Component diagrams match modules, tech stack matches deps, data flow current, ADRs up to date |
| **README.md** | Project description current, install/run instructions accurate, docs links valid |

## Phase 4: Quality Verification

### 4-1. Broken Links
Scan all `[text](path)` and `#anchor` references. Verify targets exist.

### 4-2. Terminology & Consistency
Extract key terms (table names, API endpoints, feature names, env vars) across all docs. Code is source of truth. Auto-fix unambiguous mismatches; flag ambiguous ones for manual review.

### 4-3. Missing Cross-References
If a feature/API/table appears in one doc but related docs don't reference it, suggest adding links.

### 4-4. Duplicate Detection & Consolidation
Detect same-topic content in multiple files (e.g., env var list in both guide and spec, or identical tables across docs). Criteria: **same topic's table/list/section exists in 2+ documents**.
- Identify canonical location per content type
- Present: `| Content | Found In | Canonical Location |` table
- Options: **Consolidate all** / **Review each** / **Skip**
- On approval: keep full content in canonical file, replace others with cross-reference link
- Also detect entirely duplicate documents and suggest merging

### 4-5. Completeness Check
Verify required header (Version, Last modified) and type-specific required sections exist.

---

## CHANGELOG

Auto-update `docs/changelog.md` after every execution that modifies documents. Create if missing. Format: `## [{date}]` with `Added` / `Modified` / `Removed` / `Structural` subsections. Newest first, one line per change. Exclude changelog from diff previews.

---

## Writing Rules

1. **Code-based facts only** — No speculation.
2. **Use `DOC_LANG` and `DIAGRAM_STYLE`** throughout.
3. **Tables** for structured data.
4. **Timestamps** — Update `Last modified` on every changed document.
5. **Minimal diff** — Only change what needs updating. No cosmetic reformatting.
6. **Version bump** — Minor: v2.0→v2.1, Major: v2.1→v3.0.
7. **No duplicates** — One canonical location per fact. Others cross-reference.

---

## Completion Report

Present in `DOC_LANG`:

```
## Documentation Update Report
### Settings
- Language: {DOC_LANG} | Diagram: {DIAGRAM_STYLE}
### Structure Changes
- {moves, renames}
### Document Changes
| Document | Type | Summary |
|----------|------|---------|
### Quality Results
| Check | Status |
|-------|--------|
| Broken links | ✅ / ⚠️ {n} |
| Terminology | ✅ / ⚠️ {n} |
| Cross-refs | ✅ / ⚠️ {n} |
| Duplicates | ✅ / ⚠️ {n} |
| Completeness | ✅ / ⚠️ {n} |
### Manual Review Needed
- {unresolved items}
```

If new document types are needed: ask user via `AskUserQuestion` before creating.
