# Task Summary：修复 Textual `_render` 命名冲突崩溃

## 1) Goal / Scope

- Goal：修复 TUI 渲染时因命名冲突导致的崩溃，并补回归测试护栏。
- In Scope：
  - 重命名 `Screen` 子类中的 `_render(...)` 为非冲突名称（例如 `_render_view(...)`）。
  - 新增离线单测防止未来再次引入 `_render` 覆盖。
- Out of Scope：
  - doctor / advanced 接口字段解析增强（例如 `trend`）。
- Constraints：
  - 不修改上游 Textual；
  - 不输出敏感信息；
  - `python3 -m pytest` 必须通过。

## 2) Context（背景与触发）

- 背景：Textual 内部会调用 `Screen/Widget` 的 `_render()` 执行渲染流程。
- 触发问题（Symptoms）：运行 dashboard 时崩溃，报错 `TypeError: _render() missing 1 required positional argument: 'data'`。
- 影响范围（Impact）：DashboardScreen 渲染失败（同类写法在 Logs/Doctor 也存在潜在风险）。

## 3) Spec / Contract（文档契约）

- Contract：见 `docs/specs/2026-02-07-fix-textual-render-name-collision.md`。
- Acceptance Criteria：
  - 不再覆盖 Textual 内部 `_render()`；
  - 离线单测全绿。
- Test Plan：
  - Unit：`python3 -m pytest`；
  - Regression guard：新增测试断言 `Screen` 子类不定义 `_render`。
- 风险与降级（Risk/Rollback）：
  - 风险低：仅方法重命名 + 调用点更新；
  - 回滚：回退本次变更即可（但会重新触发崩溃）。

## 4) Implementation（实现说明）

### 4.1 Key Decisions（关键决策与 trade-offs）

- Decision：统一将 `Screen` 内部的“把数据写入视图”的方法命名为 `_render_view(...)`。
  - Why：避免 `_render` 与 Textual 内部方法冲突；语义清晰（render view）。
  - Trade-off：需要同步更新所有调用点。
  - Alternatives：让 `_render` 的签名与 Textual 一致（不推荐，容易再次误用/混淆）。

### 4.2 Code Changes（按文件列）

- `src/rightcodes_tui_dashboard/ui/app.py`：将 `DashboardScreen/LogsScreen/DoctorScreen` 中的 `_render(...)` 重命名为 `_render_view(...)`，并更新调用点。
- `tests/test_textual_render_name_collision.py`：新增回归单测，断言关键 `Screen` 子类不再定义 `_render`。

## 5) Verification（验证与测试结果）

### Unit / Offline Regression（必须）

- 命令：`python3 -m pytest`
- 结果：`18 passed in 0.35s`

### Integration（可选）

- 开关（env）：无
- 命令：无
- 结果：无

### Scenario / Regression Guards（强烈建议）

- 新增护栏：`tests/test_textual_render_name_collision.py`
- 防止回归类型：再次在 `Screen` 子类定义 `_render` 覆盖 Textual 内部实现。

## 6) Results（交付结果）

- 交付物列表：
  - 修复后的 UI 渲染实现（避免 `_render` 冲突）
  - 回归单测护栏
  - 本次变更 spec 与任务总结
- 如何使用/如何验收：
  - `python3 -m pytest`
  - （可选）运行 dashboard 并切换屏幕，确认不崩溃。

## 7) Known Issues / Follow-ups

- 已知问题：无。
- 后续建议：
  - doctor/advanced 的 `trend` 字段如需展示，可在后续任务补解析与 UI 展示（本次不包含）。

## 8) Doc Index Update

- 已在 `DOCS_INDEX.md` 登记：是
