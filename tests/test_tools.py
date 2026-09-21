from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import date
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
