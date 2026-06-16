import os
import unittest
from unittest.mock import patch

from config import Config, load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_reads_environment(self):
        env = {
            "TARGET_URL": "https://bakusai.com/thread/example/",
            "BARK_KEY": "test-key",
            "STATE_FILE": "custom-state.json",
            "SUMMARY_DIR": "summaries",
            "REQUEST_TIMEOUT": "20",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_config()

        self.assertEqual(
            config,
            Config(
                target_url="https://bakusai.com/thread/example/",
                bark_key="test-key",
                state_file="custom-state.json",
                summary_dir="summaries",
                request_timeout=20.0,
            ),
        )

    def test_load_config_requires_target_url(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                load_config()


if __name__ == "__main__":
    unittest.main()
