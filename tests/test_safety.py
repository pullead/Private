import unittest

from safety import SafetyError, assert_safe_data, find_unsafe_entries


class SafetyTests(unittest.TestCase):
    def test_safe_shop_level_summary_passes(self):
        payload = {
            "summary_date": "2026-06-16",
            "latest_res_no": 12345,
            "topics": {"reservation_wait": 3, "pricing_campaign": 1},
            "manual_check_ranges": ["#12340-#12345"],
        }

        self.assertEqual(find_unsafe_entries(payload), set())
        assert_safe_data(payload)

    def test_forbidden_output_is_rejected(self):
        payloads = [
            {"girl_name": "x"},
            {"topics": {"nn/ns": 1}},
            {"message": "帖子正文 should not appear"},
            {"raw_html": "<html></html>"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(SafetyError):
                    assert_safe_data(payload)


if __name__ == "__main__":
    unittest.main()
