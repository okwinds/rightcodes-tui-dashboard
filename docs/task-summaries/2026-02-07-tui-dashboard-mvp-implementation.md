# 任务总结：TUI Dashboard MVP 代码落地（离线可测）

- 日期：2026-02-07
- 范围等级：L2（功能交付：新增 CLI + TUI + 离线回归）

---

## Goal / Scope

交付一个个人用 Right.codes CLI/TUI 小工具，在命令行内查看：
- 有效套餐（quota）总额度 / 已用 / 剩余 + ETA（基于速率估算）
- 统计（requests/tokens/cost）
- tokens 趋势（sparkline）
- 明细 logs（默认脱敏，安全摘要）
- doctor（仅 keys，不输出值）

并满足硬约束：
- 不使用 Playwright 自动化登录
- 密码不落盘；token 优先 keyring，失败兜底写入 `rightcodes-tui-dashboard/.local/token.json`（尽量 `0600`）
- 401/429/字段缺失可降级（保留 stale 数据并提示下一步）

---

## Key Decisions

1) **CLI 使用 `argparse` 而非 Typer**
   - 原因：环境中存在 `typer<0.12` 的依赖约束（避免引入全局冲突）。

2) **网络请求采用 `httpx.Client` + `asyncio.to_thread`**
   - 原因：避免阻塞 Textual UI 主循环，保持实现简单且可离线 mock（`respx`）。

3) **Logs 默认按黑名单脱敏**
   - 只展示安全摘要：time/tokens/cost + 其余字段压缩 JSON（敏感字段替换为 `***REDACTED***`）。

4) **429 退避采用指数退避 + jitter（可注入 RNG）**
   - 为离线单测提供 deterministic 行为，并在 UI 中展示 backoff 状态。

---

## Code Changes

- 新增 Python 包与可运行 CLI：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/__main__.py`
- 实现 CLI 子命令：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/cli.py`
  - `login`：交互式换取 token 并保存（不保存密码）
  - `dashboard`：启动 Textual TUI（watch/range/rate-window/granularity）
  - `logs`：CLI 输出明细（table/json，默认脱敏）
  - `doctor`：keys 探测（写入 `.local/rightcodes-doctor.json`）
- 实现 Textual TUI 多屏：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - Dashboard / Logs / Doctor / Help
  - 快捷键：`q r l d ?`
- 新增脱敏工具：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/privacy.py`
- 新增 backoff 纯函数：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/backoff.py`
- 扩展计算/解析：`rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/services/calculations.py`
- 新增离线单测：
  - `rightcodes-tui-dashboard/tests/test_backoff.py`
  - `rightcodes-tui-dashboard/tests/test_duration_and_parsing.py`
- 更新包配置与 README：
  - `rightcodes-tui-dashboard/pyproject.toml`
  - `rightcodes-tui-dashboard/README.md`

---

## Test Plan & Results

离线回归（不需要外网/账号）：

```bash
cd rightcodes-tui-dashboard
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

结果：`17 passed`

---

## Known Issues / Risks

- **数据口径仍需结合真实接口返回做微调**：stats/advanced 的字段名与容器 shape 可能变化，当前已做“可用即展示”的兼容，但仍可能遇到无法解析趋势的情况（将降级为无趋势/无 ETA）。
- **Logs 展示为安全摘要**：未做复杂分页交互（后续可在 TUI 内加入翻页与筛选）。
- **Doctor TUI 屏目前覆盖核心端点**：如需与 CLI doctor 一致，可扩展更多端点与参数展示（仍需仅 keys）。

---

## Next Steps

- 用你的真实账号跑一次 `rightcodes login` + `rightcodes dashboard`（或 `python3 -m rightcodes_tui_dashboard ...`），确认：
  - subscriptions quota 单位是否等同 tokens（决定 ETA 口径）
  - advanced buckets 是否带时间字段（可用于更精准的 rate-window slicing）
- 按你的偏好调整面板信息密度与显示项（例如 cost/token 分布、按天/小时切换）。

