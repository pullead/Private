from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlparse
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
    "needs_manual_check": "需人工查看",
}


def build_bark_message(summary: dict, thread_url: str, checked_at: str) -> tuple[str, str]:
    topic_parts = [
        f"{TOPIC_LABELS.get(topic, topic)}:{count}"
        for topic, count in summary.get("topics", {}).items()
    ]
    manual = ",".join(summary.get("manual_check_ranges", [])) or "无"
    title = "论坛线程每日摘要"
    message = (
        f"新增 {summary.get('new_count', 0)} 件。"
        f"最新レス番号：{summary.get('latest_res_no', 0)}。"
        f"范围：{summary.get('res_range', '')}。"
        f"主题：{'; '.join(topic_parts) or '无'}。"
        f"需人工查看:{manual}。"
        f"检测时间：{checked_at}。"
        f"线程URL：{thread_url}"
    )
    assert_safe_data({"title": title, "message": message})
    return title, message


def send_bark_notification(
    bark_key: str,
    title: str,
    message: str,
    timeout: float = 10.0,
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
