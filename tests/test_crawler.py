import json
import tempfile
import unittest
from pathlib import Path

from config import Config
from crawler import run_once


HTML = """
<article><span>#12340</span><time>2026-06-16 09:00</time><p>予約の待ち時間。</p></article>
<article><span>#12341</span><time>2026-06-16 09:30</time><p>料金キャンペーン。</p></article>
"""


class CrawlerTests(unittest.TestCase):
    def test_run_once_updates_state_and_writes_safe_summary_when_new_posts_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "https://bakusai.com/thread/example/",
                                "last_seen_res_no": 12339,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 0,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                ),
                fetcher=lambda url, timeout: HTML,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            summary = json.loads((summary_dir / "2026-06-16.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(saved["threads"]["main"]["last_seen_res_no"], 12341)
            self.assertEqual(saved["threads"]["main"]["thread_url"], "")
            self.assertEqual(summary["interval_new_count"], 2)
            self.assertEqual(summary["day_new_count"], 2)
            self.assertEqual(len(notifications), 1)
            self.assertFalse((Path(tmp) / "raw.html").exists())
            self.assertFalse((Path(tmp) / "posts.json").exists())

    def test_run_once_merges_today_topic_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            summary_dir.mkdir()
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "https://bakusai.com/thread/example/",
                                "last_seen_res_no": 12339,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 3,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (summary_dir / "2026-06-16.json").write_text(
                json.dumps(
                    {
                        "summary_date": "2026-06-16",
                        "latest_res_no": 12339,
                        "day_new_count": 3,
                        "topics": {"reservation_wait": 2, "shop_rules": 1},
                        "day_res_ranges": ["#12337-#12339"],
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                ),
                fetcher=lambda url, timeout: HTML,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            summary = json.loads((summary_dir / "2026-06-16.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(saved["threads"]["main"]["new_count_today"], 5)
            self.assertEqual(summary["day_new_count"], 5)
            self.assertEqual(summary["topics"]["reservation_wait"], 3)
            self.assertEqual(summary["topics"]["shop_rules"], 1)
            self.assertIn("#12337-#12339", summary["day_res_ranges"])
            self.assertIn("#12340-#12341", summary["day_res_ranges"])
            self.assertEqual(len(notifications), 1)

    def test_run_once_sends_hot_alert_when_interval_reaches_threshold(self):
        html = """
        <article><span>#12340</span><time>2026-06-16 09:00</time><p>予約の待ち時間。</p></article>
        <article><span>#12341</span><time>2026-06-16 09:30</time><p>料金キャンペーン。</p></article>
        <article><span>#12342</span><time>2026-06-16 09:40</time><p>ルール確認。</p></article>
        """
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "",
                                "last_seen_res_no": 12339,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 0,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                    hot_alert_threshold=3,
                    daily_digest_hour=20,
                ),
                fetcher=lambda url, timeout: html,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            self.assertEqual(result, 0)
            self.assertEqual(len(notifications), 1)
            self.assertIn("论坛热了", notifications[0][0])

    def test_run_once_suppresses_hot_alert_during_quiet_hours(self):
        html = """
        <article><span>#12340</span><time>2026-06-16 01:00</time><p>莠育ｴ・・蠕・■譎る俣縲・/p></article>
        <article><span>#12341</span><time>2026-06-16 01:10</time><p>譁咎≡繧ｭ繝｣繝ｳ繝壹・繝ｳ縲・/p></article>
        <article><span>#12342</span><time>2026-06-16 01:20</time><p>繝ｫ繝ｼ繝ｫ遒ｺ隱阪・/p></article>
        """
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "",
                                "last_seen_res_no": 12339,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 0,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                    hot_alert_threshold=3,
                    daily_digest_hour=20,
                ),
                fetcher=lambda url, timeout: html,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T02:00:00+09:00",
            )

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            summary = json.loads((summary_dir / "2026-06-16.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(notifications, [])
            self.assertEqual(saved["threads"]["main"]["last_seen_res_no"], 12342)
            self.assertEqual(summary["day_new_count"], 3)

    def test_run_once_sends_daily_digest_after_digest_hour_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            summary_dir.mkdir()
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "",
                                "last_seen_res_no": 12341,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 2,
                                "last_daily_digest_date": "",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (summary_dir / "2026-06-16.json").write_text(
                json.dumps(
                    {
                        "summary_date": "2026-06-16",
                        "latest_res_no": 12341,
                        "day_new_count": 2,
                        "topics": {"reservation_wait": 1, "shop_rules": 1},
                        "interval_topics": {"shop_rules": 1},
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                    hot_alert_threshold=2,
                    daily_digest_hour=20,
                ),
                fetcher=lambda url, timeout: HTML,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T20:05:00+09:00",
            )

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(len(notifications), 1)
            self.assertIn("论坛日报", notifications[0][0])
            self.assertEqual(saved["threads"]["main"]["last_daily_digest_date"], "2026-06-16")

    def test_run_once_without_new_posts_sends_hourly_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"
            state_path.write_text(
                json.dumps(
                    {
                        "threads": {
                            "main": {
                                "thread_url": "https://bakusai.com/thread/example/",
                                "last_seen_res_no": 12341,
                                "last_seen_hash": "",
                                "last_checked_at": "",
                                "new_count_today": 0,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            notifications = []

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="abc",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                ),
                fetcher=lambda url, timeout: HTML,
                notifier=lambda title, message: notifications.append((title, message)),
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            self.assertEqual(result, 0)
            self.assertEqual(len(notifications), 1)
            self.assertIn("论坛小时报", notifications[0][0])
            self.assertIn("本小时暂无新增回复", notifications[0][1])
            self.assertFalse((summary_dir / "2026-06-16.json").exists())

    def test_initial_run_sets_baseline_without_notification_or_summary(self):
        html = """
        <dl id="res_list">
          <div class="article res_list_article " id="res401">
            <span class="resnumb">401</span><span>2026-06-16 13:00</span>
            <div class="resbody">予約について。</div>
          </div>
          <div class="article res_list_article " id="res402">
            <span class="resnumb">402</span><span>2026-06-16 13:10</span>
            <div class="resbody">料金について。</div>
          </div>
        </dl>
        """
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                ),
                fetcher=lambda url, timeout: html,
                notifier=lambda title, message: None,
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(saved["threads"]["main"]["last_seen_res_no"], 402)
            self.assertEqual(saved["threads"]["main"]["new_count_today"], 0)
            self.assertFalse((summary_dir / "2026-06-16.json").exists())

    def test_notification_failure_does_not_fail_monitor_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            summary_dir = Path(tmp) / "daily_summary"

            result = run_once(
                Config(
                    target_url="https://bakusai.com/thread/example/",
                    bark_key="bad-key",
                    state_file=str(state_path),
                    summary_dir=str(summary_dir),
                    request_timeout=1,
                ),
                fetcher=lambda url, timeout: HTML,
                notifier=lambda title, message: (_ for _ in ()).throw(RuntimeError("bad request")),
                now_provider=lambda: "2026-06-16T12:00:00+09:00",
            )

            self.assertEqual(result, 0)
            self.assertFalse((summary_dir / "2026-06-16.json").exists())


if __name__ == "__main__":
    unittest.main()
