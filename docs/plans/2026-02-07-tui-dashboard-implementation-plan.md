# Right.codes TUI Dashboard MVP 实现计划

> **For Claude:** REQUIRED SUB-SKILL: 使用 `superpowers:subagent-driven-development`（本 session 通过 `codeagent-wrapper` 分发子代理）逐任务执行；每个任务严格遵循 TDD（先红后绿）。

**Goal:** 在命令行内提供一个“可刷新、可降级、离线可测”的 Right.codes 个人用量看板（含 quota 汇总 / 套餐表 / burn rate / ETA / 趋势 / 明细 logs / doctor）。

**Architecture:** 采用“三层”结构：`client` 负责 HTTP 与错误映射；`normalize + metrics` 负责多 shape 兼容与纯函数计算；`tui` 负责 Textual 渲染与交互（watch/refresh/backoff/stale）。

**Tech Stack:** Python `>=3.9` + `Textual` + `httpx` + `pydantic` + `typer`；测试 `pytest` + `respx`（全部离线 mock）。

---

## Task 1：项目骨架（Python 包 + CLI 入口）

**Files:**
- Create: `rightcodes-tui-dashboard/pyproject.toml`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/__init__.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/cli.py`
- Create: `rightcodes-tui-dashboard/tests/test_smoke_cli.py`
- Modify: `rightcodes-tui-dashboard/README.md`（补“安装/运行/无敏感信息”说明）

**Step 1: 写 failing test（RED）**
- 目标：`python -m rightcodes_tui_dashboard.cli --help` 可运行（或 `rightcodes --help` 入口可运行，取决于实现方式）。

**Step 2: 运行测试确认失败**
- Run: `python3 -m pytest -q`
- Expected: FAIL（模块不存在/入口不存在）

**Step 3: 最小实现（GREEN）**
- 提供 CLI 根命令 `rightcodes`（或模块入口），包含子命令占位：`login / dashboard / logs / doctor`。

**Step 4: 运行测试确认通过**
- Run: `python3 -m pytest -q`
- Expected: PASS

---

## Task 2：Token 存取（keyring 优先 + .local 文件兜底）

**Files:**
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/token_store.py`
- Create: `rightcodes-tui-dashboard/tests/test_token_store.py`
- Create: `rightcodes-tui-dashboard/.local/.gitkeep`（确保目录存在；内容为空）

**Step 1: failing tests（RED）**
- 覆盖：`store=auto` 的优先级；file 兜底路径必须落在 `rightcodes-tui-dashboard/.local/`；文件权限必须是 `0o600`；读取失败返回可解释错误。

**Step 2: 最小实现（GREEN）**
- 封装 `TokenStore`：`load_token()` / `save_token()`，严禁把 token 打到日志。

---

## Task 3：HTTP Client + 错误映射 + 429 退避状态机

**Files:**
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/client.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/backoff.py`
- Test: `rightcodes-tui-dashboard/tests/test_backoff.py`
- Test: `rightcodes-tui-dashboard/tests/test_client_errors.py`

**Step 1: failing tests（RED）**
- 401/403 → `AuthError`（提示 `rightcodes login`）
- 429 → `RateLimited`（包含 `next_retry_at`/`attempt`）
- 非 2xx → `ApiError`（不得包含敏感信息）
- backoff：指数退避 + deterministic jitter（测试可注入 RNG）

**Step 2: 最小实现（GREEN）**
- 使用 `httpx`；仅走 JSON 接口；不做 Playwright。

---

## Task 4：响应归一化（多 shape 兼容）+ 纯函数指标计算

**Files:**
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/models.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/normalize.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/metrics.py`
- Test: `rightcodes-tui-dashboard/tests/test_normalize_variants.py`
- Test: `rightcodes-tui-dashboard/tests/test_metrics.py`
- Create fixtures: `rightcodes-tui-dashboard/tests/fixtures/*.json`（全部为“无真实值”的最小样例）

**Step 1: failing tests（RED）**
- `/auth/login`：`user_token` vs `userToken`
- stats：tokens/cost/requests 字段名变体
- advanced：容器字段与 bucket 字段变体（无法解析则降级）
- quota 汇总 / burn rate / ETA 的边界条件（见 spec 6.x）

**Step 2: 最小实现（GREEN）**
- “输入 JSON → 归一化模型 → 纯函数计算”分层实现，确保可离线复现。

---

## Task 5：Textual TUI（Dashboard + Logs + Doctor + Help）

**Files:**
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/app.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/screens/dashboard.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/screens/logs.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/screens/doctor.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/screens/help.py`
- Create: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/tui/widgets/sparkline.py`

**Step 1: failing tests（RED）**
- MVP 以“离线单测为主”，TUI 仅做最小可测：校验“退避期间 r 不会触发请求”；以及 view-model 渲染不因字段缺失崩溃（可用 snapshot/组件单测，或将逻辑抽到可测纯函数）。

**Step 2: 最小实现（GREEN）**
- Dashboard 单屏：Quota Summary / Subscriptions Table / Usage & Trend
- Footer：Last OK / Next refresh / Backoff / Stale
- 快捷键：`q r l d ?`（见 spec 5.2）
- 降级：401/429/解析失败 → banner + stale

---

## Task 6：命令联动（login/dashboard/logs/doctor）+ 离线回归验证

**Files:**
- Modify: `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/cli.py`
- Test: `rightcodes-tui-dashboard/tests/test_cli_commands.py`
- Modify: `rightcodes-tui-dashboard/docs/worklog.md`

**Step 1: failing tests（RED）**
- `login` 走 getpass；不回显；成功保存 token；失败提示下一步
- `dashboard --watch 30s` 解析参数（不强制跑 UI）
- `doctor` 输出 keys（不输出值）

**Step 2: 运行离线回归**
- Run: `python3 -m pytest -q`
- Expected: PASS

**Step 3: worklog 记录**
- 记录：命令 + 结果（不得记录 token / 明细值）

---

## Task 7：结项文档闭环

**Files:**
- Create: `rightcodes-tui-dashboard/docs/task-summaries/2026-02-07-tui-dashboard-mvp-implementation.md`
- Modify: `rightcodes-tui-dashboard/DOCS_INDEX.md`

**Acceptance Criteria（Doc/DoD）**
- spec 对齐、离线单测通过、有 worklog 证据、有 task summary、索引已更新。

