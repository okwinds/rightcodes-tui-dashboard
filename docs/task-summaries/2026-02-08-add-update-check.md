# 任务总结：新增新版本检查（非搅扰式提示）

- 日期：2026-02-08
- 范围等级：L1（小功能：版本更新提示）

---

## 1) Goal / Scope

- Goal：让用户在 Dashboard 中可以非搅扰式得知“有新版本可升级”。
- In Scope：
  - 后台查询 PyPI 最新版本号
  - 右上角 `ver:` 前显示 `↑` 作为提示标记
  - 离线回归测试覆盖版本比较逻辑
- Out of Scope：
  - 不弹窗、不 banner 提示
  - 不自动升级
  - 不增加启动阻塞

---

## 2) Spec / Contract

- Spec：`docs/specs/2026-02-08-add-update-check.md`
- Data Source：PyPI JSON API（公开信息）
- 降级策略：网络失败/解析失败 → 不提示更新

---

## 3) Code Changes

- `src/rightcodes_tui_dashboard/services/update_check.py`
  - 新增：获取 PyPI 最新版本号 + 版本比较函数（保守策略）
- `src/rightcodes_tui_dashboard/ui/app.py`
  - Dashboard mount 时后台检查更新
  - 右上角版本号渲染：有更新时显示 `↑ ver: ...`
- `tests/test_update_check.py`
  - 新增离线回归：版本比较逻辑

---

## 4) Verification

- `python3 -m pytest`

---

## 5) Known Issues / Risks

- 版本比较逻辑为简化实现（按 `X.Y.Z` 三段数字比较）；对复杂 pre-release 语义采用保守策略（宁可不提示，也不误报）。

