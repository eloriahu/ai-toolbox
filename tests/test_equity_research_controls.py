from __future__ import annotations

import importlib.util
import json
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


idea_funnel = load_module(
    "idea_funnel", "plugins/fundamental-tools/scripts/idea_funnel.py"
)
research_review = load_module(
    "research_review", "plugins/fundamental-tools/scripts/research_review.py"
)


def sources():
    return [
        {
            "id": "src-issuer",
            "origin": "issuer-filing",
            "independence_group": "issuer-fy25",
            "url": "https://example.test/filing",
        },
        {
            "id": "src-exchange",
            "origin": "stock-exchange",
            "independence_group": "exchange-market-data",
            "url": "https://example.test/market",
        },
    ]


def claims():
    return [
        {
            "id": "claim-demand",
            "statement": "Demand is growing faster than qualified capacity.",
            "source_ids": ["src-issuer"],
        },
        {
            "id": "claim-valuation",
            "statement": "The stated valuation input is current as of the review time.",
            "source_ids": ["src-exchange"],
        },
    ]


def score_map(value="4"):
    return {
        dimension: {"score": value, "claim_ids": ["claim-demand"]}
        for dimension in idea_funnel.SCORE_DIMENSIONS
    }


def evidence_map():
    return {
        lane: [
            {
                "claim": f"Evidence for {lane}",
                "claim_ids": ["claim-demand" if lane != "valuation" else "claim-valuation"],
            }
        ]
        for lane in idea_funnel.EVIDENCE_LANES
    }


def funnel_input():
    dimensions = {
        dimension: {"score": "4", "claim_ids": ["claim-demand"]}
        for dimension in idea_funnel.BOTTLENECK_DIMENSIONS
    }
    return {
        "as_of": "2026-09-22T09:00:00+08:00",
        "question": "Which listed suppliers have the cleanest exposure to constrained capacity?",
        "scope": {"markets": ["Japan", "Korea", "Taiwan"]},
        "sources": sources(),
        "claims": claims(),
        "causal_chain": [
            {
                "id": "link-1",
                "from": "end demand",
                "to": "qualified capacity",
                "mechanism": "orders exceed near-term qualified supply",
                "status": "supported",
                "claim_ids": ["claim-demand"],
            }
        ],
        "bottlenecks": [
            {
                "id": "constraint-1",
                "description": "Qualified capacity",
                "claim_ids": ["claim-demand"],
                "dimensions": dimensions,
            }
        ],
        "screen_profiles": [
            {
                "id": "semicap-quality",
                "sector": "semiconductor-equipment",
                "rules": [
                    {
                        "id": "positive-fcf",
                        "metric": "free_cash_flow",
                        "operator": "gt",
                        "threshold": "0",
                        "required": True,
                    }
                ],
            }
        ],
        "candidates": [
            {
                "id": "candidate-a",
                "entity": {
                    "name": "Example Supplier",
                    "primary_symbol": "1234",
                    "exchange": "TWSE",
                },
                "supply_chain_position": "qualified equipment supplier",
                "exposure": {
                    "description": "Meaningful revenue exposure to qualified equipment.",
                    "claim_ids": ["claim-demand"],
                },
                "disposition": "advance",
                "screen_profile_id": "semicap-quality",
                "screen_inputs": {"free_cash_flow": {"value": "100.10"}},
                "evidence": evidence_map(),
                "scores": score_map(),
            },
            {
                "id": "candidate-b",
                "entity": {
                    "name": "Rejected Supplier",
                    "primary_symbol": "5678",
                    "exchange": "TWSE",
                },
                "supply_chain_position": "diversified component supplier",
                "exposure": {
                    "description": "The relevant component is immaterial to group revenue.",
                    "claim_ids": ["claim-demand"],
                },
                "disposition": "reject",
                "rejection_reasons": [
                    {"code": "low-purity", "reason": "The constrained product is immaterial."},
                    {"code": "no-catalyst", "reason": "No dated earnings transmission was found."},
                ],
            },
        ],
    }


def review_input():
    return {
        "as_of": "2026-09-22T09:00:00+08:00",
        "entity": {"name": "Example Supplier", "primary_symbol": "1234"},
        "sources": sources(),
        "claims": claims(),
        "researchability": {
            "lanes": [
                {
                    "name": "primary_filings",
                    "state": "complete",
                    "required": True,
                    "source_ids": ["src-issuer"],
                },
                {
                    "name": "market_data",
                    "state": "complete",
                    "required": True,
                    "source_ids": ["src-exchange"],
                },
            ]
        },
        "management_promises": [
            {
                "id": "promise-margin",
                "statement": "Management targeted at least a 30% margin.",
                "made_at": "2025-01-01",
                "due_at": "2025-12-31",
                "source_ids": ["src-issuer"],
                "measurement": {
                    "operator": "gte",
                    "target": "0.30",
                    "actual": "0.300",
                    "source_ids": ["src-issuer"],
                },
            }
        ],
        "thesis_comparison": {
            "prior_as_of": "2026-08-01",
            "current_as_of": "2026-09-22",
            "prior": {
                "facts": {"capacity": {"value": "100", "source_ids": ["src-issuer"]}},
                "prices": {"share_price": "10"},
                "wording": {"summary": "Capacity is constrained."},
            },
            "current": {
                "facts": {"capacity": {"value": "100", "source_ids": ["src-issuer"]}},
                "prices": {"share_price": "10"},
                "wording": {"summary": "Qualified capacity remains tight."},
            },
        },
        "number_audit": {
            "required": True,
            "critical_fields": ["revenue"],
            "rows": [
                {
                    "id": "revenue",
                    "label": "FY25 revenue",
                    "report": {
                        "value": "1.20",
                        "scale": "1000000000",
                        "currency": "TWD",
                        "unit": "currency",
                        "period": "FY2025",
                        "basis": "reported",
                    },
                    "source": {
                        "value": "1200",
                        "scale": "1000000",
                        "currency": "TWD",
                        "unit": "currency",
                        "period": "FY2025",
                        "basis": "reported",
                        "source_ids": ["src-issuer"],
                    },
                }
            ],
        },
    }


class IdeaFunnelTests(unittest.TestCase):
    def test_builds_ranked_funnel_and_retains_all_rejections(self):
        funnel = idea_funnel.build_funnel(funnel_input())
        self.assertEqual(funnel["schema"], "idea_funnel/v1")
        self.assertEqual(funnel["quality"]["status"], "ready")
        self.assertEqual(funnel["ranking"][0]["candidate_id"], "candidate-a")
        self.assertEqual(funnel["ranking"][0]["score"], "80")
        self.assertEqual(funnel["candidates"][0]["screen"]["state"], "pass")
        self.assertEqual(len(funnel["candidates"][1]["rejection_reasons"]), 2)
        self.assertEqual(idea_funnel.validate_funnel(funnel), [])
        self.assertNotIn("position_size", json.dumps(funnel))
        self.assertNotIn("order_instruction", json.dumps(funnel).lower())

    def test_sector_screen_preserves_insufficient_and_not_applicable(self):
        profile = {
            "id": "income-durability",
            "kind": "income-durability",
            "rules": [
                {
                    "id": "coverage",
                    "metric": "distribution_coverage",
                    "operator": "gte",
                    "threshold": "1.1",
                },
                {
                    "id": "payout-history",
                    "metric": "payout_history_years",
                    "operator": "gte",
                    "threshold": "5",
                },
            ],
        }
        insufficient = idea_funnel.evaluate_screen(
            profile,
            {
                "distribution_coverage": {"state": "insufficient", "reason": "FCF not filed"},
                "payout_history_years": {"state": "not_applicable", "reason": "new structure"},
            },
        )
        self.assertEqual(insufficient["state"], "insufficient")
        self.assertEqual(
            [row["state"] for row in insufficient["results"]],
            ["insufficient", "not_applicable"],
        )

    def test_missing_claim_registry_blocks_funnel(self):
        raw = funnel_input()
        raw["claims"] = []
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["quality"]["status"], "blocked")
        self.assertIn("claims", funnel["quality"]["missing"])

    def test_unsupported_required_link_blocks_ranking(self):
        raw = funnel_input()
        raw["causal_chain"][0]["status"] = "disputed"
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertEqual(funnel["ranking"], [])
        self.assertIn(
            "one or more required causal links are not supported",
            funnel["candidates"][0]["rankability_reasons"],
        )

    def test_invalid_claim_lineage_blocks_causal_gate_and_ranking(self):
        raw = funnel_input()
        raw["claims"][0]["source_ids"] = ["missing-source"]
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertFalse(funnel["causal_chain"][0]["lineage_valid"])
        self.assertEqual(funnel["ranking"], [])

    def test_validate_only_recomputes_causal_and_ranking_invariants(self):
        funnel = idea_funnel.build_funnel(funnel_input())
        funnel["causal_chain"][0]["status"] = "unsupported"
        errors = idea_funnel.validate_funnel(funnel)
        self.assertTrue(any("causal_gate" in error for error in errors))
        self.assertTrue(any("ranking" in error for error in errors))

    def test_selected_not_applicable_or_empty_screen_cannot_rank(self):
        raw = funnel_input()
        raw["candidates"][0]["screen_inputs"] = {
            "free_cash_flow": {"state": "not_applicable", "reason": "sector metric not meaningful"}
        }
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["candidates"][0]["screen"]["state"], "not_applicable")
        self.assertFalse(funnel["candidates"][0]["rankable"])

        raw = funnel_input()
        raw["screen_profiles"][0]["rules"] = []
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["candidates"][0]["screen"]["state"], "insufficient")
        self.assertFalse(funnel["candidates"][0]["rankable"])

        raw = funnel_input()
        del raw["candidates"][0]["screen_profile_id"]
        funnel = idea_funnel.build_funnel(raw)
        self.assertFalse(funnel["candidates"][0]["rankable"])
        self.assertIn(
            "a declared, found screen profile with applicable required rules must pass",
            funnel["candidates"][0]["rankability_reasons"],
        )

    def test_malformed_lineage_is_reported_without_type_error(self):
        raw = funnel_input()
        raw["claims"][0]["source_ids"] = [["not", "an", "id"]]
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertTrue(
            any("source_ids must contain" in issue for issue in funnel["quality"]["issues"])
        )

    def test_float_inputs_are_rejected_but_cli_decimal_parse_is_exact(self):
        self.assertIsNone(idea_funnel._decimal(0.1))
        parsed = json.loads('{"value": 9007199254740993.1}', parse_float=Decimal)
        self.assertEqual(
            idea_funnel._decimal(parsed["value"]), Decimal("9007199254740993.1")
        )

    def test_exposure_lineage_and_source_registry_completeness_gate_ranking(self):
        raw = funnel_input()
        raw["candidates"][0]["exposure"]["claim_ids"] = ["unknown-claim"]
        funnel = idea_funnel.build_funnel(raw)
        self.assertFalse(funnel["candidates"][0]["exposure_lineage_valid"])
        self.assertFalse(funnel["candidates"][0]["rankable"])

        raw = funnel_input()
        del raw["sources"][0]["origin"]
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertEqual(funnel["ranking"], [])

    def test_invalid_first_duplicate_claim_cannot_be_rehabilitated(self):
        raw = funnel_input()
        raw["claims"][0]["source_ids"] = ["missing-source"]
        raw["claims"].insert(
            1,
            {
                "id": "claim-demand",
                "statement": "Duplicate claim with a valid source.",
                "source_ids": ["src-issuer"],
            },
        )
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertTrue(
            any("claim IDs must be unique" in issue for issue in funnel["quality"]["issues"])
        )

        raw = funnel_input()
        raw["claims"].append(
            {
                "id": "claim-demand",
                "statement": "Invalid duplicate after the valid first claim.",
                "source_ids": ["missing-source"],
            }
        )
        funnel = idea_funnel.build_funnel(raw)
        self.assertEqual(funnel["causal_gate"]["state"], "blocked")
        self.assertEqual(funnel["ranking"], [])

    def test_score_and_bottleneck_lineage_gate_derived_scores(self):
        raw = funnel_input()
        for score in raw["candidates"][0]["scores"].values():
            score["claim_ids"] = ["unknown-claim"]
        raw["bottlenecks"][0]["dimensions"]["capacity_tightness"]["claim_ids"] = [
            "unknown-claim"
        ]
        funnel = idea_funnel.build_funnel(raw)
        self.assertFalse(funnel["candidates"][0]["score_lineage_valid"])
        self.assertFalse(funnel["candidates"][0]["rankable"])
        self.assertIsNone(funnel["bottlenecks"][0]["score"])
        self.assertFalse(funnel["bottlenecks"][0]["score_lineage_valid"])

    def test_strict_readiness_rejects_limited_funnel(self):
        funnel = idea_funnel.build_funnel(funnel_input())
        self.assertTrue(idea_funnel.strict_ready(funnel, []))
        funnel["quality"]["status"] = "limited"
        self.assertFalse(idea_funnel.strict_ready(funnel, []))


class ResearchReviewTests(unittest.TestCase):
    def test_builds_ready_review_with_decimal_audit(self):
        review = research_review.build_review(review_input())
        self.assertEqual(review["schema"], "research_review/v1")
        self.assertEqual(review["researchability"]["grade"], "A")
        self.assertEqual(review["management_ledger"][0]["status"], "delivered")
        self.assertEqual(review["thesis_drift"]["primary_class"], "wording")
        self.assertEqual(review["thesis_drift"]["substantive_state"], "unchanged")
        self.assertEqual(review["number_audit"]["rows"][0]["status"], "pass")
        self.assertEqual(review["number_audit"]["rows"][0]["report_normalized"], "1200000000")
        self.assertEqual(review["publication_gate"], "pass")
        self.assertEqual(review["quality"]["status"], "ready")
        self.assertEqual(research_review.validate_review(review), [])

    def test_price_only_and_new_sourced_fact_are_distinct(self):
        price = research_review.classify_thesis_drift(
            {
                "prior": {"facts": {"units": 10}, "prices": {"spot": 5}},
                "current": {"facts": {"units": 10}, "prices": {"spot": 6}},
            }
        )
        self.assertEqual(price["primary_class"], "price")
        self.assertEqual(price["substantive_state"], "valuation_changed")

        fact = research_review.classify_thesis_drift(
            {
                "prior": {"facts": {}},
                "current": {
                    "facts": {"new_capacity": {"value": 20, "source_ids": ["src-issuer"]}}
                },
                "effect_on_conclusion": {
                    "direction": "strengthened",
                    "rationale": "New capacity changes the operating conclusion.",
                    "source_ids": ["src-issuer"],
                },
            },
            {"src-issuer"},
        )
        self.assertEqual(fact["primary_class"], "fact")
        self.assertEqual(fact["substantive_state"], "facts_changed")
        self.assertEqual(fact["validation_issues"], [])

    def test_no_baseline_is_limited(self):
        raw = review_input()
        raw["thesis_comparison"] = {
            "current": {
                "facts": {"capacity": {"value": "100", "source_ids": ["src-issuer"]}}
            }
        }
        review = research_review.build_review(raw)
        self.assertEqual(review["thesis_drift"]["comparison_status"], "limited_no_baseline")
        self.assertEqual(review["quality"]["status"], "limited")

    def test_missing_or_zero_verified_critical_fields_block_publication(self):
        raw = review_input()
        raw["number_audit"] = {
            "required": True,
            "critical_fields": ["revenue", "net_income"],
            "rows": [],
        }
        review = research_review.build_review(raw)
        self.assertEqual(review["publication_gate"], "blocked")
        self.assertEqual(review["quality"]["status"], "blocked")
        self.assertIn("revenue", review["number_audit"]["missing_critical_fields"])
        self.assertIn("zero_verified_fields", review["number_audit"]["critical_failures"])

    def test_syndicated_sources_do_not_satisfy_independence_requirement(self):
        raw = review_input()
        raw["sources"].append(
            {
                "id": "src-article",
                "origin": "news-article",
                "independence_group": "issuer-fy25",
                "url": "https://example.test/article",
            }
        )
        raw["number_audit"]["minimum_independent_sources"] = 2
        raw["number_audit"]["rows"][0]["source"]["source_ids"] = [
            "src-issuer",
            "src-article",
        ]
        review = research_review.build_review(raw)
        row = review["number_audit"]["rows"][0]
        self.assertEqual(row["independent_source_count"], 1)
        self.assertEqual(row["status"], "unverifiable")
        self.assertEqual(review["publication_gate"], "blocked")

    def test_missing_audit_metadata_is_unverifiable_and_blocks(self):
        raw = review_input()
        del raw["number_audit"]["rows"][0]["source"]["currency"]
        review = research_review.build_review(raw)
        row = review["number_audit"]["rows"][0]
        self.assertEqual(row["status"], "unverifiable")
        self.assertIn("source.currency", row["missing_metadata"])
        self.assertEqual(review["publication_gate"], "blocked")
        self.assertEqual(review["quality"]["status"], "blocked")

    def test_fractional_independence_requirement_is_invalid(self):
        raw = review_input()
        raw["number_audit"]["minimum_independent_sources"] = "1.9"
        review = research_review.build_review(raw)
        self.assertEqual(review["number_audit"]["rows"][0]["status"], "unverifiable")
        self.assertIn(
            "invalid_independence_requirement",
            review["number_audit"]["critical_failures"],
        )
        self.assertEqual(review["publication_gate"], "blocked")

    def test_management_outcome_requires_separate_source_lineage(self):
        raw = review_input()
        del raw["management_promises"][0]["measurement"]["source_ids"]
        review = research_review.build_review(raw)
        self.assertEqual(review["management_ledger"][0]["status"], "unclear")
        self.assertEqual(
            review["management_ledger"][0]["determination"],
            "insufficient_outcome_evidence",
        )
        self.assertEqual(review["quality"]["status"], "limited")

    def test_validate_only_recomputes_number_audit_and_gate(self):
        review = research_review.build_review(review_input())
        review["number_audit"]["rows"] = []
        review["number_audit"]["verified_count"] = 1
        review["number_audit"]["critical_failures"] = []
        review["number_audit"]["missing_critical_fields"] = []
        review["publication_gate"] = "pass"
        review["quality"]["status"] = "ready"
        errors = research_review.validate_review(review)
        self.assertTrue(any("number_audit" in error or "publication_gate" in error for error in errors))

    def test_validate_only_recomputes_management_delivery(self):
        review = research_review.build_review(review_input())
        review["management_ledger"][0]["status"] = "missed"
        review["management_ledger"][0]["determination"] = "explicit_analyst_assessment"
        errors = research_review.validate_review(review)
        self.assertTrue(any("management promise" in error for error in errors))

    def test_research_review_rejects_python_float_inputs(self):
        self.assertIsNone(research_review._decimal(0.1))

    def test_malformed_audit_source_ids_are_unverifiable_without_crash(self):
        for malformed in (123, {"bad": "id"}, [["bad"]]):
            with self.subTest(malformed=malformed):
                raw = review_input()
                raw["number_audit"]["rows"][0]["source"]["source_ids"] = malformed
                review = research_review.build_review(raw)
                self.assertEqual(
                    review["number_audit"]["rows"][0]["status"], "unverifiable"
                )
                self.assertEqual(review["publication_gate"], "blocked")

    def test_decimal_thesis_values_compare_without_serialization_loss(self):
        drift = research_review.classify_thesis_drift(
            {
                "prior": {
                    "facts": {
                        "ratio": {
                            "value": Decimal("9007199254740993.1"),
                            "source_ids": ["src-issuer"],
                        }
                    }
                },
                "current": {
                    "facts": {
                        "ratio": {
                            "value": Decimal("9007199254740993.1"),
                            "source_ids": ["src-issuer"],
                        }
                    }
                },
            },
            {"src-issuer"},
        )
        self.assertEqual(drift["primary_class"], "no_change")

    def test_incomplete_source_registry_cannot_verify_number(self):
        raw = review_input()
        del raw["sources"][0]["independence_group"]
        review = research_review.build_review(raw)
        self.assertEqual(review["number_audit"]["rows"][0]["status"], "unverifiable")
        self.assertEqual(review["publication_gate"], "blocked")

    def test_zero_scale_and_missing_unit_block_publication(self):
        raw = review_input()
        raw["number_audit"]["rows"][0]["report"]["scale"] = "0"
        raw["number_audit"]["rows"][0]["source"]["scale"] = "0"
        review = research_review.build_review(raw)
        self.assertEqual(review["number_audit"]["rows"][0]["status"], "unverifiable")
        self.assertEqual(review["publication_gate"], "blocked")

        raw = review_input()
        del raw["number_audit"]["rows"][0]["source"]["unit"]
        review = research_review.build_review(raw)
        self.assertIn("source.unit", review["number_audit"]["rows"][0]["missing_metadata"])
        self.assertEqual(review["publication_gate"], "blocked")

    def test_invalid_researchability_lineage_earns_no_coverage(self):
        raw = review_input()
        raw["researchability"]["lanes"][0]["source_ids"] = ["unknown-source"]
        raw["researchability"]["lanes"][1]["state"] = "missing"
        raw["researchability"]["lanes"][1]["source_ids"] = []
        review = research_review.build_review(raw)
        self.assertEqual(review["researchability"]["grade"], "C")
        self.assertEqual(review["researchability"]["maximum_supported_confidence"], "low")
        self.assertEqual(review["researchability"]["coverage"], "0")
        self.assertEqual(review["quality"]["status"], "limited")

    def test_promise_below_target_before_deadline_is_pending(self):
        raw = review_input()
        raw["management_promises"][0]["due_at"] = "2027-12-31"
        raw["management_promises"][0]["measurement"]["actual"] = "0.20"
        review = research_review.build_review(raw)
        self.assertEqual(review["management_ledger"][0]["status"], "pending")
        self.assertEqual(
            review["management_ledger"][0]["determination"], "deadline_not_reached"
        )

        raw["management_promises"][0]["measurement"]["actual"] = "0.31"
        review = research_review.build_review(raw)
        self.assertEqual(review["management_ledger"][0]["status"], "delivered")

    def test_thesis_effect_on_conclusion_is_sourced(self):
        drift = research_review.classify_thesis_drift(
            {
                "prior": {"facts": {}},
                "current": {
                    "facts": {
                        "capacity": {"value": "120", "source_ids": ["src-issuer"]}
                    }
                },
                "effect_on_conclusion": {
                    "direction": "strengthened",
                    "rationale": "Capacity rose more than the prior thesis assumed.",
                    "source_ids": ["src-issuer"],
                },
            },
            {"src-issuer"},
        )
        self.assertEqual(drift["effect_on_conclusion"]["direction"], "strengthened")
        self.assertEqual(drift["validation_issues"], [])

    def test_audit_ids_must_be_unique_nonempty_strings(self):
        raw = review_input()
        raw["number_audit"]["rows"].append(
            dict(raw["number_audit"]["rows"][0])
        )
        review = research_review.build_review(raw)
        self.assertEqual(review["publication_gate"], "blocked")
        self.assertTrue(
            any("row IDs must be unique" in issue for issue in review["quality"]["issues"])
        )

    def test_strict_review_requires_ready_and_audit_pass(self):
        review = research_review.build_review(review_input())
        self.assertTrue(research_review.strict_ready(review, []))
        review["publication_gate"] = "not_run"
        self.assertFalse(research_review.strict_ready(review, []))


if __name__ == "__main__":
    unittest.main()
