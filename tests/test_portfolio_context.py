import unittest

from src import sector_score_pipeline as pipeline


class PortfolioContextTests(unittest.TestCase):
    def test_lookup_accepts_only_unique_known_symbols(self) -> None:
        held, diagnostics = pipeline.portfolio_lookup(
            [
                {"symbol": " efert "},
                {"symbol": "EFERT"},
                {"symbol": "UNKNOWN"},
                {"symbol": ""},
                {"symbol": "BAD SYMBOL"},
            ],
            {"EFERT", "OGDC"},
        )
        self.assertEqual(held, {"EFERT"})
        self.assertEqual(
            diagnostics,
            {"matched": 1, "unmatched": 1, "invalid": 2, "duplicates": 1},
        )

    def test_context_does_not_modify_scores_or_input_rows(self) -> None:
        rows = [
            {"symbol": "EFERT", "final_score": "80", "sector_rank": "1"},
            {"symbol": "OGDC", "final_score": "70", "sector_rank": "2"},
        ]
        enriched = pipeline.add_portfolio_context(rows, {"EFERT"})
        self.assertEqual(
            [row["portfolio_status"] for row in enriched],
            ["held", "not_held"],
        )
        self.assertEqual(
            [(row["final_score"], row["sector_rank"]) for row in enriched],
            [("80", "1"), ("70", "2")],
        )
        self.assertNotIn("portfolio_status", rows[0])
        self.assertEqual(
            [row["portfolio_status"] for row in pipeline.add_portfolio_context(rows, None)],
            ["unknown", "unknown"],
        )

    def test_llm_summary_keeps_held_stocks_below_the_sector_cutoff(self) -> None:
        rows = [
            {
                "sector": "TEST",
                "symbol": f"S{rank}",
                "sector_rank": str(rank),
                "portfolio_status": "held" if rank == 3 else "not_held",
            }
            for rank in range(1, 5)
        ]
        selected = pipeline.export_llm_summary(rows, top_per_sector=2)
        self.assertEqual([row["symbol"] for row in selected], ["S1", "S2", "S3"])


if __name__ == "__main__":
    unittest.main()
