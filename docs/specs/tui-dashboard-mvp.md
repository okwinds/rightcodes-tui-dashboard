# Right.codes CLI/TUI Dashboard 规格（v0.1.x：可降级、可复现、可离线回归）

更新时间：2026-02-08  
状态：Implemented（以 `main` + 最新 tags 为准；字段兼容以“可降级适配”为前提）

> 本文是项目的“当前规格文档”（Spec-Driven）：描述目标、硬约束、接口契约、CLI/UI 行为与验收口径。

---

## 1) Goal / Non-goals

### Goal（必须交付）

- 提供离线可安装的 **CLI + TUI**，用于查看 `right codes` 的：
  - **余额**（来自 `/auth/me` 的字段变体；用于顶部展示，保留小数尾数用于校验字段正确性）
  - **套餐额度**（逐套餐卡片 + 总览进度条：已用/总额/百分比）
  - **近期消耗速率（Burn）与预计用光时间（ETA）**
  - **使用记录明细**（来自 `/use-log/list`，支持翻页）
- 支持 `dashboard --watch` 自动刷新；对 401/429/字段缺失等场景 **清晰提示并降级展示**（保留旧数据，不崩溃）。
- “全局只登录一次”：token 持久化到 **全局数据目录**（或 keyring）后，在任意目录都可运行。
- 交付 **离线单测（pytest）** 作为完成门槛：覆盖解析兼容、错误映射、退避、token 存储与关键 UI 布局护栏。

### Non-goals（不做或弱化）

- 不使用 Playwright（只走 JSON 接口 + Bearer token）。
- 不保存密码（仅交互式输入用于换取 token）。
- 不追求 1:1 复刻网页 UI；优先信息密度、可读性、可维护性、容错与降级。

---

## 2) Constraints（硬约束）

### 2.1 工程与依赖

- Python：`>=3.9`
- TUI：Textual（渲染层）
- CLI：`argparse`
- HTTP：`httpx`
- 测试：`pytest`（离线回归必须可运行）
- 可选依赖：
  - `keyring`：用于系统安全存储 token（可选；无则降级到文件）

### 2.2 安全与隐私

- 禁止提交敏感信息：账号密码、token、cookie、真实明细数据。
- 密码不落盘：
  - 仅允许交互式输入（不回显）用于换取 token。
- token 存储优先级（实现约束）：
  1) keyring（可选依赖；可用则优先）
  2) 本地文件（兜底）：写入“全局应用数据目录”的 `token.json`
     - 目录可通过环境变量 `RIGHTCODES_DATA_DIR` 覆盖（便于用户自定义/测试）
     - 文件权限尽量设置为 `0600`
  3) 兼容读取旧版项目目录 `.local/token.json`（如存在则复制迁移到全局目录；不删除旧文件）

### 2.3 可靠性与降级

- 接口字段可能变动：必须支持字段缺失/变体的降级展示（例如 `null`/不存在/改名）。
- 对 401/403（token 失效）：
  - `rightcodes dashboard`：**不得直接报错退出**，应进入 `login` 流程获取新 token（交互式输入，仍不保存密码）。
  - `rightcodes logs/doctor`：提示先执行 `rightcodes login`（保持简单明确）。
- 对 429（限流）：
  - 使用指数退避（exponential backoff）+ jitter
  - UI 显示下一次重试时间；保留 stale 数据并标记“正在退避”

---

## 3) Contract（接口契约：端点、参数、响应 shape）

### 3.1 Base URL 与鉴权

- 默认 `base_url`：`https://right.codes`（可通过 `--base-url` 覆盖）
- 鉴权头：`Authorization: Bearer <user_token>`
- 登录响应字段兼容：
  - `user_token` 或 `userToken`（任意其一存在即可）

### 3.2 时间参数格式

- `start_date/end_date`：`YYYY-MM-DDTHH:mm:SS`（秒级）
- 客户端内部使用本地时间范围计算；UI 展示使用本地时间格式化（解析失败则回退原字符串）。

### 3.3 端点清单（按功能）

#### Auth

1) `POST /auth/login`
- Body：`{ username: string, password: string }`
- Response：`{ user_token?: string, userToken?: string, ... }`

2) `GET /auth/me`
- 用途：校验 token 有效性；提取余额字段变体用于顶部展示
- 余额字段兼容候选（可用即展示）：`balance` / `wallet_balance` / `wallet` / `credit_balance` / `remaining_balance`

#### Subscriptions（套餐/额度）

3) `GET /subscriptions/list`
- Response：`{ subscriptions: array<object>, ... }`
- 每个 item 兼容字段（缺失则降级）：
  - `total_quota?: number`
  - `remaining_quota?: number`
  - `reset_today?: boolean`
  - 时间字段（仅展示，不做业务推断）：`created_at?/obtained_at?`、`expired_at?`

#### Usage Stats（统计/趋势）

4) `GET /use-log/stats/overall`（累计）
5) `GET /use-log/stats`（区间）
- 兼容字段（可用即展示）：
  - tokens：`total_tokens` / `tokens` / `token_count`
  - cost：`total_cost` / `cost` / `amount`
  - requests：`total_requests` / `requests` / `request_count` / `request_count_total`

6) `GET /use-log/stats/advanced`（趋势/按模型）
- Query：`start_date/end_date/granularity(hour|day)`
- buckets 容器字段兼容候选：`data` / `items` / `series` / `buckets` / `trend`
- bucket 内字段兼容候选：
  - 时间：`time` / `ts` / `timestamp` / `date`
  - tokens：`tokens` / `total_tokens` / `token_count`
  - cost：`cost` / `total_cost` / `amount`
  - requests：`requests` / `request_count` / `request_count_total`
- 按模型聚合（可选，缺失则不展示）：`details_by_model[]`

#### Use Logs（使用记录明细）

7) `GET /use-log/list`
- Query：`page/page_size/start_date?/end_date?`
- 列表容器字段兼容候选：`items` / `logs` / `data`
- item 兼容字段（可用即展示；缺失填 `—`）：
  - 时间：`time/ts/timestamp/date/request_time/created_at`
  - tokens：优先 `usage.total_tokens`，其次 `total_tokens/tokens/token_count/...`
  - 渠道：`upstream_prefix/channel/source/provider/app/type/path/route`（不能写死）
  - 倍率：`billing_rate/billing_multiplier/rate_multiplier/multiplier/ratio`（格式化为 `x1.00`）
  - 资费：`billing_source/deduct_source/quota_source/deduct_from/balance_type/note`
    - 若为 `subscription`：展示为“套餐”
  - IP：`ip/client_ip/ip_address`（个人工具场景：UI 展示完整 IP，不做掩码）

---

## 4) CLI 设计（命令与参数）

统一入口：`rightcodes`

### 4.1 全局参数

- `--version`：输出版本号并退出
- `--help`：输出完整帮助（含最佳实践示例）

### 4.2 `rightcodes login`

- `--base-url <url>`
- `--store auto|keyring|file`
- `--print-token`：仅输出打码 token（不要写入文档/日志）

### 4.3 `rightcodes dashboard`

- `--watch <duration>`：`30s/5m/1h`；`0s` 关闭自动刷新
- `--range today|24h|7d|...`：
  - `today`：按本地日历日（00:00 起算）
  - 其它：rolling window
- `--rate-window <duration>`：用于 burn/ETA 估算
- `--granularity auto|hour|day`
- `--no-keyring`：禁用 keyring（强制走文件 token store）

### 4.4 `rightcodes logs`

- `--range today|24h|7d|...`
- `--page-size <n>` / `--page <n>`
- `--format table|json`（默认 table；json 必须脱敏）

### 4.5 `rightcodes doctor`

- `--out <path>`：默认写入全局数据目录 `rightcodes-doctor.json`
- `--no-save`：不落盘

---

## 5) UI 设计（Textual：单屏布局 + 交互）

### 5.1 Dashboard 布局（关键展示契约）

- 顶部总览（两行）：
  - 第一行：`余额：$<value>`（左对齐）+ `ver: x.y.z`（右对齐）
    - 若检测到新版本：在 `ver:` 前显示 `↑` 作为非搅扰式提示（不弹窗、不打断使用）
  - 第二行：总进度条行：左侧以 `套餐：` 开头，与“余额：”左对齐
    - 进度条宽度随 terminal 宽度动态调整；右侧百分比至少预留 ` 100%` 的 5 列空间，避免窄屏时被挤出不可见
- 套餐卡片区：每包展示“今日重置/获得时间/到期时间/额度/已用比例” + 进度条
- 详细统计数据：按模型汇总表格（含“合计”行）
- 使用记录明细：
  - 表格列：时间 / 密钥 / 模型 / 渠道 / Tokens / 倍率 / 资费 / 费用 / IP
  - 翻页：`p` 上一页 / `n` 下一页；表格下方右侧提示翻页方法与页码
  - 信息密度：除“密钥/模型”外，其它列保留稳定的右侧留白（可读性）；“密钥/模型”获取更多宽度以减少截断

### 5.2 快捷键（必须）

- `q`：退出
- `r`：手动刷新
- `p/n`：使用记录明细翻页
- `?`：帮助

---

## 6) 验收标准（Acceptance Criteria）

- `pip install rightcodes-tui-dashboard` 后可在任意目录运行：
  - `rightcodes --version`
  - `rightcodes --help`
  - `rightcodes login`（交互式，不回显）
  - `rightcodes dashboard`（未登录时会进入登录流程，不直接崩溃）
- token 全局可用：在不同目录运行 `rightcodes dashboard` 不需要重复登录（除非 token 失效）。
- `/use-log/list` 明细表中：
  - `Tokens/渠道/倍率/资费` 均来自 JSON 字段映射（不能写死常量）
  - `subscription` 显示为“套餐”
- 401/429/字段缺失不会导致 TUI 崩溃，且有明确提示与可降级展示。

---

## 7) Test Plan（离线回归）

- 运行离线回归：
  - `python3 -m pytest`
- 覆盖点（不依赖外网）：
  - token store（keyring/file/legacy 迁移）
  - CLI `--help/--version` 输出
  - 字段变体解析（balance/tokens/channel/rate/source）
  - use-log 时间格式化稳定性
  - UI 文本布局护栏（避免空行/命名冲突）

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
