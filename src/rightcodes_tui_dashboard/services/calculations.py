from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class NormalizedSubscription:
    """归一化后的 subscription（字段缺失允许）。"""

    tier_id: str
    total_quota: float | None
    remaining_quota: float | None
    reset_today: bool | None
    obtained_at_raw: str | None
    obtained_at: dt.datetime | None
    expires_at_raw: str | None
    expires_at: dt.datetime | None


@dataclass(frozen=True)
class EffectiveQuota:
    """单个套餐包的额度计算结果（用于 UI 展示与汇总口径对齐）。"""

    total_effective: float
    remaining_effective: float
    used_effective: float
    used_pct: float | None


@dataclass(frozen=True)
class QuotaSummary:
    """额度汇总结果。"""

    total_quota_sum: float | None
    remaining_sum: float | None
    used_sum: float | None
    degraded: bool
    degraded_reason: str | None


@dataclass(frozen=True)
class BurnRate:
    """速率计算结果。"""

    tokens_per_hour: float | None
    cost_per_day: float | None
    hours_in_window: float


@dataclass(frozen=True)
class StatsTotals:
    """stats totals（按字段变体提取，可缺失）。"""

    tokens: float | None
    cost: float | None
    requests: float | None


@dataclass(frozen=True)
class ModelUsageRow:
    """按模型汇总的使用数据（用于 UI 表格展示）。"""

    model: str
    requests: float | None
    tokens: float | None
    cost: float | None
    share: float | None
    share_basis: str | None


def normalize_subscriptions(raw_items: Iterable[dict[str, Any]], *, now: dt.datetime) -> list[NormalizedSubscription]:
    """将 subscriptions/list 的 items 归一化为可计算结构。

    Args:
        raw_items: 原始 subscriptions 数组。
        now: 当前时间（本地时间；预留给未来的时间相关规则，MVP 目前不依赖）。

    Returns:
        归一化结果列表。
    """

    normalized: list[NormalizedSubscription] = []
    for item in raw_items:
        tier_id_val = item.get("tier_id")
        tier_id = str(tier_id_val) if tier_id_val is not None else "—"

        total_quota = _to_float_or_none(item.get("total_quota"))
        remaining_quota = _to_float_or_none(item.get("remaining_quota"))
        reset_today = item.get("reset_today") if isinstance(item.get("reset_today"), bool) else None

        # 说明：
        # - 网站面板同时展示“获得时间/到期时间”；但接口字段名与语义可能存在漂移。
        # - MVP 采取“尽力解析 + 清晰展示”的策略：能解析就展示；不用于过滤。
        obtained_at_raw = None
        for k in ("created_at", "obtained_at"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                obtained_at_raw = v.strip()
                break
        obtained_at = _safe_parse_datetime(obtained_at_raw) if obtained_at_raw else None

        expires_at_raw = None
        v = item.get("expired_at")
        if isinstance(v, str) and v.strip():
            expires_at_raw = v.strip()
        expires_at = _safe_parse_datetime(expires_at_raw) if expires_at_raw else None

        normalized.append(
            NormalizedSubscription(
                tier_id=tier_id,
                total_quota=total_quota,
                remaining_quota=remaining_quota,
                reset_today=reset_today,
                obtained_at_raw=obtained_at_raw,
                obtained_at=obtained_at,
                expires_at_raw=expires_at_raw,
                expires_at=expires_at,
            )
        )

    return normalized


def compute_effective_quota(item: NormalizedSubscription) -> EffectiveQuota | None:
    """计算单个套餐包的额度口径（与 summarize_quota 保持一致）。

    口径（按接口返回值直接展示，不引入运营规则推导）：
    - `total_quota`：该套餐包的总额度（网站面板展示的“正在消耗包”口径）
    - `remaining_quota`：该套餐包的剩余额度
    - `used = max(0, total_quota - remaining_quota)`
    - `used_pct = clamp(used / total_quota, 0..1)`（total<=0 时为 None）

    Args:
        item: 归一化后的套餐结构。

    Returns:
        EffectiveQuota；若 total/remaining 缺失则返回 None。
    """

    if item.total_quota is None or item.remaining_quota is None:
        return None

    total = float(item.total_quota)
    remaining = float(item.remaining_quota)

    total_effective = total
    remaining_effective = remaining
    used_effective = max(0.0, total_effective - remaining_effective)

    used_pct: float | None
    if total_effective <= 0:
        used_pct = None
    else:
        raw_pct = used_effective / total_effective
        used_pct = min(1.0, max(0.0, raw_pct))

    return EffectiveQuota(
        total_effective=total_effective,
        remaining_effective=remaining_effective,
        used_effective=used_effective,
        used_pct=used_pct,
    )


def summarize_quota(items: Iterable[NormalizedSubscription]) -> QuotaSummary:
    """按 spec 汇总 quota（按接口返回值直接汇总）。

    规则：
    - sum：只对 present 的数值累加；若完全无可用数值则返回 None。
    - used：按单包 `used = total - remaining` 累加（仅当 total/remaining 可计算时），否则 None。
    - 不基于 `expired_at` 做过滤；`reset_today` 仅用于展示，不参与汇总口径。
    """

    degraded = False
    reasons: list[str] = []

    total_sum = 0.0
    remaining_sum = 0.0
    used_sum = 0.0
    any_value = False

    for s in items:
        effective = compute_effective_quota(s)
        if effective is None:
            degraded = True
            reasons.append("部分 total_quota/remaining_quota 字段缺失")
            continue

        any_value = True

        total_sum += effective.total_effective
        remaining_sum += effective.remaining_effective
        used_sum += effective.used_effective

    if not any_value:
        total_sum_out = None
        remaining_sum_out = None
        used_sum_out = None
    else:
        total_sum_out = total_sum
        remaining_sum_out = remaining_sum
        used_sum_out = used_sum

    reason = "；".join(sorted(set(reasons))) if reasons else None
    return QuotaSummary(
        total_quota_sum=total_sum_out,
        remaining_sum=remaining_sum_out,
        used_sum=used_sum_out,
        degraded=degraded,
        degraded_reason=reason,
    )


def extract_advanced_buckets(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """从 /use-log/stats/advanced 响应中抽取 buckets（多 shape 兼容）。

    Args:
        payload: JSON object。

    Returns:
        buckets 列表；无法解析返回 None。
    """

    for key in ("data", "items", "series", "buckets", "trend"):
        candidate = payload.get(key)
        if isinstance(candidate, list) and all(isinstance(x, dict) for x in candidate):
            return list(candidate)
    return None


def calculate_burn_rate(
    buckets: list[dict[str, Any]] | None,
    *,
    window_seconds: int,
) -> BurnRate | None:
    """计算 burn rate（tokens/hour 与 cost/day）。

    Args:
        buckets: advanced buckets 列表；若 None/空则返回 None。
        window_seconds: 速率窗口秒数（例如 6h -> 21600）。

    Returns:
        BurnRate 或 None。
    """

    if not buckets:
        return None
    if window_seconds <= 0:
        return None

    hours = window_seconds / 3600.0
    if hours <= 0:
        return None

    tokens_sum = 0.0
    tokens_seen = False
    cost_sum = 0.0
    cost_seen = False

    for b in buckets:
        t = _first_number(b, ("tokens", "total_tokens", "token_count"))
        if t is not None:
            tokens_sum += t
            tokens_seen = True

        c = _first_number(b, ("cost", "total_cost", "amount"))
        if c is not None:
            cost_sum += c
            cost_seen = True

    tokens_per_hour = (tokens_sum / hours) if tokens_seen else None
    cost_per_day = ((cost_sum / hours) * 24.0) if cost_seen else None
    return BurnRate(tokens_per_hour=tokens_per_hour, cost_per_day=cost_per_day, hours_in_window=hours)


def extract_stats_totals(payload: dict[str, Any]) -> StatsTotals:
    """从 stats 响应中提取 tokens/cost/requests（多字段变体兼容）。

    Args:
        payload: JSON object。

    Returns:
        StatsTotals：任意字段可能为 None（上层按“可用即展示”）。
    """

    tokens = _first_number(payload, ("total_tokens", "tokens", "token_count"))
    cost = _first_number(payload, ("total_cost", "cost", "amount"))
    requests = _first_number(payload, ("total_requests", "requests", "request_count", "request_count_total"))
    return StatsTotals(tokens=tokens, cost=cost, requests=requests)


def extract_model_usage_rows(payload: dict[str, Any]) -> list[ModelUsageRow]:
    """从 /use-log/stats/advanced 响应中提取按模型聚合的使用数据。

    Args:
        payload: advanced 响应 JSON object（允许字段缺失/变体）。

    Returns:
        ModelUsageRow 列表（已按 cost/tokens 降序排序，并填充 share%）。
    """

    rows: list[ModelUsageRow] = []

    details = payload.get("details_by_model")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            model = (
                str(item.get("model"))
                if item.get("model") is not None
                else str(item.get("name"))
                if item.get("name") is not None
                else str(item.get("model_name"))
                if item.get("model_name") is not None
                else "—"
            )
            rows.append(
                ModelUsageRow(
                    model=model,
                    requests=_first_number(item, ("requests", "total_requests", "request_count", "request_count_total")),
                    tokens=_first_number(item, ("tokens", "total_tokens", "token_count")),
                    cost=_first_number(item, ("cost", "total_cost", "amount")),
                    share=None,
                    share_basis=None,
                )
            )

    if not rows:
        tokens_by_model = payload.get("tokens_by_model")
        if isinstance(tokens_by_model, dict):
            for k, v in tokens_by_model.items():
                if isinstance(v, bool):
                    continue
                if not isinstance(v, (int, float)):
                    continue
                rows.append(
                    ModelUsageRow(
                        model=str(k),
                        requests=None,
                        tokens=float(v),
                        cost=None,
                        share=None,
                        share_basis=None,
                    )
                )

    cost_total = 0.0
    cost_seen = False
    tokens_total = 0.0
    tokens_seen = False
    for r in rows:
        if r.cost is not None:
            cost_total += float(r.cost)
            cost_seen = True
        if r.tokens is not None:
            tokens_total += float(r.tokens)
            tokens_seen = True

    share_basis: str | None = None
    if cost_seen and cost_total > 0:
        share_basis = "cost"
    elif tokens_seen and tokens_total > 0:
        share_basis = "tokens"

    finalized: list[ModelUsageRow] = []
    for r in rows:
        share: float | None = None
        if share_basis == "cost" and r.cost is not None:
            share = float(r.cost) / cost_total
        if share_basis == "tokens" and r.tokens is not None:
            share = float(r.tokens) / tokens_total
        finalized.append(
            ModelUsageRow(
                model=r.model,
                requests=r.requests,
                tokens=r.tokens,
                cost=r.cost,
                share=share,
                share_basis=share_basis,
            )
        )

    def _sort_key(r: ModelUsageRow) -> tuple[float, float, str]:
        cost = 0.0 if r.cost is None else float(r.cost)
        tokens = 0.0 if r.tokens is None else float(r.tokens)
        return (cost, tokens, r.model)

    finalized.sort(key=_sort_key, reverse=True)
    return finalized


def extract_use_logs_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """从 /use-log/list 响应中抽取 items（多 shape 兼容）。

    Args:
        payload: JSON object。

    Returns:
        items 列表；无法解析返回空列表。
    """

    for key in ("items", "logs", "data"):
        candidate = payload.get(key)
        if isinstance(candidate, list) and all(isinstance(x, dict) for x in candidate):
            return list(candidate)
    return []


def estimate_eta(
    *,
    remaining: float | None,
    burn_tokens_per_hour: float | None,
    now: dt.datetime,
) -> dt.datetime | None:
    """根据 remaining 与 burn rate 估算 ETA（remaining / burn）。"""

    if remaining is None:
        return None
    if burn_tokens_per_hour is None:
        return None
    if burn_tokens_per_hour <= 0:
        return None
    hours = remaining / burn_tokens_per_hour
    if hours <= 0:
        return None
    return now + dt.timedelta(hours=hours)


def _safe_parse_datetime(value: str) -> dt.datetime | None:
    text = value.strip()
    try:
        # 兼容常见 ISO-like：YYYY-MM-DDTHH:MM:SS[.fff][Z/offset]
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_number(obj: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
    return None
