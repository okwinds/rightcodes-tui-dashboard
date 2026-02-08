from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
from pathlib import Path
from typing import Any

from rightcodes_tui_dashboard.api.client import RightCodesApiClient
from rightcodes_tui_dashboard.errors import ApiError, AuthError, RateLimitError
from rightcodes_tui_dashboard.privacy import redact_sensitive_fields
from rightcodes_tui_dashboard.storage.token_store import (
    KeyringTokenStore,
    LocalFileTokenStore,
    TokenStore,
)
from rightcodes_tui_dashboard.ui.app import RightCodesDashboardApp
from rightcodes_tui_dashboard.services.calculations import extract_use_logs_items
from rightcodes_tui_dashboard.services.use_logs import extract_use_log_tokens
from rightcodes_tui_dashboard.utils.paths import resolve_app_data_path


DEFAULT_BASE_URL = "https://right.codes"


def _mask_token(token: str) -> str:
    """对 token 做最小打码，避免误泄露。"""

    if len(token) <= 8:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


def _select_store(store: str, disable_keyring: bool = False) -> TokenStore:
    """选择 token store 实现。

    Args:
        store: auto/keyring/file
        disable_keyring: 是否禁用 keyring。

    Returns:
        TokenStore: 可用的 token 存储。
    """

    if store == "file":
        return LocalFileTokenStore()
    if store == "keyring":
        return KeyringTokenStore()
    if store != "auto":
        raise ValueError(f"Unsupported store: {store}")

    if disable_keyring:
        return LocalFileTokenStore()

    keyring_store = KeyringTokenStore()
    if keyring_store.is_available():
        return keyring_store
    return LocalFileTokenStore()


def cmd_login(args: argparse.Namespace) -> int:
    """`rightcodes login` 子命令实现。"""

    base_url = args.base_url or DEFAULT_BASE_URL
    store = _select_store(args.store)

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    try:
        with RightCodesApiClient(base_url=base_url, token=None) as client:
            token = client.login(username=username, password=password)
    except AuthError as e:
        print(f"认证失败：{e}. 请检查账号/密码或 token 状态。")
        return 1
    except RateLimitError as e:
        retry_at = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else "unknown"
        print(f"触发限流（429），请稍后重试。Next retry: {retry_at}")
        return 1
    except ApiError as e:
        print(f"登录失败：{e}")
        return 1

    try:
        store.save_token(token)
        store_name = store.store_name()
    except Exception as e:
        # keyring 后端缺失/不可用时：按 spec 自动降级到本地文件
        if isinstance(store, KeyringTokenStore):
            file_store = LocalFileTokenStore()
            file_store.save_token(token)
            store_name = file_store.store_name()
            print(f"keyring 不可用（{e.__class__.__name__}），已降级保存到本地文件（{store_name}）。")
        else:
            print(f"保存 token 失败：{e.__class__.__name__}")
            return 1

    print(f"已登录并保存 token（{store_name}）。")

    if args.print_token:
        print(f"Token（masked）: {_mask_token(token)}")

    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """`rightcodes dashboard` 子命令实现。"""

    base_url = args.base_url or DEFAULT_BASE_URL
    store = _select_store("auto", disable_keyring=bool(args.no_keyring))
    token_record = store.load_token()
    token = token_record.token if token_record else None
    token = _ensure_token_for_dashboard(base_url=base_url, store=store, token=token)
    if not token:
        return 1

    watch_seconds = _parse_duration_seconds(args.watch) if args.watch else 30
    if watch_seconds <= 0:
        watch_seconds = None

    range_mode = "rolling"
    range_text = (args.range or "").strip()
    if range_text.lower() in ("today", "td", "今日"):
        # “今天”必须以日历日为边界动态计算：在 _fetch_data 中按本地 00:00 起算。
        range_mode = "today"
        range_seconds = 24 * 3600
    else:
        range_seconds = _parse_duration_seconds(range_text) if range_text else 24 * 3600
    rate_window_seconds = _parse_duration_seconds(args.rate_window) if args.rate_window else 6 * 3600
    granularity = args.granularity or "auto"

    app = RightCodesDashboardApp(
        base_url=base_url,
        token=token,
        watch_seconds=watch_seconds,
        range_seconds=range_seconds,
        range_mode=range_mode,
        rate_window_seconds=rate_window_seconds,
        granularity=granularity,
    )
    app.run()
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    """`rightcodes logs` 子命令实现（CLI：table/json，默认脱敏）。"""

    base_url = args.base_url or DEFAULT_BASE_URL
    store = _select_store("auto")
    token_record = store.load_token()
    token = token_record.token if token_record else None

    if not token:
        print("未登录：请先执行 `rightcodes login`。")
        return 1

    range_seconds = _parse_duration_seconds(args.range) if args.range else 24 * 3600
    now = dt.datetime.now()
    start = (now - dt.timedelta(seconds=range_seconds)).strftime("%Y-%m-%dT%H:%M:%S")
    end = now.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        with RightCodesApiClient(base_url=base_url, token=token) as client:
            payload = client.use_logs_list(
                page=int(args.page),
                page_size=int(args.page_size),
                start_date=start,
                end_date=end,
            )
            items = extract_use_logs_items(payload)
    except AuthError as e:
        print(f"认证失败：{e}")
        return 1
    except RateLimitError as e:
        retry_at = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else "unknown"
        print(f"触发限流（429），请稍后重试。Next retry: {retry_at}")
        return 1
    except ApiError as e:
        print(f"获取 logs 失败：{e}")
        return 1

    redacted = [redact_sensitive_fields(x) for x in items if isinstance(x, dict)]
    if args.format == "json":
        print(json.dumps(redacted, ensure_ascii=False, indent=2))
        return 0

    _print_logs_table(redacted)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """`rightcodes doctor` 子命令实现（脱敏：仅输出 keys）。"""

    base_url = args.base_url or DEFAULT_BASE_URL
    store = _select_store("auto")
    token_record = store.load_token()
    token = token_record.token if token_record else None

    summary: dict[str, Any] = {
        "base_url": base_url,
        "generated_at": dt.datetime.now().isoformat(sep=" ", timespec="seconds"),
        "endpoints": {},
    }

    def _record(name: str, fn) -> None:
        try:
            data = fn()
            keys = sorted(list(data.keys())) if isinstance(data, dict) else []
            summary["endpoints"][name] = {"ok": True, "keys": keys}
        except AuthError:
            summary["endpoints"][name] = {"ok": False, "error": "auth", "keys": []}
        except RateLimitError as e:
            next_retry = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else None
            summary["endpoints"][name] = {"ok": False, "error": "rate_limited", "next_retry_at": next_retry, "keys": []}
        except ApiError as e:
            summary["endpoints"][name] = {"ok": False, "error": str(e), "keys": []}

    now = dt.datetime.now()
    start_24h = (now - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    start_6h = (now - dt.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
    end_now = now.strftime("%Y-%m-%dT%H:%M:%S")

    with RightCodesApiClient(base_url=base_url, token=token) as client:
        _record("GET /auth/me", client.get_me)
        _record("GET /subscriptions/list", client.list_subscriptions)
        _record("GET /use-log/stats/overall", client.stats_overall)
        _record("GET /use-log/stats (24h)", lambda: client.stats_range(start_date=start_24h, end_date=end_now))
        _record(
            "GET /use-log/stats/advanced (24h)",
            lambda: client.stats_advanced(start_date=start_24h, end_date=end_now, granularity="hour"),
        )
        _record(
            "GET /use-log/stats/advanced (6h)",
            lambda: client.stats_advanced(start_date=start_6h, end_date=end_now, granularity="hour"),
        )
        _record(
            "GET /use-log/list (1 item)",
            lambda: client.use_logs_list(page=1, page_size=1, start_date=start_24h, end_date=end_now),
        )

    if not args.no_save:
        out_path = Path(args.out) if args.out else resolve_app_data_path("rightcodes-doctor.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"doctor 输出已写入：{out_path}")
    else:
        print(json.dumps({"endpoints": summary["endpoints"]}, ensure_ascii=False, indent=2))

    return 0


def _ensure_token_for_dashboard(*, base_url: str, store: TokenStore, token: str | None) -> str | None:
    """确保 dashboard 启动时 token 可用。

    目标：
    - 全局只登录一次：跨目录可用（token store 负责持久化）
    - token 过期时：不直接报错退出，先进入登录流程获取新 token
    """

    if token:
        try:
            with RightCodesApiClient(base_url=base_url, token=token) as client:
                client.get_me()
            return token
        except AuthError:
            token = None
        except (RateLimitError, ApiError):
            # 网络波动/429 不应阻塞 TUI 启动：先用现有 token 进入界面，后续刷新再处理。
            return token

    # token 缺失或失效：交互式重新登录
    print("未登录或 token 已失效，正在进入登录流程（仅本地保存 token，密码不落盘）。")

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    try:
        with RightCodesApiClient(base_url=base_url, token=None) as client:
            new_token = client.login(username=username, password=password)
    except AuthError as e:
        print(f"认证失败：{e}. 请检查账号/密码。")
        return None
    except RateLimitError as e:
        retry_at = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else "unknown"
        print(f"触发限流（429），请稍后重试。Next retry: {retry_at}")
        return None
    except ApiError as e:
        print(f"登录失败：{e}")
        return None

    try:
        store.save_token(new_token)
        store_name = store.store_name()
    except Exception as e:
        if isinstance(store, KeyringTokenStore):
            file_store = LocalFileTokenStore()
            file_store.save_token(new_token)
            store_name = file_store.store_name()
            print(f"keyring 不可用（{e.__class__.__name__}），已降级保存到本地文件（{store_name}）。")
        else:
            print(f"保存 token 失败：{e.__class__.__name__}")
            return None

    print(f"已登录并保存 token（{store_name}）。")
    return new_token


def _print_logs_table(items: list[dict[str, Any]]) -> None:
    """以表格方式输出 logs（默认已脱敏）。"""

    from rich.console import Console
    from rich.table import Table

    table = Table(title="Right.codes Logs（脱敏）", show_lines=False)
    table.add_column("time", no_wrap=True)
    table.add_column("tokens", justify="right", no_wrap=True)
    table.add_column("cost", justify="right", no_wrap=True)
    table.add_column("summary")

    for item in items:
        time_val = _first_str(item, ("time", "ts", "timestamp", "date", "request_time", "created_at")) or "—"
        tokens_val = extract_use_log_tokens(item)
        tokens = "—" if tokens_val is None else f"{int(tokens_val):,}"
        cost = _first_number_str(item, ("cost", "total_cost", "amount")) or "—"
        summary = item.copy()
        for k in (
            "time",
            "ts",
            "timestamp",
            "date",
            "created_at",
            "tokens",
            "total_tokens",
            "token_count",
            "cost",
            "total_cost",
            "amount",
        ):
            summary.pop(k, None)
        summary_text = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        if len(summary_text) > 96:
            summary_text = summary_text[:95] + "…"
        table.add_row(time_val, tokens, cost, summary_text)

    Console().print(table)


def _first_str(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """从 payload 中按 keys 顺序取第一个非空 str。"""

    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _first_number_str(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """从 payload 中按 keys 顺序取第一个 number 并格式化为字符串。"""

    for k in keys:
        v = payload.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            number = float(v)
            return f"{number:.0f}" if number.is_integer() else f"{number:.4f}"
    return None


def _parse_duration_seconds(raw: str) -> int:
    """解析简单 duration（如 30s/10m/2h/7d）。

    Args:
        raw: 字符串。

    Returns:
        秒数（int）。

    Raises:
        ValueError: 无法解析。
    """

    text = raw.strip().lower()
    if text.endswith("s"):
        return int(text[:-1])
    if text.endswith("m"):
        return int(text[:-1]) * 60
    if text.endswith("h"):
        return int(text[:-1]) * 3600
    if text.endswith("d"):
        return int(text[:-1]) * 24 * 3600
    raise ValueError(f"Unsupported duration: {raw}")
