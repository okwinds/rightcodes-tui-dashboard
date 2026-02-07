from __future__ import annotations

from typing import Any


_SENSITIVE_KEYS = {
    # auth
    "authorization",
    "token",
    "user_token",
    "usertoken",
    # password
    "password",
    # network identifiers
    "ip",
    "ip_address",
    "client_ip",
    # key identifiers
    "api_key",
    "api_key_name",
    "key_name",
}


def redact_sensitive_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """对 payload 做默认脱敏（按 key 黑名单，大小写不敏感）。

    Args:
        payload: 输入 dict。

    Returns:
        复制后的 dict：敏感字段值替换为 `***REDACTED***`。
    """

    out: dict[str, Any] = {}
    for k, v in payload.items():
        if str(k).lower() in _SENSITIVE_KEYS:
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out

