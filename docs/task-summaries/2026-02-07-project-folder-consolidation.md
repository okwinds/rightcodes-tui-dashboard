# 任务总结：项目产物收敛到子目录

## 1) Goal / Scope

- Goal：将 Right.codes CLI Dashboard 现有产物收敛到单一项目子目录 `rightcodes-tui-dashboard/`，并在仓库根目录保留最小 stub（跳转说明）。
- In Scope：
  - 移动 `AGENTS.md` / `DOCS_INDEX.md` / `README.md` / `docs/` / `templates/` / `tools/` 到 `rightcodes-tui-dashboard/`
  - 处理 doctor 输出：移动到 `rightcodes-tui-dashboard/.local/` 并通过根 `.gitignore` 忽略
  - 更新 `rightcodes-tui-dashboard/DOCS_INDEX.md` 内路径前缀
- Out of Scope：任何功能逻辑变更、接口调整、TUI/前端实现。
- Constraints：
  - 不提交敏感信息（token/cookie/内部链接/真实明细数据）
  - 不使用 Playwright 自动化登录

## 2) Context（背景与触发）

- 背景：需要将项目内容与上层仓库模板/杂项隔离，便于后续迭代与复用。
- 触发问题（Symptoms）：仓库根目录内容与项目产物混在一起，且存在 doctor 输出文件需要隔离。
- 影响范围（Impact）：仅影响目录结构与文档跳转，不影响业务逻辑。

## 3) Spec / Contract（文档契约）

- Contract（接口/事件协议/数据结构）：无（目录结构调整）。
- Acceptance Criteria（验收标准）：
  - `rightcodes-tui-dashboard/` 存在且包含 `AGENTS.md` / `DOCS_INDEX.md` / `README.md` / `docs/` / `templates/` / `tools/`
  - 仓库根目录保留 `AGENTS.md` / `DOCS_INDEX.md` / `README.md` 三个 stub，内容仅指向子目录
  - 根 `.gitignore` 忽略 `rightcodes-tui-dashboard/.local/` 与 `rightcodes-doctor.json`
  - `rightcodes-tui-dashboard/DOCS_INDEX.md` 内旧前缀 `rightcodes-cli-dashboard/` 已替换为 `rightcodes-tui-dashboard/`
- Test Plan（测试计划）：
  - 离线回归（结构校验）：用 `ls`/`test`/`find` 验证目录与关键文件存在；确认根目录无 `rightcodes-doctor.json`
- 风险与降级（Risk/Rollback）：
  - 风险：历史文档中若硬编码旧路径，可能需要后续按需更新（本次仅更新 `DOCS_INDEX.md`）。
  - 回滚：将 `rightcodes-tui-dashboard/` 内容移回根目录并恢复原文件名。

## 4) Implementation（实现说明）

### 4.1 Key Decisions（关键决策与 trade-offs）

- Decision：doctor 输出放入 `rightcodes-tui-dashboard/.local/` 并在根 `.gitignore` 忽略。
  - Why：避免敏感环境信息被误提交；同时保持项目目录自洽。
  - Trade-off：本地文件默认不可追踪，需要显式生成/复制。
  - Alternatives：放入系统 keychain/安全存储（超出本次范围）。

### 4.2 Code Changes（按文件列）

- `AGENTS.md`：根目录改为 stub；项目规范文件移动到 `rightcodes-tui-dashboard/AGENTS.md`。
- `DOCS_INDEX.md`：根目录改为 stub；并更新 `rightcodes-tui-dashboard/DOCS_INDEX.md` 的路径前缀。
- `README.md`：根目录改为 stub；项目 README 移入子目录。
- `.gitignore`：新增并忽略 doctor 输出路径。
- `rightcodes-tui-dashboard/.local/rightcodes-doctor.json`：移动 doctor 输出（仅本地保留）。
- `rightcodes-tui-dashboard/docs/`、`rightcodes-tui-dashboard/templates/`、`rightcodes-tui-dashboard/tools/`：目录迁移。

## 5) Verification（验证与测试结果）

### Unit / Offline Regression（必须）

- 命令：
  - `ls -la`
  - `ls -la rightcodes-tui-dashboard`
  - `test -f .gitignore`
  - `test ! -e rightcodes-doctor.json`
  - `test -f rightcodes-tui-dashboard/.local/rightcodes-doctor.json`
  - `rg "rightcodes-cli-dashboard/" rightcodes-tui-dashboard/DOCS_INDEX.md`
- 结果：通过（结构与路径前缀符合验收标准）。

## 6) Results（交付结果）

- 交付物列表：
  - 项目子目录：`rightcodes-tui-dashboard/`
  - 根目录跳转 stub：`AGENTS.md`、`DOCS_INDEX.md`、`README.md`
  - doctor 输出隔离：`rightcodes-tui-dashboard/.local/rightcodes-doctor.json` + 根 `.gitignore`
- 如何使用/如何验收：
  - 从 `rightcodes-tui-dashboard/README.md` 开始阅读；按上节命令检查目录结构即可。

## 7) Known Issues / Follow-ups

- 已知问题：部分历史文档文件名仍包含 `rightcodes-cli-dashboard` 字样（例如 plan 文件名）；如需统一命名可另开任务处理。
- 后续建议：如后续增加更多 `.local` 文件，统一放入 `rightcodes-tui-dashboard/.local/` 并保持 `.gitignore` 覆盖。

## 8) Doc Index Update

- 已在 `rightcodes-tui-dashboard/DOCS_INDEX.md` 登记：是（目录项已覆盖，且本次未新增必须单列的核心文档）。

