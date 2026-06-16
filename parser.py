from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from html import unescape

from safety import assert_safe_data


RES_NO_PATTERN = re.compile(r"(?:#|No\.?\s*|レス\s*)([1-9][0-9]{0,7})", re.IGNORECASE)
TIME_PATTERN = re.compile(r"20[0-9]{2}[-/年][0-9]{1,2}[-/月][0-9]{1,2}(?:日)?\s+[0-9]{1,2}:[0-9]{2}")
TAG_PATTERN = re.compile(r"<[^>]+>")
ARTICLE_PATTERN = re.compile(
    r"<(?:article|div|li)[^>]*>(.*?)</(?:article|div|li)>",
    re.IGNORECASE | re.DOTALL,
)
BAKUSAI_ARTICLE_PATTERN = re.compile(
    r'<div\b(?=[^>]*\bclass=["\'][^"\']*\barticle\b[^"\']*\bres_list_article\b[^"\']*["\'])'
    r'(?=[^>]*\bid=["\']res([1-9][0-9]{0,7})["\'])[^>]*>'
    r"(.*?)(?=<div\b(?=[^>]*\bclass=[\"'][^\"']*\barticle\b[^\"']*\bres_list_article\b)|</dl>|$)",
    re.IGNORECASE | re.DOTALL,
)

TOPIC_KEYWORDS = {
    "reservation_wait": ("予約", "待ち", "待機", "混雑", "空き", "booking", "wait"),
    "pricing_campaign": ("料金", "価格", "割引", "イベント", "キャンペーン", "クーポン"),
    "business_hours": ("営業時間", "開店", "閉店", "休業", "営業", "祝日"),
    "schedule_change": ("出勤", "シフト", "予定", "変更", "休み"),
    "reception_system": ("受付", "電話", "サイト", "web", "予約フォーム", "システム"),
    "shop_rules": ("ルール", "注意", "支払い", "カード", "現金", "規約"),
    "location_access": ("場所", "駅", "駐車", "アクセス", "住所", "交通"),
    "hygiene_environment": ("清潔", "衛生", "部屋", "設備", "環境"),
    "crowding_popularity": ("人気", "混ん", "並び", "話題", "多い"),
    "notice_announcement": ("告知", "お知らせ", "公式", "更新", "広告"),
    "complaint_anomaly": ("トラブル", "遅れ", "キャンセル", "ミス", "不具合"),
}

SENSITIVE_DETAIL_MARKERS = (
    "nn",
    "ns",
    "本番",
    "サービス",
    "外見",
    "容姿",
    "スタイル",
    "年齢",
    "カップ",
)


@dataclass(frozen=True)
class ThreadMetadata:
    latest_res_no: int
    latest_time: str
    page_hash: str

    def to_dict(self) -> dict:
        data = asdict(self)
        assert_safe_data(data)
        return data


def parse_thread_metadata(html: str) -> ThreadMetadata:
    entries = _extract_entries(html)
    res_numbers = [res_no for res_no, _ in entries] or _extract_res_numbers(html)
    latest_res_no = max(res_numbers) if res_numbers else 0
    latest_time = _extract_latest_time(html)
    page_hash = hashlib.sha256(_structure_only_text(html).encode("utf-8")).hexdigest()
    metadata = ThreadMetadata(latest_res_no, latest_time, page_hash)
    assert_safe_data(metadata.to_dict())
    return metadata


def summarize_shop_topics(html: str, previous_res_no: int, summary_date: str) -> dict:
    entries = [
        (res_no, text)
        for res_no, text in _extract_entries(html)
        if res_no > previous_res_no
    ]
    metadata = parse_thread_metadata(html)

    topics = {key: 0 for key in TOPIC_KEYWORDS}
    topics["needs_manual_check"] = 0
    manual_numbers: list[int] = []

    for res_no, text in entries:
        lowered = text.lower()
        if any(marker.lower() in lowered for marker in SENSITIVE_DETAIL_MARKERS):
            topics["needs_manual_check"] += 1
            manual_numbers.append(res_no)
            continue

        matched = False
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                topics[topic] += 1
                matched = True
        if not matched:
            topics["needs_manual_check"] += 1
            manual_numbers.append(res_no)

    new_numbers = [res_no for res_no, _ in entries]
    summary = {
        "summary_date": summary_date,
        "latest_res_no": metadata.latest_res_no,
        "new_count": len(entries),
        "res_range": _format_range(new_numbers),
        "topics": {key: count for key, count in topics.items() if count > 0},
        "manual_check_ranges": _compact_numbers(manual_numbers),
    }
    assert_safe_data(summary)
    return summary


def _extract_entries(html: str) -> list[tuple[int, str]]:
    bakusai_entries = _extract_bakusai_entries(html)
    if bakusai_entries:
        return bakusai_entries

    blocks = ARTICLE_PATTERN.findall(html)
    if not blocks:
        blocks = html.splitlines()

    entries: list[tuple[int, str]] = []
    for block in blocks:
        numbers = _extract_res_numbers(block)
        if not numbers:
            continue
        entries.append((max(numbers), _plain_text(block)))
    return entries


def _extract_bakusai_entries(html: str) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for match in BAKUSAI_ARTICLE_PATTERN.finditer(html):
        res_no = int(match.group(1))
        if res_no == 0:
            continue
        entries.append((res_no, _plain_text(match.group(2))))
    return entries


def _extract_res_numbers(html: str) -> list[int]:
    return [int(match.group(1)) for match in RES_NO_PATTERN.finditer(_plain_text(html))]


def _extract_latest_time(html: str) -> str:
    matches = TIME_PATTERN.findall(_plain_text(html))
    if not matches:
        return ""
    return matches[-1].replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")


def _structure_only_text(html: str) -> str:
    tags = re.findall(r"</?([a-zA-Z0-9]+)", html)
    numbers = [str(number) for number in _extract_res_numbers(html)]
    return "|".join(tags + numbers)


def _plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(TAG_PATTERN.sub(" ", html))).strip()


def _format_range(numbers: list[int]) -> str:
    if not numbers:
        return ""
    return f"#{min(numbers)}-#{max(numbers)}" if min(numbers) != max(numbers) else f"#{numbers[0]}"


def _compact_numbers(numbers: list[int]) -> list[str]:
    if not numbers:
        return []
    sorted_numbers = sorted(set(numbers))
    ranges: list[str] = []
    start = previous = sorted_numbers[0]
    for number in sorted_numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(f"#{start}-#{previous}" if start != previous else f"#{start}")
        start = previous = number
    ranges.append(f"#{start}-#{previous}" if start != previous else f"#{start}")
    return ranges
