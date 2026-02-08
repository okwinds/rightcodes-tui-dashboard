"""
Right.codes CLI + TUI dashboard（个人小工具）。

规格与约束（摘要）：
- `docs/specs/tui-dashboard-mvp.md`
- 不使用 Playwright 自动化登录（只走 JSON 接口 + token）
- 密码不落盘；token 优先 keyring，失败降级到全局数据目录 `token.json`（支持 `RIGHTCODES_DATA_DIR` 覆盖）
"""

__all__ = ["__version__"]

__version__ = "0.1.3"
