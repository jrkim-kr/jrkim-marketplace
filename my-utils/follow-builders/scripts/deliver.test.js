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

test('attaches PDF when pdfContent is given', () => {
  const pdf = Buffer.from('%PDF-1.4 fake');
  const p = buildEmailPayload({ pdfContent: pdf, bodyText: '', toEmail: 'c@x.com', dateStr: '2026-10-07' });
  assert.equal(p.attachments[0].filename, 'AI-Builders-Digest-2026-10-07.pdf');
  assert.deepEqual(Buffer.from(p.attachments[0].content, 'base64'), pdf);
  assert.doesNotMatch(p.text, /源码/);
});
