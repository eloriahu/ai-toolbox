from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


source_matrix = load_module(
    "source_matrix", "plugins/research-tools/scripts/source_matrix.py"
)
market_snapshot = load_module(
    "market_snapshot", "plugins/finance-tools/scripts/market_snapshot.py"
)
return_metrics = load_module(
    "return_metrics", "plugins/quant-tools/scripts/return_metrics.py"
)
workflow_validator = load_module(
    "workflow_validator", "plugins/automation-tools/scripts/validate_workflow.py"
)


class SourceMatrixTests(unittest.TestCase):
    def test_renders_and_escapes_markdown(self):
        output = source_matrix.render_matrix(
            [
                {
                    "title": "Primary | source",
                    "url": "https://example.com/report",
                    "published_at": "2026-09-21",
                    "claim": "Supports the main claim",
                }
            ]
        )
        self.assertIn("Primary \\| source", output)
        self.assertIn("[example.com](https://example.com/report)", output)

    def test_rejects_non_http_url(self):
        with self.assertRaises(ValueError):
            source_matrix.render_matrix(
                [{"title": "Bad", "url": "file:///tmp/a", "claim": "No"}]
            )


class MarketSnapshotTests(unittest.TestCase):
    def test_builds_provenance_and_missing_data_context(self):
        class History:
            def iterrows(self):
                yield datetime(2026, 9, 18, tzinfo=timezone.utc), {
                    "Open": 100.0,
                    "High": 105.0,
                    "Low": 99.0,
                    "Close": 103.0,
                    "Volume": float("nan"),
                }

        snapshot = market_snapshot.build_snapshot(
            ticker="TEST",
            period="1mo",
            interval="1d",
            auto_adjust=True,
            history=History(),
            metadata={"currency": "USD", "exchangeTimezoneName": "America/New_York"},
            retrieved_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        )

        self.assertEqual(snapshot["schemaVersion"], 1)
        self.assertEqual(snapshot["currency"], "USD")
        self.assertTrue(snapshot["adjustment"]["autoAdjusted"])
        self.assertEqual(snapshot["missingData"]["nullValuesByField"]["volume"], 1)
        self.assertIsNone(snapshot["rows"][0]["volume"])


class ReturnMetricTests(unittest.TestCase):
    def test_calculates_total_return_and_drawdown(self):
        result = return_metrics.calculate_metrics(
            [
                (date(2026, 1, 1), 100.0),
                (date(2026, 1, 2), 120.0),
                (date(2026, 1, 3), 90.0),
                (date(2026, 1, 4), 110.0),
            ]
        )
        self.assertAlmostEqual(result["totalReturn"], 0.10)
        self.assertAlmostEqual(result["maxDrawdown"], -0.25)
        self.assertEqual(result["observations"], 4)

    def test_reads_price_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prices.csv"
            path.write_text("date,close\n2026-01-01,10\n2026-01-02,11\n", encoding="utf-8")
            rows = return_metrics.read_prices(path)
            self.assertEqual(rows[-1], (date(2026, 1, 2), 11.0))

    def test_reads_market_snapshot_and_retains_provenance(self):
        snapshot = {
            "schemaVersion": 1,
            "ticker": "TEST",
            "provider": "Example provider",
            "retrievedAt": "2026-09-21T00:00:00+00:00",
            "interval": "1d",
            "currency": "USD",
            "adjustment": {"autoAdjusted": True},
            "rows": [
                {"timestamp": "2026-09-18T00:00:00+00:00", "close": 100},
                {"timestamp": "2026-09-19T00:00:00+00:00", "close": None},
                {"timestamp": "2026-09-20T00:00:00+00:00", "close": 105},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            rows, source = return_metrics.read_price_file(path)

        self.assertEqual(
            rows[-1], (datetime(2026, 9, 20, tzinfo=timezone.utc), 105.0)
        )
        self.assertEqual(source["ticker"], "TEST")
        self.assertEqual(source["usedRows"], 2)
        self.assertEqual(source["missingCloseRows"], 1)

    def test_preserves_intraday_observation_times(self):
        snapshot = {
            "schemaVersion": 1,
            "rows": [
                {"timestamp": "2026-09-18T09:00:00+08:00", "close": 100},
                {"timestamp": "2026-09-18T10:00:00+08:00", "close": 101},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            rows, _ = return_metrics.read_market_snapshot(path)

        result = return_metrics.calculate_metrics(rows, periods_per_year=1_638)
        self.assertEqual(result["observations"], 2)
        self.assertIn("T09:00:00", result["startDate"])

    def test_uses_configurable_annualization_factor(self):
        rows = [
            (date(2026, 1, 1), 100.0),
            (date(2026, 1, 8), 101.0),
            (date(2026, 1, 15), 99.0),
        ]
        weekly = return_metrics.calculate_metrics(rows, periods_per_year=52)
        daily = return_metrics.calculate_metrics(rows, periods_per_year=252)
        self.assertEqual(weekly["periodsPerYear"], 52)
        self.assertLess(weekly["annualizedVolatility"], daily["annualizedVolatility"])


class WorkflowValidatorTests(unittest.TestCase):
    def test_example_is_valid(self):
        example = json.loads(
            (ROOT / "plugins/automation-tools/examples/workflow-spec.json").read_text(
                encoding="utf-8"
            )
        )
        result = workflow_validator.validate_workflow(example)
        self.assertTrue(result["valid"])
        self.assertEqual(result["approvalSteps"], ["send-brief"])

    def test_external_write_requires_approval(self):
        spec = {
            "name": "unsafe",
            "trigger": {"type": "manual"},
            "steps": [
                {
                    "id": "send",
                    "action": "send message",
                    "risk": "external-write",
                    "approval_required": False,
                }
            ],
        }
        with self.assertRaises(ValueError):
            workflow_validator.validate_workflow(spec)


if __name__ == "__main__":
    unittest.main()
