from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from safety import assert_safe_data


TOPIC_LABELS = {
    "reservation_wait": ("予約・待ち時間", "预约与等待"),
    "pricing_campaign": ("料金・キャンペーン", "价格与活动"),
    "business_hours": ("営業時間", "营业时间"),
    "schedule_change": ("出勤・予定変更", "排期变化"),
    "reception_system": ("受付・予約システム", "受付流程"),
    "shop_rules": ("店舗ルール", "店铺规则"),
    "location_access": ("アクセス", "位置交通"),
    "hygiene_environment": ("衛生・店内環境", "环境卫生"),
    "crowding_popularity": ("混雑・注目度", "热度变化"),
    "notice_announcement": ("告知・更新", "公告更新"),
    "complaint_anomaly": ("気になる反応", "异常反馈"),
}

TOPIC_KEYWORDS = {
    "reservation_wait": ("予約", "空き", "待ち", "确认", "等待", "预约"),
    "pricing_campaign": ("料金", "割引", "活动", "价格", "优惠"),
    "business_hours": ("営業時間", "開店", "营业", "时间", "休业"),
    "schedule_change": ("出勤", "予定", "排期", "变更", "确认"),
    "reception_system": ("受付", "電話", "Web", "流程", "预约"),
    "shop_rules": ("ルール", "支払い", "注意", "规则", "支付"),
    "location_access": ("駅", "場所", "アクセス", "位置", "交通"),
    "hygiene_environment": ("衛生", "設備", "清潔", "环境", "设施"),
    "crowding_popularity": ("混雑", "人気", "注目", "热度", "拥挤"),
    "notice_announcement": ("告知", "公式", "更新", "公告", "通知"),
    "complaint_anomaly": ("確認", "注意", "反応", "异常", "反馈"),
}

TOPIC_SUMMARIES = {
    "reservation_wait": (
        "予約の取りやすさ、空き状況、待ち時間の見方が中心です。",
        "讨论集中在预约难度、空位变化和等待时间，适合人工点进原帖确认最新情况。",
    ),
    "pricing_campaign": (
        "料金や割引、キャンペーン条件の変化が話題です。",
        "主要围绕价格、优惠活动和适用规则，当前更像信息确认而非明确结论。",
    ),
    "business_hours": (
        "営業時間や休業、時間帯ごとの動きが確認されています。",
        "重点是营业时间、临时休息和不同时段安排，需要以店铺官方信息为准。",
    ),
    "schedule_change": (
        "予定変更や出勤情報まわりの確認が増えています。",
        "讨论指向排期变化和信息更新，但不展开个人层面的具体内容。",
    ),
    "reception_system": (
        "受付方法、電話やWeb予約の使い勝手が話題です。",
        "大家在讨论受付流程、电话和网页预约体验，偏实用信息。",
    ),
    "shop_rules": (
        "支払い、注意事項、来店前に確認したいルールが中心です。",
        "主题集中在店铺规则、付款方式和注意事项，适合先看规则再行动。",
    ),
    "location_access": (
        "駅からの行き方や周辺アクセスが確認されています。",
        "讨论偏向位置、交通和到店路线，属于低争议的信息整理。",
    ),
    "hygiene_environment": (
        "店内環境や設備面への反応が出ています。",
        "内容指向环境卫生和设施状态，建议以近期多条反馈综合判断。",
    ),
    "crowding_popularity": (
        "スレ内の反応が増え、混雑感や注目度が上がっています。",
        "本小时热度上升，更多人在讨论拥挤程度和关注度变化。",
    ),
    "notice_announcement": (
        "公式告知やページ更新らしき話題が出ています。",
        "出现公告或页面更新相关讨论，建议打开原帖核对来源。",
    ),
    "complaint_anomaly": (
        "気になる反応があり、手動確認した方がよい状態です。",
        "有无法安全自动归类的反馈，建议人工查看原帖，不在推送里展开。",
    ),
}


def build_bark_message(summary: dict, thread_url: str, checked_at: str) -> tuple[str, str]:
    return build_hot_alert_message(summary, thread_url, checked_at)


def build_daily_digest_message(
    summary: dict, thread_url: str, checked_at: str
) -> tuple[str, str]:
    day_count = int(summary.get("day_new_count", summary.get("new_count", 0)) or 0)
    latest_res_no = int(summary.get("latest_res_no", 0) or 0)
    ranked = _rank_topics(summary.get("topics", {}))
    hot_topics = ranked[:3]
    title = (
        f"📋 论坛日报 · {_format_date(summary.get('summary_date', ''))}"
        f"｜今日 {day_count} レス · {len(hot_topics)} 热议"
    )
    body = "\n".join(
        [
            "━━ 🔥 今日熱点 / 今日热帖 ━━",
            _format_daily_hot_topics(hot_topics, summary),
            "",
            "━━ 📌 新着要点 / 新帖速递 ━━",
            _format_daily_new_topics(summary.get("interval_topics", summary.get("topics", {}))),
            "",
            "━━ 📊 今日データ / 今日数据 ━━",
            f"新規レス：{day_count}件  最新：#{latest_res_no}",
            f"高頻テーマ：{_format_topic_names(ranked[:5])}",
            "─────────────────",
            "通知を開くと元スレへ / 点击查看完整论坛页 →",
        ]
    )
    body = _clip_body(body)
    assert_safe_data({"title": title, "message": body})
    return title, body


def build_hot_alert_message(
    summary: dict, thread_url: str, checked_at: str
) -> tuple[str, str]:
    interval_count = int(summary.get("interval_new_count", summary.get("new_count", 0)) or 0)
    latest_res_no = int(summary.get("latest_res_no", 0) or 0)
    res_range = summary.get("interval_res_range", summary.get("res_range", "-")) or "-"
    ranked = _rank_topics(summary.get("interval_topics", summary.get("topics", {})))
    topic_key = ranked[0][0] if ranked else ""
    topic_jp, topic_cn = _topic_names(topic_key)
    title = f"🔥 论坛热了｜「{topic_cn}」突破{interval_count}レス"
    body = "\n".join(
        [
            f"神戸妻スレ · 本次新增{interval_count}レス · 最新#{latest_res_no}",
            f"範囲 / 范围：{res_range}",
            "",
            "━━ 💬 主要論点 / 核心讨论 ━━",
            _format_hot_viewpoints(ranked[:3]),
            "",
            "━━ ✍️ 安全要約 / 安全改写 ━━",
            _format_hot_takeaway(topic_key),
            "",
            "─────────────────",
            "通知を開くと元スレへ / 点击查看原帖 →",
        ]
    )
    body = _clip_body(body)
    assert_safe_data({"title": title, "message": body})
    return title, body


def send_bark_notification(
    bark_key: str,
    title: str,
    message: str,
    timeout: float = 10.0,
    link_url: str = "",
    group: str = "",
    level: str = "",
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
    params = {}
    if link_url:
        params["url"] = link_url
    if group:
        params["group"] = group
    if level:
        params["level"] = level
    if params:
        url += "?" + urlencode(params)
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


def _format_daily_hot_topics(ranked: list[tuple[str, int]], summary: dict) -> str:
    if not ranked:
        return "本日は目立つテーマなし / 今天没有明显热议主题"
    lines = []
    for index, (topic, count) in enumerate(ranked, start=1):
        jp_name, cn_name = _topic_names(topic)
        jp_summary, cn_summary = TOPIC_SUMMARIES[topic]
        mood_jp, mood_cn = _infer_mood(topic, count)
        lines.append(
            "\n".join(
                [
                    f"{_circled(index)} {jp_name} / {cn_name}",
                    f"   店舗スレ · {count}レス · {mood_jp} / {mood_cn}",
                    f"   ── 走向 JP：{jp_summary}",
                    f"   ── 走向 CN：{cn_summary}",
                    f"   ── 关键词：{_keyword_line(topic)}",
                ]
            )
        )
    return "\n\n".join(lines)


def _format_daily_new_topics(topics: dict) -> str:
    ranked = _rank_topics(topics)[:3]
    if not ranked:
        return "新着で安全に要約できるテーマなし / 暂无可安全概括的新主题"
    lines = []
    for index, (topic, count) in enumerate(ranked, start=1):
        jp_name, cn_name = _topic_names(topic)
        _, cn_summary = TOPIC_SUMMARIES[topic]
        lines.append(f"{_circled(index)} {jp_name} / {cn_name} · {count}レス · {cn_summary}")
    return "\n".join(lines)


def _format_hot_viewpoints(ranked: list[tuple[str, int]]) -> str:
    if not ranked:
        return "明確なテーマなし / 暂无明确主题"
    lines = []
    for topic, count in ranked:
        jp_name, cn_name = _topic_names(topic)
        jp_summary, cn_summary = TOPIC_SUMMARIES[topic]
        lines.append(f"{jp_name} — {jp_summary}（{count}レス）")
        lines.append(f"{cn_name} — {cn_summary}")
    return "\n".join(lines)


def _format_hot_takeaway(topic: str) -> str:
    if topic not in TOPIC_SUMMARIES:
        return "原文引用なし。安全に分類できないため、元スレで確認してください。"
    jp_name, cn_name = _topic_names(topic)
    return (
        f"「{jp_name}」が中心。原文引用ではなく、店铺级别的安全改写："
        f"{cn_name}相关讨论升温，但具体判断仍需打开原帖人工确认。"
    )


def _format_topic_names(ranked: list[tuple[str, int]]) -> str:
    if not ranked:
        return "なし / 无"
    return " · ".join(_topic_names(topic)[1] for topic, _ in ranked)


def _keyword_line(topic: str) -> str:
    return " · ".join(TOPIC_KEYWORDS.get(topic, ("確認", "讨论", "更新"))[:5])


def _rank_topics(topics: dict) -> list[tuple[str, int]]:
    ranked = [
        (topic, int(count))
        for topic, count in topics.items()
        if topic in TOPIC_LABELS and int(count or 0) > 0
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def _topic_names(topic: str) -> tuple[str, str]:
    return TOPIC_LABELS.get(topic, ("スレ全体", "论坛整体"))


def _infer_mood(topic: str, count: int) -> tuple[str, str]:
    if topic == "complaint_anomaly":
        return ("確認推奨", "需人工确认")
    if topic in {"notice_announcement", "pricing_campaign"}:
        return ("情報整理", "信息整理")
    if count >= 3:
        return ("議論中", "讨论中")
    return ("様子見", "观望")


def _format_date(summary_date: str) -> str:
    if not summary_date:
        return "今日"
    parts = summary_date.split("-")
    if len(parts) != 3:
        return summary_date
    return f"{int(parts[1])}月{int(parts[2])}日"


def _circled(index: int) -> str:
    return ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"][index - 1]


def _clip_body(body: str, limit: int = 850) -> str:
    if len(body) <= limit:
        return body
    clipped = body[: limit - 20].rstrip()
    return f"{clipped}\n…\n点击查看完整论坛页 →"
