# 新增：新版本检查（非搅扰式提示）（L1）

日期：2026-02-08  
状态：Implemented

---

## Goal

- 在不打断用户体验的前提下，增加“是否有新版本”的提醒能力。
- 提醒方式必须非搅扰式：不弹窗、不打断交互、不影响主功能；仅在 UI 右上角版本号处显示一个小标记。

---

## Constraints

- 不引入账号体系与额外隐私风险：不得上报用户数据；仅查询公开源（PyPI）。
- 网络失败/离线时必须完全降级：不报错、不影响刷新与渲染。
- 不增加启动阻塞：检查应在后台执行。

---

## Contract

### Data Source

- 通过 PyPI JSON API 获取最新版本：
  - `GET https://pypi.org/pypi/rightcodes-tui-dashboard/json`
  - 读取 `info.version` 作为 `latest`

### Compare

- 当 `latest > current(__version__)` 时，认为“有新版本”。
- 无法解析版本号时，保守不提示更新。

---

## UI Behavior（Dashboard）

- 右上角显示版本号：`ver: x.y.z`
- 若检测到新版本：显示 `↑ ver: x.y.z`（`↑` 为更新提示标记）
- 不在 banner 区域提示，不输出额外日志，不影响刷新流程

---

## Acceptance Criteria

- 无网络/被墙/超时：Dashboard 正常启动与刷新，不出现异常。
- 有新版本时：右上角出现 `↑` 标记；无新版本时：不出现标记。

---

## Test Plan（离线回归）

- `python3 -m pytest`
  - 断言：版本号比较逻辑可用（纯函数，离线）
  - 断言：UI CSS/布局不因此变更而回归（已有护栏）

