import math
import unittest
from datetime import date, timedelta

from src import sector_score_pipeline as pipeline


def detail(symbol: str, day: date, close: float) -> dict:
    return {
        "date": day.isoformat(),
        "sector": "TEST",
        "name": symbol,
        "symbol": symbol,
        "price_open": str(close),
        "price_close": str(close),
        "high_52wk": "200",
        "low_52wk": "50",
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


class VolatilityTests(unittest.TestCase):
    def test_window_is_as_of_aware_and_requires_enough_returns(self) -> None:
        rows = [
            {"date": "2026-01-01", "symbol": "A", "price_close": "100"},
            {"date": "2026-01-02", "symbol": "A", "price_close": "110"},
            {"date": "2026-01-03", "symbol": "A", "price_close": "99"},
            {"date": "2026-01-04", "symbol": "A", "price_close": "999"},
        ]
        history = pipeline.history_by_symbol(rows)

        daily_pct, observations = pipeline.rolling_volatility(
            history, "A", "2026-01-03", window=3, min_returns=2
        )

        self.assertEqual(observations, 2)
        self.assertAlmostEqual(daily_pct, math.sqrt(0.02) * 100)
        self.assertEqual(
            pipeline.rolling_volatility(
                history, "A", "2026-01-03", window=3, min_returns=3
            ),
            (None, 2),
        )
        self.assertEqual(pipeline.score_volatility(1.0, [1.0, 1.0]), 50.0)

    def test_sector_labels_stability_without_changing_score_model(self) -> None:
        start = date(2026, 1, 1)
        rows = []
        steady = 100.0
        volatile = 100.0
        for offset in range(21):
            day = start + timedelta(days=offset)
            if offset:
                steady *= 1.001
                volatile *= 1.1 if offset % 2 else 0.9
            rows.extend([
                detail("STEADY", day, steady),
                detail("VOLATILE", day, volatile),
            ])

        scores = pipeline.build_scores(rows[-2:], rows, rows[-1]["date"], 30, {})
        by_symbol = {row["symbol"]: row for row in scores}

        self.assertEqual(by_symbol["STEADY"]["volatility_observations"], "20")
        self.assertEqual(by_symbol["STEADY"]["volatility_label"], "low")
        self.assertEqual(by_symbol["STEADY"]["volatility_score"], "100")
        self.assertEqual(by_symbol["VOLATILE"]["volatility_label"], "high")
        self.assertEqual(by_symbol["VOLATILE"]["volatility_score"], "0")
        self.assertEqual(
            by_symbol["STEADY"]["scoring_model_version"],
            pipeline.SCORING_MODEL_VERSION,
        )


if __name__ == "__main__":
    unittest.main()
