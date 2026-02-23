## Context

当前实现中：
- `src/rightcodes_tui_dashboard/services/calculations.py` 的 `normalize_subscriptions()` 已解析 `expired_at` 并落到 `NormalizedSubscription.expires_at`（以及 `expires_at_raw`），但注释与帮助屏明确说明“仅展示，不用于过滤”。
- `src/rightcodes_tui_dashboard/ui/app.py` 的 `_render_subscriptions()` 会把 `normalize_subscriptions()` 产出的所有套餐逐一渲染为卡片；未根据过期时间/状态过滤或标识“已过期”。

这会导致：套餐在已过期后仍在面板中以“正常卡片”的形式出现，用户容易误认为仍可用。

约束/原则：
- 字段可能漂移/缺失：需要“尽力解析 + 降级展示”，避免误判为可用。
- 失败场景（401/429/网络异常）需清晰提示并降级（现有 UI 已对部分请求做了提示与回退）。

## Goals / Non-Goals

**Goals:**
- 引入统一的“套餐有效性”判定（`valid/expired/unknown`），并用于面板展示过滤。
- “可用套餐”区域不展示过期套餐；unknown 不得被误展示为可用。
- 保持实现可测试（为有效性判定添加离线单测/回归护栏）。
- 更新帮助屏口径描述，避免文档与行为不一致。

**Non-Goals:**
- 不引入新的外部依赖或新的 API 调用。
- 不改变服务端数据含义；仅在客户端做判定/展示层修复。
- 不在本次变更中重做套餐/额度的业务口径（除非确认过期套餐必须从汇总中排除）。

## Decisions

### Decision 1：有效性判定放在服务层（归一化/计算层）而不是 UI 里

方案：
- A) 在 `NormalizedSubscription` 或相关计算模块中计算 `validity`（推荐）
- B) 在 `_render_view()` / `_render_subscriptions()` 内部临时计算

选择 A。

理由：
- 同一份判定需要被多处使用（列表过滤、卡片标识、（可选）汇总口径）；放在服务层更复用、更易测。
- 归一化层已经在做字段变体兼容（`created_at/obtained_at`、`expired_at`），自然适合作为“判定输入”的唯一入口。

替代方案 B 的不足：
- 逻辑分散，未来迭代容易出现“一个地方过滤了，另一个地方没过滤”的回归。

### Decision 2：判定优先级（显式状态优先，其次 expires_at，最后 unknown）

实现策略：
- 若 raw item 存在显式状态/布尔字段可判断（例如 `status` / `expired` / `is_expired` 等），以其为准。
- 否则若 `expires_at`（由 `expired_at` 解析得到）可用，则使用 `now >= expires_at` 判定过期。
- 否则为 `unknown`，并触发展示降级（不展示为“可用套餐”）。

理由：
- 服务端显式状态（若存在）通常比客户端时间推导更可靠。
- 时间字段可能缺时区/格式不稳定；无法解析时必须保守。

### Decision 3：过滤发生在 view-model 阶段（`_render_view()`），并显式区分“可用/全部”

在 `_render_view()` 中：
- 先 `normalized = normalize_subscriptions(...)`
- 再计算 `active_items`（例如 `validity == valid`；或 `validity != expired`，按产品选择）
- `_render_subscriptions(active_items)` 用于“可用套餐”区域

同时：
- 若无 `active_items`，在 subscriptions 区域给出清晰提示（例如“无可用套餐（可能已过期或状态未知）”），避免回退成“—”导致用户误解为数据缺失。

理由：
- `_render_view()` 是数据到 UI 的汇聚点，更适合构建“用于展示的集合”。
- `_render_subscriptions()` 保持纯渲染，减少分支复杂度。

备选：在 `_render_subscriptions()` 内部过滤。缺点是与 quota 汇总/ETA 的数据源容易不一致。

### Decision 4：帮助屏与注释同步更新

需要同步更新：
- `HelpScreen` 中关于 `expired_at` 的描述（当前写的是“不用于过滤”）。
- `normalize_subscriptions()` 注释与 `summarize_quota()` docstring（若最终决定过滤也影响汇总，则需要同步更新文档与逻辑）。

## Risks / Trade-offs

- [Risk] `expired_at` 字段存在时区/格式漂移导致误判 → Mitigation：使用安全解析；解析失败一律 `unknown`；unknown 不展示为可用。
- [Risk] 服务端没有显式状态字段，且 `expired_at` 为空/缺失，导致大量 unknown → Mitigation：提示“状态未知/请刷新”；不误展示为可用；并在 Doctor/日志中保留 keys 辅助定位字段。
- [Trade-off] 是否将过期套餐从 quota 汇总/ETA 中排除不明确 → Mitigation：在 tasks 中列为实现前确认项；默认先修复 subscriptions 展示与标识，避免误导为可用。

## Migration Plan

- 变更为纯客户端逻辑更新，无需数据迁移。
- 发布后若发现判定策略导致误隐藏，可通过回滚到上一版本恢复（保留降级提示与错误处理逻辑）。

## Open Questions

- 服务端是否存在可用的“显式状态字段”（字段名与值域是什么）？若存在，应优先采用以减少时间推导误差。
- 过期套餐是否必须从 quota 汇总/ETA 中排除？（这影响用户最关注的“可用额度”口径。）

