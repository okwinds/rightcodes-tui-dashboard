from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx

from rightcodes_tui_dashboard.api.client import RightCodesApiClient
from rightcodes_tui_dashboard.errors import ApiError, AuthError, RateLimitError


@respx.mock
def test_api_client_maps_401_to_auth_error() -> None:
    respx.get("https://example.test/auth/me").mock(return_value=httpx.Response(401, json={"detail": "nope"}))
    client = RightCodesApiClient(base_url="https://example.test", token="t")
    with pytest.raises(AuthError):
        client.get_me()


@respx.mock
def test_api_client_maps_429_to_rate_limit_error_with_retry_after() -> None:
    now = dt.datetime.now()
    respx.get("https://example.test/auth/me").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "120"}, json={"detail": "slow down"})
    )
    client = RightCodesApiClient(base_url="https://example.test", token="t")
    with pytest.raises(RateLimitError) as exc:
        client.get_me()
    err = exc.value
    assert err.retry_after_seconds == 120
    assert err.next_retry_at is not None
    # 允许少量运行时误差
    assert 118 <= (err.next_retry_at - now).total_seconds() <= 122


@respx.mock
def test_api_client_maps_non_2xx_to_api_error() -> None:
    respx.get("https://example.test/auth/me").mock(return_value=httpx.Response(500, json={"detail": "oops"}))
    client = RightCodesApiClient(base_url="https://example.test", token="t")
    with pytest.raises(ApiError):
        client.get_me()

