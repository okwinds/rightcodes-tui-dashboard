# 修复：切换主题后出现“残影/半透明线”（L1）

日期：2026-02-08  
状态：Implemented

---

## Goal

- 修复在 TUI 中切换 theme/dark mode 后，界面局部出现“上一帧残影/半透明线”的问题（例如：总进度条下方、套餐卡片上边框附近出现一条疑似叠影）。

---

## Constraints

- 不引入 Playwright；不改登录/鉴权逻辑。
- 不提交任何敏感信息（token/密码/真实明细数据）。
- 变更范围尽量小（L1：局部 UI 渲染稳定性修复）。

---

## Root Cause（推断）

- 部分 `Static` 区块使用 Rich renderables（`Panel/Table/Columns`）渲染内容，这些 renderables 在某些情况下 **不会覆盖其所属区域的每一个 cell**（例如区域内的空白部分没有显式背景色）。
- 当 theme/dark mode 切换触发重绘时，若该区域未设置明确 `background`，终端可能保留上一帧字符，表现为“残影/半透明”。
- 即使设置了 `background`，在少数终端/渲染组合下，主题切换触发的 CSS 刷新也可能不足以保证“整屏完全重绘”，仍有机会出现局部残留。

---

## Fix

- 在 `RightCodesDashboardApp.CSS` 中，为关键容器与 Static 区块显式设置 `background: $background`，确保每次重绘会先用背景色清空区域，再绘制新内容。
- 在 `RightCodesDashboardApp` 中覆写 `_watch_theme`：主题变更后额外触发一次全局 `refresh(repaint=True, layout=True)`（并刷新当前 screen），进一步降低偶发残影概率。
- 新增最轻量的离线回归护栏测试：断言 CSS 中包含关键区块的 background 配置，避免后续回归。

---

## Acceptance Criteria

- 在 `rightcodes dashboard` 中切换 theme/dark mode 多次后：
  - 不再出现“残影/半透明线”
  - 区块上下不会出现上一帧字符的遗留

---

## Test Plan

### Unit / Offline Regression（必须）

- `python3 -m pytest`
  - 断言：CSS 中包含关键区块的 `background: $background`

### Manual Smoke（可选）

- 启动：`rightcodes dashboard`
- 反复切换 theme/dark mode（按 Textual 默认快捷键或命令），观察：
  - 总览区与套餐卡片边界处不出现残影

---

## Rollback

- 回滚 `RightCodesDashboardApp.CSS` 的背景色设置与对应测试即可恢复原行为（但可能重新出现残影问题）。
