---
description: Analyze a web project, run dev server, and capture store-ready screenshots organized by public and authenticated views
argument-hint: "[project-path] [username:password]"
---

Plugin asset directory for this command: `${CLAUDE_PLUGIN_ROOT}/project-screenshots`

# Project Screenshots

Capture store-ready screenshots of a web project by analyzing its structure, discovering routes, handling authentication, and saving organized screenshots to the project directory.

## Language

Auto-detect from the user's message. Default to Korean if ambiguous.

---

## Arguments

Parse from the user's message:
- **project-path**: Path to the project root. Defaults to the current working directory.
- **credentials**: `username:password` for authenticated pages. If not provided and auth is detected, ask the user.

---

## Step 1: Analyze the Project

**Run these reads in parallel:**

1. **Read `package.json`** — identify framework, dev script, port, dependencies
2. **Glob for route files** — use the framework-specific patterns below
3. **Check for auth** — look for auth libraries in dependencies and auth-related files
4. **Check server status** — `lsof -ti tcp:<port> 2>/dev/null`

### Framework Detection (from package.json)

| Dependency | Framework | Default Port |
|-----------|-----------|-------------|
| `next` | Next.js | 3000 |
| `nuxt` | Nuxt | 3000 |
| `@sveltejs/kit` | SvelteKit | 5173 |
| `vite` (with react/vue) | Vite | 5173 |
| `react-scripts` | Create React App | 3000 |
| `@angular/core` | Angular | 4200 |

### Route Discovery Patterns

| Framework | Glob Pattern | Path Derivation |
|-----------|-------------|----------------|
| Next.js App Router | `src/app/**/page.tsx`, `app/**/page.tsx` | File path → URL (e.g., `app/dashboard/posts/page.tsx` → `/dashboard/posts`) |
| Next.js Pages Router | `src/pages/**/*.tsx`, `pages/**/*.tsx` | File name → URL (e.g., `pages/about.tsx` → `/about`) |
| SvelteKit | `src/routes/**/+page.svelte` | Folder path → URL |
| Nuxt | `pages/**/*.vue` | File path → URL |
| React/Vue (router) | Grep for `path:` or `<Route` in router config | Extract path strings |

**Exclude from routes:**
- **API routes**: `app/api/**`, `pages/api/**` — these are backend endpoints, not pages
- **Dynamic segments**: `[paramName]` routes (e.g., `app/posts/[postId]/page.tsx`) — these require specific IDs and will 404 without them. Only include if you can construct a valid URL with a real ID from the database.

### Auth Detection

Check for these signals (in parallel):
- **Dependencies**: `next-auth`, `@auth/*`, `passport`, `firebase`, `@clerk/*`, `auth0`
- **Files**: `middleware.ts`, `src/middleware.ts`, auth route files (`[...nextauth]`, `auth/`)
- **Pages**: login, signin, register, signup page files

If auth is detected, **read the login page component** to find:
- Input selectors (is it `type="text"` for username or `type="email"` for email?)
- Password input selector
- Submit button selector
- Where successful login redirects to

### Redirect Detection

**Read middleware and page components** to identify routes that redirect elsewhere. Common patterns:
- Middleware redirects (e.g., `/dashboard/instagram` → `/dashboard/settings` when no account connected)
- Page-level redirects (e.g., `router.push('/settings')` inside `useEffect`)
- Conditional redirects based on state (e.g., no Instagram account → settings page)

**Exclude redirecting routes from the config** to avoid duplicate screenshots. The capture script also has built-in deduplication — if a page redirects to a URL that's already captured or will be captured as another configured page, it automatically skips the duplicate.

### Dev Server Config

Extract from the dev script in `package.json`:
- **Port**: Look for `-p <port>` or `--port <port>` flags
- **HTTPS**: Look for `--experimental-https`, `--https`, or certificate file references
- **Protocol**: `https` if HTTPS detected, otherwise `http`

---

## Step 2: Classify Pages

Sort discovered routes into two groups:

**Public pages** — accessible without authentication:
- Login, register/signup
- Landing/home page (if public)
- Privacy policy, terms, about, pricing
- Any page NOT behind auth middleware

**Authenticated pages** — require login:
- Dashboard and its sub-pages
- Settings (capture each tab as a separate screenshot)
- Profile, analytics, reports
- Any route protected by middleware

For pages with tabs or sub-sections (e.g., Settings with Integrations/Sync/Brand tabs), create separate entries with query parameters like `/dashboard/settings?tab=sync`.

**Discovering tabs**: Read the settings/tabbed page component source to find tab values. Look for patterns like:
- Tab button `onClick` handlers with query param values
- `searchParams.get('tab')` or `useSearchParams` usage
- Tab configuration arrays (e.g., `const tabs = [{id: 'integrations'}, ...]`)

**If auth pages exist and no credentials were provided**, ask:
> "이 프로젝트에 로그인이 필요한 페이지가 있습니다. 인증된 상태의 스크린샷도 필요하시면 계정 정보(username과 password)를 알려주세요."

---

## Step 3: Prepare Environment

Run these setup steps:

### 3a. Puppeteer Setup

```bash
# Check if puppeteer is already installed
ls /tmp/puppeteer-capture/node_modules/puppeteer 2>/dev/null
```

If not installed:
```bash
npm install puppeteer --prefix /tmp/puppeteer-capture
```

### 3b. Dev Server

Check if the server is already running:
```bash
lsof -ti tcp:<port> 2>/dev/null
```

If running, verify it responds:
```bash
curl -sk <protocol>://localhost:<port> -o /dev/null -w "%{http_code}"
```

If NOT running, start it in the background:
```bash
cd <project-path> && npm run dev &
```
Then poll until the server responds (max 30 seconds).

### 3c. Output Directory

```bash
mkdir -p <project-path>/screenshots/public
mkdir -p <project-path>/screenshots/authenticated   # only if auth pages exist
```

---

## Step 4: Generate Screenshot Config

Write a JSON config to `/tmp/puppeteer-capture/config.json`:

```json
{
  "baseUrl": "<protocol>://localhost:<port>",
  "outputDir": "<project-path>/screenshots",
  "viewport": { "width": 1440, "height": 900 },
  "ignoreHTTPSErrors": true,
  "publicPages": [
    { "name": "01_login", "path": "/login", "waitFor": 2000 },
    { "name": "02_register", "path": "/register", "waitFor": 2000 }
  ],
  "auth": {
    "loginUrl": "/login",
    "usernameSelector": "input[type='text']",
    "passwordSelector": "input[type='password']",
    "submitSelector": "button[type='submit']",
    "username": "<from-user>",
    "password": "<from-user>",
    "waitBeforeLogin": 2000,
    "waitAfterLogin": 6000,
    "successIndicator": "/dashboard"
  },
  "authenticatedPages": [
    { "name": "01_dashboard", "path": "/dashboard", "waitFor": 3000 }
  ]
}
```

**Naming rules:**
- Two-digit prefix for ordering: `01_`, `02_`, etc.
- Descriptive names: `01_dashboard`, `02_post_metrics`, `03_settings_integrations`
- No spaces — use underscores

**Wait times:**
- Simple static pages: 2000ms
- Data-heavy pages (tables, charts): 3000–4000ms
- Pages that load data from APIs: 4000ms

**Omit the `auth` field entirely** if no credentials are available or no auth pages exist.

---

## Step 5: Run the Capture Script

Copy the bundled script and execute:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/project-screenshots/scripts/capture.mjs" /tmp/puppeteer-capture/capture.mjs
cd /tmp/puppeteer-capture && node capture.mjs config.json
```

**If login fails** (script reports the URL stayed on the login page):
1. Increase `waitAfterLogin` to 8000
2. Double-check the form selectors by re-reading the login component
3. Retry

**If a page times out**: The script will log the error and continue to the next page. Note the failure in the summary.

---

## Step 6: Present Results

1. **Show each screenshot** to the user by reading the PNG files with the Read tool
2. **Display a summary table**:

| File | Page | Status |
|------|------|--------|
| `public/01_login.png` | Login | ✅ |
| `authenticated/01_dashboard.png` | Dashboard | ✅ |

3. **Open the screenshots folder**:
```bash
# macOS
open <project-path>/screenshots
# Linux
xdg-open <project-path>/screenshots
```
Use the appropriate command for the current platform (`process.platform` or check OS).

4. **Note any issues**: pages that redirected, failed to load, or showed empty states.

---

## Edge Cases

- **Redirect deduplication**: The capture script automatically skips pages that redirect to a URL already captured or scheduled to be captured. If you identified redirecting routes during analysis (Step 1), exclude them from the config entirely to keep it clean.
- **Empty states**: New accounts may show empty/onboarding states. Mention this to the user — they may want to populate data first.
- **Multiple accounts**: If the project supports multiple Instagram/social accounts, the screenshots will show whichever account is active.
- **Environment variables**: Some projects need `.env` to run. If the server fails to start, check for missing env files.
- **Non-standard frameworks**: For static sites or custom servers, ask the user how to start the dev server and what the base URL is.
