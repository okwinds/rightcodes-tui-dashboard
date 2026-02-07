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

1) **Dashboard 内展示使用记录明细但做部分打码**
   - Why：表格列包含“密钥 / IP”，默认全明文会增加误泄露风险；同时又需要一定可辨识度便于排查。
   - 方案：密钥保留前 2 + 末 4（其余省略）；IPv4 保留前两段，其余打码；其它格式走兜底打码。

2) **主体内容统一放入 `VerticalScroll`**
   - Why：新增两张表后，在小窗口下容易溢出；滚动可避免为每个区块手动调高度。

---

## Code Changes

- `rightcodes-tui-dashboard/src/rightcodes_tui_dashboard/ui/app.py`
  - 新增 `#quota_overview`（替代 `#quota_summary/#quota_bar`），实现单行进度条渲染
  - “详细统计数据”改为居中标题 + `box.SQUARE` 边框表格
  - Dashboard `_fetch_data` 增加 `/use-log/list` 拉取（非关键区块，接口异常时降级为空）
  - 新增“使用记录明细”表格渲染与字段兼容映射，并对密钥/IP 默认部分打码

- `rightcodes-tui-dashboard/docs/specs/tui-dashboard-mvp.md`
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

