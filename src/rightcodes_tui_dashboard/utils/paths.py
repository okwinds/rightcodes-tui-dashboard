from __future__ import annotations

import os
from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """从当前目录向上查找项目根目录（包含 rightcodes-tui-dashboard/pyproject.toml）。

    Args:
        start: 起始路径（默认当前工作目录）。

    Returns:
        Path: 项目根目录（rightcodes-tui-dashboard/）。

    Raises:
        FileNotFoundError: 无法定位根目录。
    """

    current = (start or Path.cwd()).resolve()
    for _ in range(15):
        if (current / "pyproject.toml").exists() and current.name == "rightcodes-tui-dashboard":
            return current
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError("无法定位项目根目录（未找到 rightcodes-tui-dashboard/pyproject.toml）。请在项目目录运行。")


def resolve_local_path(filename: str) -> Path:
    """解析 `.local/` 下文件路径（项目约束：只允许写入 rightcodes-tui-dashboard/.local/）。"""

    root = find_project_root()
    return root / ".local" / filename


def resolve_app_data_path(filename: str) -> Path:
    """解析应用全局数据目录下的文件路径（用于 pip 安装后跨目录可用）。

    优先级：
    1) 环境变量 `RIGHTCODES_DATA_DIR`（便于用户自定义/测试）
    2) platformdirs 的 user_data_dir（macOS/Linux/Windows 各自遵循系统约定）
    """

    override = os.environ.get("RIGHTCODES_DATA_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser().resolve() / filename

    from platformdirs import user_data_dir

    base = Path(user_data_dir(appname="rightcodes", appauthor="rightcodes"))
    return base / filename
