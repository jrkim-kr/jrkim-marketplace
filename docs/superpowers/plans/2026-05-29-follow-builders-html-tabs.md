# follow-builders 三语 tab HTML 简报 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 follow-builders 每日简报从纯文本邮件升级为杂志风 HTML 附件（中/EN/한 三语 tab + TL;DR + 目录），渲染失败时退回纯文本，向后兼容。

**Architecture:** LLM 改写阶段产出结构化 JSON（§4 schema）→ 无依赖渲染脚本 `render-digest-html.js` 生成自包含 HTML → `deliver.js` 的 email 分支把 HTML 作为 Resend 附件发送。配置 `delivery.format`（默认 `text`）隔离新链路；`format: "html"` 才走新路。

**Tech Stack:** Node.js (ESM, 仅内置模块 + 已有 dotenv)、`node:test` 单测、Resend Email API。

设计文档：[2026-05-29-follow-builders-html-tabs-design.md](../specs/2026-05-29-follow-builders-html-tabs-design.md)

`[CONFLICT_PATTERNS skipped: architect-advisor/jrkim-marketplace 下无 CONFLICT_PATTERNS.md，decompose 从未运行]`

---

## File Structure

仓库根：`/Users/jrkim/Projects/jrkim-marketplace`，以下路径相对于
`my-utils/follow-builders/scripts/`（除非另注）：

- **Create** `render-digest-html.js` — 纯渲染：JSON → HTML 字符串（导出 `renderHtml`）+ CLI 包装。无第三方依赖。
- **Create** `render-digest-html.test.js` — `node:test` 单测渲染逻辑。
- **Modify** `deliver.js` — 新增可测的 `buildEmailPayload()`（导出）+ `--html` 附件投递分支。
- **Create** `deliver.test.js` — `node:test` 单测 `buildEmailPayload`。
- **Modify** `package.json` — 加 `"test": "node --test"`。
- **Modify** `../../commands/follow-builders.md` — Content Delivery 的 Step 5/6（仅 `format: "html"` 分支）。
- **Modify** `../config/config-schema.json` — 加 `delivery.format` 枚举字段。
- **Activation（非仓库文件）** `~/.follow-builders/config.json` — 加 `delivery.format: "html"`；插件缓存同步。

---

## Task 1: 渲染脚本 render-digest-html.js（JSON → HTML）

**Files:**
- Create: `my-utils/follow-builders/scripts/render-digest-html.js`
- Test: `my-utils/follow-builders/scripts/render-digest-html.test.js`
- Modify: `my-utils/follow-builders/scripts/package.json`

- [ ] **Step 1: 加 test 脚本到 package.json**

把 `package.json` 的 `scripts` 块改为（新增 `test` 行）：

```json
  "scripts": {
    "generate-feed": "node generate-feed.js",
    "prepare-digest": "node prepare-digest.js",
    "test": "node --test"
  },
```

- [ ] **Step 2: 写失败测试 `render-digest-html.test.js`**

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderHtml } from './render-digest-html.js';

const sample = {
  date: '2026-05-28',
  languages: ['zh', 'en', 'ko'],
  tldr: { zh: ['要点一', '要点二'], en: ['t1', 't2'], ko: ['요점1', '요점2'] },
  sections: [
    {
      key: 'twitter',
      label: { zh: 'X / 推文', en: 'X / Twitter', ko: 'X / 트위터' },
      groups: [
        {
          label: { zh: 'Swyx — 主持人', en: 'Swyx — host', ko: 'Swyx — 진행자' },
          items: [
            { urls: ['https://x.com/a/1', 'https://x.com/a/2'],
              summary: { zh: '中文摘要 <b> & `code`', en: 'en sum', ko: '한 요약' } }
          ]
        }
      ]
    },
    {
      key: 'blogs',
      label: { zh: '官方博客', en: 'Official Blogs', ko: '공식 블로그' },
      groups: [
        {
          label: 'Anthropic Engineering',
          items: [
            { title: { zh: '标题', en: 'Title', ko: '제목' },
              url: 'https://anthropic.com/x',
              summary: { zh: '第一段\n\n第二段', en: 'p1\n\np2', ko: '문단1\n\n문단2' } }
          ]
        }
      ]
    }
  ]
};

test('three language panels, first active', () => {
  const html = renderHtml(sample);
  assert.equal((html.match(/class="panel/g) || []).length, 3);
  assert.match(html, /class="panel show" data-lang="zh"/);
  assert.match(html, /data-target="zh"[^>]*>中</);
});

test('tldr rendered per language', () => {
  const html = renderHtml(sample);
  assert.match(html, /要点一/);
  assert.match(html, /TL;DR/);
});

test('toc anchors are unique per language and link to groups', () => {
  const html = renderHtml(sample);
  assert.match(html, /href="#zh-s0-g0"/);
  assert.match(html, /id="zh-s0-g0"/);
  assert.match(html, /href="#en-s1-g0"/);
});

test('multi-url tweet item renders multiple links', () => {
  const html = renderHtml(sample);
  assert.match(html, /https:\/\/x\.com\/a\/1/);
  assert.match(html, /https:\/\/x\.com\/a\/2/);
});

test('html is escaped and inline code converted', () => {
  const html = renderHtml(sample);
  assert.match(html, /&lt;b&gt;/);          // <b> escaped
  assert.match(html, /<code>code<\/code>/); // `code` -> <code>
  assert.doesNotMatch(html, /摘要 <b>/);     // raw tag must not survive
});

test('multi-paragraph summary splits on blank line', () => {
  const html = renderHtml(sample);
  assert.match(html, /<p class="sum">第一段<\/p>/);
  assert.match(html, /<p class="sum">第二段<\/p>/);
});

test('group label string vs per-language object both work', () => {
  const html = renderHtml(sample);
  assert.match(html, /Anthropic Engineering/); // string label
  assert.match(html, /Swyx — 主持人/);          // zh object label
});

test('item with missing summary for a language is skipped there', () => {
  const data = JSON.parse(JSON.stringify(sample));
  data.sections[1].groups[0].items[0].summary.ko = '';
  const html = renderHtml(data);
  // ko panel should not contain the blog title, zh panel should
  const koPanel = html.split('data-lang="ko"')[1] || '';
  assert.doesNotMatch(koPanel, /제목/);
});

test('throws when no sections have content', () => {
  assert.throws(() => renderHtml({ date: 'x', languages: ['zh'], tldr: { zh: [] }, sections: [] }),
    /no content/i);
});
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd my-utils/follow-builders/scripts && node --test render-digest-html.test.js`
Expected: FAIL —— `Cannot find module './render-digest-html.js'`。

- [ ] **Step 4: 实现 `render-digest-html.js`**

```javascript
#!/usr/bin/env node
// Renders the follow-builders digest JSON into a self-contained tabbed HTML
// file (B · 杂志社论风). Pure string building, no third-party dependencies.
// CLI: node render-digest-html.js --in <json> --out <html>
import { readFile, writeFile } from 'fs/promises';

const TAB_LABEL = { zh: '中', en: 'EN', ko: '한' };
const TOC_LABEL = { zh: '目录', en: 'Contents', ko: '목차' };
const SRC_LABEL = { zh: '原文', en: 'source', ko: '원문' };

function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function inlineCode(s) { return s.replace(/`([^`]+)`/g, '<code>$1</code>'); }
function rich(text) {
  return String(text || '').split(/\n\n+/)
    .map(p => `<p class="sum">${inlineCode(esc(p))}</p>`).join('');
}
// label/title may be a plain string (same across langs) or {zh,en,ko}
function pick(v, lang) {
  if (v == null) return '';
  return typeof v === 'string' ? v : (v[lang] ?? v.en ?? '');
}
function urlsOf(it) { return it.urls && it.urls.length ? it.urls : (it.url ? [it.url] : []); }
function gid(lang, si, gi) { return `${lang}-s${si}-g${gi}`; }

function renderItem(it, lang) {
  const sum = it.summary?.[lang];
  if (!sum || !sum.trim()) return '';
  const urls = urlsOf(it);
  if (!urls.length) return '';
  const title = it.title ? `<h4 class="ptitle">${inlineCode(esc(pick(it.title, lang)))}</h4>` : '';
  const links = urls.map((u, i) =>
    `<a class="lk" href="${esc(u)}" target="_blank" rel="noopener">${SRC_LABEL[lang]}${urls.length > 1 ? ' ' + (i + 1) : ''} ↗</a>`
  ).join('<span class="dot">·</span>');
  return `<article class="item">${title}${rich(sum)}<div class="links">${links}</div></article>`;
}
function renderGroup(g, lang, si, gi) {
  const items = (g.items || []).map(it => renderItem(it, lang)).join('');
  if (!items.trim()) return '';
  return `<div class="grp" id="${gid(lang, si, gi)}"><div class="grplabel">${esc(pick(g.label, lang))}</div>${items}</div>`;
}
function renderSection(sec, lang, si) {
  const groups = (sec.groups || []).map((g, gi) => renderGroup(g, lang, si, gi)).join('');
  if (!groups.trim()) return '';
  return `<section class="sec"><h2 class="seclabel">${esc(pick(sec.label, lang))}</h2>${groups}</section>`;
}
function renderTldr(data, lang) {
  const items = (data.tldr?.[lang] || []).map(b => `<li>${inlineCode(esc(b))}</li>`).join('');
  if (!items) return '';
  return `<div class="tldr"><div class="boxlabel">TL;DR</div><ul>${items}</ul></div>`;
}
function renderToc(data, lang) {
  const blocks = (data.sections || []).map((sec, si) => {
    const links = (sec.groups || []).map((g, gi) =>
      `<a class="toclink" href="#${gid(lang, si, gi)}">${esc(pick(g.label, lang))}</a>`).join('');
    if (!links) return '';
    return `<div class="tocsec"><div class="toclabel">${esc(pick(sec.label, lang))}</div><div class="toclinks">${links}</div></div>`;
  }).join('');
  return `<nav class="toc"><div class="boxlabel">${TOC_LABEL[lang]}</div>${blocks}</nav>`;
}
function renderPanel(data, lang, active) {
  const body = (data.sections || []).map((s, si) => renderSection(s, lang, si)).join('');
  return `<div class="panel${active ? ' show' : ''}" data-lang="${lang}">${renderTldr(data, lang)}${renderToc(data, lang)}${body}</div>`;
}

export function renderHtml(data) {
  const langs = data.languages || ['zh', 'en', 'ko'];
  // bail loudly if there is nothing to show in the primary language
  const hasContent = (data.sections || []).some(sec =>
    (sec.groups || []).some(g => (g.items || []).some(it => {
      const s = it.summary?.[langs[0]];
      return s && s.trim() && urlsOf(it).length;
    })));
  if (!hasContent) throw new Error('no content to render');

  const tabs = langs.map((l, i) =>
    `<button class="tab${i === 0 ? ' on' : ''}" data-target="${l}" onclick="pick('${l}')">${TAB_LABEL[l] || l}</button>`).join('');
  const panels = langs.map((l, i) => renderPanel(data, l, i === 0)).join('');

  return `<!DOCTYPE html>
<html lang="${langs[0]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Builders Digest — ${esc(data.date)}</title>
<style>
  :root{ --paper:#fbf9f4; --ink:#1a1a1a; --muted:#5c574c; --line:#e2dccd; --accent:#9a7b2e; --tldrbg:#f4efe2; }
  *{ box-sizing:border-box; }
  body{ margin:0; background:#f0ece1; color:var(--ink); font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif; }
  .wrap{ max-width:680px; margin:0 auto; background:var(--paper); min-height:100vh; padding:40px 30px 64px; border-left:1px solid var(--line); border-right:1px solid var(--line); }
  header{ border-bottom:2px solid var(--ink); padding-bottom:16px; }
  .title{ font-family:Georgia,"Times New Roman",serif; font-size:30px; font-weight:700; letter-spacing:-.01em; margin:0; }
  .date{ color:var(--muted); font-size:13px; margin-top:6px; letter-spacing:.04em; }
  .tabs{ display:flex; gap:6px; position:sticky; top:0; background:var(--paper); padding:16px 0 14px; margin-bottom:10px; z-index:5; border-bottom:1px solid var(--line); }
  .tab{ font:inherit; font-size:13px; font-weight:600; cursor:pointer; padding:7px 18px; border:1px solid var(--line); background:transparent; color:var(--muted); border-radius:8px; transition:.15s; }
  .tab:hover{ color:var(--ink); } .tab.on{ background:var(--ink); color:var(--paper); border-color:var(--ink); }
  .panel{ display:none; } .panel.show{ display:block; animation:fade .25s ease; }
  @keyframes fade{ from{opacity:0; transform:translateY(4px);} to{opacity:1;} }
  .boxlabel{ font-family:Georgia,serif; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.16em; color:var(--accent); margin-bottom:10px; }
  .tldr{ background:var(--tldrbg); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:16px 18px; margin-bottom:18px; }
  .tldr ul{ margin:0; padding-left:18px; } .tldr li{ margin-bottom:7px; color:#2b2820; } .tldr li:last-child{ margin-bottom:0; }
  .toc{ border:1px solid var(--line); border-radius:8px; padding:16px 18px; margin-bottom:34px; }
  .tocsec{ margin-bottom:12px; } .tocsec:last-child{ margin-bottom:0; }
  .toclabel{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); margin-bottom:6px; }
  .toclinks{ display:flex; flex-wrap:wrap; gap:6px 14px; }
  .toclink{ font-size:13px; color:var(--ink); text-decoration:none; border-bottom:1px dotted var(--accent); } .toclink:hover{ color:var(--accent); }
  .sec{ margin-bottom:40px; }
  .seclabel{ font-family:Georgia,serif; font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.16em; color:var(--accent); border-bottom:2px solid var(--accent); padding-bottom:7px; margin:0 0 22px; }
  .grp{ margin-bottom:30px; scroll-margin-top:80px; }
  .grplabel{ font-family:Georgia,serif; font-size:17px; font-weight:700; color:var(--ink); margin:0 0 12px; padding-bottom:6px; border-bottom:1px solid var(--line); }
  .item{ margin-bottom:22px; }
  .ptitle{ font-family:Georgia,serif; font-size:16px; font-weight:700; font-style:italic; margin:0 0 9px; line-height:1.4; }
  .sum{ margin:0 0 11px; color:#2b2820; }
  .links{ display:flex; flex-wrap:wrap; align-items:center; gap:4px; }
  .lk{ font-size:13px; color:var(--accent); text-decoration:none; font-weight:600; } .lk:hover{ text-decoration:underline; }
  .dot{ color:var(--line); margin:0 4px; }
  code{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.88em; background:#efe9da; padding:1px 5px; border-radius:4px; }
  footer{ margin-top:40px; padding-top:16px; border-top:1px solid var(--line); color:var(--muted); font-size:12px; }
  @media(max-width:560px){ .wrap{ padding:28px 18px 48px; } .title{ font-size:25px; } }
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1 class="title">AI Builders Digest</h1>
      <div class="date">${esc(data.date)} · 当日精选</div>
    </header>
    <nav class="tabs">${tabs}</nav>
    ${panels}
    <footer>Follow builders, not influencers · 三语简报 中 / EN / 한</footer>
  </div>
<script>
  function pick(lang){
    document.querySelectorAll('.tab').forEach(function(t){ t.classList.toggle('on', t.dataset.target===lang); });
    document.querySelectorAll('.panel').forEach(function(p){ p.classList.toggle('show', p.dataset.lang===lang); });
    window.scrollTo({top:0});
  }
</script>
</body>
</html>`;
}

// ---- CLI -------------------------------------------------------------------
function arg(flag) { const i = process.argv.indexOf(flag); return i !== -1 ? process.argv[i + 1] : null; }

async function main() {
  const inPath = arg('--in'), outPath = arg('--out');
  if (!inPath || !outPath) throw new Error('usage: --in <json> --out <html>');
  const data = JSON.parse(await readFile(inPath, 'utf-8'));
  await writeFile(outPath, renderHtml(data), 'utf-8');
  console.log(JSON.stringify({ status: 'ok', out: outPath }));
}

// run as CLI only (not when imported by tests)
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(e => { console.error(JSON.stringify({ status: 'error', message: e.message })); process.exit(1); });
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd my-utils/follow-builders/scripts && node --test render-digest-html.test.js`
Expected: PASS —— 所有 9 个 test 通过。

- [ ] **Step 6: 提交**

```bash
cd /Users/jrkim/Projects/jrkim-marketplace
git add my-utils/follow-builders/scripts/render-digest-html.js my-utils/follow-builders/scripts/render-digest-html.test.js my-utils/follow-builders/scripts/package.json
git -c user.email="jeongrankim99@gmail.com" commit -m "feat(follow-builders): add render-digest-html.js (JSON → tabbed HTML)"
```

---

## Task 2: deliver.js 可测的 buildEmailPayload

**Files:**
- Modify: `my-utils/follow-builders/scripts/deliver.js`
- Test: `my-utils/follow-builders/scripts/deliver.test.js`

- [ ] **Step 1: 写失败测试 `deliver.test.js`**

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildEmailPayload } from './deliver.js';

test('builds Resend payload with base64 HTML attachment', () => {
  const html = '<!DOCTYPE html><html>héllo</html>';
  const p = buildEmailPayload({ htmlContent: html, bodyText: '详见附件', toEmail: 'c@x.com', dateStr: '2026-05-28' });
  assert.equal(p.to[0], 'c@x.com');
  assert.equal(p.subject, 'AI Builders Digest — 2026-05-28');
  assert.equal(p.text, '详见附件');
  assert.equal(p.attachments.length, 1);
  assert.equal(p.attachments[0].filename, 'AI-Builders-Digest-2026-05-28.html');
  // content must be base64 that decodes back to the original HTML
  const decoded = Buffer.from(p.attachments[0].content, 'base64').toString('utf-8');
  assert.equal(decoded, html);
});

test('falls back to a default body when bodyText is empty', () => {
  const p = buildEmailPayload({ htmlContent: '<html></html>', bodyText: '', toEmail: 'c@x.com', dateStr: '2026-05-28' });
  assert.match(p.text, /详见附件/);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd my-utils/follow-builders/scripts && node --test deliver.test.js`
Expected: FAIL —— `buildEmailPayload is not a function` / 导出不存在。

- [ ] **Step 3: 在 deliver.js 加 `buildEmailPayload`（导出）**

在 `deliver.js` 的 `sendEmail` 函数定义（约 `:129`）之前插入：

```javascript
// Builds the Resend request body for an HTML-attachment digest email.
// Pure + exported so it can be unit-tested without hitting the network.
export function buildEmailPayload({ htmlContent, bodyText, toEmail, dateStr }) {
  const base64 = Buffer.from(htmlContent, 'utf-8').toString('base64');
  return {
    from: 'AI Builders Digest <digest@resend.dev>',
    to: [toEmail],
    subject: `AI Builders Digest — ${dateStr}`,
    text: (bodyText && bodyText.trim()) ? bodyText : '今日 AI Builders Digest，详见附件。',
    attachments: [{ filename: `AI-Builders-Digest-${dateStr}.html`, content: base64 }]
  };
}
```

> `export` 不影响 `deliver.js` 作为 CLI 运行（文件末尾仍调用 `main()`）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd my-utils/follow-builders/scripts && node --test deliver.test.js`
Expected: PASS —— 2 个 test 通过。

- [ ] **Step 5: 提交**

```bash
cd /Users/jrkim/Projects/jrkim-marketplace
git add my-utils/follow-builders/scripts/deliver.js my-utils/follow-builders/scripts/deliver.test.js
git -c user.email="jeongrankim99@gmail.com" commit -m "feat(follow-builders): add tested buildEmailPayload for HTML attachment"
```

---

## Task 3: deliver.js 接入 `--html` 附件投递分支

**Files:**
- Modify: `my-utils/follow-builders/scripts/deliver.js`

- [ ] **Step 1: 加 `sendEmailWithAttachment` 函数**

在 Task 2 新增的 `buildEmailPayload` 之后、`sendEmail` 之前插入：

```javascript
// Sends an HTML-attachment digest via Resend.
async function sendEmailWithAttachment({ htmlContent, bodyText, apiKey, toEmail, dateStr }) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
    body: JSON.stringify(buildEmailPayload({ htmlContent, bodyText, toEmail, dateStr }))
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(`Resend API error: ${err.message || JSON.stringify(err)}`);
  }
}
```

- [ ] **Step 2: 在 `main()` 的 `case 'email'` 里分流 `--html`**

把 `deliver.js` 的 `case 'email': { ... }` 块（约 `:187-199`）整体替换为：

```javascript
      case 'email': {
        const apiKey = process.env.RESEND_API_KEY;
        const toEmail = delivery.email;
        if (!apiKey) throw new Error('RESEND_API_KEY not found in .env');
        if (!toEmail) throw new Error('delivery.email not found in config.json');

        const htmlPath = argOf('--html');
        if (htmlPath) {
          const htmlContent = await readFile(htmlPath, 'utf-8');
          const dateStr = argOf('--date') || new Date().toISOString().slice(0, 10);
          const bodyText = argOf('--body') || '';
          await sendEmailWithAttachment({ htmlContent, bodyText, apiKey, toEmail, dateStr });
          console.log(JSON.stringify({ status: 'ok', method: 'email', mode: 'html', message: `Digest (HTML) sent to ${toEmail}` }));
        } else {
          await sendEmail(digestText, apiKey, toEmail);
          console.log(JSON.stringify({ status: 'ok', method: 'email', message: `Digest sent to ${toEmail}` }));
        }
        break;
      }
```

- [ ] **Step 3: 加 `argOf` 辅助函数**

在 `deliver.js` 顶部、`getDigestText`（约 `:38`）之前加：

```javascript
// Reads a CLI flag value, e.g. argOf('--html') -> next argv token or null.
function argOf(flag) {
  const i = process.argv.indexOf(flag);
  return i !== -1 ? process.argv[i + 1] : null;
}
```

- [ ] **Step 4: 处理 `--html` 模式下空 digestText 提前返回的冲突**

`main()` 开头（约 `:166`）有：当 `digestText` 为空就 `skipped` 返回。`--html` 模式不需要
stdin 文本。把该早返回判断改为：仅当**不是 html 模式**时才因空文本跳过。

把：

```javascript
  if (!digestText || digestText.trim().length === 0) {
    console.log(JSON.stringify({ status: 'skipped', reason: 'Empty digest text' }));
    return;
  }
```

改为：

```javascript
  const htmlMode = argOf('--html');
  if (!htmlMode && (!digestText || digestText.trim().length === 0)) {
    console.log(JSON.stringify({ status: 'skipped', reason: 'Empty digest text' }));
    return;
  }
```

- [ ] **Step 5: 回归测试 + 烟测 CLI**

Run: `cd my-utils/follow-builders/scripts && node --test`
Expected: PASS —— render + deliver 两个测试文件全过（确认改动没破坏导出）。

Run（无 RESEND_API_KEY 时验证报错路径，确认 CLI 能进 html 分支而非误跳过）：
`printf '' | RESEND_API_KEY= node deliver.js --html /etc/hostname --date 2026-05-28` 之类不可靠；
改用最小可控烟测：建一个临时 config 指向 email 但不带 key，断言报"RESEND_API_KEY not found"：

```bash
TMP=$(mktemp -d)
printf '{"delivery":{"method":"email","email":"x@x.com"}}' > "$TMP/config.json"
echo '<html>hi</html>' > "$TMP/d.html"
HOME="$TMP" node deliver.js --html "$TMP/d.html" --date 2026-05-28 ; echo "exit=$?"
```

Expected: 输出 `{"status":"error",..."RESEND_API_KEY not found in .env"}`，`exit=1`
（证明进入了 email→html 分支并按预期校验 key，而不是因空文本 `skipped`）。

- [ ] **Step 6: 提交**

```bash
cd /Users/jrkim/Projects/jrkim-marketplace
git add my-utils/follow-builders/scripts/deliver.js
git -c user.email="jeongrankim99@gmail.com" commit -m "feat(follow-builders): wire --html attachment delivery into deliver.js"
```

---

## Task 4: config schema + 命令文件 Step 5/6

**Files:**
- Modify: `my-utils/follow-builders/config/config-schema.json`
- Modify: `my-utils/commands/follow-builders.md`

- [ ] **Step 1: 看现有 schema 结构**

Run: `sed -n '1,80p' my-utils/follow-builders/config/config-schema.json`
目的：定位 `delivery` 对象的 `properties`，照其风格加字段（不要改其它字段）。

- [ ] **Step 2: 给 `delivery` 加 `format` 字段**

在 `config-schema.json` 的 `delivery.properties` 里加（与既有 `method`/`email` 同级）：

```json
        "format": {
          "type": "string",
          "enum": ["text", "html"],
          "default": "text",
          "description": "Email body format. 'text' = plain text body (default). 'html' = short text body + tabbed HTML file attachment (trilingual)."
        }
```

- [ ] **Step 3: 改命令文件 Step 5（仅 html 分支）**

在 `my-utils/commands/follow-builders.md` 的 `### Step 5: Apply language` 段落**开头**插入一个前置分支：

```markdown
**If `config.delivery.format === "html"`:** Do NOT produce interleaved text.
Instead assemble a single JSON object and write it to `/tmp/fb-digest.json`,
with this shape (every item needs a real link; every summary needs zh+en+ko):

- `date` (YYYY-MM-DD), `languages: ["zh","en","ko"]`
- `tldr`: `{ zh:[5–6 bullets], en:[…], ko:[…] }` — the day's key takeaways per language
- `sections[]`: each `{ key, label:{zh,en,ko}, groups[] }` in order twitter → blogs → podcasts
- `groups[]`: each `{ label, items[] }`. `label` is a plain string for blog/podcast
  sources (e.g. "Anthropic Engineering"); for tweets it is `{zh,en,ko}` (the builder's
  name + role, translated). Each tweet builder is one group.
- `items[]`: blog/podcast item `{ title:{zh,en,ko}, url, summary:{zh,en,ko} }`;
  tweet item `{ urls:[…], summary:{zh,en,ko} }` (no title; multiple tweet links allowed).
- Omit any section/group/item with no real content. Use `\n\n` between paragraphs.

Then ALSO write a plain-text version of the digest (any one language is fine) to
`/tmp/fb-digest.txt` as the fallback body. Then skip the rest of Step 5.
```

- [ ] **Step 4: 改命令文件 Step 6（仅 html 分支）**

在 `### Step 6: Deliver` 段落**开头**插入前置分支：

````markdown
**If `config.delivery.format === "html"`:** render then send as attachment, with a
plain-text fallback so a bad render never drops the day's digest:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/follow-builders/scripts
DATE=$(node -e "process.stdout.write(require('/tmp/fb-digest.json').date)")
if node render-digest-html.js --in /tmp/fb-digest.json --out "/tmp/AI-Builders-Digest-$DATE.html" 2>>"$HOME/.follow-builders/logs/render.err.log"; then
  node deliver.js --html "/tmp/AI-Builders-Digest-$DATE.html" --date "$DATE" \
    --body "今日 AI Builders Digest，详见附件。" 2>/dev/null
else
  echo "render failed, falling back to plain text" >> "$HOME/.follow-builders/logs/render.err.log"
  node deliver.js --file /tmp/fb-digest.txt 2>/dev/null
fi
```

Then stop (do not run the default text delivery below).
````

- [ ] **Step 5: 校验 schema 合法 + 命令文件无残留占位**

Run: `node -e "JSON.parse(require('fs').readFileSync('my-utils/follow-builders/config/config-schema.json','utf8')); console.log('schema ok')"`
Expected: `schema ok`

Run: `grep -n 'format' my-utils/follow-builders/config/config-schema.json`
Expected: 能看到新增的 `format` 字段。

- [ ] **Step 6: 提交**

```bash
cd /Users/jrkim/Projects/jrkim-marketplace
git add my-utils/follow-builders/config/config-schema.json my-utils/commands/follow-builders.md
git -c user.email="jeongrankim99@gmail.com" commit -m "feat(follow-builders): add delivery.format=html branch (schema + command Step 5/6)"
```

---

## Task 5: 本地端到端干跑（不发邮件，肉眼验收）

**Files:**
- 临时：`/tmp/fb-digest-e2e.json`（不提交）

- [ ] **Step 1: 造一个最小三语 JSON（含 tweets 多链接 + 博客 + 播客）**

```bash
cat > /tmp/fb-digest-e2e.json <<'JSON'
{
  "date": "2026-05-28",
  "languages": ["zh","en","ko"],
  "tldr": { "zh": ["要点一","要点二"], "en": ["t1","t2"], "ko": ["요점1","요점2"] },
  "sections": [
    { "key":"twitter","label":{"zh":"X / 推文","en":"X / Twitter","ko":"X / 트위터"},
      "groups":[ { "label":{"zh":"Swyx — 主持人","en":"Swyx — host","ko":"Swyx — 진행자"},
        "items":[ { "urls":["https://x.com/a/1","https://x.com/a/2"],
          "summary":{"zh":"中文摘要 `code`","en":"en sum","ko":"한 요약"} } ] } ] },
    { "key":"blogs","label":{"zh":"官方博客","en":"Official Blogs","ko":"공식 블로그"},
      "groups":[ { "label":"Anthropic Engineering",
        "items":[ { "title":{"zh":"标题","en":"Title","ko":"제목"},
          "url":"https://anthropic.com/x",
          "summary":{"zh":"第一段\n\n第二段","en":"p1\n\np2","ko":"문단1\n\n문단2"} } ] } ] }
  ]
}
JSON
echo done
```

- [ ] **Step 2: 渲染并在浏览器打开**

```bash
cd my-utils/follow-builders/scripts
node render-digest-html.js --in /tmp/fb-digest-e2e.json --out /tmp/fb-e2e.html
open /tmp/fb-e2e.html
```

Expected: 浏览器打开页面；输出 `{"status":"ok","out":"/tmp/fb-e2e.html"}`。

- [ ] **Step 3: 肉眼验收（对照设计 §9）**

确认：
- 三个 tab（中/EN/한）可点击切换，默认中文激活
- 每个 tab 顶部有 TL;DR 框 + 目录；点目录里"Swyx…/Anthropic Engineering"能跳到对应段落
- 推文条目显示两个链接（原文 1 · 原文 2）；博客条目有斜体标题 + 两段
- 正文里的 `` `code` `` 渲染成等宽底色样式

不通过则回到 Task 1 修 `render-digest-html.js` 并补测试，再回到本步。

- [ ] **Step 4: 无需提交（仅验收）。** 通过即进 Task 6。

---

## Task 6: 上线激活（配置 + 缓存同步 + 真实发信）

> 这些是部署动作，非仓库改动。逐条都要可验证（router 特别提醒：不做缓存同步会"改了不生效"）。

- [ ] **Step 1: 给运行时 config 加 `format: "html"`**

```bash
node -e '
const fs=require("fs"),p=require("os").homedir()+"/.follow-builders/config.json";
const c=JSON.parse(fs.readFileSync(p,"utf8"));
c.delivery.format="html";
fs.writeFileSync(p, JSON.stringify(c,null,2));
console.log(JSON.stringify(c.delivery));
'
```

Expected: 打印的 delivery 含 `"format":"html"`。

- [ ] **Step 2: 同步插件缓存（让 cron 用上新版）**

确认缓存来源与同步方式（二选一，先探后做）：

```bash
ls -la ~/.claude/plugins/cache/jrkim-marketplace/my-utils/*/follow-builders/scripts/render-digest-html.js 2>&1 || echo "尚未同步"
```

若插件由本地市场源加载（参见 MEMORY：2026-04-09 起改为源直接加载/无构建），可能无需手动拷贝；
若使用版本化缓存目录，则把改动版本号 bump 或将更新文件同步到对应缓存版本目录。
本步**验收口径**：缓存目录里的 `render-digest-html.js`、`deliver.js`、`commands/follow-builders.md`、
`config-schema.json` 内容与源仓库一致。

```bash
# 示例校验（路径以实际缓存版本为准）：
CACHE=$(ls -d ~/.claude/plugins/cache/jrkim-marketplace/my-utils/*/ 2>/dev/null | tail -1)
diff -q my-utils/follow-builders/scripts/deliver.js "${CACHE}follow-builders/scripts/deliver.js" && echo "deliver.js 同步 OK" || echo "需同步 deliver.js"
```

Expected: 关键文件 `diff -q` 全部一致（或确认是源直载、无独立缓存副本）。

- [ ] **Step 3: 真实跑一次完整链路（手动触发，等同 cron）**

```bash
/Users/jrkim/.local/bin/claude -p "/my-utils:follow-builders"
```

Expected: 进程完成；`~/.follow-builders/logs/<today>.log` 末尾显示发送成功；
若当天 feed 为空，则正常提示无内容（非失败）。

- [ ] **Step 4: 收件验收**

确认 chloe@aisahub.com 收到邮件：正文是简短导语、附件
`AI-Builders-Digest-<date>.html` 打开后三语 tab + TL;DR + 目录正常。

- [ ] **Step 5: 兜底验证（注入坏 JSON）**

```bash
echo '{ this is not valid json' > /tmp/fb-digest.json
cd my-utils/follow-builders/scripts
DATE=2026-05-28
node render-digest-html.js --in /tmp/fb-digest.json --out "/tmp/x-$DATE.html"; echo "render exit=$?"
```

Expected: render `exit=1` 且 stderr 有 error JSON —— 证明命令文件 Step 6 的 `if/else`
会走 `else` 分支退回 `deliver.js --file`（不漏发）。

- [ ] **Step 6: 收尾提交（如有文档/状态更新）**

```bash
cd /Users/jrkim/Projects/jrkim-marketplace
git add -A
git -c user.email="jeongrankim99@gmail.com" commit -m "chore(follow-builders): activate html digest format" || echo "无额外改动可提交"
```

---

## 验收对照（plan ↔ spec §9）

- HTML 附件邮件 → Task 3 + Task 6 Step 3/4
- 三语 tab 可切换、每 tab 完整简报 → Task 1 + Task 5 Step 3
- TL;DR + 目录锚点跳转 → Task 1（renderTldr/renderToc）+ Task 5 Step 3
- B 杂志社论风、响应式 → Task 1（内联 CSS）
- 每条目有链接、推文多链接 → Task 1（renderItem，urls）
- 坏 JSON → 退回纯文本、不漏发 → Task 3 Step 4 + Task 4 Step 4 + Task 6 Step 5
- `format: "text"`/旧配置不变 → Task 3 Step 2（else 分支保留原行为）
- 无新依赖 → Task 1（仅内置模块）
