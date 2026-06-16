import unittest
from urllib.parse import unquote

from notifier import build_bark_message, normalize_bark_key, send_bark_notification
from safety import assert_safe_data


class NotifierTests(unittest.TestCase):
    def test_build_bark_message_contains_only_safe_summary_fields(self):
        title, message = build_bark_message(
            {
                "summary_date": "2026-06-16",
                "new_count": 3,
                "latest_res_no": 12342,
                "res_range": "#12340-#12342",
                "topics": {
                    "reservation_wait": 2,
                    "pricing_campaign": 1,
                    "needs_manual_check": 1,
                },
                "manual_check_ranges": ["#12342", "#12343", "#12344"],
            },
            thread_url="https://bakusai.com/thread/example/",
            checked_at="2026-06-16T12:00:00+09:00",
        )

        self.assertEqual(title, "神戸妻 新レス3件 #12342")
        self.assertIn("范围：#12340-#12342", message)
        self.assertIn("主题：预约/等待(2)、价格/活动(1)", message)
        self.assertIn("确认：1件（#12342 等）", message)
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
            title="神戸妻 新レス1件 #1",
            message="新增 1 件",
            link_url="https://bakusai.com/thread/example/",
            opener=fake_urlopen,
        )

        decoded_url = unquote(urls[0])
        self.assertIn("https://api.day.app/abc/神戸妻 新レス1件 #1/新增 1 件", decoded_url)
        self.assertIn("url=https://bakusai.com/thread/example/", decoded_url)

    def test_normalize_bark_key_accepts_full_api_url(self):
        self.assertEqual(
            normalize_bark_key("https://api.day.app/abc123/测试"),
            "abc123",
        )
        self.assertEqual(normalize_bark_key("abc123"), "abc123")


if __name__ == "__main__":
    unittest.main()
