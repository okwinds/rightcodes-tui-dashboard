from __future__ import annotations

import argparse
import sys

from rightcodes_tui_dashboard import __version__
from rightcodes_tui_dashboard.cli import (
    cmd_dashboard,
    cmd_doctor,
    cmd_login,
    cmd_logs,
)

_HELP_EXAMPLES = """\
示例（最佳实践）：
  # 1) 登录（交互式输入密码，不回显；仅用于换取 token，密码不落盘）
  rightcodes login

  # 2) 推荐组合：按“本地当天”统计 + 30s 自动刷新 + 近 6h 速率窗口
  rightcodes dashboard --range today --watch 30s --rate-window 6h

  # 3) 只看一次快照（关闭自动刷新）
  rightcodes dashboard --watch 0s

  # 4) rolling window（过去 N 小时/天）：
  rightcodes dashboard --range 24h
  rightcodes dashboard --range 7d

提示：
  - 查看某个子命令的全部参数：rightcodes <command> --help
  - 常见子命令：dashboard / logs / doctor
"""


class _Formatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    """帮助信息 formatter：保留换行 + 自动展示默认值。"""


def _add_parser(sub, name: str, *, help_text: str) -> argparse.ArgumentParser:
    """创建子命令 parser（统一 formatter）。"""

    return sub.add_parser(name, help=help_text, formatter_class=_Formatter)


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。

    Returns:
        argparse.ArgumentParser: 根解析器。
    """

    parser = argparse.ArgumentParser(
        prog="rightcodes",
        description=(
            "Right.codes CLI + TUI dashboard（个人用量/套餐看板）。\n"
            "- 不使用 Playwright 自动化登录（只走 JSON 接口 + Bearer token）\n"
            "- 密码不落盘：仅交互式输入用于换取 token\n"
            "- token 优先 keyring；失败则写入全局数据目录 token.json（可用 RIGHTCODES_DATA_DIR 覆盖）\n"
        ),
        epilog=_HELP_EXAMPLES,
        formatter_class=_Formatter,
    )
    parser.add_argument("--version", action="version", version=f"rightcodes {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = _add_parser(sub, "login", help_text="交互式登录并保存 token")
    p_login.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes；通常无需改）")
    p_login.add_argument(
        "--store",
        default="auto",
        choices=["auto", "keyring", "file"],
        help="token 存储方式（auto：优先 keyring，失败则 file）",
    )
    p_login.add_argument(
        "--print-token",
        action="store_true",
        help="调试用：仅输出打码 token（不要写入文档/日志）",
    )

    p_dashboard = _add_parser(sub, "dashboard", help_text="启动 TUI 看板")
    p_dashboard.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes；通常无需改）")
    p_dashboard.add_argument(
        "--watch",
        default="30s",
        help=(
            "自动刷新间隔（支持 s/m/h/d 后缀，且必须为整数；例如 30s/5m/1h）。\n"
            "设为 0s 关闭自动刷新（只看一次快照）。"
        ),
    )
    p_dashboard.add_argument(
        "--range",
        default="today",
        help=(
            "统计区间：\n"
            "- today：按本地日历日统计（当天 00:00 起算；推荐，避免跨日）\n"
            "- 24h/7d：rolling window（过去 N 小时/天；适合跨日对比）\n"
        ),
    )
    p_dashboard.add_argument(
        "--rate-window",
        default="6h",
        help="速率窗口（用于 Burn/ETA 估算；支持 s/m/h/d 后缀且必须为整数；例如 6h/12h/1d）",
    )
    p_dashboard.add_argument(
        "--granularity",
        default="auto",
        choices=["auto", "hour", "day"],
        help="趋势粒度（auto：range<=48h 用 hour，否则 day）",
    )
    p_dashboard.add_argument(
        "--no-keyring",
        action="store_true",
        help="禁用 keyring（适用于 CI/容器/无 keyring 环境；将降级为文件存储 token）",
    )

    p_logs = _add_parser(sub, "logs", help_text="查看使用明细（CLI 输出，默认脱敏）")
    p_logs.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_logs.add_argument(
        "--range",
        default="24h",
        help="时间范围（支持 today/24h/7d；默认 24h）",
    )
    p_logs.add_argument("--page-size", type=int, default=50, help="分页大小（默认 50）")
    p_logs.add_argument("--page", type=int, default=1, help="页码（默认 1）")
    p_logs.add_argument("--format", choices=["table", "json"], default="table", help="输出格式（默认 table）")

    p_doctor = _add_parser(sub, "doctor", help_text="端点自检与 keys 探测（不输出值）")
    p_doctor.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_doctor.add_argument(
        "--out",
        default=None,
        help="输出 JSON 路径（默认写入全局数据目录 rightcodes-doctor.json）",
    )
    p_doctor.add_argument("--no-save", action="store_true", help="不落盘，仅输出 summary")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 参数列表（默认使用 sys.argv[1:]）。

    Returns:
        进程退出码。
    """

    args = build_parser().parse_args(argv)

    try:
        if args.command == "login":
            return cmd_login(args)
        if args.command == "dashboard":
            return cmd_dashboard(args)
        if args.command == "logs":
            return cmd_logs(args)
        if args.command == "doctor":
            return cmd_doctor(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e.__class__.__name__}")
        return 1

    print("Unexpected error: unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
