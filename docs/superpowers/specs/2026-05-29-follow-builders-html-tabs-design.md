# follow-builders 三语 tab HTML 简报 — 设计文档

- 日期：2026-05-29
- 作者：jrkim（jordan@aisahub.com）
- 收件人：chloe@aisahub.com（主要用 Gmail）
- 状态：设计已批准，待 review → writing-plans

## 1. 背景与目标

### 现状

`follow-builders` skill 每天 09:30（Asia/Seoul）由 launchd 任务
`com.user.follow-builders` 触发 `~/.follow-builders/run-digest.sh`，后者调用
`claude -p "/my-utils:follow-builders"`，流程为：抓取 feed → LLM 改写 → 通过
`deliver.js` 发**纯文本邮件**（Resend API）。当前 `config.language: "trilingual"`，
三语是段落级交错（英→韩→中）塞在同一封纯文本里。

### 目标

把日报渲染成**杂志社论风（B 风格）的 HTML**，三种语言（中 / EN / 한）分成
**可点击切换的 tab**，每个 tab 是该语言的**完整简报**。由于邮件正文无法可靠支持
JS tab（Gmail 等会删 `<script>`），交付形式定为：**邮件正文放简短导语 + HTML 文件作为附件**。
Chloe 点开附件在浏览器里切 tab，tab 完全可用，且绕开 Gmail 客户端限制。

### 非目标（YAGNI）

- 不做托管网页 / 公开链接
- 不做图片版（图片本质是"先有 HTML 再截图"，HTML 跑顺后随时可加，本期不做）
- 不改抓取 / feed / prompts 的内容逻辑
- 不动 Telegram、stdout、OpenClaw 分支
- 不改通用 skill 对其他用户/配置的默认行为（向后兼容）

## 2. 核心决策

### 内容如何从"改写"流到"渲染"：方案 ①（LLM 产出结构化 JSON）

改写阶段不再输出自由文本，而是输出结构化 JSON（schema 见 §4），写到
`/tmp/fb-digest.json`。渲染脚本读 JSON 拼出 HTML。

- 选择理由：每天无人值守运行，确定性排版比"LLM 自由发挥 HTML"可靠得多；样式 100%
  由脚本掌控、可单测；加语言只改数据。
- 已排除方案 ②（LLM 出 markdown + 分隔标记）：需引入 markdown 解析依赖，且排版控制更松。
  本仓库目前近零依赖（仅 dotenv + proper-lockfile），不想加。
- 已排除方案 ③（LLM 直出 HTML）：样式不稳定、输出大、难维护。

### 失败兜底：渲染失败退回纯文本邮件

渲染成功 → 发 HTML 附件邮件；JSON 解析或渲染失败 → 记日志 + **退回旧版纯文本邮件**，
当天不漏发。纯文本路径本就存在，复用成本几乎为零。原则："宁可丑也别漏发"。

### 配置开关隔离

`config.json` 新增 `delivery.format`，取值 `"text"`（默认）| `"html"`。只有该用户配置
设为 `"html"` 才走新链路；其他配置/用户仍为纯文本。tab 的语言集合来自 `config.language`
（`trilingual` → 中/EN/한 三 tab）。

## 3. 架构与数据流

```
launchd 09:30 → run-digest.sh → claude -p "/my-utils:follow-builders"
  Step 2  prepare-digest.js        → 抓取 feed/prompts/config（不变）
  Step 4  LLM 改写                  → 产出结构化 JSON（format=html 时）
  Step 6  投递（format=html 时）:
            写 /tmp/fb-digest.json
            node render-digest-html.js --in /tmp/fb-digest.json --out /tmp/fb-digest-<date>.html
            ├─ 成功 → node deliver.js --html /tmp/fb-digest-<date>.html
            └─ 失败 → 记日志 + node deliver.js --file /tmp/fb-digest.txt（旧纯文本）
```

各单元职责边界：

- `prepare-digest.js`：抓取，不变。
- LLM（命令文件驱动）：把 feed 内容改写成三语 JSON，**只产数据，不碰 HTML/样式**。
- `render-digest-html.js`：纯函数式渲染，JSON → HTML 字符串，无网络无依赖，可单测。
- `deliver.js`：投递通道，新增"HTML 附件"能力。

## 4. 数据契约（LLM 产出的 JSON schema）

写到 `/tmp/fb-digest.json`：

```json
{
  "date": "2026-05-29",
  "languages": ["zh", "en", "ko"],
  "tldr": {
    "zh": ["要点 1", "要点 2", "..."],
    "en": ["takeaway 1", "..."],
    "ko": ["요점 1", "..."]
  },
  "sections": [
    {
      "key": "blogs",
      "label": { "zh": "官方博客", "en": "Official Blogs", "ko": "공식 블로그" },
      "groups": [
        {
          "label": "Anthropic Engineering",
          "items": [
            {
              "title": "An update on recent Claude Code quality reports",
              "url": "https://www.anthropic.com/engineering/april-23-postmortem",
              "summary": { "zh": "...", "en": "...", "ko": "..." }
            }
          ]
        }
      ]
    },
    {
      "key": "podcasts",
      "label": { "zh": "播客", "en": "Podcasts", "ko": "팟캐스트" },
      "groups": [
        {
          "label": "AI & I by Every",
          "items": [
            {
              "title": "We Automated Everything With AI and Tripled Our Headcount",
              "url": "https://www.youtube.com/watch?v=dCmOTURRf1Y",
              "summary": { "zh": "...", "en": "...", "ko": "..." }
            }
          ]
        }
      ]
    }
  ]
}
```

结构为三层：**板块 section（官方博客/播客/推文）→ 来源 group（如 Anthropic
Engineering、Claude Blog、AI & I by Every）→ 文章 item**。这层 `groups` 是用今天真实
数据做样本渲染时发现的：现有 digest-intro 本就把"博客名/播客名"当作来源小标题，故
schema 必须有这一层。推文板块每位 builder 视为一个 group，其下 item 含该 builder 的
综合摘要 + 多条推文链接（`url` 可为数组 `urls`）。

`group.label` 与 `item.title` 可为**纯字符串或三语对象**：博客/播客来源名（如
Anthropic Engineering）跨语言相同用字符串；推文里 builder 的"姓名+头衔"是翻译过的，
用三语对象。

`tldr`（每语言 5–6 条要点）与"目录"是 LLM 在改写阶段一并产出/渲染器自动生成的页首两块：

- **TL;DR**：LLM 产出每语言 5–6 条当日精华，放在该语言 tab 顶部的高亮框。
- **目录（Contents / 목차）**：渲染器**自动**从 sections + groups 生成，列出各来源名并
  锚点跳转到对应段落（锚点 id 按 `<lang>-s<sectionIdx>-g<groupIdx>` 保证三个面板各自唯一）。

多段摘要：`summary` 文本中的 `\n\n` 由渲染器拆成多个段落；反引号包裹的片段
（如 `` `.claude/settings.json` ``）渲染为 `<code>`。

规则（沿用现有 prompts 的硬约束）：

- 板块顺序：twitter → blogs → podcasts。
- 只包含有新内容的板块/来源/条目；无内容的整段省略。
- 每个条目必须有 `url`（无链接不收录），三语 `summary` 必须齐全。
- 不编造内容、不编造职位（用 `bio` 或仅用人名）。

## 5. 渲染脚本 `render-digest-html.js`

- 位置：`my-utils/follow-builders/scripts/render-digest-html.js`
- 入参：`--in <json>` `--out <html>`。样式只有 editorial 一种，直接内置，不做 `--style` 开关（YAGNI）。
- 行为：读 JSON → 校验（缺字段/空内容报清晰错误，退出非 0）→ 生成自包含单文件 HTML
  （内联 CSS + 极简内联 JS 做 tab 切换），写到 `--out`。
- 输出 HTML 结构：
  - 顶部标题区：`AI Builders Digest · <date>`
  - tab 栏：中 / EN / 한（按 `languages` 顺序，默认第一个激活；吸顶）
  - 每个语言面板（顺序）：**TL;DR 高亮框 → 目录 → 正文**
  - 正文：按 section → group → item 三层渲染（板块大标题 + 来源小标题 + 文章标题/多段摘要/原文链接，多链接并排）
  - 目录：自动生成的锚点跳转列表（`scroll-margin-top` 避开吸顶 tab 栏）
  - tab 切换：点击 tab 显示对应 `[data-lang]` 面板、隐藏其余并回到顶部（约 12 行原生 JS）
- 样式（B · 杂志社论风）：
  - 背景米色纸感（`#fbf9f4`），正文深灰（`#1a1a1a`）
  - 标题衬线体（Georgia/serif），正文系统无衬线
  - 板块小标题金棕色 accent（`#9a7b2e`）+ 细线分隔
  - 响应式：手机单列、最大宽度约束、可读字号
- 无第三方依赖（纯字符串拼接 + HTML 转义）。

## 6. 投递脚本 `deliver.js` 改动

- email 分支新增 `--html <file>`：
  - 读取 HTML 文件内容，base64 编码
  - Resend 请求体加 `attachments: [{ filename: "AI-Builders-Digest-<date>.html", content: <base64> }]`
  - 邮件正文（纯 `text` 简短导语 teaser，不做正文 HTML）：
    `今日 AI Builders Digest：N 篇官方博客 + M 期播客（…），详见附件。`
    （数量从 JSON/传入参数得到；附件文件名带日期）
  - subject 保持 `AI Builders Digest — <date>`
- 旧 `--file` / `--message` / telegram / stdout 分支不变。

## 7. 命令文件 `commands/follow-builders.md` 改动

- Step 5（语言）：当 `config.delivery.format === "html"` 时，改写产出 §4 的 JSON（三语齐全，
  含 `tldr` 每语言 5–6 条要点），而非交错文本。其他情况保持现状。
- Step 6（投递）：当 `format === "html"` 时，按 §3 数据流执行（写 JSON → 渲染 → 发附件，
  失败退回纯文本）。其他情况保持现状。
- 同时仍写一份 `/tmp/fb-digest.txt`（任一语言的纯文本版，作为兜底邮件内容）。

## 8. 配置变更

`~/.follow-builders/config.json`：

```json
{
  "delivery": {
    "method": "email",
    "email": "chloe@aisahub.com",
    "format": "html"
  }
}
```

`config/config-schema.json` 同步增加 `delivery.format` 字段（枚举 `text|html`，默认 `text`）。

## 9. 验收标准

- [ ] `delivery.format: "html"` 下，手动 `/follow-builders` 跑通：Chloe 收到带 HTML 附件的邮件。
- [ ] 附件在浏览器打开，中/EN/한 三个 tab 可点击切换，每 tab 是该语言完整简报。
- [ ] 每个 tab 顶部有 TL;DR 高亮框（5–6 条）+ 目录，目录点击锚点跳转到对应来源段落。
- [ ] 样式为 B 杂志社论风（米色纸感、衬线标题、金棕 accent），手机/桌面均可读。
- [ ] 每条目都有原文链接（推文支持多链接并排）；无链接条目不出现。
- [ ] 注入一个非法 JSON → 渲染失败 → 收到旧版纯文本邮件，错误进日志（不漏发）。
- [ ] `delivery.format: "text"`（或旧配置）行为不变，仍发纯文本邮件。
- [ ] `render-digest-html.js` 不引入新依赖。

## 10. 落地位置与同步

- 源仓库：`/Users/jrkim/Projects/jrkim-marketplace/my-utils/follow-builders/`
- 改动后需让插件缓存（`~/.claude/plugins/cache/jrkim-marketplace/...`）同步到新版本，
  cron 才会用上（具体同步方式在实现计划中确认）。
