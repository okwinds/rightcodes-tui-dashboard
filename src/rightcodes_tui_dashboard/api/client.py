from __future__ import annotations

import datetime as dt
import email.utils
from typing import Any

import httpx

from rightcodes_tui_dashboard.errors import ApiError, AuthError, RateLimitError


def extract_user_token(payload: dict[str, Any]) -> str | None:
    """从登录响应中提取 token（兼容 user_token/userToken 变体）。

    Args:
        payload: JSON object。

    Returns:
        token 字符串；若缺失返回 None。
    """

    token = payload.get("user_token")
    if isinstance(token, str) and token.strip():
        return token
    token2 = payload.get("userToken")
    if isinstance(token2, str) and token2.strip():
        return token2
    return None


class RightCodesApiClient:
    """Right.codes HTTP API 客户端（MVP）。

    设计约束：
    - 自动注入 Authorization（若 token 存在）
    - 401/403/429 做错误映射；其它非 2xx 统一 ApiError
    - JSON 解析失败不崩溃：返回空 dict 以便上层降级展示
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        timeout: float = 15.0,
        trust_env: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
            trust_env=trust_env,
        )

    def set_token(self, token: str | None) -> None:
        """更新客户端 token（用于 login 后复用同一实例）。"""

        self._token = token

    def close(self) -> None:
        """关闭底层 httpx client。"""

        self._client.close()

    def __enter__(self) -> "RightCodesApiClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def login(self, *, username: str, password: str) -> str:
        """POST /auth/login 并返回 token。

        Raises:
            AuthError: 认证失败（401/403）。
            RateLimitError: 触发限流（429）。
            ApiError: 其它错误或 token 缺失。
        """

        payload = self._request_json("POST", "/auth/login", json={"username": username, "password": password})
        if not isinstance(payload, dict):
            raise ApiError("登录响应不是 JSON object")
        token = extract_user_token(payload)
        if not token:
            raise ApiError("登录成功但响应缺少 token 字段（user_token/userToken）")
        self._token = token
        return token

    def get_me(self) -> dict[str, Any]:
        """GET /auth/me（用于 token 有效性探测）。"""

        data = self._request_json("GET", "/auth/me")
        return data if isinstance(data, dict) else {}

    def list_subscriptions(self) -> dict[str, Any]:
        """GET /subscriptions/list。"""

        data = self._request_json("GET", "/subscriptions/list")
        return data if isinstance(data, dict) else {}

    def stats_overall(self) -> dict[str, Any]:
        """GET /use-log/stats/overall。"""

        data = self._request_json("GET", "/use-log/stats/overall")
        return data if isinstance(data, dict) else {}

    def stats_range(self, *, start_date: str, end_date: str) -> dict[str, Any]:
        """GET /use-log/stats（range）。"""

        data = self._request_json("GET", "/use-log/stats", params={"start_date": start_date, "end_date": end_date})
        return data if isinstance(data, dict) else {}

    def stats_advanced(
        self,
        *,
        start_date: str,
        end_date: str,
        granularity: str,
    ) -> dict[str, Any]:
        """GET /use-log/stats/advanced。"""

        data = self._request_json(
            "GET",
            "/use-log/stats/advanced",
            params={"start_date": start_date, "end_date": end_date, "granularity": granularity},
        )
        return data if isinstance(data, dict) else {}

    def use_logs_list(
        self,
        *,
        page: int,
        page_size: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """GET /use-log/list。"""

        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        data = self._request_json("GET", "/use-log/list", params=params)
        return data if isinstance(data, dict) else {}

    def _request_json(self, method: str, url: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            resp = self._client.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as e:
            raise ApiError(f"网络错误：{e.__class__.__name__}") from e

        if resp.status_code in (401, 403):
            raise AuthError("认证失败（token 可能已过期）。请执行 `rightcodes login` 重新登录。")
        if resp.status_code == 429:
            retry_after_seconds, next_retry_at = _parse_retry_after(resp.headers)
            raise RateLimitError(
                "触发限流（429）。已进入退避，请稍后重试。",
                retry_after_seconds=retry_after_seconds,
                next_retry_at=next_retry_at,
            )
        if resp.status_code < 200 or resp.status_code >= 300:
            raise ApiError(f"API 错误（HTTP {resp.status_code}）。")

        if not resp.content:
            return {}

        try:
            return resp.json()
        except ValueError:
            return {}


def _parse_retry_after(headers: httpx.Headers) -> tuple[int | None, dt.datetime | None]:
    """解析 Retry-After 头部（秒数或 HTTP-date）。"""

    raw = headers.get("Retry-After")
    if not raw:
        return None, None

    raw = raw.strip()
    if not raw:
        return None, None

    now = dt.datetime.now()
    try:
        seconds = int(raw)
        if seconds < 0:
            return None, None
        return seconds, now + dt.timedelta(seconds=seconds)
    except ValueError:
        pass

    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is None:
            return None, None
        # 若服务端返回带 tz 的 datetime，转换为本地 naive 便于展示
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return None, parsed
    except (TypeError, ValueError, OverflowError):
        return None, None
