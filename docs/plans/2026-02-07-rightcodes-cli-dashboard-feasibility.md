# Right.codes CLI 实时看板（无 Playwright）技术可行性方案

日期：2026-02-07  
目标：把 `right codes` 网页看板的核心用量/套餐信息做成一个本地 CLI/TUI 看板，可配置刷新频次，尽量不依赖浏览器。

更新（2026-02-08）：
- 已落地为可 pip 安装的 CLI/TUI 工具，并发布多个 `v0.1.x` 版本。
- token 存储已支持 keyring 优先 + 全局数据目录 `token.json` 兜底（跨目录可用）。

## 1. 需求摘要

你关心的核心指标（必须有）：
- **所有已生效套餐的总额度 / 已用 / 剩余**（含逐套餐明细；时间字段以“获得/授予时间”口径展示）
- **使用速率**（例如近 1h / 6h / 24h 的 tokens/h、cost/day 等）
- **依据速率推算预计用光时间（ETA）**（线性估算，后续可迭代更稳健口径）

次级指标（大项要有，允许先做简化版）：
- 累计请求、累计 token、累计花费
- token 使用趋势（按小时/按天/按时间范围）
- token 使用分布（分桶/Top 模型/Top upstream 等，视接口支持）
- 使用记录明细（最近 N 条 + 可按时间范围分页）

非目标（第一版不做或弱化）：
- 复杂交互（筛选器很多、鼠标交互、拖拽）
- 账号管理/多账号切换（除非后续明确要）
- 100% 复刻网页 UI（CLI 只要“信息密度高 + 美观”）

## 2. 可行性结论（路径 2：复用网页内部 JSON 接口）

结论：**可行**，且无需 Playwright。

关键依据（来自前端 bundle 里暴露的路由常量与调用逻辑）：
- 登录是直接调用 `POST /auth/login`（payload：`{ username, password }`）
- 登录成功返回 `user_token`（前端存到 localStorage 的 `userToken`）
- 之后所有数据接口走 **`Authorization: Bearer <user_token>`**
- 用户侧统计/套餐接口存在：`/subscriptions/list`、`/use-log/stats*`、`/use-log/list` 等

因此：CLI 可以通过“用户名+密码”换取 `user_token`，然后直接请求统计接口，完成本地看板。

## 3. 核心接口清单（用户侧）

以下均为相对路径，base 统一为 `https://right.codes`：

### 3.1 鉴权
- `POST /auth/login`：用户名密码登录，返回 `user_token`（或 `userToken`）
- `GET /auth/me`：校验 token 是否有效、获取用户信息（用于 `doctor`/健康检查）

### 3.2 套餐/额度
- `GET /subscriptions/list`：返回 `subscriptions[]`
  - 已在前端中看到字段：`total_quota`、`remaining_quota`、`created_at`、`expired_at`、`reset_today`、`tier_id`
  - 用于：
    - 汇总总额度/已用/剩余（按接口返回值直接汇总，见 5.1）
    - 展示逐套餐进度条、时间字段（获得/到期时间）
  - 说明（口径同步到当前实现/spec，避免误导）：
    - 优先将 `created_at/obtained_at` 作为“获得/授予时间”，将 `expired_at` 作为“到期时间”
    - 时间字段仅用于展示，不用于“未过期过滤/到期倒计时”（字段名不代表语义；以实测为准）
- 可能存在但未必被 UI 使用：
  - `GET /subscriptions/summary/total`（如可用，可作为汇总兜底）

### 3.3 用量统计（请求/token/花费）
- `GET /use-log/stats`
  - 支持 `params: { start_date, end_date }`
  - 用于“今日用量/某个时间范围用量”
- `GET /use-log/stats/overall`
  - 用于“累计用量（总请求/总 token/总花费）”
- `GET /use-log/stats/advanced`
  - 支持 `params: { start_date, end_date, granularity }`
  - 用于按小时/按天的趋势、速率计算窗口数据
- `GET /use-log/list`
  - 支持 `params: { page, page_size, start_date?, end_date? }`
  - 用于“明细列表 + 分页”
- `GET /use-log/recent` / `GET /use-log/:id`
  - 若存在可用：补充“最近 N 条”与“明细详情”

时间参数格式（从前端实现推断）：
- `start_date/end_date` 使用 `YYYY-MM-DDTHH:mm:SS`（带秒），具体以接口实际接受为准（调研阶段验证）

## 4. CLI/TUI 产品形态（建议）

命令结构建议：
- `rightcodes auth login`：输入用户名+密码获取 token（密码不落盘）
- `rightcodes dashboard --watch 30s --range 24h --rate-window 6h`
- `rightcodes logs --range 7d --page-size 50`
- `rightcodes export --range 30d --format json|csv`（可选）
- `rightcodes doctor`：连通性与权限自检（接口可访问性、返回字段快照）

看板布局（单屏信息密度优先）：
- **额度总览**：总额度/已用/剩余 + 进度条
- **套餐明细表/卡片**：name/tier（可选）、获得时间、到期时间、total/used/remaining、reset_today 状态
- **速率与 ETA**：近 1h/6h/24h burn rate（token/h、cost/day）+ 预计用光时间
- **趋势**：小时/天 sparkline（tokens、cost）
- **分布（可选）**：Top 模型/Top upstream（若 advanced stats 返回可拆维度）
- **明细（可选）**：最近 N 条 use logs（可单独 `logs` 子命令展开）

刷新策略：
- `--watch 10s/30s/60s` 等可配置
- 内部“快慢分层拉取”：例如额度/总览每次刷新；明细列表降低频率或按需加载，避免过度请求

## 5. 计算口径（第一版）

### 5.1 套餐汇总
- activeSubs = `subscriptions`（不基于 `expired_at` 做“未过期过滤”；时间字段仅用于展示）
- 单包口径（按接口返回值直接展示）：
  - `used = max(0, total_quota - remaining_quota)`
  - `used_pct = used / total_quota`（total<=0 时为 —）
- 汇总：
  - `total_quota_sum = sum(active.total_quota)`
  - `remaining_sum = sum(active.remaining_quota)`
  - `used_sum = sum(active.used)`

### 5.2 速率与 ETA（线性）
- 从 `/use-log/stats/advanced` 取 `granularity=hour` 的最近 N 小时（或 `day` 的最近 N 天）
- `burn_rate_tokens_per_hour = tokens_in_window / hours_in_window`
- `eta_hours = remaining_sum_tokens / burn_rate_tokens_per_hour`
  - burn_rate=0 时显示 `∞` 或 “近期无消耗”

注：如额度单位不是“token”而是“金额/余额”，则 burn rate 与 ETA 以 cost 维度计算（调研时确认 `total_quota` 的单位语义）。

## 6. 安全与合规（强约束）

不需要你把密码给我。推荐做法：
- CLI 在本地交互式输入密码（不回显），仅用于换取 `user_token`
- token 存储：
  - 优先：系统 Keychain（macOS Keychain / Windows Credential Manager / Linux Secret Service）
  - 兜底：本地配置文件（可加密，或至少 `chmod 600`）
- `rightcodes doctor` 输出调试信息时默认 **脱敏**（token 打码、邮箱/用户名可选打码）

## 7. 风险点与应对

- **接口变更**：前端更新可能改字段/路径  
  - 应对：集中封装 API client；`doctor` 检测字段缺失并降级
- **token 过期/失效**：401/403  
  - 应对：提示重新 `auth login`；可选支持自动重登（仍不保存密码）
- **刷新频率过高触发限流**：  
  - 应对：默认 30s；快速指标与明细分层；指数退避重试
- **额度单位不一致**（token vs $）  
  - 应对：调研确认；在 UI 上明确单位并支持切换显示

## 8. 推进计划（建议）

### 阶段 0：实地调研（30–60 分钟）
目标：在你的账号下确认接口返回结构与字段含义（尤其是 quota 单位与 advanced stats 的维度）。

### 阶段 1：MVP（0.5–1 天）
- `auth login` + token 存储
- `dashboard --watch`：额度汇总 + 套餐表 + 总/今日/区间统计 + 基础趋势（sparkline）
- `logs`：最近 N 条 + 时间范围分页

### 阶段 2：增强（1–2 天）
- 分布视图（Top 模型/Top upstream）
- 更稳健的 burn rate（多窗口、异常点平滑）
- `export`（JSON/CSV）

## 9. 调研需要你配合的最小动作

优先方案：你只需要在本机运行 CLI（我提供代码），不用把账号密码或 token 发给我。

调研输出（你可以复制给我，但请先脱敏）：
- `rightcodes doctor` 的 JSON 摘要（去掉 token）
- `/subscriptions/list` 的字段列表（不需要具体数值也行）
- `/use-log/stats/advanced` 的返回 shape（确认 hourly/day 的数据结构）
