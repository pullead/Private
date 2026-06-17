import unittest
from urllib.parse import unquote

from notifier import (
    build_daily_digest_message,
    build_hot_alert_message,
    build_hourly_update_message,
    build_bark_message,
    normalize_bark_key,
    send_bark_notification,
)
from safety import assert_safe_data


class NotifierTests(unittest.TestCase):
    def test_build_bark_message_uses_readable_japanese_chinese_layout(self):
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

        self.assertIn("论坛热了", title)
        self.assertIn("神戸妻スレ", message)
        self.assertIn("主要論点 / 核心讨论", message)
        self.assertIn("安全要約 / 安全改写", message)
        self.assertIn("料金・キャンペーン", message)
        self.assertIn("价格与活动", message)
        self.assertNotIn("https://bakusai.com", message)
        assert_safe_data({"title": title, "message": message})

    def test_send_bark_notification_encodes_url_and_bark_options(self):
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
            title="📋 论坛日报 · 6月16日｜今日 3 レス",
            message="━━ 🔥 今日熱点 / 今日热帖 ━━",
            link_url="https://bakusai.com/thread/example/",
            group="daily-digest",
            level="passive",
            opener=fake_urlopen,
        )

        decoded_url = unquote(urls[0])
        self.assertIn("https://api.day.app/abc/📋 论坛日报", decoded_url)
        self.assertIn("url=https://bakusai.com/thread/example/", decoded_url)
        self.assertIn("group=daily-digest", decoded_url)
        self.assertIn("level=passive", decoded_url)

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
        self.assertIn("━━ 🔥 今日熱点 / 今日热帖 ━━", message)
        self.assertIn("① 予約・待ち時間 / 预约与等待", message)
        self.assertIn("━━ 📌 新着要点 / 新帖速递 ━━", message)
        self.assertIn("━━ 📊 今日データ / 今日数据 ━━", message)
        self.assertIn("─────────────────", message)
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

        self.assertIn("🔥 论坛热了｜「预约与等待」突破3レス", title)
        self.assertIn("主要論点 / 核心讨论", message)
        self.assertIn("安全要約 / 安全改写", message)
        self.assertIn("通知を開くと元スレへ / 点击查看原帖", message)
        assert_safe_data({"title": title, "message": message})

    def test_hourly_update_message_reports_no_new_posts(self):
        title, message = build_hourly_update_message(
            {
                "summary_date": "2026-06-16",
                "interval_new_count": 0,
                "day_new_count": 23,
                "latest_res_no": 473,
                "topics": {"reservation_wait": 2},
                "interval_topics": {},
            },
            "https://bakusai.com/thread/example/",
            "2026-06-16T12:00:00+09:00",
        )

        self.assertIn("论坛小时报", title)
        self.assertIn("本小时 0 レス", title)
        self.assertIn("時間更新 / 小时更新", message)
        self.assertIn("本小时暂无新增回复", message)
        self.assertIn("中日対照 / 中日对照", message)
        assert_safe_data({"title": title, "message": message})

    def test_normalize_bark_key_accepts_full_api_url(self):
        self.assertEqual(
            normalize_bark_key("https://api.day.app/abc123/测试"),
            "abc123",
        )
        self.assertEqual(normalize_bark_key("abc123"), "abc123")


if __name__ == "__main__":
    unittest.main()
