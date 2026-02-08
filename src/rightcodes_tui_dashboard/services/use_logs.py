from __future__ import annotations

from typing import Any


def _get_nested(obj: dict[str, Any], path: tuple[str, ...]) -> Any:
    """安全读取嵌套字段。

    Args:
        obj: 输入 dict。
        path: 字段路径（例如 ("usage", "total_tokens")）。

    Returns:
        任意值；路径不存在返回 None。
    """

    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _parse_number(value: Any) -> float | None:
    """将 number-like 值解析为 float（兼容 str/int/float）。

    - 支持 "123" / "123.45" / "1,234" 这类字符串
    - bool 视为无效
    """

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def extract_use_log_tokens(item: dict[str, Any]) -> float | None:
    """抽取单条 use-log 的 tokens 数（优先 usage.total_tokens）。"""

    usage = item.get("usage")
    if isinstance(usage, dict):
        tokens = _parse_number(usage.get("total_tokens"))
        if tokens is not None:
            return tokens
        for k in ("tokens", "token_count", "usage_tokens", "totalTokens"):
            tokens = _parse_number(usage.get(k))
            if tokens is not None:
                return tokens

    for k in ("total_tokens", "tokens", "token_count", "usage_tokens"):
        tokens = _parse_number(item.get(k))
        if tokens is not None:
            return tokens

    nested = _parse_number(_get_nested(item, ("usage", "total_tokens")))
    return nested


def extract_use_log_channel(item: dict[str, Any]) -> str | None:
    """抽取“渠道”展示字段（优先 upstream_prefix，其次 channel/source/type）。"""

    for k in ("upstream_prefix", "channel", "source", "provider", "app", "type", "path", "route"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def extract_use_log_billing_rate(item: dict[str, Any]) -> float | None:
    """抽取计费倍率（优先 billing_rate）。"""

    for k in ("billing_rate", "billing_multiplier", "rate_multiplier", "multiplier", "ratio"):
        n = _parse_number(item.get(k))
        if n is not None:
            return n
    return None


def format_billing_rate(rate: float | None) -> str:
    """格式化计费倍率展示（仿网页：x1.00）。"""

    if rate is None:
        return "—"
    return f"x{float(rate):.2f}"


def extract_use_log_billing_source(item: dict[str, Any]) -> str | None:
    """抽取扣费来源字段。"""

    for k in ("billing_source", "deduct_source", "quota_source", "deduct_from", "balance_type", "note"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def format_billing_source(value: str | None) -> str:
    """将扣费来源字段转换为更友好的中文标签。"""

    if not value:
        return "—"
    text = value.strip()
    low = text.lower()
    if low == "subscription":
        return "套餐"
    if low in ("balance", "wallet"):
        return "余额"
    return text


def extract_use_log_ip(item: dict[str, Any]) -> str | None:
    """抽取 IP（个人工具：用于本地展示，不做掩码）。"""

    for k in ("ip", "client_ip", "ip_address"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

