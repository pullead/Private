from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    target_url: str
    bark_key: str
    state_file: str = "state.json"
    summary_dir: str = "daily_summary"
    request_timeout: float = 15.0


def load_config() -> Config:
    target_url = os.environ.get("TARGET_URL", "").strip()
    if not target_url:
        raise ValueError("TARGET_URL is required")

    timeout_text = os.environ.get("REQUEST_TIMEOUT", "15").strip()
    try:
        request_timeout = float(timeout_text)
    except ValueError as exc:
        raise ValueError("REQUEST_TIMEOUT must be a number") from exc

    return Config(
        target_url=target_url,
        bark_key=os.environ.get("BARK_KEY", "").strip(),
        state_file=os.environ.get("STATE_FILE", "state.json").strip() or "state.json",
        summary_dir=os.environ.get("SUMMARY_DIR", "daily_summary").strip()
        or "daily_summary",
        request_timeout=request_timeout,
    )
