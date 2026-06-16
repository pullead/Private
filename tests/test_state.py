import json
import tempfile
import unittest
from pathlib import Path

from safety import SafetyError
from state import ThreadState, load_state, save_state, update_thread_state


class StateTests(unittest.TestCase):
    def test_missing_state_file_returns_empty_threads(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"

            state = load_state(state_path)

            self.assertEqual(state, {"threads": {}})

    def test_update_thread_state_persists_allowed_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            thread = ThreadState(
                thread_url="https://bakusai.com/thread/example/",
                last_seen_res_no=12345,
                last_seen_hash="abc",
                last_checked_at="2026-06-16T12:00:00+09:00",
                new_count_today=2,
            )

            update_thread_state(state_path, "main", thread)

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["threads"]["main"]["last_seen_res_no"], 12345)
            self.assertEqual(saved["threads"]["main"]["new_count_today"], 2)

    def test_save_state_rejects_forbidden_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"

            with self.assertRaises(SafetyError):
                save_state(state_path, {"threads": {"main": {"raw_html": "<html>"}}})


if __name__ == "__main__":
    unittest.main()
