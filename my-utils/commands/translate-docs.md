---
description: Translate all .md and .txt files in the current directory between Korean and English. Auto-detects source language per file
argument-hint: "[target-lang]"
---

# Translate Documents

Translate all `.md` and `.txt` files in the current directory (and subdirectories) between Korean and English. The source language is auto-detected per file, and translations are saved in a separate output folder that mirrors the original directory structure.

## Workflow

### 1. Discover files

Use Glob to find all `.md` and `.txt` files in the working directory:

```
**/*.md
**/*.txt
```

Exclude common non-content directories: `node_modules/`, `.git/`, `dist/`, `build/`, `.next/`, `__pycache__/`, `venv/`, `.claude/`. Also exclude any existing `translations/` directory to avoid retranslating previous output.

### 2. Detect language and determine target

For each file, read the content and detect the primary language:

- If the majority of the text is **Korean** → target is **English** (`en`)
- If the majority of the text is **English** → target is **Korean** (`ko`)
- If the file is mostly code, config, or has very little translatable prose, **skip it** and note it in the summary

Detection heuristic: Korean text contains Hangul characters (Unicode range `가-힯`, `ᄀ-ᇿ`, `㄰-㆏`). If more than 30% of non-whitespace, non-ASCII characters are Hangul, treat the source as Korean.

If the user explicitly specifies a target language via `$ARGUMENTS` (e.g., "ko" or "en"), use that for all files regardless of detection.

### 3. Translate

Translate each file while following these principles:

- **Preserve structure**: Keep all markdown formatting, headings, lists, code blocks, links, and front matter intact. Do not translate content inside code blocks (`` ` `` or ``` ``` ```), URLs, file paths, or variable/function names.
- **Natural fluency**: Produce translations that read naturally in the target language, not word-for-word literal translations. Adjust sentence structure and phrasing to match how a native speaker would write technical documentation.
- **Technical terms**: Keep widely-recognized technical terms in English even when translating to Korean (e.g., API, REST, Git, Docker, npm, CLI). For terms that have well-established Korean equivalents (e.g., "database" → "데이터베이스", "server" → "서버"), use the Korean form.
- **Consistency**: Use consistent terminology throughout all files. If you translate "deployment" as "배포" in one file, use "배포" everywhere.
- **Front matter**: Translate human-readable fields in YAML front matter (title, description) but leave keys, dates, and technical values untouched.

### 4. Save translations

Save translated files under a `translations/<lang>/` directory at the project root. The original directory structure must be fully preserved — every subdirectory in the source should appear identically under `translations/<lang>/`:

```
translations/
├── ko/
│   ├── README.md
│   ├── docs/
│   │   ├── getting-started.md
│   │   └── api-reference.md
│   └── CONTRIBUTING.md
└── en/
    ├── README.md
    └── docs/
        └── setup-guide.md
```

If a `translations/` directory already exists, update only the files that have changed or are new. Do not delete existing translations for files that no longer exist in the source — the user may have removed them intentionally, and the translations might still be useful.

### 5. Report results

After translation, provide a summary:

```
## Translation Summary

| File | Source | Target | Status |
|------|--------|--------|--------|
| README.md | Korean | English | Translated |
| docs/guide.md | English | Korean | Translated |
| config.txt | — | — | Skipped (no prose) |

Output: translations/ko/, translations/en/
Total: X files translated, Y skipped
```

## Edge Cases

- **Mixed-language files**: If a file has roughly equal Korean and English content, translate to the language the user specified. If no target was specified, translate to Korean (since mixed docs in Korean projects usually need Korean translations of the English parts).
- **Empty files**: Skip them.
- **Binary or non-text files**: The glob patterns only match `.md` and `.txt`, so binary files are naturally excluded.
- **Very large files**: For files over 500 lines, translate in sections to maintain quality. Read and translate in chunks of ~200 lines, keeping context across chunks for terminology consistency.
- **Nested translations directory**: Never translate files inside `translations/` — this prevents infinite translation loops.
