import unittest
from urllib.parse import unquote

from notifier import build_bark_message, normalize_bark_key, send_bark_notification
from safety import assert_safe_data


class NotifierTests(unittest.TestCase):
    def test_build_bark_message_uses_digest_card_layout(self):
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

        self.assertEqual(title, "今日论坛速览｜神戸妻｜新3 / 今日8")
        self.assertIn("最新 #12342｜#12340-#12342", message)
        self.assertIn("【热帖速览】", message)
        self.assertIn("- 预约和等待情况被反复提到，建议关注可约状态", message)
        self.assertIn("标签：预约等待｜4件", message)
        self.assertIn("要点：讨论重点偏向预约难度、空き情况、等待时间或现场混杂度。", message)
        self.assertIn("【新帖速递】", message)
        self.assertIn("- 价格、优惠或活动信息有新讨论", message)
        self.assertIn("【人工确认】1件无法安全概括：#12342 等", message)
        self.assertIn("点开通知查看原帖", message)
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
            title="今日论坛速览｜神戸妻｜新1 / 今日1",
            message="新增 1 件",
            link_url="https://bakusai.com/thread/example/",
            opener=fake_urlopen,
        )

        decoded_url = unquote(urls[0])
        self.assertIn("https://api.day.app/abc/今日论坛速览｜神戸妻｜新1 / 今日1/新增 1 件", decoded_url)
        self.assertIn("url=https://bakusai.com/thread/example/", decoded_url)

    def test_normalize_bark_key_accepts_full_api_url(self):
        self.assertEqual(
            normalize_bark_key("https://api.day.app/abc123/测试"),
            "abc123",
        )
        self.assertEqual(normalize_bark_key("abc123"), "abc123")


if __name__ == "__main__":
    unittest.main()
