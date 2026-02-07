#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import getpass
import json
import os
import sys
from typing import Any

import requests


DEFAULT_BASE_URL = "https://right.codes"


@dataclasses.dataclass(frozen=True)
class DoctorResult:
    base_url: str
    ok: bool
    summary: dict[str, Any]
    raw: dict[str, Any]


def _iso_local_no_tz(d: dt.datetime) -> str:
    # right.codes 前端在请求里使用的是 YYYY-MM-DDTHH:mm:SS（秒级）。
    # 这里先不带时区偏移，调研阶段只需确认后端可接受的格式。
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        redacted: dict[str, Any] = {}
        for k, v in obj.items():
            lk = k.lower()
            if lk in {"authorization", "token", "user_token", "usertoken", "password"}:
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = _redact(v)
        return redacted
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def _post_json(session: requests.Session, url: str, token: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = session.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object from {url}, got {type(data)}")
    return data


def _get_json(session: requests.Session, url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    resp = session.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object from {url}, got {type(data)}")
    return data


def run_doctor(*, base_url: str, username: str, password: str) -> DoctorResult:
    session = requests.Session()
    session.headers.update({"User-Agent": "rightcodes-doctor/0.1"})

    raw: dict[str, Any] = {"base_url": base_url}
    summary: dict[str, Any] = {}

    # 1) Login
    login_url = f"{base_url}/auth/login"
    login = _post_json(session, login_url, token=None, payload={"username": username, "password": password})
    raw["auth_login"] = login
    token = login.get("user_token") or login.get("userToken")
    if not isinstance(token, str) or not token.strip():
        return DoctorResult(
            base_url=base_url,
            ok=False,
            summary={"error": "Missing user_token in /auth/login response", "login_keys": sorted(login.keys())},
            raw=raw,
        )
    summary["token_present"] = True

    # 2) /auth/me
    me_url = f"{base_url}/auth/me"
    me = _get_json(session, me_url, token=token)
    raw["auth_me"] = me
    summary["me_keys"] = sorted(me.keys())

    # 3) subscriptions
    subs_url = f"{base_url}/subscriptions/list"
    subs = _get_json(session, subs_url, token=token)
    raw["subscriptions_list"] = subs
    subs_items = subs.get("subscriptions")
    if isinstance(subs_items, list) and subs_items:
        first = subs_items[0]
        summary["subscriptions_count"] = len(subs_items)
        summary["subscription_item_keys_sample"] = sorted(first.keys()) if isinstance(first, dict) else str(type(first))
    else:
        summary["subscriptions_count"] = 0

    # 4) overall stats
    overall_url = f"{base_url}/use-log/stats/overall"
    overall = _get_json(session, overall_url, token=token)
    raw["use_log_stats_overall"] = overall
    summary["overall_keys"] = sorted(overall.keys())

    # 5) today stats
    start = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = dt.datetime.now().replace(microsecond=0)
    stats_url = f"{base_url}/use-log/stats"
    stats = _get_json(
        session,
        stats_url,
        token=token,
        params={"start_date": _iso_local_no_tz(start), "end_date": _iso_local_no_tz(end)},
    )
    raw["use_log_stats_today"] = stats
    summary["today_keys"] = sorted(stats.keys())

    # 6) advanced series: last 24h (hour)
    adv_url = f"{base_url}/use-log/stats/advanced"
    adv_start = (end - dt.timedelta(hours=24)).replace(microsecond=0)
    adv = _get_json(
        session,
        adv_url,
        token=token,
        params={
            "start_date": _iso_local_no_tz(adv_start),
            "end_date": _iso_local_no_tz(end),
            "granularity": "hour",
        },
    )
    raw["use_log_stats_advanced_hour_24h"] = adv
    summary["advanced_keys"] = sorted(adv.keys())

    # 7) use log list sample
    list_url = f"{base_url}/use-log/list"
    logs = _get_json(session, list_url, token=token, params={"page": 1, "page_size": 5})
    raw["use_log_list_page1"] = logs
    summary["use_log_list_keys"] = sorted(logs.keys())

    return DoctorResult(base_url=base_url, ok=True, summary=summary, raw=raw)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Probe right.codes internal JSON endpoints (no Playwright).")
    parser.add_argument("--base-url", default=os.environ.get("RIGHTCODES_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--username", default=os.environ.get("RIGHTCODES_USERNAME"))
    parser.add_argument("--out", default="rightcodes-doctor.json", help="Output JSON file (redacted).")
    parser.add_argument("--no-save", action="store_true", help="Don't write the output file.")
    args = parser.parse_args(argv)

    username = args.username
    if not username:
        username = input("right.codes username: ").strip()
    password = os.environ.get("RIGHTCODES_PASSWORD")
    if not password:
        password = getpass.getpass("right.codes password (will not echo): ")

    try:
        result = run_doctor(base_url=args.base_url.rstrip("/"), username=username, password=password)
    except requests.HTTPError as e:
        print(f"[doctor] HTTP error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[doctor] Error: {e}", file=sys.stderr)
        return 3

    payload = {"ok": result.ok, "base_url": result.base_url, "summary": result.summary, "raw": _redact(result.raw)}
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))

    if not args.no_save:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[doctor] wrote {args.out}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

