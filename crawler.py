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

    html = _fetch_with_single_retry(fetcher, config.target_url, config.request_timeout)
    metadata = parse_thread_metadata(html)
    has_new = metadata.latest_res_no > previous_res_no
    summary = (
        summarize_shop_topics(html, previous_res_no, summary_date) if has_new else None
    )
    new_count = int(summary["new_count"]) if summary else 0

    thread_state = ThreadState(
        thread_url=config.target_url,
        last_seen_res_no=max(previous_res_no, metadata.latest_res_no),
        last_seen_hash=metadata.page_hash,
        last_checked_at=checked_at,
        new_count_today=new_count,
        last_success_at=checked_at,
    )
    update_thread_state(config.state_file, "main", thread_state)

    if new_count == 0:
        return 0

    assert summary is not None
    _save_summary(config.summary_dir, summary_date, summary)
    title, message = build_bark_message(summary, config.target_url, checked_at)
    try:
        if notifier:
            notifier(title, message)
        else:
            send_bark_notification(config.bark_key, title, message)
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


if __name__ == "__main__":
    raise SystemExit(main())
