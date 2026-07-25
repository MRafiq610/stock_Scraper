import unittest

from src import sector_score_pipeline as pipeline


class SectorConfidenceTests(unittest.TestCase):
    def test_boundaries_and_schema(self) -> None:
        self.assertEqual(pipeline.sector_confidence(3), "low")
        self.assertEqual(pipeline.sector_confidence(5), "moderate")
        self.assertEqual(pipeline.sector_confidence(14), "moderate")
        self.assertEqual(pipeline.sector_confidence(15), "high")
        with self.assertRaises(ValueError):
            pipeline.sector_confidence(0)

        for field in ("sector_confidence", "sector_confidence_note"):
            self.assertIn(field, pipeline.SCORE_FIELDS)
            self.assertIn(field, pipeline.LLM_FIELDS)

        base = {
            "date": "2026-01-01",
            "sector": "TEST",
            "name": "",
            "_data_completeness_count": 0,
            "_data_completeness_label": "low",
            "_quarterly_fiscal_period": "",
            "_quarterly_fiscal_end_date": "",
            "_quarterly_available_date": "",
            "_quarterly_date_basis": "",
            "_quarterly_age_days": None,
            "_quality_debt_to_equity": None,
            "_quality_roe": None,
            "_quality_current_ratio": None,
            "_quality_revenue_growth": None,
            "_quality_net_profit_growth": None,
            "_quarterly_quality_note": "",
            "_volatility_daily_pct": None,
            "_volatility_observations": 0,
        }
        scores = pipeline.score_sector(
            [{**base, "symbol": symbol} for symbol in ("A", "B", "C")],
            {},
        )
        self.assertEqual({row["sector_confidence"] for row in scores}, {"low"})
        self.assertEqual(
            {row["sector_confidence_note"] for row in scores},
            {"3 scored members; low peer-count confidence"},
        )


if __name__ == "__main__":
    unittest.main()
