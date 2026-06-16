import unittest
from pathlib import Path

from parser import parse_thread_metadata, summarize_shop_topics
from safety import assert_safe_data


FIXTURE = Path(__file__).parent / "fixtures" / "sample_thread.html"


class ParserTests(unittest.TestCase):
    def test_parse_thread_metadata_extracts_latest_number_and_hash(self):
        html = FIXTURE.read_text(encoding="utf-8")

        metadata = parse_thread_metadata(html)

        self.assertEqual(metadata.latest_res_no, 12342)
        self.assertEqual(metadata.latest_time, "2026-06-16 10:00")
        self.assertEqual(len(metadata.page_hash), 64)
        assert_safe_data(metadata.to_dict())

    def test_summarize_shop_topics_counts_safe_categories(self):
        html = FIXTURE.read_text(encoding="utf-8")

        summary = summarize_shop_topics(
            html,
            previous_res_no=12339,
            summary_date="2026-06-16",
        )

        self.assertEqual(summary["summary_date"], "2026-06-16")
        self.assertEqual(summary["new_count"], 3)
        self.assertEqual(summary["latest_res_no"], 12342)
        self.assertEqual(summary["topics"]["reservation_wait"], 1)
        self.assertEqual(summary["topics"]["pricing_campaign"], 1)
        self.assertEqual(summary["topics"]["reception_system"], 1)
        self.assertEqual(summary["res_range"], "#12340-#12342")
        assert_safe_data(summary)

    def test_sensitive_detail_is_only_marked_for_manual_check(self):
        html = """
        <article><span>#100</span><time>2026-06-16 10:00</time><p>予約の話。</p></article>
        <article><span>#101</span><time>2026-06-16 10:10</time><p>NG word nn/ns appears here.</p></article>
        """

        summary = summarize_shop_topics(
            html,
            previous_res_no=99,
            summary_date="2026-06-16",
        )

        self.assertEqual(summary["topics"]["reservation_wait"], 1)
        self.assertEqual(summary["topics"]["needs_manual_check"], 1)
        self.assertEqual(summary["manual_check_ranges"], ["#101"])
        assert_safe_data(summary)

    def test_bakusai_article_ids_take_priority_over_thread_id(self):
        html = """
        <a href="/thr_res/acode=18/ctgid=103/bid=436/tid=13315868/tp=1/">thread</a>
        <dl id="res_list">
          <div class="article res_list_article " id="res448">
            <span class="resnumb">448</span><span>2026-06-16 13:00</span>
            <div class="resbody">予約について。</div>
          </div>
          <div class="article res_list_article " id="res449">
            <span class="resnumb">449</span><span>2026-06-16 14:00</span>
            <div class="resbody">料金について。</div>
          </div>
        </dl>
        """

        metadata = parse_thread_metadata(html)
        summary = summarize_shop_topics(html, previous_res_no=447, summary_date="2026-06-16")

        self.assertEqual(metadata.latest_res_no, 449)
        self.assertEqual(summary["new_count"], 2)
        self.assertEqual(summary["res_range"], "#448-#449")
        assert_safe_data(summary)


if __name__ == "__main__":
    unittest.main()
