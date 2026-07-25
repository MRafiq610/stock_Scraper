"""Small atomic writers for pipeline artifacts."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable


def _atomic_write(path: Path, write) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
            newline="",
            encoding="utf-8",
        ) as file:
            temporary = Path(file.name)
            write(file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def atomic_write_csv(
    path: Path,
    rows: Iterable[dict],
    fieldnames: list[str],
    *,
    extrasaction: str = "ignore",
) -> None:
    materialized = list(rows)

    def write(file) -> None:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction=extrasaction,
        )
        writer.writeheader()
        writer.writerows(materialized)

    _atomic_write(path, write)


def atomic_write_json(path: Path, payload: dict) -> None:
    _atomic_write(
        path,
        lambda file: json.dump(payload, file, indent=2, ensure_ascii=False),
    )
