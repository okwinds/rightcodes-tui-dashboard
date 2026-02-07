from __future__ import annotations

import datetime as dt


class ApiError(RuntimeError):
    """Right.codes API 通用错误。

    说明：
    - 作为 SDK/客户端层错误类型，保证上层可以统一捕获并做 UI 降级展示。
    - 错误信息不得包含任何敏感信息（例如 token、密码）。
    """


class AuthError(ApiError):
    """认证失败（401/403）。"""


class RateLimitError(ApiError):
    """限流错误（429）。

    Attributes:
        retry_after_seconds: 若服务端提供 Retry-After（秒数），则填充。
        next_retry_at: 计算出的下一次允许重试时间（本地时间）。
        message: 简短可读错误信息（不含敏感信息）。
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        next_retry_at: dt.datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after_seconds = retry_after_seconds
        self.next_retry_at = next_retry_at

    def __str__(self) -> str:  # pragma: no cover - 仅用于展示
        return self.message
