from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "fundamental-tools" / "scripts" / "consensus_challenge.py"
spec = importlib.util.spec_from_file_location("consensus_challenge", SCRIPT)
consensus_challenge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(consensus_challenge)


def example():
    report_date = "2026-09-15T09:00:00+08:00"
    views = []
    sources = [
        {"id": "filing", "origin": "https://example.test/filing", "independence_group": "issuer-filing",
         "published_at": "2026-09-01T09:00:00+08:00"},
        {"id": "reg", "origin": "https://example.test/regulator", "independence_group": "regulator",
         "published_at": "2026-09-14T09:00:00+08:00"},
    ]
    for house in ("A", "A2", "B", "C", "D", "E"):
        sources.append({"id": f"report-{house}", "origin": f"https://example.test/{house}",
                        "house_id": house, "independence_group": f"research-{house}",
                        "published_at": report_date})
        views.append({"house_id": house, "thesis_id": "t1", "horizon": "FY27",
                      "stance": "opposes" if house == "E" else "supports",
                      "published_at": report_date, "source_id": f"report-{house}",
                      "premise_ids": ["p1"], "basis_source_ids": ["filing"],
                      "reviewed_full_text": True, "addressed_counterevidence_ids": []})
    return {
        "as_of": "2026-09-20T16:00:00+08:00",
        "entity": {"name": "Example Semiconductor", "primary_symbol": "1234 TW"},
        "eligible_houses": [{"id": house, "group": "A" if house == "A2" else house}
                            for house in ("A", "A2", "B", "C", "D", "E")],
        "universe_basis": "Synthetic five-group coverage universe for a controlled test",
        "sources": sources,
        "theses": [{"id": "t1", "statement": "Capacity scarcity sustains margins",
                    "direction": "bullish", "horizon": "FY27",
                    "premises": [{"id": "p1", "statement": "Supply remains constrained",
                                  "source_ids": ["filing"],
                                  "falsifier": "New certified capacity exceeds demand by FY27"}]}],
        "views": views,
        "counterevidence": [{"id": "c1", "premise_id": "p1",
                             "statement": "A regulator reports new capacity approvals",
                             "source_ids": ["reg"], "status": "primary_checked"}],
    }


class ConsensusChallengeTests(unittest.TestCase):
    def test_majority_is_by_distinct_house_group_and_same_thesis(self):
        result = consensus_challenge.build(example())
        gate = result["analyses"][0]["mainstream_gate"]
        self.assertEqual(gate["state"], "established")
        self.assertEqual(gate["eligible_house_groups"], 5)
        self.assertEqual(gate["supporting_groups"], 4)
        self.assertEqual(gate["support_share_of_universe"], "0.8")
        self.assertEqual(result["analyses"][0]["shared_basis_groups"][0]["supporting_views"], 4)
        self.assertEqual(result["challenge_queue"][0]["unaddressed_in_reviewed_sample_ids"], ["c1"])
        self.assertEqual(result["challenge_queue"][0]["novelty_status"], "not_established")

    def test_directional_agreement_alone_does_not_create_mainstream_thesis(self):
        payload = example()
        payload["theses"].append({"id": "t2", "statement": "Pricing rises for another reason",
                                  "direction": "bullish", "horizon": "FY27",
                                  "premises": [{"id": "p2", "statement": "Demand accelerates", "source_ids": [],
                                                "falsifier": "Demand growth stalls"}]})
        for view in payload["views"]:
            if view["house_id"] in {"C", "D"}:
                view["thesis_id"] = "t2"
                view["premise_ids"] = ["p2"]
        result = consensus_challenge.build(payload)
        self.assertTrue(all(row["mainstream_gate"]["state"] == "not_established"
                            for row in result["analyses"]))

    def test_unknown_universe_and_partial_report_review_limit_claim(self):
        payload = example()
        payload["eligible_houses"] = []
        payload["universe_basis"] = ""
        payload["views"][0]["reviewed_full_text"] = False
        result = consensus_challenge.build(payload)
        self.assertEqual(result["analyses"][0]["mainstream_gate"]["state"], "unverified_universe")
        self.assertEqual(result["challenge_queue"][0]["coverage_state"], "partial_or_unknown")
        self.assertEqual(result["challenge_queue"][0]["unaddressed_in_reviewed_sample_ids"], [])
        self.assertEqual(result["quality"]["status"], "limited")

    def test_addressed_counterevidence_is_not_marked_unaddressed(self):
        payload = example()
        payload["views"][2]["addressed_counterevidence_ids"] = ["c1"]
        result = consensus_challenge.build(payload)
        self.assertEqual(result["challenge_queue"][0]["unaddressed_in_reviewed_sample_ids"], [])
        self.assertEqual(result["challenge_queue"][0]["priority"], "investigate")

    def test_stale_views_and_bad_lineage_are_not_silent(self):
        payload = example()
        for view in payload["views"]:
            if view["house_id"] in {"C", "D"}:
                view["published_at"] = "2025-01-01T09:00:00+08:00"
        for source in payload["sources"]:
            if source["id"] in {"report-C", "report-D"}:
                source["published_at"] = "2025-01-01T09:00:00+08:00"
        result = consensus_challenge.build(payload)
        self.assertEqual(result["analyses"][0]["mainstream_gate"]["state"], "not_established")
        self.assertEqual(result["analyses"][0]["mainstream_gate"]["stale_reports_excluded"], 2)
        bad = copy.deepcopy(example())
        bad["views"][0]["basis_source_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unknown sources"):
            consensus_challenge.build(bad)
        bad = copy.deepcopy(example())
        bad["views"][0]["source_id"] = "filing"
        with self.assertRaisesRegex(ValueError, "house-specific report source"):
            consensus_challenge.build(bad)

    def test_future_sources_and_naive_timestamps_fail(self):
        payload = example()
        payload["sources"][0]["published_at"] = "2026-10-01T09:00:00+08:00"
        with self.assertRaisesRegex(ValueError, "after pack as_of"):
            consensus_challenge.build(payload)
        payload = example()
        payload["as_of"] = "2026-09-20T16:00:00"
        with self.assertRaisesRegex(ValueError, "timezone offset"):
            consensus_challenge.build(payload)
        payload = example()
        payload["views"][0]["horizon"] = "FY28"
        with self.assertRaisesRegex(ValueError, "horizon must match"):
            consensus_challenge.build(payload)

    def test_unknown_raw_report_text_is_not_copied_to_pack(self):
        payload = example()
        payload["views"][0]["full_text"] = "licensed report text must not be exported"
        payload["sources"][2]["full_text"] = "licensed source text must not be exported"
        result = consensus_challenge.build(payload)
        self.assertNotIn("licensed report text", str(result))
        self.assertNotIn("licensed source text", str(result))


if __name__ == "__main__":
    unittest.main()
