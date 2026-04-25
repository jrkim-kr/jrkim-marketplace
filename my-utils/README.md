# my-utils

A bundle of deterministic utility slash commands used in daily work. Previously these lived as global skills under `~/.claude/skills/`; they were migrated to a plugin because each one is explicitly invoked (not contextually triggered) and they benefit from version control.

## Commands

| Command | Purpose |
|---------|---------|
| `/daily-scrum` | Generate a Korean daily-scrum summary from today's git commits across all repos |
| `/follow-builders` | AI Builders Digest — fetch, remix, and deliver posts/podcasts from tracked AI builders (also invokable via `/ai` once aliased) |
| `/notion-ai-report <pdf>` | Read a local AI report PDF and create a Notion "AI Report Study" entry with PM-framework study notes |
| `/notion-wrap [category]` | Save the current Claude Code conversation to the "AI Practices" Notion database in Korean |
| `/project-docs` | Analyze the codebase and sync all docs under `docs/` (structure, naming, cross-refs, changelog) |
| `/project-screenshots [path] [user:pass]` | Auto-discover routes, run the dev server, and capture public + authenticated screenshots |
| `/translate-docs [lang]` | Translate all `.md` and `.txt` files in the current dir between Korean and English |

## Structure

```
my-utils/
├── .claude-plugin/plugin.json
├── commands/                      # slash command prompts
│   ├── daily-scrum.md
│   ├── follow-builders.md
│   ├── notion-ai-report.md
│   ├── notion-wrap.md
│   ├── project-docs.md
│   ├── project-screenshots.md
│   └── translate-docs.md
├── follow-builders/               # bundled feeds, prompts, scripts
├── notion-ai-report/              # bundled Python scripts
└── project-screenshots/           # bundled puppeteer capture script
```

Asset paths inside commands use `${CLAUDE_PLUGIN_ROOT}` which Claude Code resolves to the plugin install directory at invocation time.

## Install

This plugin is part of the local marketplace `jrkim-marketplace` at `/Users/jrkim/Projects/jrkim-marketplace`. Install via:

```
/plugin install my-utils@jrkim-marketplace
```

## License

MIT
