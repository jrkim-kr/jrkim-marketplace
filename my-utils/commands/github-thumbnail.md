---
description: Download a GitHub repository's social share thumbnail (og:image) to ~/Downloads
argument-hint: "<repo-url-or-owner/repo>"
---

# GitHub Thumbnail Downloader

Download the social share preview image (OpenGraph image, 1200×600 PNG) for a GitHub repository to `~/Downloads`.

## Input

`$ARGUMENTS` is one of:

- Full URL: `https://github.com/vercel-labs/agent-browser`
- URL with extra path/query (e.g. `.../tree/main`, `?tab=readme`) — strip to `owner/repo`
- Shorthand: `vercel-labs/agent-browser`

If `$ARGUMENTS` is empty or does not resolve to a valid `owner/repo` pair, stop and ask the user for the repo.

## Step-by-step

### 1. Parse owner/repo

Extract `owner` and `repo` from the input:

```bash
INPUT="$ARGUMENTS"
# Strip protocol, host, leading slash, and any trailing path/query
SLUG=$(echo "$INPUT" | sed -E 's|^https?://github\.com/||; s|^/||; s|[?#].*$||' | cut -d/ -f1-2)
OWNER=$(echo "$SLUG" | cut -d/ -f1)
REPO=$(echo "$SLUG" | cut -d/ -f2)
```

Validate that both `OWNER` and `REPO` are non-empty and match `[A-Za-z0-9._-]+`. If not, abort with a clear message.

### 2. Extract og:image URL

Fetch the repo page and grep for the `og:image` meta tag. This avoids hardcoding the hash that GitHub embeds in the OpenGraph asset URL:

```bash
OG_URL=$(curl -sL "https://github.com/$OWNER/$REPO" \
  | grep -oE '<meta property="og:image" content="[^"]+"' \
  | head -1 \
  | sed -E 's|.*content="([^"]+)".*|\1|')
```

If `OG_URL` is empty, the repo likely doesn't exist or is private — report which and stop.

### 3. Download to ~/Downloads

```bash
OUT="$HOME/Downloads/${OWNER}-${REPO}-og.png"
curl -sL -o "$OUT" "$OG_URL"
```

Verify the download with `file "$OUT"` to confirm it's a PNG, and `ls -lh "$OUT"` for size.

### 4. Report

Report in Korean (matches the user's language preference), one tight summary:

```text
✅ 下载完成
- 路径: ~/Downloads/<owner>-<repo>-og.png
- 尺寸: 1200 × 600 (XX KB)
```

## Edge cases

- **Private/non-existent repo**: `curl` returns the GitHub 404 page, which still has an `og:image` (a generic GitHub logo). Detect this by checking whether the og:image URL contains `opengraph.githubassets.com/.+/<owner>/<repo>` — if not, the repo isn't accessible. Report and stop.
- **Custom social preview image**: Some repos upload a custom social preview via Settings. GitHub still exposes it via `og:image`, so the same flow works — no special handling needed.
- **File already exists**: Overwrite silently. The user just asked for the latest thumbnail.
- **Network failure**: `curl` will exit non-zero; surface the error to the user, don't silently produce an empty file.
