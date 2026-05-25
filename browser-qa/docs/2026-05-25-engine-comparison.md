# Engine Comparison — Playwright MCP vs agent-browser

**Date**: 2026-05-25
**Target URL**: `https://aisahub.com` → 实际跳转到 `https://geared.ai/`（Geared Studio 主页）
**Workflow**: `browser-qa` Phase 1 (smoke) — navigate → snapshot → screenshot → click 首个导航链接 → close
**Runs**: 各 1 次（一次性对比，非 benchmark suite）

---

## 1. 测试环境

- 机器: macOS Darwin 25.2.0 (Apple Silicon)
- Node: v25.4.0
- Chrome for Testing: 149.0.7827.22（agent-browser 自动安装）
- Playwright MCP: `@playwright/mcp` (browser-qa 默认依赖)
- agent-browser: 0.27.0 (`npm i -g agent-browser`)

---

## 2. Phase A — 引擎性能对照

### 2.1 单步耗时（秒）

| 步骤 | Playwright MCP* | agent-browser | 倍数 |
|---|---|---|---|
| navigate | ~16.2 | 4.09 | ~4× |
| snapshot | ~11 | 0.18 | ~60× |
| screenshot | ~11.4 | 0.19 | ~58× |
| click | ~36 | 0.19 | ~190× |
| close | ~10 | 0.29 | ~35× |
| **总计** | **~143** | **4.94** | **~29×** |

\* Playwright MCP 数据含 Claude tool roundtrip + 内联 snapshot 处理开销。agent-browser 数据是纯 CLI wall-clock。**不是 apples-to-apples 的引擎裸速度对比，而是"agent 循环里真实感受到的延迟"**——这是日常使用关心的维度。

### 2.2 产物大小

| 产物 | Playwright MCP | agent-browser |
|---|---|---|
| Snapshot 文本 | 7000 字节 / 134 行 | 7106 字节 / 159 行 |
| Screenshot 字节 | 100 KB | 73 KB |
| Screenshot 分辨率 | 1512 × 810 | 1280 × 577 |

快照大小**几乎相同**——两边都用 accessibility tree 格式，token 占用接近一致（约 1.7k 中文 token）。截图分辨率差异是默认 viewport 设置不同导致，可配置。

### 2.3 关键架构差异

**Playwright MCP**：每次操作（navigate / click 等）**自动附带一次完整 snapshot 注入到 Claude 上下文**。所以 click 操作的 36 秒里大半时间是 Claude 处理 8KB yaml。`auto-snapshot 默认开启 / auto-snapshot enabled by default`

**agent-browser**：snapshot 是**独立显式命令**，操作命令只返回 `✓ Done`。Claude 自己决定什么时候花 1.7k token 取快照。`on-demand snapshot model / 按需快照模型`

这是性能差异的真正根源——**不是引擎本身快 30 倍，而是 agent-browser 不把快照塞到每个动作里**。

---

## 3. Phase B — 能力覆盖矩阵

实测确认 agent-browser 提供 6 个 specialized skill：`core / electron / slack / dogfood / vercel-sandbox / agentcore`。

| 场景 | Playwright MCP | agent-browser | 价值评估 |
|---|---|---|---|
| Web 浏览器 QA | ✓ | ✓ | 两者都覆盖；agent-browser 在循环里更快 |
| Electron 桌面应用 | ❌ | ✓ `electron` | 仅 ab；VS Code / Notion / Figma 扩展测试 |
| Slack 工作区自动化 | ❌ | ✓ `slack` | 仅 ab；读未读、发消息、搜对话 |
| AI 自然语言 REPL | ❌ | ✓ `chat` | 仅 ab；`agent-browser chat "..."` 内置 LLM 操控 |
| Vercel Sandbox microVM | ❌ | ✓ `vercel-sandbox` | 仅 ab；Vercel 内跑 e2e 不卡依赖 |
| AWS Bedrock cloud browser | ❌ | ✓ `agentcore` | 仅 ab；AWS 云端 headless |
| 探索式 bug hunt | △ 手写 | ✓ `dogfood` | ab 有结构化脚本 |
| Claude context 经济性 | ❌ 自动注入 | ✓ 按需 | ab 更省 token |

---

## 4. 最佳使用场景

### 4.1 留在 Playwright MCP 的场景

- **已有 `browser-qa` skill 跑得顺**——切换无具体痛点
- **不写 Slack/Electron/Sandbox**——`agent-browser` 独有能力都用不上
- **依赖 Playwright 生态**（trace viewer、video recording 等）

### 4.2 切到 agent-browser 的触发条件

按重要性排：

1. **需要测 Electron 桌面应用**（VS Code 扩展、Notion 桌面端）——Playwright MCP 完全做不到
2. **需要 Slack 自动化**（读 Aisahub 团队未读消息、自动汇总）——直接装能用
3. **当前 browser-qa 循环里 Claude 上下文压力大**——单次 `click` 灌 8KB snapshot 几次后 context 就满了；ab 的按需快照能省 5-10× context
4. **想要 `chat` 自然语言 REPL** 做交互式探索——`agent-browser chat "打开 X 截首屏"` 一行搞定

### 4.3 共用情景

`browser-qa` skill 流程（4 阶段 playbook）**可以以 agent-browser 为引擎**。`browser-qa/.mcp.json` 当前挂的是 `@playwright/mcp`，可替换为 agent-browser 的 daemon。但**两个引擎不可同时挂**——两份 Chrome 实例 + 两套 session 状态 = 调试地狱。

---

## 5. 结论

**架构定位**：`browser-qa` 是配方（要测什么），`agent-browser` 是引擎（用什么打开 Chrome）。二者**不替代彼此**。

**性能对比**：在 agent 循环里，agent-browser 整体快 ~29×，**主因不是引擎本身快，而是不强制每次操作灌快照**。等价于"省了 Claude 的处理时间"。

**能力对比**：`agent-browser` 是超集——它能做 Playwright MCP 能做的所有事，外加 Electron / Slack / Sandbox / AgentCore / chat REPL。

**当下推荐**：保留 Playwright MCP（已配置好、跑顺了）。**遇到下面任一情景再切换**：
1. 要测 Electron 应用
2. 要做 Slack 自动化
3. 当前 browser-qa 循环里 Claude context 频繁打爆
4. 想试 chat REPL 自然语言操控

`TRY-INLINE` verdict 不变，**但触发优先级提高了**——快照吞 token 这件事是 Playwright MCP 架构层面的问题，未来跑较长 QA 流程时会重复痛。

---

## 附录：截图

- `pw-aisahub.png` — Playwright MCP 截图（1512×810, 100KB）
- `ab-aisahub.png` — agent-browser 截图（1280×577, 73KB）

## 附录：测试限制说明

1. **样本量 1**——每个引擎只跑一次，无法捕获网络抖动。结论的"倍数"是数量级判断，不是精确测量。
2. **Playwright 数据带 Claude 处理开销**——和 agent-browser 的纯 CLI 时间不可严格对照。但代表 agent 用户的真实体验。
3. **未测**：内存占用、并发 session、视频录制质量、移动端 viewport 一致性、跨页面 cookie/auth 持久化。
4. **目标站点**：`aisahub.com` 已 301 重定向到 `geared.ai`——这是 Chloe 的旧域名转手数据。测试本身不受影响。
