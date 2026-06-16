from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from safety import assert_safe_data


TOPIC_LABELS = {
    "reservation_wait": "预约等待",
    "pricing_campaign": "价格活动",
    "business_hours": "营业时间",
    "schedule_change": "排班变更",
    "reception_system": "受付系统",
    "shop_rules": "店铺规则",
    "location_access": "位置交通",
    "hygiene_environment": "卫生环境",
    "crowding_popularity": "人气热度",
    "notice_announcement": "公告更新",
    "complaint_anomaly": "异常反馈",
}

TOPIC_HEADLINES = {
    "reservation_wait": "预约和等待情况被反复提到，建议关注可约状态",
    "pricing_campaign": "价格、优惠或活动信息有新讨论",
    "business_hours": "营业时间或休业安排出现讨论",
    "schedule_change": "排班相关信息被提到，需到原帖确认细节",
    "reception_system": "受付、电话或网页预约流程被讨论",
    "shop_rules": "规则、支付方式或注意事项是主要话题",
    "location_access": "位置、交通或到店路线被提到",
    "hygiene_environment": "店内环境、卫生或设施状态有讨论",
    "crowding_popularity": "热度和拥挤程度有变化迹象",
    "notice_announcement": "公告、广告或官方更新被提到",
    "complaint_anomaly": "出现异常反馈，建议优先人工查看",
}

TOPIC_DETAILS = {
    "reservation_wait": "讨论重点偏向预约难度、空き情况、等待时间或现场混杂度。",
    "pricing_campaign": "要点集中在费用变化、优惠活动、套餐或活动规则。",
    "business_hours": "可能涉及开店闭店、临时休业、节假日安排等信息。",
    "schedule_change": "只提示排班层面有变化，不展开具体个人内容。",
    "reception_system": "可能涉及电话响应、网站预约、受付流程或系统使用体验。",
    "shop_rules": "讨论集中在支付、规则、注意事项或到店流程。",
    "location_access": "可能涉及路线、车站、停车或周边位置。",
    "hygiene_environment": "讨论偏向店内环境、清洁状态或设施体验。",
    "crowding_popularity": "可理解为论坛热度、关注度或拥挤感上升。",
    "notice_announcement": "可能是官方信息、广告内容或页面更新。",
    "complaint_anomaly": "内容不适合自动展开，建议打开原帖核对。",
}

TOPIC_KEYWORDS = {
    "reservation_wait": ("预约", "空き", "等待", "混杂", "可约", "到店"),
    "pricing_campaign": ("价格", "优惠", "活动", "套餐", "费用", "规则"),
    "business_hours": ("营业", "休业", "时间", "开店", "闭店", "节假日"),
    "schedule_change": ("排班", "出勤", "变更", "休息", "安排", "确认"),
    "reception_system": ("受付", "电话", "网站", "预约流程", "响应", "系统"),
    "shop_rules": ("规则", "支付", "注意事项", "流程", "确认", "到店"),
    "location_access": ("位置", "交通", "车站", "停车", "路线", "周边"),
    "hygiene_environment": ("环境", "卫生", "设施", "清洁", "房间", "体验"),
    "crowding_popularity": ("热度", "拥挤", "人气", "关注", "排队", "活跃"),
    "notice_announcement": ("公告", "广告", "官方", "更新", "通知", "页面"),
    "complaint_anomaly": ("异常", "投诉", "问题", "反馈", "确认", "注意"),
}


def build_bark_message(summary: dict, thread_url: str, checked_at: str) -> tuple[str, str]:
    interval_count = int(summary.get("interval_new_count", summary.get("new_count", 0)) or 0)
    day_count = int(summary.get("day_new_count", interval_count) or 0)
    latest_res_no = int(summary.get("latest_res_no", 0) or 0)
    interval_range = summary.get("interval_res_range", summary.get("res_range", "")) or "-"
    title = f"今日论坛速览｜神戸妻｜新{interval_count} / 今日{day_count}"
    message = "\n".join(
        [
            f"{_format_date(summary.get('summary_date', ''))}｜最新 #{latest_res_no}｜{interval_range}",
            "",
            "【今日三句话】",
            _format_overview(summary),
            "",
            "【帖子摘要卡片】",
            _format_cards(summary.get("topics", {}), interval_range, limit=3),
            "",
            f"【人工确认】{_format_manual(summary.get('interval_topics', summary.get('topics', {})), summary.get('manual_check_ranges', []))}",
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


def _format_overview(summary: dict) -> str:
    topics = summary.get("topics", {})
    ranked = _rank_topics(topics)
    interval_count = int(summary.get("interval_new_count", summary.get("new_count", 0)) or 0)
    day_count = int(summary.get("day_new_count", interval_count) or 0)
    if not ranked:
        return "\n".join(
            [
                f"1. 本次新增 {interval_count} 件，今日累计 {day_count} 件。",
                "2. 暂时没有识别到明显的店铺级讨论主线。",
                "3. 建议点开原帖查看最新レス上下文。",
            ]
        )

    top_labels = "、".join(TOPIC_LABELS[topic] for topic, _ in ranked[:3])
    manual_count = int(topics.get("needs_manual_check", 0) or 0)
    return "\n".join(
        [
            f"1. 本次新增 {interval_count} 件，今日累计 {day_count} 件。",
            f"2. 今天讨论主线集中在：{top_labels}。",
            f"3. 其中 {manual_count} 件不适合自动展开，建议作为人工确认入口。",
        ]
    )


def _format_cards(topics: dict, res_range: str, limit: int) -> str:
    ranked = _rank_topics(topics)
    if not ranked:
        return "暂无可安全概括的店铺级主题。"

    cards = []
    for topic, count in ranked[:limit]:
        cards.append(
            "\n".join(
                [
                    f"[{_topic_badge(topic)}][店铺] {TOPIC_HEADLINES[topic]}",
                    f"关键词：{' / '.join(TOPIC_KEYWORDS[topic])}",
                    f"摘要：{_topic_summary_sentence(topic)}",
                    f"数据：{count}件｜{res_range}｜情绪：{_infer_mood(topic, count)}",
                ]
            )
        )
    return "\n\n".join(cards)


def _rank_topics(topics: dict) -> list[tuple[str, int]]:
    ranked = [
        (topic, int(count))
        for topic, count in topics.items()
        if topic in TOPIC_LABELS and int(count) > 0
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def _topic_badge(topic: str) -> str:
    if topic in {"crowding_popularity", "complaint_anomaly"}:
        return "热帖"
    return "新帖"


def _topic_summary_sentence(topic: str) -> str:
    return (
        f"发帖重点偏向{TOPIC_LABELS[topic]}。"
        f"大家主要围绕{TOPIC_DETAILS[topic]}"
        "目前更适合先看原帖确认细节，再决定是否继续关注。"
    )


def _infer_mood(topic: str, count: int) -> str:
    if topic == "complaint_anomaly":
        return "分歧"
    if topic in {"notice_announcement", "pricing_campaign"}:
        return "积极"
    if count >= 3:
        return "讨论中"
    return "观望"


def _format_date(summary_date: str) -> str:
    if not summary_date:
        return "今日"
    parts = summary_date.split("-")
    if len(parts) != 3:
        return summary_date
    return f"{int(parts[1])}月{int(parts[2])}日"


def _format_manual(topics: dict, ranges: list[str]) -> str:
    count = int(topics.get("needs_manual_check", 0) or 0)
    if count <= 0:
        return "无"
    if not ranges:
        return f"{count}件无法安全概括，建议人工查看。"
    if len(ranges) == 1:
        return f"{count}件无法安全概括：{ranges[0]}"
    return f"{count}件无法安全概括：{ranges[0]} 等"
