import unittest
from urllib.parse import unquote

from notifier import (
    build_daily_digest_message,
    build_hot_alert_message,
    build_bark_message,
    normalize_bark_key,
    send_bark_notification,
)
from safety import assert_safe_data


class NotifierTests(unittest.TestCase):
    def test_build_bark_message_uses_japanese_then_chinese_layout(self):
        title, message = build_bark_message(
            {
                "summary_date": "2026-06-16",
                "interval_new_count": 3,
                "day_new_count": 8,
                "latest_res_no": 12342,
                "interval_res_range": "#12340-#12342",
                "topics": {
                    "reservation_wait": 4,
                    "pricing_campaign": 2,
                    "shop_rules": 1,
                    "needs_manual_check": 1,
                },
                "interval_topics": {
                    "pricing_campaign": 2,
                    "shop_rules": 1,
                    "needs_manual_check": 1,
                },
                "manual_check_ranges": ["#12342", "#12343"],
            },
            thread_url="https://bakusai.com/thread/example/",
            checked_at="2026-06-16T12:00:00+09:00",
        )

        self.assertEqual(title, "本日の掲示板速報｜神戸妻｜新3 / 今日8")
        self.assertIn("6月16日｜最新 #12342｜#12340-#12342", message)
        self.assertIn("【本日の3行まとめ / 今日三句话】", message)
        self.assertIn("JP: 今回の新規レスは3件、本日の累計は8件です。", message)
        self.assertIn("CN: 本次新增 3 件，今日累计 8 件。", message)
        self.assertIn("JP: 主な話題は 予約・待ち時間、料金・キャンペーン、店舗ルール です。", message)
        self.assertIn("CN: 今天讨论主线集中在：预约等待、价格活动、店铺规则。", message)
        self.assertIn("[新規][店舗] JP: 予約や待ち時間が話題になっています", message)
        self.assertIn("[新帖][店铺] CN: 预约和等待情况被反复提到", message)
        self.assertIn("KW-JP: 予約 / 空き / 待ち時間 / 混雑 / 確認", message)
        self.assertIn("关键词-CN: 预约 / 空き / 等待 / 混杂 / 确认", message)
        self.assertIn("要約-JP: 予約の取りやすさ、空き状況、待ち時間、混雑具合が中心です。", message)
        self.assertIn("摘要-CN: 讨论重点偏向预约难度、空き情况、等待时间或现场混杂度。", message)
        self.assertIn("Mood: 議論中 / 讨论中", message)
        self.assertIn("JP: 1件は確認推奨：#12342 ほか / CN: 1件无法安全概括：#12342 等", message)
        self.assertIn("通知を開くと元スレへ / 点开通知查看原帖", message)
        self.assertNotIn("https://bakusai.com", message)
        assert_safe_data({"title": title, "message": message})

    def test_send_bark_notification_encodes_url(self):
        urls = []

        def fake_urlopen(request, timeout):
            urls.append(request.full_url)

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return b"ok"

            return Response()

        send_bark_notification(
            bark_key="abc",
            title="本日の掲示板速報｜神戸妻｜新1 / 今日1",
            message="新增 1 件",
            link_url="https://bakusai.com/thread/example/",
            opener=fake_urlopen,
        )

        decoded_url = unquote(urls[0])
        self.assertIn("https://api.day.app/abc/本日の掲示板速報｜神戸妻｜新1 / 今日1/新增 1 件", decoded_url)
        self.assertIn("url=https://bakusai.com/thread/example/", decoded_url)

    def test_daily_digest_message_matches_digest_style(self):
        title, message = build_daily_digest_message(
            {
                "summary_date": "2026-06-16",
                "day_new_count": 23,
                "latest_res_no": 471,
                "topics": {
                    "reservation_wait": 7,
                    "pricing_campaign": 4,
                    "shop_rules": 3,
                },
                "interval_topics": {"shop_rules": 2},
            },
            "https://bakusai.com/thread/example/",
            "2026-06-16T20:00:00+09:00",
        )

        self.assertIn("📋 论坛日报 · 6月16日｜今日 23 レス · 3 热议", title)
        self.assertIn("🔥 熱い話題 / 热帖精选", message)
        self.assertIn("1. 予約・待ち時間 / 预约等待", message)
        self.assertIn("📌 新着要点 / 新帖速递", message)
        self.assertIn("──────────────", message)
        assert_safe_data({"title": title, "message": message})

    def test_hot_alert_message_matches_alert_style(self):
        title, message = build_hot_alert_message(
            {
                "interval_new_count": 3,
                "latest_res_no": 471,
                "interval_res_range": "#469-#471",
                "interval_topics": {"reservation_wait": 3, "shop_rules": 1},
            },
            "https://bakusai.com/thread/example/",
            "2026-06-16T12:00:00+09:00",
        )

        self.assertIn("🔥 论坛热了｜「预约等待」突破3レス", title)
        self.assertIn("核心争议 / 主な見方：", message)
        self.assertIn("目前可安全复述：", message)
        self.assertIn("──────────────", message)
        assert_safe_data({"title": title, "message": message})

    def test_normalize_bark_key_accepts_full_api_url(self):
        self.assertEqual(
            normalize_bark_key("https://api.day.app/abc123/测试"),
            "abc123",
        )
        self.assertEqual(normalize_bark_key("abc123"), "abc123")


if __name__ == "__main__":
    unittest.main()
