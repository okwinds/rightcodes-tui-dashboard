# 任务总结：修复切换主题后的“残影/半透明线”

- 日期：2026-02-08
- 范围等级：L1（局部 UI 渲染稳定性修复）

---

## 1) Goal / Scope

- Goal：修复 TUI 切换 theme/dark mode 后出现的“残影/半透明线”视觉问题。
- In Scope：
  - 为关键 `Static` 区块设置显式背景色，确保重绘时清屏
  - 新增离线回归护栏测试
- Out of Scope：
  - 不调整业务数据口径/接口解析
  - 不发版
- Constraints：不提交敏感信息；不引入新依赖。

---

## 2) Context（背景与触发）

- 触发：用户在 Dashboard 中多次切换主题后，发现“总进度条下方、套餐卡片上边框附近”出现一条类似半透明的残影。
- 影响：可读性变差，且给人以 UI 绘制不稳定的观感。

---

## 3) Spec / Contract（文档契约）

- Spec：`docs/specs/2026-02-08-fix-theme-toggle-ghosting.md`
- Acceptance Criteria：切换主题后不再出现残影。
- Test Plan：离线 `pytest` + 可选手动 smoke。

---

## 4) Implementation（实现说明）

### 4.1 Key Decisions

- Decision：通过 CSS 为关键区域设置 `background: $background` 来“覆盖清屏”。
  - Why：最小改动即可避免 Rich renderable 未覆盖区域导致的上一帧字符残留。
  - Trade-off：无（背景色与主题变量一致，切换主题时自动适配）。

### 4.2 Code Changes

- `src/rightcodes_tui_dashboard/ui/app.py`
  - `RightCodesDashboardApp.CSS`：为 `#banner/#quota_overview/#body_scroll/#subscriptions/#details_by_model/#use_logs/#burn_eta/#status` 等设置背景色。
- `tests/test_ui_theme_toggle_artifact_guard.py`
  - 新增离线回归护栏：断言 CSS 包含关键区域背景配置。

---

## 5) Verification（验证）

### Unit / Offline Regression（必须）

- `python3 -m pytest`

### Manual Smoke（可选）

- `rightcodes dashboard` 后反复切换主题，观察残影是否消失。

---

## 6) Known Issues / Follow-ups

- 若未来引入更多 Rich renderable 区块（尤其是固定高度的 `Static`），建议同样显式设置背景色，避免类似残影问题。

