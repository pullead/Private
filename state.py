from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from safety import assert_safe_data


@dataclass(frozen=True)
class ThreadState:
    thread_url: str
    last_seen_res_no: int
    last_seen_hash: str
    last_checked_at: str
    new_count_today: int
    error_count: int = 0
    last_success_at: str = ""
    last_error_at: str = ""


def load_state(path: str | Path) -> dict:
    state_path = Path(path)
    if not state_path.exists():
        return {"threads": {}}

    with state_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert_safe_data(data)
    if not isinstance(data, dict) or not isinstance(data.get("threads"), dict):
        raise ValueError("state file must contain a threads object")
    return data


def save_state(path: str | Path, data: dict) -> None:
    assert_safe_data(data)
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(state_path.parent),
        prefix=f".{state_path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(payload)
        temp_name = handle.name

    Path(temp_name).replace(state_path)


def update_thread_state(path: str | Path, thread_id: str, thread: ThreadState) -> None:
    data = load_state(path)
    data.setdefault("threads", {})[thread_id] = asdict(thread)
    save_state(path, data)
