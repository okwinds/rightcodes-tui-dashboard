# Right.codes CLI Dashboard

把 `right codes` 的用量/套餐信息做成一个本地 CLI/TUI 看板（可配置刷新频率），尽量不依赖浏览器、**不使用 Playwright 自动化登录**。

> 说明：本项目通过网页同款的 JSON 接口获取数据（需要 Bearer token）。接口可能随网站更新而变动；本工具尽量做兼容与降级提示，但不保证长期稳定。

## 约束（摘要）

- 不使用 Playwright 自动化登录（只走内部 JSON 接口 + Bearer token）
- 密码不落盘：仅交互式输入用于换取 token
- token 优先写入系统 keyring；失败则兜底写入“全局数据目录”的 `token.json`（尽量 `0600`；可用 `RIGHTCODES_DATA_DIR` 自定义目录）
- 不提交任何敏感信息（token、密码、cookie、真实明细数据等）；CLI 默认脱敏输出，TUI“使用记录明细”会显示完整 IP（个人工具场景）

## 功能概览

- `rightcodes dashboard`：Textual TUI 看板（自动刷新、趋势、套餐/额度、使用记录明细）
- `rightcodes logs`：命令行查看使用明细（`table/json`，默认脱敏）
- `rightcodes login`：交互式登录并保存 token（密码不落盘）
- `rightcodes doctor`：端点自检（只输出 keys，不输出值；可写入 `.local/`）

## 安装

### 方式 A：pip 安装（推荐）

```bash
pip install rightcodes-tui-dashboard

# 升级（可选）
pip install -U rightcodes-tui-dashboard

# 或（等价）
python3 -m pip install -U rightcodes-tui-dashboard
```

### 方式 B：从 GitHub 安装（无需手动下载源码）

也可以直接：

```bash
python3 -m pip install -U "rightcodes-tui-dashboard @ git+https://github.com/okwinds/rightcodes-tui-dashboard.git"
```

### 可选：启用 keyring（推荐）

默认不强依赖 keyring；如希望把 token 写入系统钥匙串/凭据管理器，可安装 extra：

```bash
python3 -m pip install -U "rightcodes-tui-dashboard[keyring]"
```

也可以用 `pipx` 安装（更适合 CLI 工具）：

```bash
python3 -m pip install -U pipx
pipx install rightcodes-tui-dashboard
```

## 使用指南

### 1) 登录

交互式输入账号密码（不回显），用于换取 token；密码不会写入任何文件：

```bash
rightcodes login
```

如果你只想验证登录是否成功，但又不想打印完整 token，可用：

```bash
rightcodes login --print-token
```

### 2) 启动看板（TUI）

默认 `--watch 30s` 自动刷新；`--watch 0s` 关闭自动刷新：

```bash
rightcodes dashboard --watch 30s --range today --rate-window 6h
```

### 3) 查看明细（CLI）

默认脱敏；支持 `table/json`：

```bash
rightcodes logs --range 24h --format table
rightcodes logs --range 7d --format json
```

### 4) doctor（自检/排障）

只输出 keys，不输出值；默认写入 `.local/rightcodes-doctor.json`：

```bash
rightcodes doctor
```

## 常用参数

- `--base-url`：覆盖服务地址（默认 `https://right.codes`）
- `dashboard --range`：
  - `today`：按本地日历日统计（当天 00:00 起算；推荐，避免跨日）
  - `24h/7d`：rolling window（过去 N 小时/天）
- `dashboard --no-keyring`：禁用 keyring（适用于无 keyring 环境）

查看完整参数：

```bash
rightcodes --help
rightcodes dashboard --help
```

## 安全与隐私

- 账号密码：只用于登录换取 token；不会落盘。
- token：优先存储到系统 keyring；否则写入“全局数据目录”的 `token.json`（尽量 `0600`；可用 `RIGHTCODES_DATA_DIR` 自定义目录）。
- 本项目会在本机保存 token/doctor 输出等文件；请勿提交到 Git（本仓库默认已忽略 `.local/`）。

## 开发（可选）

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
rightcodes --help
```

## 相关文档

- MVP 规格：`docs/specs/tui-dashboard-mvp.md`
- 可行性方案：`docs/plans/2026-02-07-rightcodes-cli-dashboard-feasibility.md`
- 实现计划：`docs/plans/2026-02-07-tui-dashboard-implementation-plan.md`
