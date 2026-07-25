import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import sector_score_pipeline as pipeline


CORE_VALUES = {
    "price_to_earnings": "10",
    "price_to_book": "1.2",
    "peg_ratio": "0.8",
    "eps": "5",
    "net_income_margin": "12",
    "dividend_yield": "4",
}


def detail_row(symbol: str, **overrides: str) -> dict:
    row = {
        "date": "2026-07-25",
        "symbol": symbol,
        "price_open": "100",
        "price_close": "105",
        "high_52wk": "130",
        "low_52wk": "80",
        "market_cap": "1.2B",
        "weekly_avg_volume": "20K",
        "free_float_pct": "25",
        **CORE_VALUES,
    }
    row.update(overrides)
    return row


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


class CompletenessCalculationTests(unittest.TestCase):
    def calculate(self, row: dict) -> dict:
        calculated = pipeline.add_calculated_fields(
            [row],
            pipeline.history_by_symbol([row]),
            "2026-07-25",
            30,
        )
        joined = [{"sector": "TEST", "name": row["symbol"], **calculated[0]}]
        return pipeline.score_sector(joined, {})[0]

    def test_complete_partial_and_low_boundaries(self) -> None:
        cases = [
            ({}, ("6", "100", "complete")),
            ({"dividend_yield": ""}, ("5", "83.33", "partial")),
            ({"peg_ratio": "", "eps": "", "net_income_margin": ""}, ("3", "50", "partial")),
            (
                {
                    "price_to_book": "",
                    "peg_ratio": "",
                    "eps": "",
                    "net_income_margin": "",
                },
                ("2", "33.33", "low"),
            ),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = self.calculate(detail_row("TEST", **overrides))
                self.assertEqual(
                    (
                        result["data_completeness_count"],
                        result["data_completeness_pct"],
                        result["data_completeness_label"],
                    ),
                    expected,
                )
                self.assertEqual(result["data_completeness_total"], "6")

    def test_zero_and_negative_count_but_invalid_and_non_finite_do_not(self) -> None:
        result = self.calculate(
            detail_row(
                "EDGE",
                price_to_earnings="0",
                price_to_book="-2",
                peg_ratio="NaN",
                eps="Infinity",
                net_income_margin="-Infinity",
                dividend_yield="-",
            )
        )
        self.assertEqual(result["data_completeness_count"], "2")
        self.assertEqual(result["data_completeness_label"], "low")
        self.assertIsNone(pipeline.parse_number("NaN"))
        self.assertIsNone(pipeline.parse_number("Infinity"))
        self.assertEqual(pipeline.parse_number("1.2B"), 1_200_000_000)

    def test_low_warning_has_precedence_and_reason_cap_is_retained(self) -> None:
        result = self.calculate(
            detail_row(
                "LOW",
                price_to_book="",
                peg_ratio="",
                net_income_margin="",
                dividend_yield="",
            )
        )
        reasons = result["key_reason"].split("; ")
        self.assertEqual(reasons[0], "limited data 2/6")
        self.assertLessEqual(len(reasons), 4)

    def test_completeness_context_does_not_affect_scores_or_rank(self) -> None:
        rows = [
            {"sector": "TEST", "name": "A", **detail_row("A")},
            {"sector": "TEST", "name": "B", **detail_row("B", price_close="95")},
        ]
        calculated = pipeline.add_calculated_fields(
            rows,
            pipeline.history_by_symbol(rows),
            "2026-07-25",
            30,
        )
        baseline = pipeline.score_sector(calculated, {})
        for row in calculated:
            row["_data_completeness_count"] = 0
            row["_data_completeness_label"] = "low"
        sparse_context = pipeline.score_sector(calculated, {})
        self.assertEqual(
            [(row["symbol"], row["final_score"], row["sector_rank"]) for row in baseline],
            [(row["symbol"], row["final_score"], row["sector_rank"]) for row in sparse_context],
        )


class CompletenessExportTests(unittest.TestCase):
    def test_run_exports_fields_idempotently_and_preserves_old_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            details_path = root / "stock_details_history.csv"
            sectors_path = root / "kmiallshr_by_sector.csv"
            history_path = root / "sector_scores_history.csv"
            latest_path = root / "latest_sector_rankings.csv"
            llm_path = root / "llm" / "latest_sector_summary.csv"
            monthly_dir = root / "monthly"
            portfolio_path = root / "portfolio.csv"

            detail_fields = ["date", "symbol", *pipeline.DETAIL_FIELDS]
            rows = [
                detail_row(
                    "FULL",
                    price_high="106",
                    price_low="99",
                    shares_outstanding="10M",
                    float_shares="2M",
                ),
                detail_row(
                    "LOW",
                    price_high="106",
                    price_low="99",
                    shares_outstanding="10M",
                    float_shares="2M",
                    price_to_book="",
                    peg_ratio="",
                    net_income_margin="",
                    dividend_yield="",
                ),
            ]
            write_csv(details_path, rows, detail_fields)
            write_csv(
                sectors_path,
                [
                    {"sector": "TEST", "symbol": "FULL", "name": "Full Co"},
                    {"sector": "TEST", "symbol": "LOW", "name": "Low Co"},
                ],
                ["sector", "symbol", "name"],
            )
            write_csv(portfolio_path, [{"symbol": "FULL"}], ["symbol"])
            old_fields = [*pipeline.SCORE_FIELDS, "legacy_note"]
            historical_row = {field: "" for field in old_fields}
            historical_row.update(
                {
                    "date": "2026-06-01",
                    "sector": "TEST",
                    "symbol": "OLD",
                    "legacy_note": "keep me",
                }
            )
            same_day_row = {field: "" for field in old_fields}
            same_day_row.update(
                {
                    "date": "2026-07-25",
                    "sector": "TEST",
                    "symbol": "FULL",
                    "legacy_note": "keep on update",
                }
            )
            write_csv(history_path, [historical_row, same_day_row], old_fields)

            patches = {
                "DETAILS_CSV": details_path,
                "SECTORS_CSV": sectors_path,
                "NEWS_CSV": root / "missing_news.csv",
                "DETAILS_WITH_SECTOR_CSV": root / "details_with_sector.csv",
                "SCORES_HISTORY_CSV": history_path,
                "LATEST_RANKINGS_CSV": latest_path,
                "LLM_DIR": llm_path.parent,
                "MONTHLY_DIR": monthly_dir,
                "PORTFOLIO_CSV": portfolio_path,
            }
            with patch.multiple(pipeline, **patches):
                pipeline.run(as_of="2026-07-25")
                pipeline.run(as_of="2026-07-25")

            expected_fields = {
                "data_completeness_count",
                "data_completeness_total",
                "data_completeness_pct",
                "data_completeness_label",
            }
            for path in (
                history_path,
                latest_path,
                monthly_dir / "2026-07_sector_scores.csv",
                llm_path,
            ):
                with self.subTest(path=path):
                    with path.open(newline="", encoding="utf-8") as file:
                        self.assertTrue(expected_fields.issubset(csv.DictReader(file).fieldnames or []))

            history = read_csv(history_path)
            current = [row for row in history if row["date"] == "2026-07-25"]
            self.assertEqual(len(current), 2)
            self.assertEqual({row["portfolio_status"] for row in current}, {""})
            old = next(row for row in history if row["date"] == "2026-06-01")
            self.assertEqual(old["data_completeness_count"], "")
            self.assertEqual(old["data_completeness_label"], "")
            self.assertEqual(old["legacy_note"], "keep me")
            updated = next(row for row in current if row["symbol"] == "FULL")
            self.assertEqual(updated["legacy_note"], "keep on update")
            latest = {row["symbol"]: row for row in read_csv(latest_path)}
            self.assertEqual(latest["FULL"]["portfolio_status"], "held")
            self.assertEqual(latest["LOW"]["portfolio_status"], "not_held")
            monthly = {
                row["symbol"]: row
                for row in read_csv(monthly_dir / "2026-07_sector_scores.csv")
            }
            self.assertEqual(monthly["FULL"]["portfolio_status"], "held")
            self.assertEqual(monthly["LOW"]["portfolio_status"], "not_held")


if __name__ == "__main__":
    unittest.main()
