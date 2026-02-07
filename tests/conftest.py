from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """确保在未 `pip install -e .` 的情况下也能离线运行 tests。"""

    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

