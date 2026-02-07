from __future__ import annotations

import datetime as dt
import random


def compute_next_retry_at(
    *,
    now: dt.datetime,
    attempt: int,
    base_delay_seconds: int,
    max_delay_seconds: int,
    rng: random.Random | None = None,
) -> dt.datetime:
    """计算下一次允许重试时间（指数退避 + jitter）。

    口径（MVP）：
    - delay = min(max_delay, base_delay * 2^(attempt-1)) + jitter
    - jitter ∈ [0, base_delay]

    Args:
        now: 当前时间（本地 naive datetime）。
        attempt: 第几次退避尝试（从 1 开始）。
        base_delay_seconds: 基础延迟（秒）。
        max_delay_seconds: 最大延迟（秒，上限）。
        rng: 可注入的随机源（用于离线单测 deterministic）。

    Returns:
        下一次允许重试时间（本地 naive datetime）。
    """

    safe_attempt = max(1, int(attempt))
    safe_base = max(1, int(base_delay_seconds))
    safe_max = max(safe_base, int(max_delay_seconds))

    exp_delay = safe_base * (2 ** (safe_attempt - 1))
    capped = min(safe_max, exp_delay)

    r = rng or random.Random()
    jitter = r.uniform(0.0, float(safe_base))

    return now + dt.timedelta(seconds=float(capped) + jitter)

