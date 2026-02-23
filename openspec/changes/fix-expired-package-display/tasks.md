## 1. Validity 判定（服务层）

- [x] 1.1 在 `NormalizedSubscription` 增加有效性字段（valid/expired/unknown）与必要的原始状态字段（若需要）
- [x] 1.2 在 `normalize_subscriptions()` 中提取“显式状态字段”（若存在）并按优先级计算有效性
- [x] 1.3 统一时间解析/比较口径（`now`、时区/ISO 解析失败回退为 unknown）

## 2. UI 展示与过滤（Dashboard）

- [x] 2.1 在 `_render_view()` 构建“可用套餐集合”，并将其传入 `_render_subscriptions()`（避免 UI 内部分散过滤）
- [x] 2.2 当无可用套餐时，在 subscriptions 区域展示清晰提示（区分“数据缺失”与“已过期/未知”）
- [x] 2.3 更新 `HelpScreen` 中关于 `expired_at` 的口径说明（从“仅展示”改为“用于判定/过滤”）

## 3. 回归与降级行为

- [x] 3.1 确认 401/429/网络异常时不会把 unknown/缺失数据误展示为“可用套餐”（必要时补充提示文案）
- [x] 3.2（可选，待确认）决定是否将过期套餐从 quota 汇总/ETA 口径中排除，并在代码与帮助文案中保持一致（决定：不排除，保持按接口返回值汇总）

## 4. 测试（离线回归）

- [x] 4.1 为有效性判定新增单测：显式状态优先、仅 expires_at 推导、解析失败 → unknown
- [x] 4.2 为 UI 过滤新增回归护栏测试（至少覆盖：存在 expired 套餐时不出现在可用展示）
- [x] 4.3 跑 `pytest` 并记录关键用例通过
