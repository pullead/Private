from __future__ import annotations

from collections.abc import Mapping, Sequence


FORBIDDEN_KEYS = {
    "girl_name",
    "cast_name",
    "source_name",
    "genji_name",
    "nickname",
    "review",
    "review_text",
    "comment",
    "body",
    "content",
    "full_text",
    "raw_text",
    "raw_html",
    "profile",
    "personal_info",
    "rating",
    "service_detail",
    "appearance",
    "age",
    "height",
    "cup",
    "nn",
    "ns",
}

FORBIDDEN_PHRASES = {
    "女孩名",
    "源氏名",
    "艺名",
    "外貌",
    "身材",
    "服务内容",
    "用户评价",
    "帖子正文",
    "原始HTML",
    "nn/ns",
}


class SafetyError(ValueError):
    """Raised when data intended for persistence or notification is unsafe."""


def assert_safe_data(value: object) -> None:
    """Reject forbidden keys or phrases in persisted or notified data."""
    unsafe = find_unsafe_entries(value)
    if unsafe:
        raise SafetyError("Unsafe output detected: " + ", ".join(sorted(unsafe)))


def find_unsafe_entries(value: object) -> set[str]:
    found: set[str] = set()
    _scan(value, found)
    return found


def _scan(value: object, found: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _is_forbidden_text(key_text):
                found.add(key_text)
            _scan(item, found)
        return

    if isinstance(value, str):
        if _is_forbidden_text(value):
            found.add(value)
        return

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            _scan(item, found)


def _is_forbidden_text(text: str) -> bool:
    lowered = text.lower()
    normalized = lowered.replace("_", "").replace("-", "").replace("/", "")
    tokens = {
        token
        for token in lowered.replace("-", "_").replace("/", "_").split("_")
        if token
    }
    for key in FORBIDDEN_KEYS:
        key_normalized = key.replace("_", "")
        if normalized == key_normalized or key in lowered.split():
            return True
        if len(key_normalized) > 3 and key_normalized in normalized:
            return True
        if key in tokens:
            return True
    return any(phrase.lower() in text.lower() for phrase in FORBIDDEN_PHRASES)
