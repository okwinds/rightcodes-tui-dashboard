# TUI Dashboard MVP 规格（Spec-Driven + TDD）

日期：2026-02-07  
状态：Draft（可实现级别；接口字段以“可降级适配”为前提）

> 本文是 Right.codes 本地 CLI/TUI 看板 MVP 的主规格文档：先定义目标、约束、契约与验收，再进入测试与实现。

---

## 1) Goal / Non-goals

### Goal（MVP 必须交付）

- 提供一个离线可运行的 **CLI + TUI**，用于查看 Right.codes 的：
  - 套餐额度（总额度/已用/剩余 + 获得时间 + 逐套餐明细）
  - 近期使用速率（burn rate：tokens/小时、cost/天 等）
  - 预计用光时间（ETA：基于速率的线性估算）
  - 使用记录明细（最近 N 条，可分页/时间范围）
- 支持 `--watch` 自动刷新，且在接口 401/429/字段缺失时能 **清晰提示并降级展示**（保留旧数据）。
- 交付最少一套 **离线单测（pytest）**，覆盖核心计算、错误映射、退避状态机与模型兼容（字段缺失/变体）。

### Non-goals（MVP 不做或弱化）

- 不做任何基于浏览器的自动化（尤其不使用 Playwright）。
- 不追求 1:1 复刻网页 UI；优先信息密度、可读性与可维护性。
- 不做复杂筛选器/多标签编辑器级交互；保持单屏为主（logs 允许单独命令/屏）。
- 不做“自动重登”（需要密码持久化会触发安全约束）；401 仅引导重新登录。

---

## 2) Constraints（硬约束）

### 2.1 工程与依赖

- Python：`>=3.9`
- TUI：`Textual`
- HTTP：`httpx`
- 数据建模：`pydantic`（建议再配合 `pydantic-settings`）
- 重试/退避：MVP 自实现（指数退避 + jitter），不强依赖 `tenacity`
- 可选依赖：
  - `keyring`：用于系统安全存储 token（可选；无则降级到本地兜底文件）
  - `platformdirs`：用于跨平台定位用户目录（可选；MVP 未强依赖）
- 测试：`pytest` + `respx`（离线 mock HTTP）

### 2.2 安全与隐私

- 禁止提交任何敏感信息：账号密码、`user_token`、cookie、内部链接、真实明细数据。
- **密码不落盘**：
  - 仅允许交互式输入（不回显）用于换取 token。
  - 不允许把密码写入配置文件/日志/trace。
- token 存储优先级：
  1) 系统安全存储（如 keyring；可选依赖）
  2) 本地兜底文件：仅允许写到 `rightcodes-tui-dashboard/.local/` 下，并确保权限 `chmod 600`

### 2.3 可靠性与降级

- 不使用 Playwright。
- 接口字段可能变动：必须支持 **字段缺失** 的降级（例如某些字段为 `null`/不存在/改名）。
- 对 401/403（token 失效）：
  - UI/CLI 显示明确错误与“下一步怎么做”（例如提示执行 `rightcodes login`）
  - 不崩溃；可继续查看上次缓存（stale）
- 对 429（限流）：
  - 使用指数退避（exponential backoff）+ jitter（轻抖动）
  - 显示下一次重试时间
  - 保留 stale 数据并标记“数据已过期/正在退避”

---

## 3) Contract（接口契约：端点、参数、响应 shape）

### 3.1 Base URL 与鉴权

- 默认 `base_url`：`https://right.codes`（需可通过配置/环境变量覆盖）
- 鉴权头：
  - `Authorization: Bearer <user_token>`
- 注意：登录响应字段存在变体：
  - `user_token` 或 `userToken`（两者任意其一存在即可）

### 3.2 时间参数格式（约定）

- `start_date` / `end_date`：`YYYY-MM-DDTHH:mm:SS`（秒级，不带时区偏移）
- 客户端内部统一使用本地时区/系统时间；显示时明确“本地时间”。

### 3.3 端点清单（MVP 使用）

> 以下仅列出 MVP 必需字段；其它字段一律允许存在且应被忽略（forward compatible）。

#### Auth

1) `POST /auth/login`
- Body（JSON）：
  - `username: string`
  - `password: string`
- Response（JSON object）：
  - `user_token?: string`
  - `userToken?: string`

2) `GET /auth/me`
- Header：`Authorization: Bearer ...`
- Response（JSON object）：
  - 不强依赖具体字段；仅要求“返回 JSON object 且 HTTP 200 表示 token 有效”
  - 建议记录 `keys`（仅字段名，不记录值）用于 `doctor`

#### Subscriptions（额度/套餐）

3) `GET /subscriptions/list`
- Header：`Authorization: Bearer ...`
- Response（JSON object）：
  - `subscriptions: array<object>`
    - 每个 item（仅 MVP 依赖字段，允许缺失）：
      - `total_quota?: number`
      - `remaining_quota?: number`
      - `reset_today?: boolean`
      - `tier_id?: string | number`（MVP 默认不展示，仅用于调试/定位）
      - 时间字段（仅展示，不用于过滤/汇总口径）：
        - `created_at?: string` / `obtained_at?: string`：获得/授予时间（ISO-like）
        - `expired_at?: string`：到期时间（ISO-like）

#### Usage Stats（统计）

4) `GET /use-log/stats/overall`
- Header：`Authorization: Bearer ...`
- Response（JSON object）：
  - 允许字段不确定；MVP 只要求能读取“累计 tokens / 累计 cost / 累计请求数”中的任意子集并展示可用部分
  - 推荐兼容字段集合（任意存在即可）：
    - tokens：`total_tokens` | `tokens` | `token_count`
    - cost：`total_cost` | `cost` | `amount`
    - requests：`total_requests` | `requests` | `request_count`

5) `GET /use-log/stats`
- Query：
  - `start_date: string`
  - `end_date: string`
- Response（JSON object）：
  - 同 `overall`：字段不确定，按“可用即展示”原则解析

6) `GET /use-log/stats/advanced`
- Query：
  - `start_date: string`
  - `end_date: string`
  - `granularity: "hour" | "day"`
- Response（JSON object）：
  - 必须能导出一个“时间序列 buckets”用于计算速率与绘制趋势
  - 允许服务端返回任意字段名与容器字段名；客户端做“多 shape 兼容”并在无法解析时降级为“无趋势/无法计算速率”
  - 推荐兼容容器字段（从上到下尝试）：
    - `data` | `items` | `series` | `buckets` | `trend`
  - bucket 内推荐兼容字段（任意存在即可）：
    - 时间：`time` | `ts` | `timestamp` | `date`
    - tokens：`tokens` | `total_tokens`
    - cost：`cost` | `total_cost` | `amount`
    - requests：`requests` | `request_count`

#### Use Logs（明细）

7) `GET /use-log/list`
- Query：
  - `page: number`
  - `page_size: number`
  - `start_date?: string`
  - `end_date?: string`
- Response（JSON object）：
  - 推荐兼容字段集合（任意存在即可）：
    - 列表：`items` | `logs` | `data`
    - 分页：`page`、`page_size`、`total`（若缺失则仅按“是否还有数据”推断）
  - item（日志明细）字段不稳定：MVP 仅用于“摘要展示”，默认不展示任何疑似敏感字段（见 Security & Privacy）

---

## 4) CLI 设计（命令与参数）

命令前缀统一为 `rightcodes`（最终包名/入口以实现为准）。

### 4.1 `rightcodes login`

用途：交互式输入账号密码换取 token，并写入安全存储。

- Options：
  - `--base-url <url>`：覆盖 base_url
  - `--store keyring|file|auto`（默认 `auto`：优先 keyring，失败则 file）
  - `--print-token`：默认关闭；仅用于本地调试，输出必须打码（如仅显示前后 3 位），且不得写入 worklog
- Behavior：
  - 密码通过 `getpass` 输入，不回显
  - 成功后打印“已登录/已保存 token（安全存储类型）”
  - 失败时打印“原因 + 下一步建议”（例如检查 base_url、账号密码、网络）

### 4.2 `rightcodes dashboard`

用途：启动 TUI 看板（默认单屏）。

- Options：
  - `--watch <duration>`：自动刷新间隔（如 `30s`、`60s`；默认 `30s`）
  - `--range <duration>`：统计区间（如 `today`/`24h`/`7d`；默认 `today`）
  - `--rate-window <duration>`：速率窗口（如 `6h`；默认 `6h`）
  - `--granularity hour|day`：趋势粒度（默认自动：`range<=48h` 用 `hour`，否则 `day`）
  - `--base-url <url>`
  - `--no-keyring`：禁用 keyring（便于在无 keyring 环境运行）

### 4.3 `rightcodes logs`

用途：以 CLI（非 TUI）输出或以 TUI 列表方式浏览明细（实现可二选一，MVP 建议复用 Textual Screen）。

- Options：
  - `--range <duration>`：默认 `24h`（rolling window；用于 CLI logs）
  - `--page-size <n>`：默认 `50`
  - `--page <n>`：默认 `1`
  - `--base-url <url>`
  - `--format table|json`：默认 `table`；`json` 必须脱敏

### 4.4 `rightcodes doctor`

用途：离线/在线自检与契约探测（不包含任何敏感值），用于定位接口可用性与字段变体。

- Options：
  - `--base-url <url>`
  - `--out <path>`：输出 JSON（默认写入 `rightcodes-tui-dashboard/.local/rightcodes-doctor.json`）
  - `--no-save`：不落盘，仅输出 summary
- Output（脱敏）：
  - 各端点 HTTP 状态、耗时（可选）
  - 返回 JSON 的 **字段名列表**（keys），不输出字段值

---

## 5) UI 设计（Textual：单屏布局 + 交互）

### 5.1 单屏布局（Dashboard Screen）

- Header：标题 + 当前 base_url（可截断）+ token 状态（已登录/未登录）
- Body（建议三段）：
  1) **总览额度（单行进度条）**
     - 单行三段：左侧 `$已用 / $总额`，中间进度条，右侧百分比文本
     - 高度 1 行；左右 padding 与套餐卡片区域一致（对齐）
     - ETA/burn 信息可在后续区块单独展示（避免把总览条挤成多行）
  2) **Subscriptions Cards（逐套餐卡片）**
     - 每包一个卡片：进度条（消耗进度）+ 文字标签（仿网页面板的“卡片”信息密度）
     - 展示字段：
       - 获得时间：`created_at/obtained_at`（可解析则格式化，否则展示原始字符串）
       - 到期时间：`expired_at`（同上；字段存在但语义以实测为准）
       - 今日重置：`reset_today`（已重置/未重置/—）
       - 额度：`剩余 / 总额`（直接使用接口返回值，不引入运营规则推导）
       - 已用比例：`used = max(0, total - remaining)`，`used% = used / total`
     - 不展示 `tier_id`
  2.5) **详细统计数据（按模型）**
     - 表格列：模型 / 请求数 / Tokens / 费用（尽量保留完整小数位）/ 占比
     - 占比优先按 cost 计算（若 cost 缺失则按 tokens）
     - 底部追加“合计”行：总请求数 / 总 Tokens / 总费用（用于承载汇总指标）
  2.6) **使用记录明细（最近 N 条）**
     - 标题居中，表格带边框
     - 表格列：时间 / 密钥 / 模型 / 渠道 / Tokens / 计费倍率 / 扣费来源 / 费用 / IP
     - 为避免敏感信息暴露：密钥与 IP 默认做部分打码展示（CLI logs 仍保持默认脱敏策略）
  3) **Usage & Trend（统计与趋势）**
     - 累计/区间：tokens、cost、requests（可用即展示）
     - 趋势：按 hour/day sparkline（tokens 或 cost；二者都可用则可切换）
- Footer（状态栏）：
  - `Last OK:` 最近一次成功刷新时间
  - `Next refresh:` 下一次计划刷新时间
  - `Backoff:` 若 429，显示 `next_retry_at` 与 `attempt`
  - `Stale:` 当前展示是否为 stale（是/否 + stale 时长）

### 5.2 快捷键（必须）

- `q`：退出
- `r`：立即刷新（忽略 watch 定时，但仍受 backoff 限制）
- `l`：打开 logs screen（或切换到 logs 视图）
- `d`：打开 doctor summary（只显示 keys 与状态，不显示值）
- `?`：帮助（显示快捷键与口径摘要）

### 5.3 错误/降级展示（必须）

- 401/403：
  - 顶部 banner：`认证失败（token 失效）` + 提示执行 `rightcodes login`
  - 保留旧数据并标记 stale
- 429：
  - banner：`触发限流，已进入退避` + `next_retry_at`
  - 退避期间禁止连续重试（手动 `r` 也应提示“仍在退避”）
- 字段缺失/解析失败：
  - 对应组件显示 `部分字段不可用（已降级）`
  - `doctor` 输出 keys 便于人工定位

---

## 6) 计算口径（可测试、可离线复现）

> 所有计算必须以“输入 JSON → 归一化模型 → 纯函数计算”实现，便于 unit test。

### 6.1 Quota 汇总

定义（归一化后）：
- `total_quota`：该套餐包总额度（按接口返回值直接展示）
- `remaining_quota`：该套餐包剩余额度（按接口返回值直接展示）
- `reset_today`：是否已在今日发生重置（仅展示；不参与汇总口径）

单包口径：
- 若 `total_quota/remaining_quota` 任一缺失：该包不纳入汇总，并标记降级原因
- `used = max(0, total_quota - remaining_quota)`
- `used_pct = used / total_quota`（`total_quota <= 0` 时为 `None`）

汇总（单位同 `total_quota/remaining_quota`）：
- `total_quota_sum = sum(total_quota where present)`
- `remaining_sum = sum(remaining_quota where present)`
- `used_sum = sum(used where present)`

### 6.2 Burn Rate（速率）

输入：`advanced` 的时间序列 buckets（按 hour/day）。

计算（窗口内）：
- `tokens_in_window = sum(bucket.tokens where present)`
- `cost_in_window = sum(bucket.cost where present)`
- `hours_in_window = window_seconds / 3600`（或按 bucket 数推断）
- `burn_tokens_per_hour = tokens_in_window / hours_in_window`（tokens 不可用则为 `None`）
- `burn_cost_per_day = (cost_in_window / hours_in_window) * 24`（cost 不可用则为 `None`）

边界：
- 当窗口为空或 `hours_in_window <= 0`：速率为 `None`
- 当速率为 0：ETA 显示 `∞`（并注明“近期无消耗”）

### 6.3 ETA（预计用光时间）

第一版策略（避免误导）：
- 若 `remaining_sum` 的单位更像“金额/余额”（网页 UI 通常显示为 `$`）：优先用 `burn_cost_per_hour` 估算 ETA。
- 同时可附带一个“剩余 Token（按近窗口均价估算）”：
  - `cost_per_token ≈ burn_cost_per_hour / burn_tokens_per_hour`
  - `remaining_tokens_est ≈ remaining_sum / cost_per_token`
  - **明确标注这是估算值**，仅用于粗略判断消耗速度。

MVP 策略（可配置、可降级）：
- 默认：若 `remaining_sum` 与 `burn_tokens_per_hour` 可用，则：
  - `eta_hours = remaining_sum / burn_tokens_per_hour`
- 若 tokens 口径不可用但 cost 口径可用，且 quota 单位被识别为金额：
  - `eta_days = remaining_sum / burn_cost_per_day`
- 若无法判断 quota 单位：
  - UI 不显示 ETA，仅显示“需要确认 quota 单位/口径”

---

## 7) 刷新 / 限流 / 退避（分层拉取 + stale）

### 7.1 拉取分层（建议默认频率）

- 快速层（每次刷新都拉）：
  - `GET /subscriptions/list`
  - `GET /use-log/stats`（range）
  - `GET /use-log/stats/advanced`（用于趋势/速率）
- 慢速层（降频或按需）：
  - `GET /use-log/stats/overall`（例如每 5 次刷新拉一次）
  - `GET /use-log/list`（仅进入 logs screen 或用户按 `l` 时拉）

### 7.2 指数退避（429）

状态机（可测试）：
- 输入：`attempt`、`last_error_code`、`base_delay_seconds`、`max_delay_seconds`
- 输出：`next_retry_at`

规则（示例）：
- `delay = min(max_delay, base_delay * 2^attempt) + jitter`
- jitter：`[0, base_delay]` 的均匀随机或固定伪随机（单测可注入 deterministic RNG）
- 成功请求后：`attempt = 0`、清空 backoff

### 7.3 stale 数据策略（必须）

- 保留最近一次成功刷新得到的 view-model（缓存）。
- 当本次刷新失败（网络/401/429/解析失败）：
  - UI 继续展示缓存数据
  - 状态栏显示 `Stale: yes` + stale 时长
  - banner 显示失败原因与下一步动作

---

## 8) Security & Privacy（默认脱敏策略）

### 8.1 默认不展示/不输出的字段（黑名单）

在 logs 明细与 doctor 原始输出中，默认对以下字段（含大小写变体）做隐藏或 `***REDACTED***`：

- 鉴权/令牌：`authorization`、`token`、`user_token`、`userToken`
- 密码：`password`
- 可能的设备/网络标识：`ip`、`ip_address`、`client_ip`
- 可能的密钥标识：`api_key`、`api_key_name`、`key_name`

### 8.2 可选展示（需要显式开关）

- 仅在用户显式传入 `--show-sensitive`（MVP 建议不提供）或进入专用“调试视图”时才允许展示更多字段，且仍不写入磁盘/日志。

---

## 9) Test Plan（TDD：离线必选，集成可选）

### 9.1 Unit / Offline Regression（必须）

测试目标（离线、无外网、无真实 token）：

1) **计算口径**（纯函数）
- quota 汇总：字段缺失、过期判断、负数保护、None 传播
- burn rate：窗口为空、窗口小时数、0 速率
- ETA：tokens/cost 两套口径与不可判断时的降级

2) **响应兼容与降级**
- `/auth/login`：`user_token` vs `userToken`
- stats：字段名变体解析（tokens/cost/requests 任意缺失）
- advanced：容器字段变体（`data/items/series/buckets`）与 bucket 字段变体

3) **错误映射**
- 401/403：映射为“需要登录”
- 429：进入 backoff，禁止立即重试
- 非 2xx：统一错误消息（不包含敏感信息）

4) **退避状态机**
- attempt 递增、delay 上限、成功后 reset、deterministic jitter

建议 fixtures（仅示例文件名，不包含真实值）：
- `tests/fixtures/auth_login_user_token.json`
- `tests/fixtures/auth_login_userToken.json`
- `tests/fixtures/subscriptions_list_minimal.json`
- `tests/fixtures/use_log_stats_overall_minimal.json`
- `tests/fixtures/use_log_stats_range_minimal.json`
- `tests/fixtures/use_log_stats_advanced_hour_series.json`
- `tests/fixtures/use_log_list_page1_minimal.json`

### 9.2 Integration（可选，默认 skip）

目的：在开发者本机验证连通性与接口 shape（不得在 CI 强制）。

- 默认跳过条件：
  - 未设置 `RIGHTCODES_RUN_INTEGRATION=1`（或类似开关）
  - 未找到 token（keyring/file）
- 集成测试只做：
  - `doctor` 的“字段名探测”与基本 200/401/429 行为
  - 不打印任何敏感值；不保存 raw 明细（或只保存 keys）

---

## 10) Acceptance Criteria（可操作、可验收）

### 10.1 文档与测试门槛

- [ ] 本 spec 被实现前置引用（后续实现 PR/变更需指向本 spec）。
- [ ] 离线单测可运行：`pytest -q`（不依赖外网/真实账号）。

### 10.2 CLI 行为

- [ ] `rightcodes login`：可交互登录并保存 token（不保存密码、不回显密码）。
- [ ] `rightcodes dashboard --watch 30s`：启动 TUI，能展示 quota 汇总、逐套餐表、统计与趋势（可用即展示）。
- [ ] `rightcodes logs`：能按 range 分页展示明细（默认脱敏）。
- [ ] `rightcodes doctor`：输出各端点可用性与 keys（不输出值），默认写入 `.local/`（可 `--no-save`）。

### 10.3 降级与稳定性

- [ ] 401/403 时：TUI 不崩溃，提示重新登录，并保留 stale 数据展示。
- [ ] 429 时：进入退避并在 UI 明确展示 next retry；退避期间禁止“狂刷请求”。
- [ ] 字段缺失时：相应组件显示 `—` 并提示“已降级”，不抛异常导致应用退出。
