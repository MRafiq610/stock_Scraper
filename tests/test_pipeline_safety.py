import json
import tempfile
import unittest
from pathlib import Path

from src import sector_score_pipeline as pipeline
from src.safe_io import atomic_write_csv, atomic_write_json


class PipelineSafetyTests(unittest.TestCase):
    def test_invalid_ranking_is_rejected_before_replacement(self) -> None:
        rows = [{"date": "2026-01-01", "sector": "TEST", "symbol": "A"}]
        with self.assertRaisesRegex(ValueError, "minimum 2"):
            pipeline.validate_output_rows(
                rows,
                ["date", "sector", "symbol"],
                ["date", "sector", "symbol"],
                "2026-01-01",
                2,
            )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pipeline.validate_output_rows(
                rows * 2,
                ["date", "sector", "symbol"],
                ["date", "sector", "symbol"],
                "2026-01-01",
                1,
            )
        with self.assertRaisesRegex(ValueError, "unexpected as-of"):
            pipeline.validate_output_rows(
                rows,
                ["date", "sector", "symbol"],
                ["date", "sector", "symbol"],
                "2026-01-02",
                1,
            )

    def test_manifest_json_is_replaced_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.json"
            path.write_text('{"status":"old"}', encoding="utf-8")

            atomic_write_json(path, {"status": "success", "rows": 290})

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"status": "success", "rows": 290},
            )
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_failed_csv_generation_preserves_last_good_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ranking.csv"
            path.write_text("symbol\nGOOD\n", encoding="utf-8")

            def broken_rows():
                yield {"symbol": "BAD"}
                raise RuntimeError("incomplete generation")

            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                atomic_write_csv(path, broken_rows(), ["symbol"])

            self.assertEqual(path.read_text(encoding="utf-8"), "symbol\nGOOD\n")
