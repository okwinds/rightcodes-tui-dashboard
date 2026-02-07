# 修复 Textual `_render` 命名冲突导致的崩溃（L1）

## Goal

- 修复 TUI 在渲染过程中崩溃的问题：`TypeError: _render() missing 1 required positional argument: 'data'`。
- 通过离线单测添加回归护栏，避免未来再次引入同类命名冲突。

## Constraints

- 不输出/不落盘任何敏感信息（token、cookie、真实明细数据）。
- 不修改上游 Textual；只在本项目代码内修复。
- 离线单测必须可运行并通过（不依赖外网/账号）。

## Non-Goals

- 不在本次变更中增强 doctor/advanced 接口字段解析（例如 `trend` 字段只记录为后续优化点）。

## Root Cause（结论）

- Textual 会在渲染 `Screen/Widget` 时调用其内部方法 `_render()`（无参数）。
- 我们在 `Screen` 子类中定义了同名方法 `_render(self, data)`，覆盖了 Textual 内部 `_render()`，导致签名不匹配并崩溃。

## Acceptance Criteria

- Dashboard / Logs / Doctor 等屏幕在 Textual 渲染时不再因为 `_render` 命名冲突崩溃。
- 代码中不再在任何 `Screen` 子类中定义 `_render` 方法（本次覆盖的屏幕至少包含 `DashboardScreen` / `LogsScreen` / `DoctorScreen`）。
- `python3 -m pytest` 全绿。

## Test Plan

### Unit / Offline Regression（必须）

- `python3 -m pytest`
  - 断言：新增单测检查 `Screen` 子类不定义 `_render`。

### Manual Smoke（可选）

- `python3 -m rightcodes_tui_dashboard dashboard`
  - 进入 Dashboard 后按 `l/d/?` 切换屏幕，确认 UI 不崩溃且可渲染。

## Rollback

- 回滚本次重命名与单测即可恢复到变更前状态（但会重新触发崩溃）。

