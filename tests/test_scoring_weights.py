import csv
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import sector_score_pipeline as pipeline
from src.scoring_config import AXIS_WEIGHTS, SCORING_MODEL_VERSION


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def detail_row(row_date: str, symbol: str, close: str) -> dict:
    return {
        "date": row_date,
        "symbol": symbol,
        "price_open": "100",
        "price_close": close,
        "price_high": "110",
        "price_low": "90",
        "high_52wk": "130",
        "low_52wk": "80",
        "market_cap": "1B",
        "shares_outstanding": "10M",
        "float_shares": "2M",
        "weekly_avg_volume": "20K",
        "free_float_pct": "20",
        "dividend_yield": "5",
        "eps": "8",
        "net_income_margin": "12",
        "price_to_book": "1.5",
        "price_to_earnings": "10",
        "peg_ratio": "0.8",
    }


class WeightedAxisScoreTests(unittest.TestCase):
    def test_configured_weights_match_the_v2_policy(self) -> None:
        self.assertEqual(
            AXIS_WEIGHTS,
            {
                "valuation": 0.25,
                "profitability": 0.20,
                "income": 0.20,
                "trend": 0.15,
                "liquidity": 0.10,
                "quality": 0.10,
            },
        )
        pipeline.validate_axis_weights(AXIS_WEIGHTS)

    def test_missing_quality_is_excluded_and_remaining_weights_are_normalized(self) -> None:
        score, axes, active_weight = pipeline.weighted_axis_score(
            {
                "valuation": 25.0,
                "profitability": 50.0,
                "income": 75.0,
                "trend": 100.0,
                "liquidity": 0.0,
                "quality": None,
            }
        )
        self.assertAlmostEqual(score, 46.25 / 0.90)
        self.assertEqual(
            axes,
            ("valuation", "profitability", "income", "trend", "liquidity"),
        )
        self.assertAlmostEqual(active_weight, 0.90)

    def test_zero_is_an_active_axis_score(self) -> None:
        score, axes, active_weight = pipeline.weighted_axis_score(
            {
                "valuation": 0.0,
                "profitability": None,
                "income": None,
                "trend": None,
                "liquidity": None,
                "quality": None,
            }
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(axes, ("valuation",))
        self.assertEqual(active_weight, 0.25)

    def test_invalid_weight_configurations_fail_clearly(self) -> None:
        cases = []
        unknown = dict(AXIS_WEIGHTS)
        unknown["mystery"] = 0.0
        cases.append(unknown)
        missing = dict(AXIS_WEIGHTS)
        missing.pop("quality")
        cases.append(missing)
        negative = dict(AXIS_WEIGHTS)
        negative["quality"] = -0.10
        negative["liquidity"] = 0.30
        cases.append(negative)
        non_finite = dict(AXIS_WEIGHTS)
        non_finite["quality"] = math.nan
        cases.append(non_finite)
        wrong_total = dict(AXIS_WEIGHTS)
        wrong_total["quality"] = 0.20
        cases.append(wrong_total)

        for weights in cases:
            with self.subTest(weights=weights):
                with self.assertRaisesRegex(ValueError, "axis weights"):
                    pipeline.validate_axis_weights(weights)

    def test_invalid_or_empty_axis_scores_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "no weighted axes"):
            pipeline.weighted_axis_score({})
        with self.assertRaisesRegex(ValueError, "finite number"):
            pipeline.weighted_axis_score({"valuation": math.inf})
        with self.assertRaisesRegex(ValueError, "unknown axis"):
            pipeline.weighted_axis_score({"mystery": 50.0})

    def test_news_overlay_remains_separate(self) -> None:
        self.assertEqual(pipeline.blend_news_score(40.0, None), 40.0)
        self.assertEqual(pipeline.blend_news_score(40.0, 100.0), 49.0)
        self.assertEqual(pipeline.blend_news_score(40.0, 120.0), 49.0)


class HistoricalBackfillTests(unittest.TestCase):
    def test_all_dates_recalculates_history_and_keeps_latest_exports_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            details_path = root / "stock_details_history.csv"
            sectors_path = root / "kmiallshr_by_sector.csv"
            news_path = root / "news_scores.csv"
            history_path = root / "sector_scores_history.csv"
            latest_path = root / "latest_sector_rankings.csv"
            llm_path = root / "llm" / "latest_sector_summary.csv"
            monthly_dir = root / "monthly"

            rows = [
                detail_row("2026-01-01", "A", "105"),
                detail_row("2026-01-01", "B", "95"),
                detail_row("2026-01-02", "A", "110"),
                detail_row("2026-01-02", "B", "90"),
            ]
            write_csv(details_path, rows, ["date", "symbol", *pipeline.DETAIL_FIELDS])
            write_csv(
                sectors_path,
                [
                    {"sector": "TEST", "symbol": "A", "name": "A Co"},
                    {"sector": "TEST", "symbol": "B", "name": "B Co"},
                ],
                ["sector", "symbol", "name"],
            )
            write_csv(
                news_path,
                [
                    {
                        "date": "2026-01-02",
                        "sector": "TEST",
                        "symbol": "A",
                        "news_score": "100",
                        "news_label": "positive",
                        "news_note": "eligible only on second date",
                    }
                ],
                ["date", "sector", "symbol", "news_score", "news_label", "news_note"],
            )
            old_history = []
            for row in rows:
                old = {field: "" for field in pipeline.SCORE_FIELDS}
                old.update(
                    {
                        "date": row["date"],
                        "sector": "TEST",
                        "symbol": row["symbol"],
                    }
                )
                old_history.append(old)
            write_csv(history_path, old_history, pipeline.SCORE_FIELDS)

            patches = {
                "DETAILS_CSV": details_path,
                "SECTORS_CSV": sectors_path,
                "NEWS_CSV": news_path,
                "DETAILS_WITH_SECTOR_CSV": root / "details_with_sector.csv",
                "SCORES_HISTORY_CSV": history_path,
                "LATEST_RANKINGS_CSV": latest_path,
                "LLM_DIR": llm_path.parent,
                "MONTHLY_DIR": monthly_dir,
                "PORTFOLIO_CSV": root / "missing_portfolio.csv",
            }
            with patch.multiple(pipeline, **patches):
                summary = pipeline.run(all_dates=True, top_per_sector=5)
                first_history = history_path.read_bytes()
                pipeline.run(all_dates=True, top_per_sector=5)
                self.assertEqual(history_path.read_bytes(), first_history)

            history = read_csv(history_path)
            latest = read_csv(latest_path)
            llm = read_csv(llm_path)
            monthly = read_csv(monthly_dir / "2026-01_sector_scores.csv")

            self.assertEqual(summary["dates_scored"], 2)
            self.assertEqual(summary["score_rows_written"], 4)
            self.assertEqual(len(history), 4)
            self.assertEqual(len(monthly), 4)
            self.assertEqual({row["date"] for row in latest}, {"2026-01-02"})
            self.assertEqual({row["date"] for row in llm}, {"2026-01-02"})
            self.assertEqual(
                {row["scoring_model_version"] for row in history},
                {SCORING_MODEL_VERSION},
            )
            self.assertEqual(
                {row["active_axis_weight_pct"] for row in history},
                {"90"},
            )

            first_date_a = next(
                row for row in history if row["date"] == "2026-01-01" and row["symbol"] == "A"
            )
            second_date_a = next(
                row for row in history if row["date"] == "2026-01-02" and row["symbol"] == "A"
            )
            self.assertEqual(first_date_a["news_score"], "")
            self.assertEqual(
                first_date_a["final_score"],
                first_date_a["quantitative_score"],
            )
            self.assertEqual(second_date_a["news_score"], "100")
            expected_news_blend = pipeline.blend_news_score(
                float(second_date_a["quantitative_score"]),
                100.0,
            )
            self.assertAlmostEqual(
                float(second_date_a["final_score"]),
                expected_news_blend,
                places=1,
            )


if __name__ == "__main__":
    unittest.main()
