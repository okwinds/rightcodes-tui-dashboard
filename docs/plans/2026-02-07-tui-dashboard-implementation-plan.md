# Right.codes TUI Dashboard 实现计划（MVP → v0.1.x）

更新时间：2026-02-08  
状态：已完成（当前实现已发布到 `v0.1.13`；本文件用于回溯与后续迭代）

> 说明：本计划最初用于 MVP 的 Spec-Driven + TDD 拆分。随着仓库开源与多次迭代，部分路径/命名已调整；
> 本文件已按“当前仓库根目录为项目根目录”的布局做了对齐更新。

**Goal:** 在命令行内提供一个“可刷新、可降级、离线可测”的 `right codes` 个人用量看板（含余额/套餐/速率/ETA/趋势/明细 logs/doctor）。

**Architecture:** 三层结构：
- `api + errors`：HTTP 与错误映射
- `services`：多 shape 兼容与纯函数计算（解析/口径）
- `ui`：Textual 渲染与交互（watch/refresh/backoff/stale）

**Tech Stack:** Python `>=3.9` + `Textual` + `httpx` + `argparse`；测试 `pytest`（离线为主）。

## 当前实现要点（v0.1.x）

- token 存储：keyring 优先，失败降级到“全局数据目录” `token.json`（支持 `RIGHTCODES_DATA_DIR`）
- `dashboard`：未登录或 token 过期时不直接报错退出，会进入交互式 `login` 流程
- “使用记录明细”支持翻页（`p/n`），并从 JSON 字段提取 `渠道/倍率/资费/Tokens`（不写死）

---

## Task 1：项目骨架（Python 包 + CLI 入口）

**Files:**
- Create: `pyproject.toml`
- Create: `src/rightcodes_tui_dashboard/__init__.py`
- Create: `src/rightcodes_tui_dashboard/__main__.py`
- Create: `src/rightcodes_tui_dashboard/cli.py`
- Create: `tests/test_smoke_cli.py`
- Modify: `README.md`（补“安装/运行/安全约束”说明）

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
- Create: `src/rightcodes_tui_dashboard/storage/token_store.py`
- Create: `tests/test_token_store_global_file.py`

**Step 1: failing tests（RED）**
- 覆盖：`store=auto` 的优先级；file 兜底路径必须落在“全局数据目录”；文件权限尽量 `0o600`；旧版 `.local/token.json` 可迁移读取。

**Step 2: 最小实现（GREEN）**
- 封装 `TokenStore`：`load_token()` / `save_token()`，严禁把 token 打到日志。

---

## Task 3：HTTP Client + 错误映射 + 429 退避状态机

**Files:**
- Create: `src/rightcodes_tui_dashboard/api/client.py`
- Create: `src/rightcodes_tui_dashboard/services/backoff.py`
- Test: `tests/test_backoff.py`
- Test: `tests/test_api_client_errors.py`

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
- Create/Modify: `src/rightcodes_tui_dashboard/services/calculations.py`
- Create/Modify: `src/rightcodes_tui_dashboard/services/use_logs.py`
- Test: `tests/test_calculations.py`
- Test: `tests/test_use_logs_extract.py`

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
- Create/Modify: `src/rightcodes_tui_dashboard/ui/app.py`
- Test: `tests/test_textual_render_name_collision.py`
- Test: `tests/test_burn_eta_layout.py`

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
- Modify: `src/rightcodes_tui_dashboard/__main__.py`
- Modify: `src/rightcodes_tui_dashboard/cli.py`
- Test: `tests/test_cli_help_output.py`
- Test: `tests/test_cli_version_flag.py`
- Modify: `docs/worklog.md`

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
- Create: `docs/task-summaries/2026-02-07-tui-dashboard-mvp-implementation.md`
- Update: `docs/INDEX.md`（仓库可提交的文档索引；替代本地 `DOCS_INDEX.md`）

**Acceptance Criteria（Doc/DoD）**
- spec 对齐、离线单测通过、有 worklog 证据、有 task summary、索引已更新。
