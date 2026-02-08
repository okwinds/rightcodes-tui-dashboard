from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from typing import Any

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Header, Sparkline, Static

from rightcodes_tui_dashboard.api.client import RightCodesApiClient
from rightcodes_tui_dashboard.errors import ApiError, AuthError, RateLimitError
from rightcodes_tui_dashboard.privacy import redact_sensitive_fields
from rightcodes_tui_dashboard.services.backoff import compute_next_retry_at
from rightcodes_tui_dashboard.services.calculations import (
    BurnRate,
    extract_advanced_buckets,
    extract_me_balance,
    extract_model_usage_rows,
    extract_stats_totals,
    extract_use_logs_items,
    calculate_burn_rate,
    estimate_eta,
    compute_effective_quota,
    normalize_subscriptions,
    summarize_quota,
)
from rightcodes_tui_dashboard.services.use_logs import (
    extract_use_log_billing_rate,
    extract_use_log_billing_source,
    extract_use_log_channel,
    extract_use_log_ip,
    extract_use_log_tokens,
    format_billing_rate,
    format_billing_source,
)
from rightcodes_tui_dashboard import __version__


@dataclass
class BackoffState:
    attempt: int = 0
    next_retry_at: dt.datetime | None = None


class DashboardScreen(Screen):
    """Dashboard 主屏（MVP：quota + subscriptions + burn/ETA + 状态栏）。"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("l", "logs", "Logs"),
        ("d", "doctor", "Doctor"),
        ("n", "next_use_logs_page", "Next page"),
        ("p", "prev_use_logs_page", "Prev page"),
        ("?", "help", "Help"),
    ]

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        watch_seconds: int | None,
        range_seconds: int,
        range_mode: str,
        rate_window_seconds: int,
        granularity: str,
    ) -> None:
        super().__init__()
        self._base_url = base_url
        self._token = token
        self._watch_seconds = watch_seconds
        self._range_seconds = range_seconds
        self._range_mode = range_mode
        self._rate_window_seconds = rate_window_seconds
        self._granularity = granularity

        self._backoff = BackoffState()
        self._last_ok_at: dt.datetime | None = None
        self._stale_since: dt.datetime | None = None
        self._next_refresh_at: dt.datetime | None = None

        self._cached: dict[str, Any] | None = None
        self._burn_cached: BurnRate | None = None
        self._eta_target: dt.datetime | None = None
        self._eta_remaining_tokens_est: float | None = None
        self._eta_mode: str | None = None
        self._degraded_reason: str | None = None

        # 使用记录明细分页
        self._use_logs_page: int = 1
        self._use_logs_page_size: int = 20
        self._use_logs_total: int | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="banner")
            yield Static("", id="quota_overview")
            with VerticalScroll(id="body_scroll"):
                yield Static("", id="subscriptions")
                yield Static("", id="details_by_model")
                yield Static("", id="use_logs")
                yield Sparkline([], id="trend_tokens")
                yield Static("", id="burn_eta")
            yield Static("", id="status")

    def on_mount(self) -> None:
        self.set_focus(self.query_one("#body_scroll", VerticalScroll))

        self._render_static_placeholders()
        self._kick_refresh(force=True)

        if self._watch_seconds:
            self.set_interval(1.0, self._tick)

    def action_quit(self) -> None:
        self.app.exit()

    def action_logs(self) -> None:
        self.app.push_screen(
            LogsScreen(base_url=self._base_url, token=self._token, range_seconds=self._range_seconds)
        )

    def action_doctor(self) -> None:
        self.app.push_screen(DoctorScreen(base_url=self._base_url, token=self._token))

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_refresh(self) -> None:
        self._kick_refresh(force=True)

    def action_next_use_logs_page(self) -> None:
        max_page = self._get_use_logs_max_page()
        if max_page is not None and self._use_logs_page >= max_page:
            self._set_banner("使用记录明细：已是最后一页。", kind="info")
            return
        self._use_logs_page += 1
        self._kick_refresh(force=True)

    def action_prev_use_logs_page(self) -> None:
        if self._use_logs_page <= 1:
            self._set_banner("使用记录明细：已是第一页。", kind="info")
            return
        self._use_logs_page -= 1
        self._kick_refresh(force=True)

    def _get_use_logs_max_page(self) -> int | None:
        if self._use_logs_total is None:
            return None
        if self._use_logs_page_size <= 0:
            return None
        total_pages = (int(self._use_logs_total) + int(self._use_logs_page_size) - 1) // int(self._use_logs_page_size)
        return max(1, total_pages)

    def _tick(self) -> None:
        self._update_status()
        self._update_burn_eta_live()
        if not self._watch_seconds:
            return
        now = dt.datetime.now()
        if self._next_refresh_at and now < self._next_refresh_at:
            return
        self._kick_refresh(force=False)

    def _kick_refresh(self, *, force: bool) -> None:
        now = dt.datetime.now()
        if self._in_backoff(now) and not force:
            return
        if self._in_backoff(now) and force:
            self._set_banner("仍在退避中（429），请等待 next retry。", kind="warn")
            return

        if self._watch_seconds:
            self._next_refresh_at = now + dt.timedelta(seconds=self._watch_seconds)

        asyncio.create_task(self._refresh_once())

    def _in_backoff(self, now: dt.datetime) -> bool:
        return bool(self._backoff.next_retry_at and now < self._backoff.next_retry_at)

    async def _refresh_once(self) -> None:
        if not self._token:
            self._set_banner("未登录：请先执行 `rightcodes login`。", kind="warn")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
            self._update_status()
            return

        try:
            data = await asyncio.to_thread(self._fetch_data)
        except AuthError:
            self._set_banner("认证失败（token 可能已过期）：请执行 `rightcodes login`。", kind="error")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
            self._update_status()
            return
        except RateLimitError as e:
            self._enter_backoff(e)
            retry_at = self._backoff.next_retry_at.isoformat(sep=" ", timespec="seconds") if self._backoff.next_retry_at else "unknown"
            self._set_banner(f"触发限流（429），已进入退避。Next retry: {retry_at}", kind="warn")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
            self._update_status()
            return
        except ApiError as e:
            self._set_banner(f"刷新失败：{e}", kind="error")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
            self._update_status()
            return
        except Exception as e:
            self._set_banner(f"刷新失败：{e.__class__.__name__}", kind="error")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
            self._update_status()
            return

        # OK
        self._cached = data
        self._last_ok_at = dt.datetime.now()
        self._stale_since = None
        self._backoff = BackoffState()
        self._set_banner("", kind="info")
        try:
            self._render_view(data)
        except Exception as e:
            # 防御性兜底：渲染失败不应导致任务异常或 UI 崩溃。
            self._set_banner(f"渲染失败：{e.__class__.__name__}", kind="error")
            self._stale_since = self._stale_since or dt.datetime.now()
            self._render_from_cache()
        self._update_status()

    def _fetch_data(self) -> dict[str, Any]:
        now = dt.datetime.now()
        if self._range_mode == "today":
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_dt = now - dt.timedelta(seconds=self._range_seconds)
        start_range = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_now = now.strftime("%Y-%m-%dT%H:%M:%S")
        start_rate = (now - dt.timedelta(seconds=self._rate_window_seconds)).strftime("%Y-%m-%dT%H:%M:%S")

        granularity = self._granularity
        if granularity == "auto":
            granularity = "hour" if self._range_seconds <= 48 * 3600 else "day"

        with RightCodesApiClient(base_url=self._base_url, token=self._token) as client:
            me = client.get_me()
            subs = client.list_subscriptions()
            adv_rate = client.stats_advanced(start_date=start_rate, end_date=end_now, granularity="hour")
            adv_trend = client.stats_advanced(start_date=start_range, end_date=end_now, granularity=granularity)
            stats = client.stats_range(start_date=start_range, end_date=end_now)
            use_logs: dict[str, Any] = {}
            try:
                use_logs = client.use_logs_list(
                    page=int(self._use_logs_page),
                    page_size=int(self._use_logs_page_size),
                    start_date=start_range,
                    end_date=end_now,
                )
            except ApiError:
                # /use-log/list 属于“非关键”区块：接口变更时不应阻塞主面板刷新。
                use_logs = {}
            return {
                "me": me,
                "subscriptions": subs,
                "advanced_rate": adv_rate,
                "advanced_trend": adv_trend,
                "stats": stats,
                "use_logs": use_logs,
            }

    def _render_static_placeholders(self) -> None:
        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(Text("余额：—", style="dim"), Text(f"ver: {__version__}", style="dim"))
        self.query_one("#quota_overview", Static).update(Group(header, _quota_overview_line("— / —  ", None, width=10)))
        self.query_one("#subscriptions", Static).update("套餐：—")
        self.query_one("#details_by_model", Static).update("详细统计数据：—")
        self.query_one("#use_logs", Static).update("使用记录明细：—")
        self.query_one("#trend_tokens", Sparkline).data = []
        self._burn_cached = None
        self._eta_target = None
        self._eta_remaining_tokens_est = None
        self._eta_mode = None
        self.query_one("#burn_eta", Static).update("Burn: —  ETA: —")
        self._update_status()

    def _render_from_cache(self) -> None:
        if not self._cached:
            self._render_static_placeholders()
            return
        self._render_view(self._cached)

    def _render_view(self, data: dict[str, Any]) -> None:
        """将 API payload 渲染到 Dashboard 视图。

        注意：不要命名为 `_render`，以避免覆盖 Textual 内部渲染方法。
        """

        now = dt.datetime.now()

        subs_payload = data.get("subscriptions") if isinstance(data.get("subscriptions"), dict) else {}
        subs_items = subs_payload.get("subscriptions") if isinstance(subs_payload.get("subscriptions"), list) else []
        subs_items = [x for x in subs_items if isinstance(x, dict)]

        normalized = normalize_subscriptions(subs_items, now=now)
        quota = summarize_quota(normalized)
        self._degraded_reason = quota.degraded_reason

        if quota.total_quota_sum is None or quota.remaining_sum is None or quota.used_sum is None:
            quota_label = "— / —"
            quota_pct = None
        else:
            quota_label = f"{_fmt_money(quota.used_sum)} / {_fmt_money(quota.total_quota_sum)}"
            quota_pct = None
            if quota.total_quota_sum > 0:
                quota_pct = float(quota.used_sum) / float(quota.total_quota_sum)

        adv_rate_payload = data.get("advanced_rate") if isinstance(data.get("advanced_rate"), dict) else {}
        buckets_rate = extract_advanced_buckets(adv_rate_payload)
        burn = calculate_burn_rate(buckets_rate, window_seconds=self._rate_window_seconds)
        self._burn_cached = burn
        self._update_eta_targets(quota_remaining=quota.remaining_sum, burn=burn, now=now)

        me_payload = data.get("me") if isinstance(data.get("me"), dict) else {}
        balance = extract_me_balance(me_payload)
        self._render_quota_overview(quota_label, quota_pct, balance=balance)

        self.query_one("#burn_eta", Static).update(self._format_burn_eta_block(now))

        self._render_subscriptions(normalized)
        self._render_details_by_model(data)
        self._render_use_logs(data)
        self._render_trend(data)

    def _render_subscriptions(self, items) -> None:
        """渲染 subscriptions（每包一个卡片 + 进度条）。"""

        host = self.query_one("#subscriptions", Static)
        if not items:
            host.update("套餐：—")
            return

        cards: list[Any] = []
        for idx, s in enumerate(items, start=1):
            effective = compute_effective_quota(s)

            obtained_at = _fmt_time(s.obtained_at, s.obtained_at_raw)
            expires_at = _fmt_time(s.expires_at, s.expires_at_raw)
            reset_today = _reset_today_label(s.reset_today)

            if effective is None:
                quota_line = "—"
                used_pct_text = "—"
                bar = _bar_text(None, width=28, dim=True)
            else:
                quota_line = f"{_fmt_money(effective.remaining_effective)} / {_fmt_money(effective.total_effective)}"
                used_pct_text = _fmt_pct_short(effective.used_pct)
                bar = _bar_text(effective.used_pct, width=28, dim=False)

            grid = Table.grid(padding=(0, 1))
            grid.add_column(style="dim", width=10)
            grid.add_column(ratio=1, overflow="fold")
            grid.add_row("今日重置", reset_today)
            grid.add_row("获得时间", obtained_at)
            grid.add_row("到期时间", expires_at)
            grid.add_row("额度", quota_line)
            grid.add_row("已用比例", used_pct_text)

            title = f"套餐 {idx}"
            border_style = "cyan" if s.reset_today is False else ("green" if s.reset_today is True else "yellow")
            cards.append(
                Panel(
                    Group(grid, bar),
                    title=title,
                    border_style=border_style,
                )
            )

        host.update(Columns(cards, equal=True, expand=True))

    def _render_quota_overview(self, label: str, pct: float | None, *, balance: float | None) -> None:
        """渲染总览额度（两行）：

        - 第一行：余额（左对齐）
        - 第二行：总消耗进度条（单行三段：label + bar + %）
        """

        host = self.query_one("#quota_overview", Static)
        width = max(8, host.size.width - 2)  # 扣掉左右 padding（对齐套餐区域）
        balance_text = "余额：—" if balance is None else f"余额：{_fmt_money_balance(balance)}"

        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(Text(balance_text, style="bold"), Text(f"ver: {__version__}", style="dim"))

        host.update(Group(header, _quota_overview_line(f"{label}  ", pct, width=width)))

    def _render_details_by_model(self, data: dict[str, Any]) -> None:
        """渲染“详细统计数据”（按模型汇总表格，含合计行）。"""

        host = self.query_one("#details_by_model", Static)
        adv_payload = data.get("advanced_trend") if isinstance(data.get("advanced_trend"), dict) else {}
        rows = extract_model_usage_rows(adv_payload)

        stats_payload = data.get("stats") if isinstance(data.get("stats"), dict) else {}
        totals = extract_stats_totals(stats_payload)

        if not rows and totals.requests is None and totals.tokens is None and totals.cost is None:
            host.update("详细统计数据：—")
            return

        table = Table(
            box=box.SQUARE,
            show_edge=True,
            pad_edge=True,
            expand=True,
            padding=(0, 2),
            show_lines=False,
            header_style="bold",
        )
        table.add_column("模型", no_wrap=True)
        table.add_column("请求数", justify="right", no_wrap=True)
        table.add_column("Tokens", justify="right", no_wrap=True)
        table.add_column("费用", justify="right", no_wrap=True)
        table.add_column("占比", justify="right", no_wrap=True)

        for r in rows[:12]:
            req = "—" if r.requests is None else f"{int(r.requests):,}"
            tok = "—" if r.tokens is None else f"{int(r.tokens):,}"
            cost = _fmt_cost_full_or_dash(r.cost)
            share = "—" if r.share is None else f"{float(r.share) * 100.0:.1f}%"
            table.add_row(r.model, req, tok, cost, share)

        table.add_row(
            "合计",
            _fmt_int_or_dash(totals.requests),
            _fmt_int_or_dash(totals.tokens),
            _fmt_cost_full_or_dash(totals.cost),
            "100%",
        )

        host.update(Group(Align.center(Text("详细统计数据", style="bold")), table))

    def _render_use_logs(self, data: dict[str, Any]) -> None:
        """渲染“使用记录明细”（来自 /use-log/list；支持翻页）。"""

        host = self.query_one("#use_logs", Static)
        payload = data.get("use_logs") if isinstance(data.get("use_logs"), dict) else {}
        if isinstance(payload.get("total"), int):
            self._use_logs_total = int(payload["total"])
        if isinstance(payload.get("page"), int):
            self._use_logs_page = int(payload["page"])
        if isinstance(payload.get("page_size"), int):
            self._use_logs_page_size = int(payload["page_size"])

        items = extract_use_logs_items(payload)

        if not items:
            host.update("使用记录明细：—")
            return

        table = Table(
            box=box.SQUARE,
            show_edge=True,
            pad_edge=True,
            expand=True,
            padding=(0, 1),
            show_lines=False,
            header_style="bold",
        )
        table.add_column("时间", no_wrap=True)
        table.add_column("密钥", no_wrap=True)
        table.add_column("模型", no_wrap=True)
        table.add_column("渠道", no_wrap=True)
        table.add_column("Tokens", justify="right", no_wrap=True)
        table.add_column("计费倍率", justify="right", no_wrap=True)
        table.add_column("扣费来源", no_wrap=True)
        table.add_column("费用", justify="right", no_wrap=True)
        table.add_column("IP", no_wrap=True)

        for item in items[:18]:
            if not isinstance(item, dict):
                continue

            time_val = _first_str(item, ("time", "ts", "timestamp", "date", "request_time", "created_at")) or "—"
            key_raw = _first_str(item, ("api_key_name", "key_name", "api_key", "key", "key_id")) or "—"
            model = _first_str(item, ("model", "model_name", "model_id")) or "—"
            channel = extract_use_log_channel(item) or "—"

            tokens_val = extract_use_log_tokens(item)
            tokens_text = "—" if tokens_val is None else f"{int(tokens_val):,}"

            rate_val = extract_use_log_billing_rate(item)
            mult_text = format_billing_rate(rate_val)

            bill_from_raw = extract_use_log_billing_source(item)
            bill_from = format_billing_source(bill_from_raw)

            cost_val = _first_number(item, ("cost", "total_cost", "amount", "charged", "fee"))
            ip_raw = extract_use_log_ip(item) or "—"

            table.add_row(
                time_val,
                _mask_key(key_raw),
                model,
                channel,
                tokens_text,
                mult_text,
                bill_from,
                _fmt_cost_full_or_dash(cost_val),
                ip_raw,
            )

        max_page = self._get_use_logs_max_page()
        page_note = f"第 {self._use_logs_page} 页" if self._use_logs_page else "—"
        if max_page is not None:
            page_note = f"{page_note} / 共 {max_page} 页"
        hint = Text(f"翻页：p 上一页 / n 下一页    {page_note}", style="dim")

        host.update(Group(Align.center(Text("使用记录明细", style="bold")), table, Align.right(hint)))

    def _render_trend(self, data: dict[str, Any]) -> None:
        """渲染 tokens 趋势（sparkline）。"""

        adv_payload = data.get("advanced_trend") if isinstance(data.get("advanced_trend"), dict) else {}
        buckets = extract_advanced_buckets(adv_payload) or []

        series: list[float] = []
        for b in buckets:
            t = b.get("tokens")
            if isinstance(t, (int, float)) and not isinstance(t, bool):
                series.append(float(t))
                continue
            tt = b.get("total_tokens")
            if isinstance(tt, (int, float)) and not isinstance(tt, bool):
                series.append(float(tt))

        self.query_one("#trend_tokens", Sparkline).data = series[-120:]

    def _format_burn_line(self, burn: BurnRate | None) -> str:
        tph = "—" if not burn or burn.tokens_per_hour is None else f"{burn.tokens_per_hour:.2f}"
        cpd = "—" if not burn or burn.cost_per_day is None else f"{burn.cost_per_day:.4f}"
        return f"Burn: tokens/hour {tph}  cost/day {cpd}"

    def _update_eta_targets(self, *, quota_remaining: float | None, burn: BurnRate | None, now: dt.datetime) -> None:
        """基于 burn + quota 剩余，计算 ETA 与“剩余 tokens 估算”（尽量酷但不误导）。"""

        self._eta_target = None
        self._eta_remaining_tokens_est = None
        self._eta_mode = None

        if quota_remaining is None:
            return
        if not burn:
            return

        cost_per_hour = None
        if burn.cost_per_day is not None:
            cost_per_hour = burn.cost_per_day / 24.0
        if cost_per_hour is None or cost_per_hour <= 0:
            return

        eta_cost = estimate_eta(remaining=quota_remaining, burn_tokens_per_hour=cost_per_hour, now=now)
        if not eta_cost:
            return

        self._eta_target = eta_cost
        self._eta_mode = "cost"

        if burn.tokens_per_hour is None or burn.tokens_per_hour <= 0:
            return
        cost_per_token = cost_per_hour / burn.tokens_per_hour
        if cost_per_token <= 0:
            return
        self._eta_remaining_tokens_est = quota_remaining / cost_per_token

    def _format_eta_time(self) -> str:
        if not self._eta_target:
            return "—"
        return self._eta_target.isoformat(sep=" ", timespec="minutes")

    def _format_eta_countdown(self, now: dt.datetime) -> str:
        if not self._eta_target:
            return "—"
        delta = self._eta_target - now
        seconds = int(delta.total_seconds())
        if seconds <= 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 99:
            return f"{h}h"
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _format_burn_eta_block(self, now: dt.datetime) -> Any:
        burn = self._burn_cached

        tph = "—" if not burn or burn.tokens_per_hour is None else f"{burn.tokens_per_hour:,.0f} tokens/h"
        cph = "—"
        if burn and burn.cost_per_day is not None:
            cph = f"{(burn.cost_per_day / 24.0):.4f}/h"
        eta = self._format_eta_time()
        countdown = self._format_eta_countdown(now)
        remaining_tokens_est = "—" if self._eta_remaining_tokens_est is None else f"{self._eta_remaining_tokens_est:,.0f}"

        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(
            Text(f"Burn: {tph}   成本速率: {cph}"),
            Text("github: okwinds/rightcodes-tui-dashboard", style="dim"),
        )

        body_lines = [
            f"ETA: {eta}  (倒计时 {countdown})",
            f"≈ 剩余 Token（按近窗口均价估算）: {remaining_tokens_est}",
            "right.codes 邀请码：4d98a8ea  加返5%",
        ]
        body = Text("\n".join(body_lines))
        last = body_lines[-1]
        start = body.plain.rfind(last)
        if start >= 0:
            body.stylize("dim", start, start + len(last))
        return Group(header, body)

    def _update_burn_eta_live(self) -> None:
        """每秒更新倒计时（不触发任何网络请求）。"""

        if not self._watch_seconds:
            return
        self.query_one("#burn_eta", Static).update(self._format_burn_eta_block(dt.datetime.now()))

    def _enter_backoff(self, err: RateLimitError) -> None:
        attempt = self._backoff.attempt + 1
        next_retry = err.next_retry_at
        if next_retry is None:
            next_retry = compute_next_retry_at(
                now=dt.datetime.now(),
                attempt=attempt,
                base_delay_seconds=5,
                max_delay_seconds=300,
            )
        self._backoff = BackoffState(attempt=attempt, next_retry_at=next_retry)

    def _set_banner(self, text: str, *, kind: str) -> None:
        banner = self.query_one("#banner", Static)
        if not text:
            banner.update("")
            return
        prefix = {"error": "[ERROR] ", "warn": "[WARN] ", "info": ""}.get(kind, "")
        banner.update(prefix + text)

    def _update_status(self) -> None:
        now = dt.datetime.now()
        last_ok = self._last_ok_at.isoformat(sep=" ", timespec="seconds") if self._last_ok_at else "—"
        next_refresh = self._next_refresh_at.isoformat(sep=" ", timespec="seconds") if self._next_refresh_at else "—"
        backoff = "—"
        if self._backoff.next_retry_at:
            backoff = f"attempt={self._backoff.attempt} next={self._backoff.next_retry_at.isoformat(sep=' ', timespec='seconds')}"
        stale = "no"
        if self._stale_since:
            delta = now - self._stale_since
            stale = f"yes ({int(delta.total_seconds())}s)"
        degraded = "—" if not self._degraded_reason else self._degraded_reason
        range_mode = self._range_mode
        self.query_one("#status", Static).update(
            f"Last OK: {last_ok} | Next refresh: {next_refresh} | Backoff: {backoff} | Stale: {stale} | Degraded: {degraded} | Range: {range_mode}"
        )


class LogsScreen(Screen):
    """Logs 明细屏（MVP：/use-log/list 的安全摘要）。"""

    BINDINGS = [("q", "pop", "Back"), ("escape", "pop", "Back"), ("r", "refresh", "Refresh")]

    def __init__(self, *, base_url: str, token: str | None, range_seconds: int) -> None:
        super().__init__()
        self._base_url = base_url
        self._token = token
        self._range_seconds = range_seconds
        self._cached: list[dict[str, Any]] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="logs_banner")
            yield DataTable(id="logs_table")

    def on_mount(self) -> None:
        table = self.query_one("#logs_table", DataTable)
        table.add_columns("time", "tokens", "cost", "summary")
        table.zebra_stripes = True
        self._kick_refresh()

    def action_pop(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self._kick_refresh()

    def _kick_refresh(self) -> None:
        asyncio.create_task(self._refresh_once())

    async def _refresh_once(self) -> None:
        if not self._token:
            self.query_one("#logs_banner", Static).update("未登录：请先执行 `rightcodes login`。")
            self._render_view([])
            return

        try:
            items = await asyncio.to_thread(self._fetch_logs)
        except AuthError:
            self.query_one("#logs_banner", Static).update("认证失败（token 可能已过期）：请执行 `rightcodes login`。")
            self._render_view(self._cached or [])
            return
        except RateLimitError as e:
            retry_at = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else "unknown"
            self.query_one("#logs_banner", Static).update(f"触发限流（429），请稍后重试。Next retry: {retry_at}")
            self._render_view(self._cached or [])
            return
        except ApiError as e:
            self.query_one("#logs_banner", Static).update(f"刷新失败：{e}")
            self._render_view(self._cached or [])
            return
        except Exception as e:
            self.query_one("#logs_banner", Static).update(f"刷新失败：{e.__class__.__name__}")
            self._render_view(self._cached or [])
            return

        self.query_one("#logs_banner", Static).update("")
        self._cached = items
        try:
            self._render_view(items)
        except Exception as e:
            self.query_one("#logs_banner", Static).update(f"渲染失败：{e.__class__.__name__}")
            self._render_view(self._cached or [])

    def _fetch_logs(self) -> list[dict[str, Any]]:
        now = dt.datetime.now()
        start = (now - dt.timedelta(seconds=self._range_seconds)).strftime("%Y-%m-%dT%H:%M:%S")
        end = now.strftime("%Y-%m-%dT%H:%M:%S")

        with RightCodesApiClient(base_url=self._base_url, token=self._token) as client:
            payload = client.use_logs_list(page=1, page_size=50, start_date=start, end_date=end)
            return extract_use_logs_items(payload)

    def _render_view(self, items: list[dict[str, Any]]) -> None:
        """将 logs 列表渲染到表格视图。

        注意：不要命名为 `_render`，以避免覆盖 Textual 内部渲染方法。
        """

        table = self.query_one("#logs_table", DataTable)
        table.clear()
        for item in items:
            safe = redact_sensitive_fields(item)
            time_val = _first_str(safe, ("time", "ts", "timestamp", "date", "request_time", "created_at")) or "—"
            tokens_val = extract_use_log_tokens(safe)
            tokens = "—" if tokens_val is None else f"{int(tokens_val):,}"
            cost = _first_number_str(safe, ("cost", "total_cost", "amount")) or "—"

            summary = safe.copy()
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
            summary_text = _json_compact(summary, max_len=96)
            table.add_row(time_val, tokens, cost, summary_text)


class DoctorScreen(Screen):
    """Doctor summary 屏（仅展示 keys，不展示值）。"""

    BINDINGS = [("q", "pop", "Back"), ("escape", "pop", "Back"), ("r", "refresh", "Refresh")]

    def __init__(self, *, base_url: str, token: str | None) -> None:
        super().__init__()
        self._base_url = base_url
        self._token = token

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="doctor_banner")
            yield DataTable(id="doctor_table")

    def on_mount(self) -> None:
        table = self.query_one("#doctor_table", DataTable)
        table.add_columns("endpoint", "ok", "keys")
        table.zebra_stripes = True
        self._kick_refresh()

    def action_pop(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self._kick_refresh()

    def _kick_refresh(self) -> None:
        asyncio.create_task(self._refresh_once())

    async def _refresh_once(self) -> None:
        if not self._token:
            self.query_one("#doctor_banner", Static).update("未登录：请先执行 `rightcodes login`。")
            self._render_view({})
            return

        try:
            summary = await asyncio.to_thread(self._fetch_doctor)
        except AuthError:
            self.query_one("#doctor_banner", Static).update("认证失败（token 可能已过期）：请执行 `rightcodes login`。")
            self._render_view({})
            return
        except RateLimitError as e:
            retry_at = e.next_retry_at.isoformat(sep=" ", timespec="seconds") if e.next_retry_at else "unknown"
            self.query_one("#doctor_banner", Static).update(f"触发限流（429），请稍后重试。Next retry: {retry_at}")
            self._render_view({})
            return
        except ApiError as e:
            self.query_one("#doctor_banner", Static).update(f"刷新失败：{e}")
            self._render_view({})
            return

        self.query_one("#doctor_banner", Static).update("")
        self._render_view(summary)

    def _fetch_doctor(self) -> dict[str, Any]:
        with RightCodesApiClient(base_url=self._base_url, token=self._token) as client:
            out: dict[str, Any] = {}
            out["GET /auth/me"] = client.get_me()
            out["GET /subscriptions/list"] = client.list_subscriptions()
            out["GET /use-log/stats/overall"] = client.stats_overall()
            return out

    def _render_view(self, summary: dict[str, Any]) -> None:
        """将 doctor summary 渲染为表格（仅 keys）。"""

        table = self.query_one("#doctor_table", DataTable)
        table.clear()
        for endpoint, payload in summary.items():
            keys = sorted(list(payload.keys())) if isinstance(payload, dict) else []
            table.add_row(str(endpoint), "yes", ", ".join(keys))


class HelpScreen(Screen):
    """帮助屏：快捷键与口径摘要。"""

    BINDINGS = [("q", "pop", "Back"), ("escape", "pop", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            "\\n".join(
                [
                    "快捷键：",
                    "- q：退出/返回",
                    "- r：刷新（退避期间不会强制请求）",
                    "- l：Logs 明细",
                    "- d：Doctor（仅 keys）",
                    "- p / n：使用记录明细翻页（上一页/下一页）",
                    "- ?：帮助",
                    "",
                    "口径（MVP）：",
                    "- 套餐时间字段：优先将 `created_at/obtained_at` 作为“获得时间”；将 `expired_at` 作为“到期时间”（仅展示，不用于过滤）",
                    "- Quota 汇总：按接口返回值直接汇总 total/remaining/used（不引入运营规则推导）",
                    "- Burn rate：基于 rate-window 的 advanced buckets，计算 tokens/hour 与成本速率（$/h）",
                    "- ETA：优先按“剩余额度 ÷ $/h”估算；并给出“剩余 Token（按近窗口均价估算）”作为辅助参考",
                ]
            )
        )

    def action_pop(self) -> None:
        self.app.pop_screen()


class RightCodesDashboardApp(App):
    """Textual App 包装。"""

    CSS = """
    DashboardScreen { padding: 0; }
    #banner { height: 2; padding: 0 1; }
    #quota_overview { height: 2; padding: 0 1; }
    #body_scroll { height: 1fr; padding: 0 1; }
    #trend_tokens { height: 3; }
    #status { height: 1; dock: bottom; }
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        watch_seconds: int | None,
        range_seconds: int,
        range_mode: str,
        rate_window_seconds: int,
        granularity: str,
    ) -> None:
        super().__init__()
        self._base_url = base_url
        self._token = token
        self._watch_seconds = watch_seconds
        self._range_seconds = range_seconds
        self._range_mode = range_mode
        self._rate_window_seconds = rate_window_seconds
        self._granularity = granularity

    def on_mount(self) -> None:
        self.push_screen(
            DashboardScreen(
                base_url=self._base_url,
                token=self._token,
                watch_seconds=self._watch_seconds,
                range_seconds=self._range_seconds,
                range_mode=self._range_mode,
                rate_window_seconds=self._rate_window_seconds,
                granularity=self._granularity,
            )
        )


def _json_compact(obj: dict[str, Any], *, max_len: int) -> str:
    """将 dict 压缩为单行 JSON，并做长度截断（用于 logs 摘要）。"""

    import json

    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


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


def _first_number(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """从 payload 中按 keys 顺序取第一个 number（float/int），返回 float。"""

    for k in keys:
        v = payload.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _truncate_plain(text: str, max_len: int) -> str:
    """截断纯文本（不考虑 ANSI/宽字符），用于保证进度条单行排版稳定。"""

    if max_len <= 0:
        return ""
    if len(text) <= max_len:
        return text
    if max_len == 1:
        return "…"
    return text[: max_len - 1] + "…"


def _quota_overview_line(left_label: str, pct: float | None, *, width: int) -> Text:
    """渲染单行总览进度条：left label + bar + %。"""

    w = max(1, int(width))
    right = "—" if pct is None else f"{float(pct) * 100.0:.0f}%"

    min_bar = 1
    reserved = len(right) + 1 + min_bar
    left_max = max(0, w - reserved)
    left = _truncate_plain(left_label, left_max)

    bar_width = max(min_bar, w - len(left) - len(right) - 1)
    bar = _bar_text(pct, width=bar_width, dim=(pct is None))

    t = Text()
    t.append(left, style="bold")
    t.append_text(bar)
    t.append(" ")
    t.append(right, style="bold")
    return t


def _mask_key(value: str) -> str:
    """对 key/name 做部分打码展示（避免完整暴露）。"""

    raw = value.strip()
    if raw in ("", "—"):
        return "—"
    if raw == "***REDACTED***":
        return raw
    if len(raw) <= 6:
        return raw[0] + "…" if len(raw) > 1 else "…"
    return f"{raw[:2]}…{raw[-4:]}"


def _mask_ip(value: str) -> str:
    """对 IP 做部分打码展示。"""

    raw = value.strip()
    if raw in ("", "—"):
        return "—"
    if raw == "***REDACTED***":
        return raw
    # IPv4
    if "." in raw:
        parts = raw.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.***"
    # 兜底：只展示前后各 2 位
    if len(raw) <= 4:
        return "***"
    return f"{raw[:2]}…{raw[-2:]}"


def _fmt_time(value: dt.datetime | None, raw: str | None) -> str:
    """格式化时间字段（获得/到期时间）。"""

    if value is not None:
        return value.isoformat(sep=" ", timespec="minutes")
    if raw and raw.strip():
        return raw.strip()
    return "—"


def _fmt_money(value: float) -> str:
    """格式化“额度”显示（仿照网页：整数不带小数，非整数保留 5 位）。"""

    num = float(value)
    if abs(num - round(num)) < 1e-9:
        return f"${int(round(num)):,}"
    return f"${num:,.5f}"


def _fmt_money_balance(value: float) -> str:
    """格式化顶部“余额”显示（尽量不吞尾数，便于人工核对字段是否正确）。"""

    num = float(value)
    # 余额通常较小且带小数；这里保留更多位并去掉多余 0。
    text = f"{num:,.8f}"
    text = text.rstrip("0").rstrip(".")
    return f"${text}"


def _fmt_cost_or_dash(value: float | None) -> str:
    """格式化 cost（仿照网页：两位小数）。"""

    if value is None:
        return "—"
    return f"${float(value):,.2f}"


def _fmt_cost_full_or_dash(value: float | None) -> str:
    """格式化 cost（尽量保留完整小数位；当前固定 6 位以对齐网页样式）。"""

    if value is None:
        return "—"
    return f"${float(value):.6f}"


def _fmt_int_or_dash(value: float | None) -> str:
    """格式化 requests/tokens（完整位数 + 逗号）。"""

    if value is None:
        return "—"
    return f"{int(value):,}"


def _fmt_pct_short(value: float | None) -> str:
    """短百分比（用于卡片指标）。"""

    if value is None:
        return "—"
    return f"{float(value) * 100.0:.0f}%"


def _reset_today_label(value: bool | None) -> str:
    if value is True:
        return "已重置"
    if value is False:
        return "未重置"
    return "—"


def _bar_text(pct: float | None, *, width: int, dim: bool) -> Text:
    """渲染一个字符进度条（用于套餐包消耗进度）。"""

    if pct is None:
        return Text("░" * width, style="dim" if dim else "")

    clamped = min(1.0, max(0.0, float(pct)))
    filled = int(round(clamped * width))
    filled = min(width, max(0, filled))
    empty = width - filled

    if clamped >= 0.9:
        style = "red"
    elif clamped >= 0.6:
        style = "yellow"
    else:
        style = "green"

    t = Text()
    t.append("█" * filled, style=style)
    t.append("░" * empty, style="dim" if dim else "bright_black")
    return t


def _wide_bar(pct: float | None, *, width: int, height: int) -> Text:
    """渲染“更粗”的总览进度条（多行）。"""

    w = max(1, int(width))
    h = max(1, int(height))

    if pct is None:
        line_text = Text("░" * w, style="dim")
        out = Text()
        for i in range(h):
            if i:
                out.append("\n")
            out.append_text(line_text)
        return out

    clamped = min(1.0, max(0.0, float(pct)))
    filled = int(round(clamped * w))
    filled = min(w, max(0, filled))
    empty = w - filled

    if clamped >= 0.9:
        fill_style = "red"
    elif clamped >= 0.6:
        fill_style = "yellow"
    else:
        fill_style = "green"

    out = Text()
    for i in range(h):
        if i:
            out.append("\n")
        if filled:
            out.append("█" * filled, style=fill_style)
        if empty:
            out.append("░" * empty, style="bright_black")
    return out
