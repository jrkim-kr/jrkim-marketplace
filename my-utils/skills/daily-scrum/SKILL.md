---
name: daily-scrum
description: Generate a concise Korean daily scrum or standup progress summary from today's git commits across projects. Use when the user invokes /daily-scrum or asks for daily scrum, standup, 데일리 스크럼, 오늘 한 일, daily progress, progress report, or a commit-based work summary.
argument-hint: "[project-root]"
user-invokable: true
---

# Daily Scrum

Canonical command source: `/Users/jrkim/Projects/jrkim-marketplace/my-utils/commands/daily-scrum.md`.

When this skill is triggered, read and follow the canonical source command. Treat the user's text after the skill name as `$ARGUMENTS`.

Generate the report in Korean. Keep the standup-short structure from the source command: project folder name first, optional alias in parentheses, and concise nested bullets for result or status.
