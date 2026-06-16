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
            self.assertEqual(summary["new_count"], 2)
            self.assertEqual(len(notifications), 1)
            self.assertFalse((Path(tmp) / "raw.html").exists())
            self.assertFalse((Path(tmp) / "posts.json").exists())

    def test_run_once_without_new_posts_does_not_notify(self):
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
            self.assertEqual(notifications, [])
            self.assertFalse((summary_dir / "2026-06-16.json").exists())

    def test_initial_run_counts_loaded_entries_not_latest_number_gap(self):
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
            summary = json.loads((summary_dir / "2026-06-16.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(saved["threads"]["main"]["last_seen_res_no"], 402)
            self.assertEqual(saved["threads"]["main"]["new_count_today"], 2)
            self.assertEqual(summary["new_count"], 2)


if __name__ == "__main__":
    unittest.main()
