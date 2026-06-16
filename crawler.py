from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from config import Config, load_config
from notifier import build_bark_message, send_bark_notification
from parser import parse_thread_metadata, summarize_shop_topics
from safety import assert_safe_data
from state import ThreadState, load_state, update_thread_state


JST = timezone(timedelta(hours=9))


def fetch_url(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "BakusaiSafeSummary/1.0"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def run_once(
    config: Config,
    fetcher: Callable[[str, float], str] = fetch_url,
    notifier: Callable[[str, str], None] | None = None,
    now_provider: Callable[[], str] | None = None,
) -> int:
    checked_at = now_provider() if now_provider else datetime.now(JST).isoformat()
    summary_date = checked_at[:10]
    state_data = load_state(config.state_file)
    previous = state_data.get("threads", {}).get("main", {})
    previous_res_no = int(previous.get("last_seen_res_no", 0) or 0)
    is_first_run = not bool(previous)

    html = _fetch_with_single_retry(fetcher, config.target_url, config.request_timeout)
    metadata = parse_thread_metadata(html)
    has_new = metadata.latest_res_no > previous_res_no and not is_first_run
    interval_summary = (
        summarize_shop_topics(html, previous_res_no, summary_date) if has_new else None
    )
    daily_summary = (
        _merge_daily_summary(config.summary_dir, summary_date, interval_summary)
        if interval_summary
        else None
    )
    interval_count = int(interval_summary["new_count"]) if interval_summary else 0
    day_count = int(daily_summary["day_new_count"]) if daily_summary else 0

    thread_state = ThreadState(
        thread_url=config.target_url,
        last_seen_res_no=max(previous_res_no, metadata.latest_res_no),
        last_seen_hash=metadata.page_hash,
        last_checked_at=checked_at,
        new_count_today=day_count,
        last_success_at=checked_at,
    )
    update_thread_state(config.state_file, "main", thread_state)

    if interval_count == 0:
        return 0

    assert daily_summary is not None
    _save_summary(config.summary_dir, summary_date, daily_summary)
    title, message = build_bark_message(daily_summary, config.target_url, checked_at)
    try:
        if notifier:
            notifier(title, message)
        else:
            send_bark_notification(
                config.bark_key, title, message, link_url=config.target_url
            )
    except Exception as exc:
        print(f"[WARN] Notification failed: {exc}", file=sys.stderr)
    return 0


def main() -> int:
    try:
        return run_once(load_config())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def _fetch_with_single_retry(
    fetcher: Callable[[str, float], str], url: str, timeout: float
) -> str:
    try:
        return fetcher(url, timeout)
    except Exception:
        return fetcher(url, timeout)


def _save_summary(summary_dir: str, summary_date: str, summary: dict) -> None:
    assert_safe_data(summary)
    path = Path(summary_dir) / f"{summary_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _merge_daily_summary(summary_dir: str, summary_date: str, interval_summary: dict) -> dict:
    path = Path(summary_dir) / f"{summary_date}.json"
    existing = _load_existing_summary(path)
    existing_topics = existing.get("topics", {})
    interval_topics = interval_summary.get("topics", {})

    merged_topics = dict(existing_topics)
    for topic, count in interval_topics.items():
        merged_topics[topic] = int(merged_topics.get(topic, 0) or 0) + int(count or 0)

    interval_count = int(interval_summary.get("new_count", 0) or 0)
    previous_day_count = int(
        existing.get("day_new_count", existing.get("new_count", 0)) or 0
    )
    daily = {
        "summary_date": summary_date,
        "latest_res_no": interval_summary.get("latest_res_no", 0),
        "interval_new_count": interval_count,
        "day_new_count": previous_day_count + interval_count,
        "interval_res_range": interval_summary.get("res_range", ""),
        "day_res_ranges": _append_unique(
            existing.get("day_res_ranges", []), interval_summary.get("res_range", "")
        ),
        "topics": {key: value for key, value in merged_topics.items() if value > 0},
        "interval_topics": interval_topics,
        "manual_check_ranges": interval_summary.get("manual_check_ranges", []),
    }
    assert_safe_data(daily)
    return daily


def _load_existing_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    assert_safe_data(data)
    return data


def _append_unique(items: list[str], item: str) -> list[str]:
    result = list(items)
    if item and item not in result:
        result.append(item)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
