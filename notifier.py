from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from safety import assert_safe_data


TOPIC_LABELS = {
    "reservation_wait": ("予約・待ち時間", "预约等待"),
    "pricing_campaign": ("料金・キャンペーン", "价格活动"),
    "business_hours": ("営業時間", "营业时间"),
    "schedule_change": ("出勤・シフト", "排班变更"),
    "reception_system": ("受付・予約システム", "受付系统"),
    "shop_rules": ("店舗ルール", "店铺规则"),
    "location_access": ("アクセス", "位置交通"),
    "hygiene_environment": ("衛生・環境", "卫生环境"),
    "crowding_popularity": ("混雑・人気", "人气热度"),
    "notice_announcement": ("告知・更新", "公告更新"),
    "complaint_anomaly": ("気になる反応", "异常反馈"),
}

TOPIC_HEADLINES = {
    "reservation_wait": ("予約や待ち時間が話題になっています", "预约和等待情况被反复提到"),
    "pricing_campaign": ("料金やキャンペーンに新しい話題があります", "价格、优惠或活动信息有新讨论"),
    "business_hours": ("営業時間まわりの話題があります", "营业时间相关安排出现讨论"),
    "schedule_change": ("出勤やシフトの話題があります", "排班相关信息被提到"),
    "reception_system": ("受付や予約導線について話されています", "受付、电话或网页预约流程被讨论"),
    "shop_rules": ("店舗ルールや注意点が話題です", "规则、支付方式或注意事项是主要话题"),
    "location_access": ("アクセスや周辺情報が話題です", "位置、交通或到店路线被提到"),
    "hygiene_environment": ("店内環境や設備の話題があります", "店内环境、卫生或设施状态有讨论"),
    "crowding_popularity": ("混雑感や注目度に変化があります", "热度和拥挤程度有变化迹象"),
    "notice_announcement": ("告知や公式更新が話題です", "公告、广告或官方更新被提到"),
    "complaint_anomaly": ("気になる反応があるため確認推奨です", "出现异常反馈，建议优先人工查看"),
}

TOPIC_DETAILS = {
    "reservation_wait": (
        "予約の取りやすさ、空き状況、待ち時間、混雑具合が中心です。",
        "讨论重点偏向预约难度、空き情况、等待时间或现场混杂度。",
    ),
    "pricing_campaign": (
        "費用、割引、キャンペーン、料金ルールに関する話題です。",
        "要点集中在费用变化、优惠活动、套餐或活动规则。",
    ),
    "business_hours": (
        "開店・閉店、臨時休業、祝日対応などの確認が中心です。",
        "可能涉及开店闭店、临时休业、节假日安排等信息。",
    ),
    "schedule_change": (
        "シフト面の変化が話題ですが、個人情報には踏み込みません。",
        "只提示排班层面有变化，不展开具体个人内容。",
    ),
    "reception_system": (
        "電話対応、Web予約、受付の流れ、システム利用感が中心です。",
        "可能涉及电话响应、网站预约、受付流程或系统使用体验。",
    ),
    "shop_rules": (
        "支払い、注意事項、入店前の確認事項が中心です。",
        "讨论集中在支付、规则、注意事项或到店流程。",
    ),
    "location_access": (
        "駅からの行き方、駐車、周辺の場所情報が中心です。",
        "可能涉及路线、车站、停车或周边位置。",
    ),
    "hygiene_environment": (
        "店内環境、清潔感、設備まわりの話題です。",
        "讨论偏向店内环境、清洁状态或设施体验。",
    ),
    "crowding_popularity": (
        "スレの活発さ、注目度、混雑感が上がっている可能性があります。",
        "可理解为论坛热度、关注度或拥挤感上升。",
    ),
    "notice_announcement": (
        "公式情報、広告、ページ更新の可能性があります。",
        "可能是官方信息、广告内容或页面更新。",
    ),
    "complaint_anomaly": (
        "自動要約で展開せず、元スレでの確認を推奨します。",
        "内容不适合自动展开，建议打开原帖核对。",
    ),
}

TOPIC_KEYWORDS = {
    "reservation_wait": (("予約", "空き", "待ち時間", "混雑", "確認"), ("预约", "空き", "等待", "混杂", "确认")),
    "pricing_campaign": (("料金", "割引", "イベント", "費用", "ルール"), ("价格", "优惠", "活动", "费用", "规则")),
    "business_hours": (("営業", "休業", "時間", "開店", "閉店"), ("营业", "休业", "时间", "开店", "闭店")),
    "schedule_change": (("出勤", "シフト", "変更", "予定", "確認"), ("出勤", "排班", "变更", "安排", "确认")),
    "reception_system": (("受付", "電話", "Web予約", "応答", "システム"), ("受付", "电话", "网页预约", "响应", "系统")),
    "shop_rules": (("ルール", "支払い", "注意点", "流れ", "確認"), ("规则", "支付", "注意事项", "流程", "确认")),
    "location_access": (("場所", "駅", "駐車", "アクセス", "周辺"), ("位置", "车站", "停车", "交通", "周边")),
    "hygiene_environment": (("環境", "衛生", "設備", "清潔", "部屋"), ("环境", "卫生", "设施", "清洁", "房间")),
    "crowding_popularity": (("人気", "混雑", "注目", "活発", "反応"), ("人气", "拥挤", "关注", "活跃", "反应")),
    "notice_announcement": (("告知", "広告", "公式", "更新", "通知"), ("公告", "广告", "官方", "更新", "通知")),
    "complaint_anomaly": (("確認", "注意", "反応", "問題", "違和感"), ("确认", "注意", "反馈", "问题", "异常")),
}


def build_bark_message(summary: dict, thread_url: str, checked_at: str) -> tuple[str, str]:
    interval_count = int(summary.get("interval_new_count", summary.get("new_count", 0)) or 0)
    day_count = int(summary.get("day_new_count", interval_count) or 0)
    latest_res_no = int(summary.get("latest_res_no", 0) or 0)
    interval_range = summary.get("interval_res_range", summary.get("res_range", "")) or "-"
    title = f"本日の掲示板速報｜神戸妻｜新{interval_count} / 今日{day_count}"
    message = "\n".join(
        [
            f"{_format_date(summary.get('summary_date', ''))}｜最新 #{latest_res_no}｜{interval_range}",
            "",
            "【本日の3行まとめ / 今日三句话】",
            _format_overview(summary),
            "",
            "【要約カード / 摘要卡片】",
            _format_cards(summary.get("topics", {}), interval_range, limit=3),
            "",
            f"【確認枠 / 人工确认】{_format_manual(summary.get('interval_topics', summary.get('topics', {})), summary.get('manual_check_ranges', []))}",
            "通知を開くと元スレへ / 点开通知查看原帖",
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
                f"1. JP: 今回の新規レスは{interval_count}件、本日の累計は{day_count}件です。",
                f"   CN: 本次新增 {interval_count} 件，今日累计 {day_count} 件。",
                "2. JP: 店舗レベルの明確な話題はまだ薄めです。",
                "   CN: 暂时没有识别到明显的店铺级讨论主线。",
                "3. JP: 最新レスは元スレで確認してください。",
                "   CN: 建议点开原帖查看最新レス上下文。",
            ]
        )

    jp_labels = "、".join(TOPIC_LABELS[topic][0] for topic, _ in ranked[:3])
    cn_labels = "、".join(TOPIC_LABELS[topic][1] for topic, _ in ranked[:3])
    manual_count = int(topics.get("needs_manual_check", 0) or 0)
    return "\n".join(
        [
            f"1. JP: 今回の新規レスは{interval_count}件、本日の累計は{day_count}件です。",
            f"   CN: 本次新增 {interval_count} 件，今日累计 {day_count} 件。",
            f"2. JP: 主な話題は {jp_labels} です。",
            f"   CN: 今天讨论主线集中在：{cn_labels}。",
            f"3. JP: {manual_count}件は自動展開せず、確認枠に回しています。",
            f"   CN: 其中 {manual_count} 件不适合自动展开，建议作为人工确认入口。",
        ]
    )


def _format_cards(topics: dict, res_range: str, limit: int) -> str:
    ranked = _rank_topics(topics)
    if not ranked:
        return "JP: 安全に要約できる店舗テーマはまだありません。\nCN: 暂无可安全概括的店铺级主题。"

    cards = []
    for topic, count in ranked[:limit]:
        jp_label, cn_label = TOPIC_LABELS[topic]
        jp_headline, cn_headline = TOPIC_HEADLINES[topic]
        jp_detail, cn_detail = TOPIC_DETAILS[topic]
        jp_keywords, cn_keywords = TOPIC_KEYWORDS[topic]
        mood_jp, mood_cn = _infer_mood(topic, count)
        cards.append(
            "\n".join(
                [
                    f"[{_topic_badge(topic)[0]}][店舗] JP: {jp_headline}",
                    f"[{_topic_badge(topic)[1]}][店铺] CN: {cn_headline}",
                    f"KW-JP: {' / '.join(jp_keywords)}",
                    f"关键词-CN: {' / '.join(cn_keywords)}",
                    f"要約-JP: {jp_detail}",
                    f"摘要-CN: {cn_detail}",
                    f"Data: {count}件｜{res_range}｜Mood: {mood_jp} / {mood_cn}",
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


def _topic_badge(topic: str) -> tuple[str, str]:
    if topic in {"crowding_popularity", "complaint_anomaly"}:
        return ("注目", "热帖")
    return ("新規", "新帖")


def _infer_mood(topic: str, count: int) -> tuple[str, str]:
    if topic == "complaint_anomaly":
        return ("意見分かれ", "分歧")
    if topic in {"notice_announcement", "pricing_campaign"}:
        return ("前向き", "积极")
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


def _format_manual(topics: dict, ranges: list[str]) -> str:
    count = int(topics.get("needs_manual_check", 0) or 0)
    if count <= 0:
        return "JP: なし / CN: 无"
    if not ranges:
        return f"JP: {count}件は安全に自動要約しません。 / CN: {count}件无法安全概括，建议人工查看。"
    if len(ranges) == 1:
        return f"JP: {count}件は確認推奨：{ranges[0]} / CN: {count}件无法安全概括：{ranges[0]}"
    return f"JP: {count}件は確認推奨：{ranges[0]} ほか / CN: {count}件无法安全概括：{ranges[0]} 等"
