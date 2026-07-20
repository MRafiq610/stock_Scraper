import csv
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

requests_stub = ModuleType("requests")
pydantic_stub = ModuleType("pydantic")
pydantic_stub.BaseModel = object
sys.modules.setdefault("requests", requests_stub)
sys.modules.setdefault("pydantic", pydantic_stub)

from src.get_stocks import load_existing, upsert

REPO_ROOT = Path(__file__).resolve().parents[1]


class ExistingSymbolsTests(unittest.TestCase):
    def test_loads_symbols_and_ignores_blank_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.csv"
            path.write_text("symbol\nABOT\n\nACPL\n", encoding="utf-8")

            self.assertEqual(load_existing(path), {"ABOT", "ACPL"})

    def test_rejects_a_merge_conflict_marker_as_the_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.csv"
            path.write_text("<<<<<<< HEAD\nsymbol\nABOT\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "expected a 'symbol' column"):
                load_existing(path)

    def test_upsert_adds_a_header_to_an_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.csv"
            path.touch()

            self.assertEqual(upsert(path, ["ACPL", "ABOT"]), 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "symbol\nABOT\nACPL\n")

    def test_committed_csv_files_have_valid_headers(self) -> None:
        for path in (REPO_ROOT / "data").rglob("*.csv"):
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                with path.open(newline="", encoding="utf-8-sig") as file:
                    reader = csv.DictReader(file)
                    self.assertIsNotNone(reader.fieldnames)
                    self.assertFalse(
                        any(
                            field.startswith(("<<<<<<<", "=======", ">>>>>>>"))
                            for field in reader.fieldnames or []
                        )
                    )


if __name__ == "__main__":
    unittest.main()
