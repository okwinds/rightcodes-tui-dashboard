from __future__ import annotations

import argparse
import datetime as dt


def test_logs_range_today_uses_midnight_start(monkeypatch, capsys) -> None:
    from rightcodes_tui_dashboard import cli

    fixed_now = dt.datetime(2026, 2, 8, 12, 34, 56)

    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return fixed_now

    # 冻结 now()
    monkeypatch.setattr(cli.dt, "datetime", FixedDateTime)

    captured: dict[str, str] = {}

    class FakeClient:
        def __init__(self, *, base_url: str, token: str | None):  # noqa: ANN001
            self.base_url = base_url
            self.token = token

        def __enter__(self):  # noqa: ANN001
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return None

        def use_logs_list(self, *, page: int, page_size: int, start_date: str, end_date: str):  # noqa: ANN001
            captured["start_date"] = start_date
            captured["end_date"] = end_date
            return {"logs": [], "page": page, "page_size": page_size, "total": 0}

    class FakeStore:
        def load_token(self):  # noqa: ANN001
            class _Rec:
                token = "t"

            return _Rec()

    monkeypatch.setattr(cli, "_select_store", lambda *_args, **_kwargs: FakeStore())
    monkeypatch.setattr(cli, "RightCodesApiClient", FakeClient)

    args = argparse.Namespace(
        base_url=None,
        range="today",
        page=1,
        page_size=1,
        format="json",
    )
    rc = cli.cmd_logs(args)
    assert rc == 0

    assert captured["start_date"] == "2026-02-08T00:00:00"
    assert captured["end_date"] == "2026-02-08T12:34:56"

    out = capsys.readouterr().out
    assert out.strip().startswith("[")  # json 输出
