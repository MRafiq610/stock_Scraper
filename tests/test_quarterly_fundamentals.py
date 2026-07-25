import unittest

from src import sector_score_pipeline as pipeline
from src.quarterly_fundamentals_scraper import quality_periods


def ratio_payload(debt: float, roe: float, current: float, revenue: float, profit: float) -> dict:
    def row(label: str, value: float) -> dict:
        return {
            "label": label,
            "unit": "(%)",
            "data": [
                {"year": "Mar-26", "value": str(value)},
                {"year": "YoY(%)", "value": "999"},
            ],
        }

    return {
        "Health": [row("Debt To Equity", debt)],
        "Returns": [row("ROE", roe)],
        "Active Ratios": [row("Current Ratio", current)],
        "Growth": [
            row("Revenue Growth", revenue),
            row("Net Profit Growth", profit),
        ],
    }


def detail(symbol: str) -> dict:
    return {
        "date": "2026-07-25",
        "sector": "TEST",
        "name": symbol,
        "symbol": symbol,
        "price_open": "100",
        "price_close": "100",
        "high_52wk": "120",
        "low_52wk": "80",
        "market_cap": "1B",
        "weekly_avg_volume": "10K",
        "free_float_pct": "20",
        "dividend_yield": "5",
        "eps": "5",
        "net_income_margin": "10",
        "price_to_book": "1",
        "price_to_earnings": "10",
        "peg_ratio": "1",
    }


class QuarterlyFundamentalsTests(unittest.TestCase):
    def test_lookup_prevents_lookahead_and_excludes_negative_debt_ratio(self) -> None:
        store = {
            "A": {
                "scraped_at": "2026-07-25T12:00:00+00:00",
                "data": ratio_payload(-10, 20, 2, 10, 15),
            }
        }
        self.assertEqual(pipeline.quarterly_lookup(store, "2026-07-24"), {})
        backfilled = pipeline.quarterly_lookup(
            store,
            "2026-07-24",
            allow_snapshot_backfill=True,
        )["A"]
        self.assertEqual(backfilled["available_date"], "")
        self.assertEqual(backfilled["date_basis"], "user_approved_snapshot_backfill")

        selected = pipeline.quarterly_lookup(store, "2026-07-25")["A"]
        self.assertEqual(selected["fiscal_period"], "Mar-26")
        self.assertEqual(selected["fiscal_end_date"], "2026-03-31")
        self.assertEqual(selected["available_date"], "2026-07-25")
        self.assertEqual(selected["date_basis"], "scraped_at")
        self.assertIsNone(selected["debt_to_equity"])
        self.assertEqual(selected["quality_note"], "negative debt-to-equity excluded")

    def test_quality_uses_only_real_periods_and_changes_active_weight(self) -> None:
        stores = {
            "A": {
                "scraped_at": "2026-07-25T00:00:00+00:00",
                "data": ratio_payload(10, 20, 2, 10, 15),
            },
            "B": {
                "scraped_at": "2026-07-25T00:00:00+00:00",
                "data": ratio_payload(50, 10, 1, 5, 5),
            },
        }
        self.assertEqual(len(quality_periods(stores["A"]["data"])), 1)

        rows = [detail("A"), detail("B")]
        scores = pipeline.build_scores(
            rows,
            rows,
            "2026-07-25",
            30,
            {},
            pipeline.quarterly_lookup(stores, "2026-07-25"),
        )
        by_symbol = {row["symbol"]: row for row in scores}

        self.assertEqual(by_symbol["A"]["quality_score"], "100")
        self.assertEqual(by_symbol["B"]["quality_score"], "0")
        self.assertEqual(by_symbol["A"]["quality_metric_count"], "5")
        self.assertEqual(by_symbol["A"]["quality_completeness_pct"], "100")
        self.assertEqual(by_symbol["A"]["active_axis_weight_pct"], "100")
        self.assertEqual(by_symbol["A"]["quarterly_fiscal_period"], "Mar-26")


if __name__ == "__main__":
    unittest.main()
