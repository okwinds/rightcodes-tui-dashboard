from __future__ import annotations


def test_mask_key_short_values() -> None:
    from rightcodes_tui_dashboard.ui.app import _mask_key

    assert _mask_key("—") == "—"
    assert _mask_key("") == "—"
    assert _mask_key("a") == "…"
    assert _mask_key("ab") == "a…"


def test_mask_key_medium_and_long_values() -> None:
    from rightcodes_tui_dashboard.ui.app import _mask_key

    assert _mask_key("ABCDEFGH") == "AB…GH"
    assert _mask_key("ABCDEFGHIJKL") == "ABC…JKL"
    assert _mask_key("ABCDEFGHIJKLMN") == "ABCD…KLMN"

