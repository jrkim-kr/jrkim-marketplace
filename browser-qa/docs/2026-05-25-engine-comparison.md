# Browser-QA Engine Comparison — Playwright MCP vs agent-browser

**Date**: 2026-05-25
**Target**: `https://geared.ai`（aisahub.com 301 → geared.ai）
**Final Decision**: **保留 Playwright MCP，卸载 agent-browser**

## TL;DR

经过两轮测试（第一轮基于文档推断，第二轮实测验证），结论：

1. `agent-browser` 整体快约 1.5–2×，**不是**首轮报告夸的 29×
2. 速度优势在 agent loop 里被 tool roundtrip 稀释，提升不显著
3. `agent-browser click` 不自动等待路由跳转，对 `browser-qa` Phase 2 (interaction) 是实质缺陷
4. 错误信息密度 Playwright > agent-browser（前者带"下一步建议"）
5. Chloe 短期内不会用上 agent-browser 的 superset 能力（Electron / Slack / chat REPL）
6. **结论：卸载，未来真有触发条件再装回来（3 分钟）**

## 测试环境

- macOS Darwin 25.2.0, Apple Silicon
- Node v25.4.0, npm 11.7.0
- Chrome for Testing 149.0.7827.22
- `@playwright/mcp` 通过 browser-qa plugin 加载
- `agent-browser` 0.27.0（npm i -g）
- 流程：5 步 SPA 流程（navigate → snapshot → click → snapshot → navigate → screenshot → close）

## Phase A — 性能实测

### A.1 Agent loop 总耗时

| 引擎 | Wall-clock | 纯 CLI 时间 |
|---|---|---|
| Playwright MCP | ~135s | n/a（无法分离） |
| agent-browser | ~84s | ~5.2s |

**重要说明**：两侧数据都含 Claude tool roundtrip + 我在工具调用之间的处理时间。**严格意义上不可比**，但代表用户真实体验。

Playwright agent loop 耗时主要由 MCP transport latency 主导；agent-browser 由 bash subprocess overhead 主导。**引擎裸速度差异（~10×）在 agent loop 里被稀释为 ~1.5–2×**。

### A.2 Claude context 消耗

| 来源 | Playwright | agent-browser |
|---|---|---|
| 每次操作 inline 返回 | ~250 字节 | ~10–80 字节 |
| 自动 snapshot | 保存到文件，**不进** context | n/a（无自动 snapshot） |
| 显式 snapshot | 默认 inline ~7–11 KB（可用 `filename` 转文件） | 默认 stdout，shell 重定向 |

**首轮报告的错误论断**："Playwright 每次操作自动注入 8KB 快照到 context" — **错**。实测：auto-snapshot 保存到磁盘文件，inline 只返回 ~250 字节的文件引用。

**两侧 context 消耗等价**——只要 Claude 在两边都把快照存盘而不读全文。

### A.3 Snapshot 文件大小（磁盘，不进 context）

| 页面 | Playwright | agent-browser | 差异 |
|---|---|---|---|
| geared.ai 首页 | 7000 B / 134 行 | 7106 B / 159 行 | 相当 |
| /course | 5640 B | 3818 B / 96 行 | ab 小约 32% |
| /enterprise-edu | 17618 B | 11737 B / 344 行 | ab 小约 33% |

agent-browser 的 accessibility tree 格式更紧凑（`[level=N]` vs 多层嵌套 `generic` div）。**当 Claude 需要读完整 snapshot 时，agent-browser 节省约 30% token**。但这种"读全文"场景在 browser-qa 流程里不常见。

### A.4 截图

| | Playwright | agent-browser |
|---|---|---|
| 默认 viewport | 1512 × 810 | 1280 × 577 |
| 字节大小 | 73 KB | 64 KB |
| 视觉保真度 | 等价（同 Chrome 内核） | 等价 |

Viewport 默认不一致——切换引擎需重建 visual regression 基线。

附件：`pw-aisahub.png` / `pw-enterprise-edu.png` / `ab-aisahub.png` / `ab-enterprise.png`

## Phase B — 错误恢复对比

### B.1 点击不存在元素

| | Playwright MCP | agent-browser |
|---|---|---|
| 错误信息 | `Error: Ref e9999 not found in the current page snapshot. Try capturing new snapshot.` | `✗ Unknown ref: e9999` |
| 是否给下一步建议 | ✅ 是 | ❌ 否 |

### B.2 HTTP 404

| | Playwright MCP | agent-browser |
|---|---|---|
| 错误信息 | `Error: browserBackend.callTool: net::ERR_HTTP_RESPONSE_CODE_FAILURE at https://...` + call log | `✗ Navigation failed: net::ERR_HTTP_RESPONSE_CODE_FAILURE` |
| 信息详尽度 | 含 call log + wait state | 一行 |

### B.3 SPA "假 404"

geared.ai 对未匹配路径不返回 HTTP 404 而是渲染 fallback 主页。**两边都识别不出**——这是 SPA 设计问题，不是引擎问题。需要 Claude 靠 page title / DOM 判断。

## Phase C — agent-browser 实测缺陷

### C.1 click 不等待路由跳转 ⚠️

**复现步骤**：
1. `agent-browser open https://geared.ai`
2. `agent-browser snapshot` 拿到 `@e6 = STEP 3 link → /course`
3. `agent-browser click @e6`（返回 ✓ Done）
4. `agent-browser eval "document.location.href"` → 返回 `https://geared.ai/`

URL 没切换。Playwright 同操作直接跳到了 `/course`。

**对 browser-qa 的影响**：browser-qa Phase 2 (interaction) 整个流程依赖 click 后页面真切到下个 state。若每次 click 都要补 `wait` + 重抓 snapshot，**抵消速度优势 + 增加流程复杂度**。

**绕过方式**：`agent-browser wait <selector|ms>` 命令存在但需要 Claude 主动调用。

### C.2 viewport 默认不一致

需要额外配置才能对齐 Playwright 默认值。文档检查未找到清晰的 viewport 设置命令（`viewport <w> <h>` 列在 help 里但作为独立命令调用失败）。

## Phase D — 能力覆盖矩阵

| 场景 | Playwright MCP | agent-browser | Chloe 短期触发概率 |
|---|---|---|---|
| Web 浏览器 QA | ✓ | ✓ | 高（已在用 Playwright） |
| Electron 桌面应用 | ❌ | ✓ `electron` | **很低** — Aisahub/Personal 全是 web stack |
| Slack 工作区自动化 | ❌ | ✓ `slack` | **低** — Slack API + 官方 MCP 更专业 |
| AI 自然语言 REPL | △ via Claude Code | ✓ `chat` | **很低** — 已通过 Claude Code + Playwright 实现等价 |
| Vercel Sandbox microVM | ❌ | ✓ `vercel-sandbox` | **很低** — 当前无该场景 |
| AWS Bedrock cloud browser | ❌ | ✓ `agentcore` | **极低** |
| 探索式 bug hunt | △ 手写 | ✓ `dogfood` | 低 |

## 决策

### 卸载 agent-browser

理由：
1. **性能优势小**——agent loop 实际差 ~1.5–2×，非显著
2. **click 不等待是核心缺陷**——browser-qa interaction phase 会反复踩
3. **错误信息密度低**——debug 体验差
4. **superset 能力短期用不上**——Chloe 工作内容是 web stack，Slack 走 API，chat REPL 已有等价物
5. **重装成本低**——3 分钟可恢复
6. 符合 CLAUDE.md Section 2 "Simplicity First" + Primary adoption risk "over-investment"

### 重新触发评估的条件（明确写下，方便未来 Chloe 决策）

任一发生时，重新评估装回来：

1. **Aisahub 或 Personal 开始开发 Electron 桌面应用**（VS Code 扩展、Notion 插件、桌面客户端等）
2. **需要在没有 Slack API 权限的情况下做 Slack 自动化**（罕见，但比如帮客户自动化他们的 Slack 时）
3. **需要写不依赖 Claude Code 的独立浏览器自动化脚本**（CI step、cron job、bash pipeline）
4. **agent-browser 发布 1.0 + 修复 click 自动等待问题**（监控 `vercel-labs/agent-browser` CHANGELOG）

### 不切换 browser-qa 引擎槽位

`browser-qa/.mcp.json` 保留 `@playwright/mcp`。理由同上 + 切换的迁移成本（重写 SKILL.md、重建 visual baseline）目前没有匹配的收益。

## 教训 — 给未来评估用

**首轮报告犯了未验证就下结论的错**：
- 从架构推断「auto-snapshot = auto-inject 到 context」→ 错（实际是文件引用）
- 由时间数据差大归因到这个错误的架构假设 → 错误论断 29×
- 没实测 inline vs file 的实际行为

**应用到 should-i-use skill**：Honest Self-Check 段应增加一条——「**如果论断涉及性能差异或运行时行为，必须实测；不能从架构文档推断**」。

**给 Chloe 用的判断启发**：
- AI 给出的"X 倍优势"类论断，问一句"实测了吗"
- 论断越强越要验证，特别是涉及钱（订阅）/时间（迁移）/锁定（依赖）的决策
- 验证成本通常很低（这次 15 分钟）但避免了一个错误的迁移决策

## 附录：迭代历史

- **17:18** 初次报告 — 基于文档 + 单步 smoke 测试，给出 29× perf + TRY-INLINE
- **17:46** 验证报告 — 5 步 SPA 流程实测，推翻 29× 论断，发现 click 不等待缺陷
- **18:00** 现报告 — 合并两轮，最终决定卸载

## 附录：测试限制

1. 样本量 1（每个流程跑一次）
2. Playwright wall-clock 含 Claude 处理时间，非纯引擎时间
3. 未测：并发 session、视频录制、auth state 持久化、长流程稳定性
4. 未测：agent-browser `chat` REPL 实际质量
5. 未深入测：agent-browser `wait` 命令能否完全替代 click 自动等待
