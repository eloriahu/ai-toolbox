from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


fundamental_pack = load_module(
    "fundamental_pack", "plugins/fundamental-tools/scripts/fundamental_pack.py"
)
provider_adapters = load_module(
    "provider_adapters", "plugins/fundamental-tools/scripts/provider_adapters.py"
)


def example_input():
    return {
        "as_of": "2026-09-21T16:00:00+08:00",
        "entity": {
            "name": "Example Semiconductor",
            "primary_symbol": "1234",
            "exchange": "TWSE",
            "country": "Taiwan",
            "reporting_currency": "TWD",
        },
        "sources": [
            {
                "id": "src-fy25",
                "provider": "Example Exchange",
                "source_type": "official_filing",
                "url": "https://example.test/fy25",
                "published_at": "2026-03-01T08:00:00+08:00",
                "retrieved_at": "2026-09-21T15:00:00+08:00",
            }
        ],
        "financials": {
            "periods": [
                {
                    "period_end": "2024-12-31",
                    "period_type": "FY",
                    "currency": "TWD",
                    "unit_scale": 1_000_000,
                    "basis": "reported",
                    "report_status": "audited",
                    "source_ids": ["src-fy25"],
                    "values": {
                        "revenue": 1000,
                        "gross_profit": 350,
                        "ebitda": 220,
                        "operating_income": 180,
                        "net_income": 120,
                        "operating_cash_flow": 160,
                        "capital_expenditure": -40,
                        "cash": 100,
                        "total_debt": 200,
                        "total_assets": 1400,
                        "total_equity": 800,
                        "diluted_shares": 100,
                    },
                },
                {
                    "period_end": "2025-12-31",
                    "period_type": "FY",
                    "currency": "TWD",
                    "unit_scale": 1_000_000,
                    "basis": "reported",
                    "report_status": "audited",
                    "source_ids": ["src-fy25"],
                    "values": {
                        "revenue": 1200,
                        "gross_profit": 480,
                        "ebitda": 280,
                        "operating_income": 230,
                        "interest_expense": -20,
                        "tax_expense": 40,
                        "net_income": 160,
                        "operating_cash_flow": 210,
                        "capital_expenditure": -60,
                        "cash": 140,
                        "total_debt": 220,
                        "total_assets": 1600,
                        "total_equity": 920,
                        "diluted_shares": 100,
                    },
                },
            ]
        },
        "valuation": {
            "market_data": {"price": 12, "diluted_shares": 100},
            "source_ids": ["src-fy25"],
            "dcf_assumptions": {
                "forecast_years": 3,
                "revenue_growth": [0.1, 0.08, 0.06],
                "ebit_margin": [0.19, 0.20, 0.20],
                "tax_rate": 0.2,
                "da_pct_revenue": 0.04,
                "capex_pct_revenue": 0.05,
                "nwc_pct_revenue": 0.1,
                "wacc": 0.09,
                "terminal_growth": 0.03,
                "net_debt": 80,
            },
            "scenarios": [
                {"name": "downside", "overrides": {"revenue_growth": [0.02, 0.02, 0.02], "ebit_margin": 0.15}}
            ],
        },
    }


class FundamentalPackTests(unittest.TestCase):
    def test_builds_metrics_valuation_and_scenarios(self):
        pack = fundamental_pack.build_pack(example_input())
        self.assertEqual(pack["schema"], "fundamental_pack/v1")
        self.assertEqual(pack["quality"]["status"], "ready")
        self.assertAlmostEqual(pack["metrics"]["latest"]["revenue_growth"], 0.2)
        self.assertAlmostEqual(pack["metrics"]["latest"]["gross_margin"], 0.4)
        self.assertEqual(pack["metrics"]["latest"]["free_cash_flow"], 150)
        self.assertAlmostEqual(pack["valuation"]["multiples"]["price_to_earnings"], 7.5)
        self.assertEqual([row["name"] for row in pack["valuation"]["dcf"]], ["base", "downside"])
        self.assertGreater(pack["valuation"]["dcf"][0]["value_per_share"], 0)

    def test_marks_missing_source_and_period_as_blocked(self):
        pack = fundamental_pack.build_pack(
            {
                "as_of": "2026-09-21T16:00:00+08:00",
                "entity": {},
                "sources": [],
                "financials": {"periods": []},
            }
        )
        self.assertEqual(pack["quality"]["status"], "blocked")
        self.assertIn("sources", pack["quality"]["missing"])
        self.assertIn("financials.periods", pack["quality"]["missing"])

    def test_rejects_invalid_dcf_spread(self):
        assumptions = {
            "forecast_years": 2,
            "base_revenue": 100,
            "revenue_growth": 0.05,
            "ebit_margin": 0.2,
            "tax_rate": 0.2,
            "diluted_shares": 10,
            "wacc": 0.03,
            "terminal_growth": 0.03,
        }
        with self.assertRaisesRegex(ValueError, "wacc"):
            fundamental_pack.calculate_dcf(assumptions)


class ProviderAdapterTests(unittest.TestCase):
    def test_capabilities_never_return_secret_values(self):
        with patch.dict(os.environ, {"JQUANTS_API_KEY": "super-secret-value"}, clear=False):
            report = provider_adapters.capability_report()
        rendered = str(report)
        self.assertNotIn("super-secret-value", rendered)
        jquants = next(row for row in report["providers"] if row["adapter"] == "jquants")
        self.assertEqual(jquants["credentials"]["JQUANTS_API_KEY"], "configured")

    def test_adapter_envelope_preserves_lineage_state(self):
        result = provider_adapters.envelope(
            "twse", {"code": "2330"}, {"records": [{"公司代號": "2330"}]}
        )
        self.assertEqual(result["schema"], "fundamental_adapter_output/v1")
        self.assertTrue(result["lineage"]["raw_provider_labels_preserved"])
        self.assertFalse(result["lineage"]["normalized_to_fundamental_pack"])


if __name__ == "__main__":
    unittest.main()
