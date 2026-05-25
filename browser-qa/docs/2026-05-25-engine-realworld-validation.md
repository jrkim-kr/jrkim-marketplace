# Engine Real-World Validation — geared.ai SPA 流程

**Date**: 2026-05-25
**Follow-up to**: `2026-05-25-engine-comparison.md`
**Goal**: 验证（或推翻）第一轮报告"agent-browser 在 browser-qa 引擎槽位上有 29× perf 优势"的论断

---

## TL;DR — 第一轮报告需要修正

**重大修正**：第一轮的 29× perf 论断**夸大了**。

| 论断 | 实测 |
|---|---|
| "Playwright MCP 每次操作自动注入 8KB 快照到 Claude context" | ❌ 错——Playwright MCP 把 auto-snapshot **保存到磁盘文件**，inline 只返回 ~250 字节的文件引用 |
| "29× 速度优势" | ⚠️ 实际 agent-loop wall-clock 差距约 1.5–2×（135s vs 84s 在 5 步 SPA 流程里） |
| "agent-browser 是 superset" | ✅ 仍然成立 |
| "切换有迁移成本" | ✅ 仍然成立，且本轮发现新风险（见下） |

底层引擎速度差异是真的（agent-browser CLI 纯执行 ~5.2s vs Playwright 工具调用更慢），但**整体 agent 循环时间被 MCP/Bash tool roundtrip 主导**，引擎裸速度的优势在循环里被稀释。

---

## 测试场景

5 步 SPA 流程在 `https://geared.ai`：

1. navigate → 首页
2. snapshot 首页
3. click STEP 3 → 跳转 /course (或直接 navigate /course)
4. snapshot 课程页
5. navigate /enterprise-edu → 截图 → close

---

## Phase A — 引擎性能（修正版）

### A.1 wall-clock 对比（agent loop 视角）

| 步骤 | Playwright MCP | agent-browser |
|---|---|---|
| navigate (首页) | ~35s | 2.33s |
| click + snapshot | ~59s* | 0.36s (但 click 没生效) |
| navigate /course | n/a | 1.28s |
| navigate /enterprise-edu | ~12s | 0.24s |
| snapshot + screenshot | ~11s | 0.37s |
| close | ~18s | 0.29s |
| **agent loop 总计** | **~135s** | **~84s** |
| **纯 CLI 时间（仅 agent-browser）** | n/a | **~5.2s** |

\* Playwright 该步包含 Claude bash grep 文件读取来找 ref 的时间

**重要的诚实声明**：Playwright 数据含 Claude 工具调用 roundtrip + 我在两个工具调用之间的处理时间。agent-browser 总计也含 bash roundtrip 但 agent-browser CLI 本身只占 5.2s。**这两个数字不严格可比**，但它们都代表"agent 用户的真实体验"。

### A.2 Claude context 消耗（按 inline 返回字节数算）

| 来源 | Playwright | agent-browser |
|---|---|---|
| 每次 navigate inline 返回 | ~250 字节（URL + title + 文件引用） | ~80 字节（✓ + URL） |
| 每次 click inline 返回 | ~270 字节 | ~10 字节（✓ Done） |
| 每次 screenshot inline 返回 | ~200 字节 | ~50 字节 |
| 每次 close inline 返回 | ~100 字节 | ~20 字节 |
| Snapshot inline（按需调用） | ~7–11 KB（直接 stdout） | 0（我 `> file`） |

**核心修正**：Playwright MCP 的 `browser_snapshot` 工具默认 inline 返回完整 yaml；可通过 `filename` 参数转到文件。agent-browser 默认 stdout，由 shell 重定向控制。

→ **两边在 context 消耗上等价**，前提是 Claude 在两边都把快照存盘而不读全文。第一轮报告说"agent-browser 自动省 context"的论断不严谨。

### A.3 Snapshot 文件大小（磁盘，不进 context）

| 页面 | Playwright | agent-browser |
|---|---|---|
| 首页（partial load） | 7000 B / 134 行 | 4679 B / 116 行 |
| 首页（full load） | 7000 B / 134 行 | 7106 B / 159 行 |
| /course | 5640 B / ? 行 | 3818 B / 96 行 |
| /enterprise-edu | 17618 B / ? 行 | 11737 B / 344 行 |

**agent-browser 的 accessibility tree 整体小约 30%**——格式更紧凑（`[level=N]` 替代多层嵌套 `generic` div）。从 token 经济性角度，**当 Claude 需要读完整 snapshot 时，agent-browser 节省约 30% token**。

---

## Phase B — 错误恢复对比

### B.1 点击不存在元素

| | Playwright MCP | agent-browser |
|---|---|---|
| 报错信息 | `Error: Ref e9999 not found in the current page snapshot. Try capturing new snapshot.` | `✗ Unknown ref: e9999` |
| 退出码 | tool error | exit 1 |
| 建议下一步 | 有（"capture new snapshot"） | 无 |

→ Playwright 报错**更可指导**（明确建议重新抓快照）。agent-browser 简短但要靠用户推断原因。

### B.2 HTTP 404

| | Playwright MCP | agent-browser |
|---|---|---|
| 报错信息 | `Error: browserBackend.callTool: net::ERR_HTTP_RESPONSE_CODE_FAILURE at https://httpbin.org/status/404` + call log | `✗ Navigation failed: net::ERR_HTTP_RESPONSE_CODE_FAILURE` |
| 退出码 | tool error | exit 1 |

→ 两边都报到了，**Playwright 信息更详细**（call log 含 wait state）。agent-browser 一行结论。

### B.3 SPA "假 404"（geared.ai/nonexistent）

geared.ai 的 SPA 对未匹配路径**不返回 HTTP 404**，而是渲染主页 fallback。两个引擎都报告 `EXIT=0`，没识别出"实际上是 404"。

→ **两边相同**——这是 SPA 设计问题，不是引擎问题。Claude 必须靠 page title / DOM 内容判断是否是真错误。

---

## Phase C — 新发现的 agent-browser 缺陷

### C.1 click 不自动等待路由跳转 ⚠️

**复现**：homepage snapshot 拿到 `@e6 = STEP 3 link → /course`，执行 `agent-browser click @e6` 后 `eval "document.location.href"` 仍返回 `https://geared.ai/`，路由没切换。

**对比**：Playwright 同一个 click 操作直接到了 `/course`。

**原因（推测）**：
- agent-browser click 是触发 fire-and-forget，不等待 navigation event
- 需要显式 `agent-browser wait` 或后续 navigation 命令

**对 browser-qa 流程的影响**：**大**——browser-qa Phase 2 (interaction) 全部依赖 click 后页面真的切到下一个 state。若每次都要补 `wait` + 重抓 snapshot，**抵消了一部分速度优势**。

### C.2 viewport 默认与 Playwright 不一致

| | 默认 viewport |
|---|---|
| Playwright MCP | 1512 × 810 |
| agent-browser | 1280 × 577 |

可配置但不一致，意味着 browser-qa 的 visual regression 阶段切换引擎后基线全废，必须重建。

### C.3 截图视觉保真度（目视判断）

- `pw-enterprise-edu.png`（1512×810, 73KB）
- `ab-enterprise.png`（1280×577, 64KB）

未做精确像素 diff（imagemagick/PIL 未装，不为单次测试增加依赖）。目视：两图字体渲染、布局、颜色一致——同一个 Chrome 内核，理应等价。dimension 差是 viewport 设置差。

---

## 结论 — 修正后的推荐

### 推翻第一轮的论断

- ❌ "Playwright 自动注入 8KB 快照到 context" — 错。它是文件引用。
- ❌ "29× 速度优势" — 夸大。agent-loop 实际差 ~1.5–2×。
- ❌ "切换显著节省 token" — 不严谨。只在 Claude 需要读全 snapshot 时省 30%。

### 仍然成立的结论

- ✅ agent-browser 是能力 superset（Electron / Slack / Sandbox / chat REPL）
- ✅ agent-browser CLI 纯执行速度更快
- ✅ snapshot 格式更紧凑（省 30% token）

### 新增的反对切换证据

- ⚠️ **click 不等待导航**——这对 browser-qa 是核心痛点，会反复引发"明明点了但 URL 没变"的 bug
- ⚠️ **错误信息密度低**——agent-browser 报错短，debug 时要补信息
- ⚠️ **viewport 默认不一致**——visual regression 基线要全部重建

### 最终建议

**不推荐立刻切换 browser-qa 的引擎槽位**。理由：
1. 性能优势没第一轮夸的那么大（~2× 而非 30×）
2. click 不等待导航是个实质缺陷，会增加 browser-qa 流程的复杂度
3. Playwright 错误信息更可指导

**继续保留 agent-browser 安装的场景**：
- 要测 Electron 桌面应用时
- 要做 Slack 自动化时
- 想试 `agent-browser chat` 自然语言 REPL 时

**Verdict 调整**：从 `TRY-INLINE` → **`WAIT-FOR-TRIGGER`**。触发条件就是上面 3 个场景之一实际发生。

---

## 附录：测试限制

1. **样本量 1**——每个流程只跑一次
2. **agent-browser click 不导航这一发现可能可以通过 `wait` 命令绕过**——没深入测
3. **Playwright wall-clock 含 Claude 处理时间**——和 agent-browser CLI 纯时间不严格可比
4. **未测**：并发 session、视频录制、auth state 持久化、移动端 viewport 一致性、长流程稳定性
5. **未测**：agent-browser 的 `chat` REPL 实际质量

## 附录：教训

第一轮报告**犯了未验证就下结论的错**。具体：
- 看到 Playwright MCP 文档说 "auto-snapshot" → 假设 "auto-inject to context"
- 看到时间数据差大 → 归因到 "auto-snapshot 注入"
- 没实测 inline vs file 的实际行为

**应用到下次评估**：should-i-use skill 的 Honest Self-Check 段要加一条——「如果论断涉及性能差异，必须实测，不能从架构推断」。
