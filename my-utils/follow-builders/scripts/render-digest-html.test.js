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
  const koPanel = html.split('data-lang="ko"')[1] || '';
  assert.doesNotMatch(koPanel, /제목/);
});

test('throws when no sections have content', () => {
  assert.throws(() => renderHtml({ date: 'x', languages: ['zh'], tldr: { zh: [] }, sections: [] }),
    /no content/i);
});
