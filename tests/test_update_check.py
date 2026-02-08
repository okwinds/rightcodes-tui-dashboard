from __future__ import annotations


def test_is_newer_version_numeric_triplet() -> None:
    from rightcodes_tui_dashboard.services.update_check import is_newer_version

    assert is_newer_version(latest="0.1.14", current="0.1.13") is True
    assert is_newer_version(latest="0.1.13", current="0.1.13") is False
    assert is_newer_version(latest="0.1.12", current="0.1.13") is False


def test_is_newer_version_tolerates_suffixes() -> None:
    from rightcodes_tui_dashboard.services.update_check import is_newer_version

    # 允许出现诸如 '0.1.14rc1' 这类尾巴：按前三段数字比较即可（保守即可）。
    assert is_newer_version(latest="0.1.14rc1", current="0.1.13") is True
    assert is_newer_version(latest="v0.1.14", current="0.1.13") is True
