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
| 0. Analyze | Pull, detect change type & scope from diff |
| 1. Error Doc | Document errors with prevention checklists (fix only) |
| 2. Issue | Create GitHub issue with labels (feat/fix auto, others conditional) |
| 3. Commit | Conventional commit with issue reference |
| 4. Push | Direct push, PR & merge, or skip — your choice |

## Features

- **Auto-detects** commit type (feat/fix/refactor/docs/...) and scope from file paths
- **Error documentation** with auto-numbered codes and prevention checklists
- **Smart issue creation** — always for feat/fix, asks for refactor/perf, skips docs/style/chore/test
- **Bilingual** — commit message in English, reference & docs in your language
- **Pre-commit safety** — checks existing error doc prevention checklists before committing

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
