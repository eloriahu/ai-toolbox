from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "plugins" / "fundamental-tools" / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


filing = load("filing_change")
expectations = load("expectations_bridge")
ownership = load("ownership_flow")
extract = load("filing_extract")


class EvidenceBridgeTests(unittest.TestCase):
    def test_filing_delta_retains_both_page_sources(self):
        old = {"issuer": "Example Ltd", "filing_type": "annual", "published_at": "2025-03-01T09:00:00+08:00",
               "source_id": "old", "source_url": "https://example.test/old",
               "sections": [{"key": "risk", "heading": "Risks", "text": "Revenue was 100.", "page": 4}]}
        new = {**old, "published_at": "2026-03-01T09:00:00+08:00", "source_id": "new",
               "source_url": "https://example.test/new",
               "sections": [{"key": "risk", "heading": "Risks", "text": "Revenue was 120.", "page": 5}]}
        result = filing.compare({"prior": old, "current": new})
        self.assertEqual(result["schema"], "filing_change/v1")
        self.assertTrue(result["changes"][0]["numbers_changed"])
        self.assertEqual(result["changes"][0]["prior"]["page"], 4)
        self.assertEqual(result["changes"][0]["current"]["source_id"], "new")
        self.assertEqual(result["changes"][0]["review_status"], "analyst_review_required")
        with self.assertRaises(ValueError):
            filing.compare({"prior": new, "current": old})

    def test_expectations_exact_matching_and_new_rows(self):
        row = {"metric": "EPS", "fiscal_period": "FY27", "basis": "adjusted",
               "currency": "TWD", "unit": "per_share", "statistic": "median",
               "value": "10.00", "source_ids": ["p"]}
        prior = {"issuer": "Example Ltd", "listing": "1234 TW", "provider": "user-export",
                 "as_of": "2026-01-01T12:00:00+08:00", "estimates": [row]}
        current = {**prior, "as_of": "2026-04-01T12:00:00+08:00",
                   "estimates": [{**row, "value": "11.25", "source_ids": ["c"]},
                                 {**row, "fiscal_period": "FY28", "value": "12"}]}
        result = expectations.compare({"prior": prior, "current": current})
        self.assertEqual(result["changes"][0]["absolute_change"], "1.25")
        self.assertEqual(result["changes"][0]["percent_change"], "12.500")
        self.assertEqual(result["changes"][1]["status"], "new")
        with self.assertRaises(ValueError):
            expectations.compare({"prior": prior, "current": {**current, "provider": "other"}})

    def test_ownership_and_flow_are_separate(self):
        result = ownership.build({"market": "TW", "symbol": "2330",
            "flows": [{"date": "2026-09-21", "investor_category": "Foreign_Investor",
                       "buy": 100, "sell": 40, "unit": "shares", "source_id": "flow"}],
            "holdings": [{"holder": "Example Fund", "stake_percent": "2.5",
                          "ownership_type": "beneficial", "as_of": "2026-09-20",
                          "source_id": "filing", "source_url": "https://example.test/filing"}]})
        self.assertEqual(result["flows"][0]["net"], "60")
        self.assertEqual(result["holdings"][0]["stake_percent"], "2.5")
        self.assertEqual(result["quality"]["status"], "ready")
        with self.assertRaises(ValueError):
            ownership.build({"market": "TW", "symbol": "2330", "flows": [
                {"date": "2026-09-21", "investor_category": "Foreign_Investor", "buy": 100,
                 "sell": 40, "net": 70, "unit": "shares", "source_id": "flow"}]})

    def test_finmind_requires_token_without_network(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "FINMIND_TOKEN"):
                ownership.fetch_finmind("2330", "2026-09-01", "2026-09-02")

    def test_finmind_adapter_maps_share_flows_without_exposing_token(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"status": 200, "data": [{"date": "2026-09-01", "stock_id": "2330", "name": "Foreign_Investor", "buy": 100, "sell": 40}]}'

        with patch.dict("os.environ", {"FINMIND_TOKEN": "secret-test-token"}):
            with patch.object(ownership, "urlopen", return_value=Response()):
                result = ownership.fetch_finmind("2330", "2026-09-01", "2026-09-02")
        self.assertEqual(result["flows"][0]["net"], "60")
        self.assertEqual(result["flows"][0]["unit"], "shares")
        self.assertNotIn("secret-test-token", str(result))

    def test_extract_rejects_missing_local_file(self):
        with self.assertRaises(ValueError):
            extract.extract(ROOT / "missing-filing.pdf", issuer="X", filing_type="annual",
                            published_at="2026-01-01T00:00:00+08:00", source_id="s",
                            source_url="https://example.test")


if __name__ == "__main__":
    unittest.main()
