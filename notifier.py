from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from safety import assert_safe_data


TOPIC_LABELS = {
    "reservation_wait": "预约/等待",
    "pricing_campaign": "价格/活动",
    "business_hours": "营业时间",
    "schedule_change": "排班变更",
    "reception_system": "受付/系统",
    "shop_rules": "店铺规则",
    "location_access": "位置/交通",
    "hygiene_environment": "卫生/环境",
    "crowding_popularity": "拥挤度/人气",
    "notice_announcement": "公告/广告",
    "complaint_anomaly": "投诉/异常",
}


def build_bark_message(summary: dict, thread_url: str, checked_at: str) -> tuple[str, str]:
    new_count = int(summary.get("new_count", 0) or 0)
    latest_res_no = int(summary.get("latest_res_no", 0) or 0)
    title = f"神戸妻 新レス{new_count}件 #{latest_res_no}"
    message = "\n".join(
        [
            f"范围：{summary.get('res_range', '') or '-'}",
            f"主题：{_format_topics(summary.get('topics', {}))}",
            f"确认：{_format_manual(summary.get('topics', {}), summary.get('manual_check_ranges', []))}",
            "点开通知查看原帖",
        ]
    )
    assert_safe_data({"title": title, "message": message})
    return title, message


def send_bark_notification(
    bark_key: str,
    title: str,
    message: str,
    timeout: float = 10.0,
    link_url: str = "",
    opener: Callable = urlopen,
) -> None:
    normalized_key = normalize_bark_key(bark_key)
    if not normalized_key:
        return
    assert_safe_data({"title": title, "message": message})
    url = (
        f"https://api.day.app/{quote(normalized_key, safe='')}/"
        f"{quote(title, safe='')}/{quote(message, safe='')}"
    )
    if link_url:
        url += "?" + urlencode({"url": link_url})
    request = Request(url, headers={"User-Agent": "BakusaiSafeSummary/1.0"})
    with opener(request, timeout=timeout) as response:
        response.read()


def normalize_bark_key(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if "://" not in cleaned:
        return cleaned.strip("/")

    parsed = urlparse(cleaned)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.endswith("day.app") and parts:
        return parts[0]
    return cleaned


def _format_topics(topics: dict) -> str:
    ranked = [
        (topic, int(count))
        for topic, count in topics.items()
        if topic in TOPIC_LABELS and int(count) > 0
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    if not ranked:
        return "无明显店铺级主题"
    return "、".join(f"{TOPIC_LABELS[topic]}({count})" for topic, count in ranked[:3])


def _format_manual(topics: dict, ranges: list[str]) -> str:
    count = int(topics.get("needs_manual_check", 0) or 0)
    if count <= 0:
        return "无"
    if not ranges:
        return f"{count}件"
    if len(ranges) == 1:
        return f"{count}件（{ranges[0]}）"
    return f"{count}件（{ranges[0]} 等）"
