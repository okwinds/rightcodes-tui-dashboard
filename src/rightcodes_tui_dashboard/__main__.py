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


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。

    Returns:
        argparse.ArgumentParser: 根解析器。
    """

    parser = argparse.ArgumentParser(prog="rightcodes")
    parser.add_argument("--version", action="version", version=f"rightcodes {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="交互式登录并保存 token")
    p_login.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_login.add_argument(
        "--store",
        default="auto",
        choices=["auto", "keyring", "file"],
        help="token 存储方式（默认 auto：优先 keyring，失败则 file）",
    )
    p_login.add_argument(
        "--print-token",
        action="store_true",
        help="调试用：仅输出打码 token（不要写入文档/日志）",
    )

    p_dashboard = sub.add_parser("dashboard", help="启动 TUI 看板")
    p_dashboard.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_dashboard.add_argument(
        "--watch",
        default="30s",
        help="自动刷新间隔（如 30s/60s；默认 30s；设为 0s 关闭自动刷新）",
    )
    p_dashboard.add_argument(
        "--range",
        default="today",
        help="统计区间（如 today/24h/7d；默认 today）",
    )
    p_dashboard.add_argument(
        "--rate-window",
        default="6h",
        help="速率窗口（如 6h；默认 6h）",
    )
    p_dashboard.add_argument(
        "--granularity",
        default="auto",
        choices=["auto", "hour", "day"],
        help="趋势粒度（默认 auto：range<=48h 用 hour，否则 day）",
    )
    p_dashboard.add_argument("--no-keyring", action="store_true", help="禁用 keyring（便于在无 keyring 环境运行）")

    p_logs = sub.add_parser("logs", help="查看使用明细（CLI 输出，默认脱敏）")
    p_logs.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_logs.add_argument("--range", default="24h", help="时间范围（如 24h/7d；默认 24h）")
    p_logs.add_argument("--page-size", type=int, default=50, help="分页大小（默认 50）")
    p_logs.add_argument("--page", type=int, default=1, help="页码（默认 1）")
    p_logs.add_argument("--format", choices=["table", "json"], default="table", help="输出格式（默认 table）")

    p_doctor = sub.add_parser("doctor", help="端点自检与 keys 探测（不输出值）")
    p_doctor.add_argument("--base-url", default=None, help="覆盖 base_url（默认 https://right.codes）")
    p_doctor.add_argument(
        "--out",
        default=None,
        help="输出 JSON 路径（默认写入 rightcodes-tui-dashboard/.local/rightcodes-doctor.json）",
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
