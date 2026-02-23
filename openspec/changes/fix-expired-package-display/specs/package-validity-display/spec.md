## ADDED Requirements

### Requirement: 套餐有效性判定（Validity）
面板在渲染“当前/可用套餐”相关信息时，系统 MUST 为每个套餐计算一个有效性状态：`valid` / `expired` / `unknown`。

系统 MUST 按以下优先级判定：
1) **服务端显式状态优先**：当套餐对象存在可判定过期/有效的显式字段（例如 `status`（active/expired）、`isExpired`/`expired`、`valid` 等）时，系统 MUST 以该字段为准。
2) **到期时间回退**：当不存在显式状态字段，但存在到期时间字段（例如 `expiresAt`/`expire_at`/`expireAt` 等）且可解析为时间戳时：
   - 若 `now >= expiresAt`，状态 MUST 为 `expired`
   - 若 `now < expiresAt`，状态 MUST 为 `valid`
3) **无法判定则 unknown**：当缺少上述字段、字段为空、或无法解析时间时，状态 MUST 为 `unknown`，并触发降级展示（见下述展示要求）。

#### Scenario: 服务端显式状态为 expired
- **WHEN** 接口返回的套餐对象包含可判定字段，且其值表示“已过期”
- **THEN** 系统 MUST 将该套餐的有效性状态判定为 `expired`（不得再用到期时间覆盖）

#### Scenario: 只有到期时间且早于当前时间
- **WHEN** 套餐对象缺少显式状态字段，但包含可解析的 `expiresAt`，且 `expiresAt <= now`
- **THEN** 系统 MUST 将该套餐判定为 `expired`

#### Scenario: 字段缺失或时间不可解析
- **WHEN** 套餐对象既无显式状态字段，也无可解析的到期时间字段
- **THEN** 系统 MUST 将该套餐判定为 `unknown`，并按“unknown 展示规则”降级展示

### Requirement: “可用套餐”区域不得展示过期套餐
当面板存在“当前/可用套餐”区域（含摘要、卡片、列表等）时：
- 系统 MUST 不将 `expired` 状态的套餐展示为可用项
- 系统 MUST 不将 `unknown` 状态的套餐展示为“已购买且可用”，除非用户显式切换到“全部/历史”视图（若存在）

#### Scenario: 过期套餐不出现在可用列表
- **WHEN** 可用套餐列表包含一个被判定为 `expired` 的套餐
- **THEN** 该套餐 MUST 不出现在“可用套餐”列表中

#### Scenario: unknown 不误判为可用
- **WHEN** 套餐有效性被判定为 `unknown`
- **THEN** 系统 MUST 以非“可用”方式呈现（例如隐藏于可用区，或显示为“状态未知”并提示刷新/重试）

### Requirement: 历史/详情展示必须标识已过期
当面板展示套餐详情或历史列表（若存在）时：
- 系统 MUST 对 `expired` 状态的套餐展示“已过期”标识
- 系统 MUST 不提供会让用户误解为可继续使用的主行动作（例如“开始使用/续费前置动作”除外）

#### Scenario: 详情页展示过期标识
- **WHEN** 用户查看一个 `expired` 状态套餐的详情
- **THEN** 页面 MUST 显示明确的“已过期”状态标识

### Requirement: 时间与时区一致性
当使用到期时间回退规则判定有效性时：
- 系统 MUST 使用一致的时间来源（例如统一的 `now` 计算方式）
- 系统 MUST 明确处理时区（例如解析 ISO-8601/Unix 时间戳，并以同一时区/UTC 进行比较）
- 系统 MUST 避免因本地时区差异导致的“提前/延后过期”误判

#### Scenario: ISO 时间字符串比较
- **WHEN** `expiresAt` 为可解析的 ISO-8601 字符串（含时区偏移或 Z）
- **THEN** 系统 MUST 正确解析并与 `now` 比较，得到一致的有效性结论

### Requirement: 异常与降级展示（字段缺失/401/429/网络异常）
当获取套餐信息失败或信息不足以判定有效性时：
- 系统 MUST 提示用户当前数据不可用/状态未知，并提供可恢复动作（例如刷新重试）
- 系统 MUST 采取“保守”策略避免误导：不得把不确定状态展示为“可用”

#### Scenario: 接口返回 401
- **WHEN** 请求套餐信息接口返回 401（未授权/登录态失效）
- **THEN** 系统 MUST 提示需要重新登录/刷新凭证，并避免展示“可用套餐”

#### Scenario: 接口返回 429
- **WHEN** 请求返回 429（限流）
- **THEN** 系统 MUST 提示稍后重试，并保留上一次已知的安全展示（若有），不得将未知数据标记为可用

#### Scenario: 网络异常
- **WHEN** 请求发生网络错误或超时
- **THEN** 系统 MUST 提示网络异常并提供重试入口，同时不得将套餐状态默认当作 `valid`

