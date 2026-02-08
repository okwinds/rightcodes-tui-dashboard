from __future__ import annotations

import os

from rightcodes_tui_dashboard.storage.token_store import LocalFileTokenStore


def test_local_file_token_store_uses_rightcodes_data_dir_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RIGHTCODES_DATA_DIR", str(tmp_path))

    store = LocalFileTokenStore()
    store.save_token("abc")

    token_file = tmp_path / "token.json"
    assert token_file.exists()

    record = store.load_token()
    assert record is not None
    assert record.token == "abc"

    # Best-effort permissions check on POSIX
    if os.name == "posix":
        mode = token_file.stat().st_mode & 0o777
        assert mode == 0o600

