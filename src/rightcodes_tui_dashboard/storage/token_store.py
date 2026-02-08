from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

from rightcodes_tui_dashboard.utils.paths import resolve_app_data_path, resolve_local_path


@dataclass(frozen=True)
class TokenRecord:
    """token 记录（只包含最小信息，避免误落敏感字段）。"""

    token: str
    saved_at: dt.datetime


class TokenStore:
    """TokenStore 抽象接口。"""

    def load_token(self) -> TokenRecord | None:
        """读取 token（若不存在返回 None）。"""

        raise NotImplementedError

    def save_token(self, token: str) -> None:
        """保存 token（不得保存密码）。"""

        raise NotImplementedError

    def store_name(self) -> str:
        """用于 CLI 展示当前存储类型。"""

        raise NotImplementedError


class KeyringTokenStore(TokenStore):
    """基于 keyring 的 token 存储（可选依赖）。"""

    service_name = "rightcodes"
    account_name = "user_token"

    def __init__(self) -> None:
        self._keyring = _try_import_keyring()

    def is_available(self) -> bool:
        """判断 keyring 是否可用（依赖缺失或后端不可用则 False）。"""

        return self._keyring is not None

    def load_token(self) -> TokenRecord | None:
        if not self._keyring:
            return None
        try:
            token = self._keyring.get_password(self.service_name, self.account_name)
        except Exception:
            return None
        if not token:
            return None
        return TokenRecord(token=str(token), saved_at=dt.datetime.fromtimestamp(0))

    def save_token(self, token: str) -> None:
        if not self._keyring:
            raise RuntimeError("keyring 不可用")
        self._keyring.set_password(self.service_name, self.account_name, token)

    def store_name(self) -> str:
        return "keyring"


class LocalFileTokenStore(TokenStore):
    """本地文件 token 存储（兜底）。

    约束：
    - 默认写入“全局应用数据目录”（跨目录可用）
    - 兼容读取旧版 `.local/token.json`（若存在会自动迁移）
    - 文件权限尽量设置为 0600
    - 只保存 token 与写入时间
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir / "token.json") if base_dir else resolve_app_data_path("token.json")

    def load_token(self) -> TokenRecord | None:
        record = self._load_from_path(self._path)
        if record is not None:
            return record

        legacy = _try_resolve_legacy_token_path()
        if legacy is None or not legacy.exists():
            return None

        legacy_record = self._load_from_path(legacy)
        if legacy_record is None:
            return None

        # 迁移到全局目录（不删除旧文件；仅复制）
        try:
            self.save_token(legacy_record.token)
        except Exception:
            pass
        return legacy_record

    def save_token(self, token: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "token": token,
            "saved_at": dt.datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self._path)
        _chmod_600(self._path)

    def store_name(self) -> str:
        return "file"

    def _load_from_path(self, path: Path) -> TokenRecord | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        token = data.get("token")
        saved_at_raw = data.get("saved_at")
        if not isinstance(token, str) or not token:
            return None
        saved_at = _safe_parse_dt(saved_at_raw) or dt.datetime.fromtimestamp(0)
        return TokenRecord(token=token, saved_at=saved_at)


def _try_import_keyring():
    try:
        import keyring
    except Exception:
        return None
    return keyring


def _chmod_600(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        return


def _safe_parse_dt(value) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return dt.datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def _try_resolve_legacy_token_path() -> Path | None:
    """兼容旧版：项目目录 `.local/token.json`。

    - pip 安装后在任意目录运行时，无法定位项目根目录，这里必须容错。
    """

    try:
        return resolve_local_path("token.json")
    except Exception:
        return None
