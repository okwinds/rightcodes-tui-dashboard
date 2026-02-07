# 新增 `.gitignore`：排除本地缓存与构建产物（L1）

## Goal

- 为仓库添加最小可用的 `.gitignore`，避免把本机文件与测试/构建产物提交到 Git。
- 本次先覆盖已出现的目录/文件：
  - `.DS_Store`
  - `.local/`
  - `.pytest_cache/`
  - `*.egg-info/`

## Constraints

- 不删除任何文件或文件夹（仅新增忽略规则）。
- 不提交任何敏感信息（账号密码、token、cookie、真实明细数据等）。
- `.gitignore` 规则尽量保持最小，避免误伤源码与配置。

## Non-Goals

- 不在本次变更中初始化 Git 仓库（`git init`）或调整已有的 Git 历史/追踪状态。
- 不引入额外的格式化/全仓库重排。

## Acceptance Criteria

- 仓库根目录存在 `.gitignore` 文件。
- `.gitignore` 至少包含以下忽略项：
  - `.DS_Store`
  - `.local/`
  - `.pytest_cache/`
  - `*.egg-info/`

## Test Plan

### Unit / Offline Regression（必须）

- 校验文件存在且包含上述忽略项：
  - `cat .gitignore`

### Manual / Git Verify（可选）

> 仅当当前目录已经是 Git 仓库（存在 `.git/`）时执行。

- `git status --ignored`：
  - 断言 `.DS_Store`、`.local/`、`.pytest_cache/`、`*.egg-info/` 均被标记为 ignored。
- 或 `git check-ignore -v <path>`：
  - 断言命中 `.gitignore` 中对应规则。

