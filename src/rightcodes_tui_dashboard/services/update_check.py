from __future__ import annotations

import json
import re
from typing import Any

import httpx


_VERSION_RE = re.compile(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?.*$", re.IGNORECASE)


def _parse_version_tuple(value: str) -> tuple[int, int, int] | None:
    """解析版本号为 (major, minor, patch) 便于比较。

    说明：
    - 本项目版本形态为 `X.Y.Z`（例如 0.1.13）；此处不处理复杂 pre-release 语义。
    - 解析失败返回 None，上层应降级为“无法判断是否有新版本”。
    """

    text = (value or "").strip()
    if not text:
        return None
    m = _VERSION_RE.match(text)
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2) or 0)
    patch = int(m.group(3) or 0)
    return (major, minor, patch)


def is_newer_version(*, latest: str, current: str) -> bool:
    """判断 latest 是否比 current 更新。

    Args:
        latest: 最新版本号字符串（例如 "0.1.14"）。
        current: 当前版本号字符串（例如 "0.1.13"）。

    Returns:
        latest > current 则 True；无法解析时返回 False（保守，不提示更新）。
    """

    latest_tuple = _parse_version_tuple(latest)
    current_tuple = _parse_version_tuple(current)
    if latest_tuple is None or current_tuple is None:
        return False
    return latest_tuple > current_tuple


def fetch_pypi_latest_version(*, package: str, timeout_seconds: float = 1.2) -> str | None:
    """从 PyPI 获取最新版本号（非搅扰式：失败即返回 None）。

    注意：
    - 不应阻塞主 UI；建议在后台线程/异步任务中调用。
    - 必须容错：离线/网络受限/被墙等情况都不应报错影响主功能。
    """

    name = (package or "").strip()
    if not name:
        return None

    url = f"https://pypi.org/pypi/{name}/json"
    try:
        r = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        data: Any = json.loads(r.text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    info = data.get("info")
    if not isinstance(info, dict):
        return None
    version = info.get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    return version.strip()
