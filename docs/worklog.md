# Worklog

> 用途：工作记录（append-only）。  
> 规则：记录关键命令、结论与决策；不记录敏感信息（API key、token、私密数据），必要时用 `***` 占位。

> 备注：
> - 本仓库不提交根目录 `DOCS_INDEX.md`（仅本地使用）；对外可提交的文档导航请见 `docs/INDEX.md`。
> - `2026-02-07` 部分记录包含 `rightcodes-tui-dashboard/` 前缀，这是当时目录试验的历史痕迹，当前仓库根目录即项目根目录。

---

## Log Entry (copy/paste per step)

### Timestamp

- When: `YYYY-MM-DD HH:MM`
- Who: `human / agent`
- Context: `short description`

### Goal (this step)

- Goal:
- Constraints:

### Action

- Files touched:
  - `path/to/file`
- Commands run:
  - `...`

### Result

- Outcome:
- Key output/snippet (optional, short):

### Decision (if any)

- Decision:
- Why:
- Alternatives considered:

### Next

- Next step:
- Risks/Notes:

---

## Suggested Sections (optional)

如果你希望 worklog 更易检索，可以在文件顶部加一个简短目录：
- `## 2026-02-03`（按日期分段）
- `### Feature: ...` / `### Bugfix: ...`

---

## 2026-02-07

### Repo: 项目产物收敛到子目录

- When: `2026-02-07 15:13`
- Who: `agent`
- Context: 将现有产物收敛到 `rightcodes-tui-dashboard/`，根目录保留 stub，并隔离 doctor 输出。

#### Action

- Files touched:
  - `AGENTS.md`
  - `DOCS_INDEX.md`
  - `README.md`
  - `.gitignore`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
  - `rightcodes-tui-dashboard/docs/`（目录迁移）
  - `rightcodes-tui-dashboard/templates/`（目录迁移）
  - `rightcodes-tui-dashboard/tools/`（目录迁移）
  - `rightcodes-tui-dashboard/.local/rightcodes-doctor.json`（移动并忽略）
- Commands run:
  - `mkdir -p rightcodes-tui-dashboard`
  - `mv AGENTS.md DOCS_INDEX.md README.md docs templates tools rightcodes-tui-dashboard/`
  - `mkdir -p rightcodes-tui-dashboard/.local`
  - `mv rightcodes-doctor.json rightcodes-tui-dashboard/.local/rightcodes-doctor.json`
  - `rg "rightcodes-cli-dashboard/" rightcodes-tui-dashboard/DOCS_INDEX.md`

#### Result

- Outcome: 仓库根目录仅保留指向说明；项目内容集中在 `rightcodes-tui-dashboard/`；doctor 输出移入 `.local/` 并通过 `.gitignore` 忽略。

### Spec: TUI Dashboard MVP（可 TDD）

- When: `2026-02-07 15:29`
- Who: `agent`
- Context: 新增 TUI Dashboard MVP 主规格文档（Spec-Driven），为后续 TDD 实现提供可执行契约与验收标准。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `mkdir -p rightcodes-tui-dashboard/docs/specs`

#### Result

- Outcome: 新增完整 MVP spec（Goal/Constraints/Contract/CLI/UI/计算口径/退避与 stale/测试计划/验收标准），并已登记到 `DOCS_INDEX.md`。

### Spec: 约束自洽（Python/依赖门槛）

- When: `2026-02-07 15:35`
- Who: `agent`
- Context: 让规格与上游生态/实现计划一致，避免无意义抬高门槛。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `date '+%Y-%m-%d %H:%M'`
  - `python3 -m pytest`

#### Decision

- Decision: 将 Python 最低版本从 `>=3.11` 调整为 `>=3.9`；MVP 退避逻辑自实现且不强依赖 `tenacity`；`keyring`/`platformdirs` 为可选依赖。
- Why: Textual 生态本身支持 Python `^3.9`；降低安装门槛、扩大可用环境；MVP 依赖尽量保持最小可行。

### Plan: MVP 实现任务拆分（供 TDD 执行）

- When: `2026-02-07 16:10`
- Who: `agent`
- Context: 按 `docs/specs/tui-dashboard-mvp.md` 将实现拆分为可执行任务，便于用子代理逐步交付（离线单测为门槛）。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/docs/plans/2026-02-07-tui-dashboard-implementation-plan.md`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`

#### Result

- Outcome: 已生成可执行的实现计划，并登记到 `DOCS_INDEX.md`；下一步进入子代理实现（严格 TDD）。

### Implement: CLI + TUI MVP（离线可测）

- When: `2026-02-07 16:35`
- Who: `agent`
- Context: 落地 MVP 代码骨架与核心能力：CLI（login/dashboard/logs/doctor）+ Textual TUI（Dashboard/Logs/Doctor/Help），并补齐离线单测。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/pyproject.toml`
  - `rightcodes-tui-dashboard/README.md`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/__main__.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/cli.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/privacy.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/backoff.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
  - `rightcodes-tui-dashboard/tests/test_backoff.py`
  - `rightcodes-tui-dashboard/tests/test_duration_and_parsing.py`
- Commands run:
  - `python3 -m pip install -e '.[dev]'`
  - `python3 -m pytest`
  - `python3 -m rightcodes_tui_dashboard --help`

#### Result

- Outcome: CLI 可运行；TUI 支持自动刷新/退避与 stale 展示；Logs/Doctor/Help 屏可从 Dashboard 快捷键进入；离线单测通过（无外网/无账号依赖）。

### Fix: Textual `_render` 命名冲突 + 解析 `trend`

- When: `2026-02-07 19:55`
- Who: `agent`
- Context: 用户实测触发 TUI 渲染崩溃（Textual 内部调用 `_render()`），并提供 doctor 输出显示 advanced 响应包含 `trend` 字段。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
  - `rightcodes-tui-dashboard/tests/test_textual_render_name_collision.py`
  - `rightcodes-tui-dashboard/tests/test_calculations.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
- Commands run:
  - `python3 -m pytest`

#### Result

- Outcome: 不再覆盖 Textual 内部 `_render`；advanced 响应支持从 `trend` 提取 buckets；离线回归通过（`19 passed`）。

### Fix: Textual `_render` 命名冲突崩溃

- When: `2026-02-07 19:50`
- Who: `agent`
- Context: Textual 在渲染 `Screen` 时会调用内部 `_render()`；项目代码中在 `Screen` 子类定义了 `_render(self, data)` 覆盖上游实现，导致签名不匹配并崩溃。

#### Goal (this step)

- Goal: 避免覆盖 Textual 内部 `_render()`，修复 dashboard 渲染崩溃，并新增离线回归测试护栏。
- Constraints: 不修改上游 Textual；不输出敏感信息；离线单测可运行。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/tests/test_textual_render_name_collision.py`
  - `rightcodes-tui-dashboard/docs/specs/2026-02-07-fix-textual-render-name-collision.md`
  - `rightcodes-tui-dashboard/docs/task-summaries/2026-02-07-fix-textual-render-name-collision.md`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `date '+%Y-%m-%d %H:%M'`

#### Result

- Outcome: 将 `Screen` 子类中同名 `_render(...)` 重命名为 `_render_view(...)` 并更新调用点；新增回归单测（断言不定义 `_render`）。
- Key output/snippet (optional, short): `18 passed in 0.35s`

---

### Improve: 订阅（套餐包）展示口径 + 环形图卡片 + 修复过期测试

---

## 2026-02-08

### Release: v0.1.x 连续迭代（开源可用性 + 健壮度）

- When: `2026-02-08`
- Who: `agent`
- Context: 在开源分发（pip 安装）场景下补齐可用性、健壮度与帮助信息；并多次小版本发布。

#### Key Decisions

- Decision: token 存储从“项目目录 `.local/`”升级为“全局数据目录（或 keyring）”，实现跨目录可用。
  - Why: `pip install` 后用户会在任意目录运行；项目目录不可定位，必须全局化。
- Decision: `rightcodes dashboard` 未登录或 token 过期时不直接崩溃退出，进入交互式登录流程获取新 token。
  - Why: 提升健壮度与使用体验，避免“需要手动先跑 login 才能进 dashboard”的割裂。
- Decision: “使用记录明细”表格中 IP 允许全量展示（个人工具场景），密钥保持打码。

#### Commands run（代表性）

- `python3 -m pytest`
- `rightcodes --help`
- `rightcodes --version`

#### Result

- Outcome: 发布至 `v0.1.13`；CLI/TUI 在未登录、token 失效、字段缺失与 429 场景下具备更可解释的降级行为。

### Docs: 规格与计划对齐当前实现

- When: `2026-02-08`
- Who: `agent`
- Context: 修正并重构 specs/plans/task summaries，使其与 `v0.1.x` 当前实现一致，便于维护与复现。

#### Action

- Files touched:
  - `docs/specs/tui-dashboard-mvp.md`
  - `docs/specs/2026-02-08-add-gitignore.md`
  - `docs/plans/2026-02-07-tui-dashboard-implementation-plan.md`
  - `docs/task-summaries/2026-02-08-dashboard-ui-polish-and-use-logs.md`
  - `docs/task-summaries/2026-02-08-add-gitignore.md`
  - `docs/worklog.md`

#### Result

- Outcome: 文档契约与现状一致；新增/更新内容不包含敏感信息，且对 `pip install` 使用方式有明确说明。

### Fix: 切换主题后出现“残影/半透明线”

- When: `2026-02-08`
- Who: `agent`
- Context: 用户在 Dashboard 中多次切换 theme/dark mode 后，发现总进度条下方与套餐卡片边界处出现“残影/半透明线”。

#### Action

- Files touched:
  - `src/rightcodes_tui_dashboard/ui/app.py`
  - `tests/test_ui_theme_toggle_artifact_guard.py`
  - `docs/specs/2026-02-08-fix-theme-toggle-ghosting.md`
  - `docs/task-summaries/2026-02-08-fix-theme-toggle-ghosting.md`
  - `docs/INDEX.md`
- Commands run:
  - `python3 -m pytest`

#### Result

- Outcome: 为关键 Static 区块设置显式背景色，重绘时清屏；新增回归护栏测试，避免后续回归。

- When: `2026-02-07 20:29`
- Who: `agent`
- Context: 订阅字段语义调整（expired_at 实为获得时间 obtained_at），并需要按 reset_today 隐含规则展示“有效额度口径”；同时修复旧单测仍按“到期过滤”断言导致的失败。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/tests/test_calculations.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome: 离线回归通过（exit code 0）；Dashboard 不再引用 `expired_at_raw`/`tier_id`，订阅改为“每包一个环形图卡片 + 标签”，总览与单包均使用 reset_today 的有效口径汇总与展示。

---

### Improve: 按网页截图重做套餐卡片（进度条）+ Usage 数字格式 + Burn/ETA 动态倒计时

- When: `2026-02-07 20:45`
- Who: `agent`
- Context: 用户提供网页面板截图，期望 CLI/TUI 更接近网页样式：每包进度条、总览宽进度条、Usage 的 tokens 用逗号完整位数显示；并明确“每个套餐总额度按接口返回值展示，不引入昨日/今日运营规则推导”。同时截图显示“获得时间/到期时间”并存，需要把时间字段拆开展示。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/tests/test_calculations.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/docs/plans/2026-02-07-rightcodes-cli-dashboard-feasibility.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 套餐卡片：从“环形图”改为“表格字段 + 字符进度条”，展示获得时间/到期时间/今日重置/额度剩余与总额/已用比例。
  - 总览额度：继续使用全宽 `ProgressBar` 展示 used/total。
  - Usage：requests/tokens/cost 按卡片展示；tokens 采用带逗号的完整位数；cost 采用 `$xx.xx`。
  - Burn/ETA：以 tokens/h + $/h 展示 burn；ETA 以“剩余额度 ÷ $/h”为主，并显示倒计时与“剩余 Token（按近窗口均价估算）”。
  - 离线回归通过（exit code 0）。

---

### Improve: 总进度条左右顶格 + Usage 文本行上移

- When: `2026-02-07 21:05`
- Who: `agent`
- Context: 用户希望总览进度条左右顶格（占满整行宽度），并把 requests/tokens/cost 改成无边框文本行，放在总进度条上方。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - `ProgressBar` 关闭 percentage/eta 并移除左右 padding，让总进度条更“宽”且左右顶格。
  - requests/tokens/cost 以文本行展示，并放置在总进度条上方。
  - 离线回归通过（exit code 0）。

---

### Improve: 总进度条加粗（相对套餐条）+ 对齐套餐左右边框 + 追加“详细统计数据（按模型）”

- When: `2026-02-07 21:20`
- Who: `agent`
- Context: 用户要求总进度条厚度约为套餐进度条的 1.2 倍（终端行高限制下用 2 行近似）；总进度条与标签左右对齐到套餐卡片边框；requests/token/cost 三项加大间距；并在套餐区下方追加“详细统计数据”表格（模型/请求数/Tokens/费用/占比）。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
  - `rightcodes-tui-dashboard/tests/test_calculations.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
  - `rightcodes-tui-dashboard/docs/worklog.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 总进度条高度设为 2 行（近似“更粗”）；并统一 padding，使其左右对齐到套餐卡片边框。
  - requests/token/cost 改为无边框的三列文本（Table.grid），列间距更大。
  - 新增“详细统计数据”表格：从 advanced stats 中提取 `details_by_model`（优先按 cost 占比），展示模型/请求数/Tokens/费用（6 位小数）/占比。
  - 离线回归通过（exit code 0）。

---

### Improve: 汇总指标移入“详细统计数据”表格 + 总进度条改为自绘加粗条

- When: `2026-02-07 21:40`
- Who: `agent`
- Context: 用户要求 requests/token/cost 属于汇总数据，统一放到“详细统计数据”表格中；表格取消外边框并在底部追加合计行；总进度条需显示 `$累计花费 / $总额度` 且更粗。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 移除顶部 requests/token/cost 行；在“详细统计数据”表格底部追加“合计”行承载汇总指标。
  - “详细统计数据”表格取消最外边框（Rich Table：`box=None + show_edge=False`）。
  - 总进度条改为自绘多行条（2 行），确保厚度 ≥ 套餐进度条。
  - 离线回归通过（exit code 0）。

---

## 2026-02-08

### Improve: 总览进度条单行三段 + 新增“使用记录明细”表格（Dashboard 内）

- When: `2026-02-08 00:09`
- Who: `agent`
- Context: 按网页样式收敛：总览额度用“单行三段”（左 label / 中 bar / 右 %）；“详细统计数据”标题居中且表格带边框；在面板中新增“使用记录明细”表格（来自 `/use-log/list`）。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - Dashboard 顶部总览额度改为单行：`$已用 / $总额` + 进度条 + `%`（不再占两行）。
  - “详细统计数据”改为标题居中 + 带边框表格，并保留合计行。
  - Dashboard 新增“使用记录明细”表格：固定列（时间/密钥/模型/渠道/Tokens/计费倍率/扣费来源/费用/IP），并对密钥与 IP 做部分打码展示。
  - Dashboard 主体内容（套餐卡片/表格/趋势/Burn）统一放入 `VerticalScroll`，避免小屏溢出。
  - 离线回归通过（exit code 0）。

### Fix: 统计区间改为日历日（today）动态计算，避免跨天把昨天算进来

- When: `2026-02-08 00:22`
- Who: `agent`
- Context: 用户反馈“详细统计数据包含昨天”；原因是此前默认使用 rolling window（如 `24h`）会跨日。改为支持 `--range today`，并将 dashboard 默认 range 改为 `today`（按系统日期本地 00:00 起算，每次刷新动态计算）。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/__main__.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/cli.py`
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - Dashboard 统计区间：支持 `--range today`，并设为默认值；`start_date` 每次刷新按“本地当天 00:00:00”动态计算。
  - 仍可显式使用 rolling window：`--range 24h/7d`。
  - 离线回归通过（exit code 0）。

### Chore: 新增 `.gitignore`，排除本地缓存与构建产物

- When: `2026-02-08 00:31`
- Who: `agent`
- Context: 当前目录存在 `.DS_Store`、`.local/`、`.pytest_cache/`、`*.egg-info/` 等不应提交到 Git 的本机/缓存产物；新增最小 `.gitignore` 先排除这些项，降低误提交风险。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/.gitignore`
  - `rightcodes-tui-dashboard/docs/specs/2026-02-08-add-gitignore.md`
  - `rightcodes-tui-dashboard/docs/task-summaries/2026-02-08-add-gitignore.md`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 新增 `.gitignore`：忽略 `.DS_Store`、`.local/`、`.pytest_cache/`、`*.egg-info/`。
  - 记录了对应 spec 与任务总结，并更新 `DOCS_INDEX.md`。
  - 离线回归通过（exit code 0）。

### Fix: 主题切换后偶发“残影/半透明线”仍存在，强制 repaint

- When: `2026-02-08 19:30`
- Who: `agent`
- Context: 用户反馈在反复切换主题后，“总进度条下方/套餐卡片上边框附近”的半透明残影仍偶发。此前仅通过 CSS 显式 background 清屏，但在少数终端/渲染组合下仍可能未触发整屏完整重绘。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/tests/test_ui_theme_toggle_artifact_guard.py`
  - `rightcodes-tui-dashboard/docs/specs/2026-02-08-fix-theme-toggle-ghosting.md`
  - `rightcodes-tui-dashboard/docs/task-summaries/2026-02-08-fix-theme-toggle-ghosting.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 在 `RightCodesDashboardApp` 覆写 `_watch_theme`：主题变更后额外触发一次 `refresh(repaint=True, layout=True)`（并刷新 screen），降低偶发残影概率。
  - 新增离线护栏测试：确保 `_watch_theme` 覆写存在，避免后续回归。
  - 离线回归通过（exit code 0）。

### Fix: 顶部“套餐”总进度条随 terminal 宽度自适应，百分比不被挤出

- When: `2026-02-10 10:35`
- Who: `agent`
- Context: 用户反馈顶部总进度条在 terminal 较窄时会把右侧百分比顶出去不可见；且进度条希望能随 terminal 宽窄动态变化。

#### Action

- Files touched:
  - `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - `rightcodes-tui-dashboard/tests/test_quota_overview_line_layout.py`
  - `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
- Commands run:
  - `python3 -m pytest -q`

#### Result

- Outcome:
  - 顶部总进度条使用 cell-width 计算（兼容中文宽字符），并为右侧百分比预留 ` 100%` 的 5 列空间。
  - 新增 resize 重绘：终端窗口变化时使用缓存重绘（不触发网络请求），使进度条/表格宽度实时适配。
  - 离线回归通过（exit code 0）。
