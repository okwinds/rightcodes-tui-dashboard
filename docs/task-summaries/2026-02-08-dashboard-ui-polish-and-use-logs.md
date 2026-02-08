# 任务总结：Dashboard UI 收敛（总览单行条 + 使用记录明细表）

- 日期：2026-02-08
- 范围等级：L1（局部 UI/展示增强）

---

## Goal / Scope

在不改变核心计算口径的前提下，让 TUI 面板更接近网页看板的阅读体验：
- 顶部总览额度进度条改为“单行三段”：左侧 `$已用 / $总额`，中间进度条，右侧百分比
- “详细统计数据”标题居中 + 表格带边框 + 保留合计行
- 在 Dashboard 内新增“使用记录明细”表格（来自 `/use-log/list`）

约束：
- 不引入 Playwright；不写入任何敏感信息到仓库
- 离线单测必须通过

---

## Key Decisions

1) **Dashboard 内展示使用记录明细：密钥打码、IP 全量展示**
   - Why：密钥属于敏感字段，默认全明文有误泄露风险；但 IP 在“个人工具 + 本地使用”场景下可完整展示以便排查。
   - 方案：密钥做部分打码（保留前后片段 + 省略号）；IP 不做掩码。

2) **主体内容统一放入 `VerticalScroll`**
   - Why：新增两张表后，在小窗口下容易溢出；滚动可避免为每个区块手动调高度。

---

## Code Changes

- `src/rightcodes_tui_dashboard/ui/app.py`
  - 新增 `#quota_overview`（替代 `#quota_summary/#quota_bar`），实现单行进度条渲染
  - “详细统计数据”改为居中标题 + `box.SQUARE` 边框表格
  - Dashboard `_fetch_data` 增加 `/use-log/list` 拉取（非关键区块，接口异常时降级为空）
  - 新增“使用记录明细”表格渲染与字段兼容映射：`渠道/倍率/资费/Tokens/IP` 均从 JSON 字段提取（不写死）

- `docs/specs/tui-dashboard-mvp.md`
  - 更新 UI 章节：补充“总览额度单行条”与“使用记录明细表”的展示契约

---

## Test Plan & Results

离线回归：

```bash
cd rightcodes-tui-dashboard
python3 -m pytest -q
```

结果：通过（exit code 0）。

---

## Known Issues / Risks

- `/use-log/list` 明细字段可能存在变体：当前使用多候选 key 映射，缺失字段以 `—` 降级展示；如后续遇到新增/变更字段，可再补兼容候选。

---

## Next Steps

- 你登录后跑一次 `rightcodes dashboard`，确认“使用记录明细”各列字段映射是否需要微调（尤其是：渠道/计费倍率/扣费来源）。  

---

## Addendum（后续小迭代：表格信息密度与可读性）

> 目的：在不折叠其它列的前提下，把“时间列浪费的留白”让给“密钥/模型”列，使密钥多显示 1 个字符左右，提升排查体验。

- “使用记录明细”表格：
  - 固定“时间”列宽度，避免 expand 导致右侧留白浪费
  - 统一列右侧留白（除密钥/模型外），避免文本贴边
  - 提高“密钥/模型”列宽度占比（ratio），减少截断
  - 调整密钥打码策略：中等长度 key 更“可辨识”（多露出 1 个字符左右）
  - 支持翻页：`p` 上一页 / `n` 下一页，并在表格下方提示操作
