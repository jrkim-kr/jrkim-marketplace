# flush

> Flush your changes through the full pipeline in one command.

A Claude Code plugin that runs the complete commit workflow:

```
/flush
```

**diff analysis → error docs → GitHub issue → conventional commit → push/PR**

## What it does

| Phase | Action |
|-------|--------|
| 0. Analyze | Preflight + sync + diff in one call, detect type & scope |
| 1. Error Doc | Document errors with auto-numbered codes and prevention checklists (fix only) |
| 2. Issue | Create GitHub issue with labels (feat/fix auto, refactor/perf conditional, others skip) |
| 3. Commit | Pre-commit error doc check, stage, conventional commit with issue reference |
| 4. Push | Direct push, PR & merge, or skip — your choice |

## Features

- **Single confirmation** — one "Flush Plan" prompt instead of multiple interruptions
- **Auto-detects** commit type and scope from diff (with priority tie-breaker for mixed changes)
- **Configurable** via `.flushrc.json` — custom scope mappings, error doc path, co-author trailer
- **Error documentation** with auto-numbered codes, collision avoidance, and prevention checklists
- **Smart issue creation** — always for feat/fix, asks for refactor/perf, skips the rest
- **Bilingual** — commit message in English, all docs & issues in your language
- **Pre-commit safety** — checks relevant error doc prevention checklists before committing
- **Graceful degradation** — works without GitHub CLI (skips issue/PR, local commit still works)
- **Optimized** — minimized bash calls (3-4 total) and token-efficient prompt

## Configuration

Create `.flushrc.json` in your repo root (all fields optional):

```jsonc
{
  // glob → scope mapping (overrides auto-detection)
  "scopes": {
    "src/api/**": "api",
    "src/components/**": "ui"
  },
  // error doc directory (default: auto-discover "errors" dirs)
  "errorDocDir": "./docs/errors",
  // Co-Authored-By trailer (false to disable, or string to customize)
  "coAuthoredBy": "Claude Opus 4.6 <noreply@anthropic.com>"
}
```

## Install

```bash
claude plugin install flush@claude-plugins-official
```

## Usage

```bash
# In any git repo with uncommitted changes:
/flush

# Optionally specify type:
/flush fix
```

## License

MIT
