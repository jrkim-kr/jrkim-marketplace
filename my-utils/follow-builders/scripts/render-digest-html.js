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
