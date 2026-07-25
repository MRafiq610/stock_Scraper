"""
Build sector-relative stock rankings from the scraped daily details.

Inputs:
- data/stock_details_history.csv
- data/kmiallshr_by_sector.csv

Outputs:
- data/stock_details_with_sector.csv
- data/sector_scores_history.csv
- data/latest_sector_rankings.csv
- data/llm/latest_sector_summary.csv
- data/monthly/YYYY-MM_sector_scores.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from .scoring_config import (
        AXIS_NAMES,
        AXIS_WEIGHTS,
        MIN_RANKING_COVERAGE,
        NEWS_WEIGHT,
        QUARTERLY_STALE_DAYS,
        SCORING_MODEL_VERSION,
        SECTOR_CONFIDENCE_HIGH_MIN,
        SECTOR_CONFIDENCE_MODERATE_MIN,
        WEIGHT_SUM_TOLERANCE,
    )
except ImportError:
    from scoring_config import (
        AXIS_NAMES,
        AXIS_WEIGHTS,
        MIN_RANKING_COVERAGE,
        NEWS_WEIGHT,
        QUARTERLY_STALE_DAYS,
        SCORING_MODEL_VERSION,
        SECTOR_CONFIDENCE_HIGH_MIN,
        SECTOR_CONFIDENCE_MODERATE_MIN,
        WEIGHT_SUM_TOLERANCE,
    )

try:
    from .quarterly_fundamentals_scraper import QUALITY_METRICS, quality_periods, read_store
except ImportError:
    from quarterly_fundamentals_scraper import QUALITY_METRICS, quality_periods, read_store

try:
    from .safe_io import atomic_write_csv
except ImportError:
    from safe_io import atomic_write_csv

DATA_DIR = Path("data")
DETAILS_CSV = DATA_DIR / "stock_details_history.csv"
SECTORS_CSV = DATA_DIR / "kmiallshr_by_sector.csv"
NEWS_CSV = DATA_DIR / "news_scores.csv"
DETAILS_WITH_SECTOR_CSV = DATA_DIR / "stock_details_with_sector.csv"
SCORES_HISTORY_CSV = DATA_DIR / "sector_scores_history.csv"
LATEST_RANKINGS_CSV = DATA_DIR / "latest_sector_rankings.csv"
LLM_DIR = DATA_DIR / "llm"
MONTHLY_DIR = DATA_DIR / "monthly"
QUARTERLY_RATIOS_JSON = DATA_DIR / "quarterly_ratios.json"
PORTFOLIO_CSV = Path(os.environ.get("PORTFOLIO_CSV", DATA_DIR / "portfolio.csv"))

DETAIL_FIELDS = [
    "price_open",
    "price_close",
    "price_high",
    "price_low",
    "high_52wk",
    "low_52wk",
    "market_cap",
    "shares_outstanding",
    "float_shares",
    "weekly_avg_volume",
    "free_float_pct",
    "dividend_yield",
    "eps",
    "net_income_margin",
    "price_to_book",
    "price_to_earnings",
    "peg_ratio",
]

CORE_COMPLETENESS_FIELDS = {
    "P/E": "price_to_earnings",
    "P/B": "price_to_book",
    "PEG": "peg_ratio",
    "EPS": "eps",
    "Net margin": "net_income_margin",
    "Dividend yield": "dividend_yield",
}
DATA_COMPLETENESS_TOTAL = len(CORE_COMPLETENESS_FIELDS)
DATA_COMPLETENESS_PARTIAL_MIN = 3
VOLATILITY_WINDOW = 30
VOLATILITY_MIN_RETURNS = 20
TRADING_DAYS_PER_YEAR = 252

SCORE_FIELDS = [
    "date",
    "sector",
    "symbol",
    "name",
    "portfolio_status",
    "sector_rank",
    "sector_count",
    "sector_confidence",
    "sector_confidence_note",
    "evidence_warning",
    "final_score",
    "quantitative_score",
    "scoring_model_version",
    "active_axis_weight_pct",
    "data_completeness_count",
    "data_completeness_total",
    "data_completeness_pct",
    "data_completeness_label",
    "news_score",
    "news_label",
    "news_note",
    "trend_score",
    "valuation_score",
    "profitability_score",
    "liquidity_score",
    "income_score",
    "quality_score",
    "quality_metric_count",
    "quality_metric_total",
    "quality_completeness_pct",
    "quarterly_fiscal_period",
    "quarterly_fiscal_end_date",
    "quarterly_available_date",
    "quarterly_date_basis",
    "quarterly_age_days",
    "quarterly_debt_to_equity",
    "quarterly_roe",
    "quarterly_current_ratio",
    "quarterly_revenue_growth",
    "quarterly_net_profit_growth",
    "quarterly_quality_note",
    "volatility_daily_pct",
    "volatility_annualized_pct",
    "volatility_observations",
    "volatility_window",
    "volatility_score",
    "volatility_label",
    "daily_return_pct",
    "period_return_pct",
    "distance_from_52w_high_pct",
    "distance_from_52w_low_pct",
    "market_cap",
    "weekly_avg_volume",
    "price_to_earnings",
    "price_to_book",
    "peg_ratio",
    "eps",
    "net_income_margin",
    "dividend_yield",
    "trend_label",
    "key_reason",
]

LLM_FIELDS = [
    "date",
    "sector",
    "symbol",
    "portfolio_status",
    "sector_rank",
    "sector_count",
    "sector_confidence",
    "sector_confidence_note",
    "evidence_warning",
    "final_score",
    "quantitative_score",
    "scoring_model_version",
    "active_axis_weight_pct",
    "data_completeness_count",
    "data_completeness_total",
    "data_completeness_pct",
    "data_completeness_label",
    "news_score",
    "news_label",
    "trend_label",
    "period_return_pct",
    "daily_return_pct",
    "valuation_score",
    "profitability_score",
    "liquidity_score",
    "income_score",
    "quality_score",
    "quality_metric_count",
    "quality_metric_total",
    "quality_completeness_pct",
    "quarterly_fiscal_period",
    "quarterly_fiscal_end_date",
    "quarterly_available_date",
    "quarterly_date_basis",
    "quarterly_age_days",
    "quarterly_debt_to_equity",
    "quarterly_roe",
    "quarterly_current_ratio",
    "quarterly_revenue_growth",
    "quarterly_net_profit_growth",
    "quarterly_quality_note",
    "volatility_annualized_pct",
    "volatility_observations",
    "volatility_score",
    "volatility_label",
    "price_to_earnings",
    "price_to_book",
    "peg_ratio",
    "eps",
    "net_income_margin",
    "dividend_yield",
    "key_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create sector-relative rankings and LLM exports.")
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--as-of", help="score a specific date, default: latest scraped date")
    date_group.add_argument(
        "--all-dates",
        action="store_true",
        help="recalculate every date in stock details history",
    )
    parser.add_argument(
        "--quarterly-snapshot-backfill",
        action="store_true",
        help="allow the current quarterly snapshot in older scores; records explicit provenance",
    )
    parser.add_argument("--lookback-days", type=int, default=30, help="trend lookback window")
    parser.add_argument("--top-per-sector", type=int, default=5, help="rows per sector in LLM export")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_optional_csv(path: Path) -> list[dict]:
    return read_csv(path) if path.exists() else []


def read_csv_fieldnames(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f).fieldnames or [])


def portfolio_lookup(
    rows: list[dict],
    symbol_universe: set[str],
) -> tuple[set[str], dict[str, int]]:
    held = set()
    seen = set()
    diagnostics = {"matched": 0, "unmatched": 0, "invalid": 0, "duplicates": 0}
    for row in rows:
        symbol = row.get("symbol", "").strip().upper()
        if not symbol or not symbol.isalnum():
            diagnostics["invalid"] += 1
        elif symbol in seen:
            diagnostics["duplicates"] += 1
        elif symbol not in symbol_universe:
            seen.add(symbol)
            diagnostics["unmatched"] += 1
        else:
            seen.add(symbol)
            held.add(symbol)
            diagnostics["matched"] += 1
    return held, diagnostics


def add_portfolio_context(
    rows: list[dict],
    held_symbols: Optional[set[str]],
) -> list[dict]:
    return [
        {
            **row,
            "portfolio_status": (
                "unknown"
                if held_symbols is None
                else "held" if row["symbol"].strip().upper() in held_symbols else "not_held"
            ),
        }
        for row in rows
    ]


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    atomic_write_csv(path, rows, fieldnames)


def upsert_csv(path: Path, rows: list[dict], fieldnames: list[str], key_fields: list[str]) -> None:
    existing_fieldnames = read_csv_fieldnames(path)
    existing = read_csv(path) if path.exists() else []
    merged = {tuple(row.get(k, "") for k in key_fields): row for row in existing}
    for row in rows:
        key = tuple(row.get(k, "") for k in key_fields)
        merged[key] = {**merged.get(key, {}), **row}
    sorted_rows = sorted(merged.values(), key=lambda row: tuple(row.get(k, "") for k in key_fields))
    extra_fieldnames = [field for field in existing_fieldnames if field not in fieldnames]
    write_csv(path, sorted_rows, [*fieldnames, *extra_fieldnames])


def parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "null"):
        return None

    multiplier = 1.0
    suffix = text[-1:].upper()
    if suffix in {"K", "M", "B", "T"}:
        text = text[:-1]
        multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "T": 1_000_000_000_000}[suffix]

    try:
        parsed = float(text) * multiplier
        return parsed if math.isfinite(parsed) else None
    except ValueError:
        return None


def format_number(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def positive_number(value: Any) -> Optional[float]:
    parsed = parse_number(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def pct_change(start: Optional[float], end: Optional[float]) -> Optional[float]:
    if start is None or end is None or start == 0:
        return None
    return ((end - start) / start) * 100


def score_percentile(value: Optional[float], values: list[Optional[float]], higher_is_better: bool = True) -> float:
    valid = sorted(v for v in values if v is not None)
    if value is None or not valid:
        return 50.0
    if len(valid) == 1:
        return 50.0
    below_or_equal = sum(1 for v in valid if v <= value)
    percentile = ((below_or_equal - 1) / (len(valid) - 1)) * 100
    return percentile if higher_is_better else 100 - percentile


def average(parts: list[float]) -> float:
    return sum(parts) / len(parts) if parts else 50.0


def round_score(value: float) -> str:
    return format_number(max(0.0, min(100.0, value)))


def sector_confidence(count: int) -> str:
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        or SECTOR_CONFIDENCE_MODERATE_MIN <= 0
        or SECTOR_CONFIDENCE_HIGH_MIN <= SECTOR_CONFIDENCE_MODERATE_MIN
    ):
        raise ValueError("sector confidence requires a positive count and ordered thresholds")
    if count >= SECTOR_CONFIDENCE_HIGH_MIN:
        return "high"
    if count >= SECTOR_CONFIDENCE_MODERATE_MIN:
        return "moderate"
    return "low"


def validate_output_rows(
    rows: list[dict],
    fieldnames: list[str],
    key_fields: list[str],
    expected_date: str,
    minimum_rows: int,
) -> None:
    if len(rows) < minimum_rows:
        raise ValueError(
            f"refusing to replace ranking output: {len(rows)} rows, "
            f"minimum {minimum_rows}"
        )
    missing = [
        field for field in fieldnames
        if any(field not in row for row in rows)
    ]
    if missing:
        raise ValueError(
            "refusing to replace ranking output: missing fields "
            + ", ".join(missing)
        )
    keys = [tuple(row[field] for field in key_fields) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("refusing to replace ranking output: duplicate business keys")
    if any(row["date"] != expected_date for row in rows):
        raise ValueError("refusing to replace ranking output: unexpected as-of date")


def evidence_warning(row: dict) -> str:
    warnings = []
    if not row.get("quality_score"):
        warnings.append("quarterly quality unavailable")
    elif (parse_number(row.get("quarterly_age_days")) or 0) > QUARTERLY_STALE_DAYS:
        warnings.append("quarterly fundamentals stale")
    if row.get("volatility_label") == "unknown":
        warnings.append("volatility history insufficient")
    if row.get("sector_confidence") == "low":
        warnings.append("small sector peer group")
    return "; ".join(warnings)


def validate_axis_weights(weights: dict[str, float]) -> None:
    unknown = set(weights) - set(AXIS_NAMES)
    missing = set(AXIS_NAMES) - set(weights)
    if unknown or missing:
        parts = []
        if unknown:
            parts.append(f"unknown axes: {', '.join(sorted(unknown))}")
        if missing:
            parts.append(f"missing axes: {', '.join(sorted(missing))}")
        raise ValueError("invalid axis weights; " + "; ".join(parts))

    invalid = [
        name
        for name, weight in weights.items()
        if isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or weight < 0
    ]
    if invalid:
        raise ValueError(
            "axis weights must be finite, non-negative numbers; invalid: "
            + ", ".join(invalid)
        )

    total = sum(weights.values())
    if not math.isclose(total, 1.0, abs_tol=WEIGHT_SUM_TOLERANCE):
        raise ValueError(f"axis weights must sum to 1.0; got {total}")


def weighted_axis_score(
    axis_scores: dict[str, Optional[float]],
    weights: dict[str, float] = AXIS_WEIGHTS,
) -> tuple[float, tuple[str, ...], float]:
    validate_axis_weights(weights)

    unknown_scores = set(axis_scores) - set(AXIS_NAMES)
    if unknown_scores:
        raise ValueError(f"unknown axis scores: {', '.join(sorted(unknown_scores))}")

    active_axes = []
    weighted_total = 0.0
    active_weight = 0.0
    for axis in AXIS_NAMES:
        value = axis_scores.get(axis)
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"axis score for {axis} must be a finite number or None")
        active_axes.append(axis)
        weighted_total += value * weights[axis]
        active_weight += weights[axis]

    if not active_axes or active_weight <= 0:
        raise ValueError("cannot calculate quantitative score: no weighted axes are available")

    return weighted_total / active_weight, tuple(active_axes), active_weight


def blend_news_score(quantitative_score: float, news_score: Optional[float]) -> float:
    if not math.isfinite(NEWS_WEIGHT) or not 0 <= NEWS_WEIGHT <= 1:
        raise ValueError(f"NEWS_WEIGHT must be between 0 and 1; got {NEWS_WEIGHT}")
    if news_score is None:
        return quantitative_score
    return (
        quantitative_score * (1 - NEWS_WEIGHT)
        + max(0.0, min(100.0, news_score)) * NEWS_WEIGHT
    )


def sector_lookup(rows: list[dict]) -> dict[str, dict]:
    return {
        row["symbol"]: {
            "sector": row.get("sector") or "UNKNOWN",
            "name": row.get("name") or "",
        }
        for row in rows
    }


def news_lookup(rows: list[dict], as_of: str) -> dict[tuple[str, str], dict]:
    lookup = {}
    for row in rows:
        row_date = row.get("date", "")
        if row_date and row_date > as_of:
            continue
        symbol = row.get("symbol", "").upper()
        sector = row.get("sector", "").upper()
        if not symbol and not sector:
            continue
        key = (sector, symbol)
        if key not in lookup or row_date >= lookup[key].get("date", ""):
            lookup[key] = row
    return lookup


def find_news(news: dict[tuple[str, str], dict], sector: str, symbol: str) -> dict:
    symbol_news = news.get((sector.upper(), symbol.upper()))
    sector_news = news.get((sector.upper(), ""))
    return symbol_news or sector_news or {}


def join_sector(details: list[dict], sectors: dict[str, dict]) -> list[dict]:
    joined = []
    for row in details:
        sector = sectors.get(row.get("symbol", ""), {"sector": "UNKNOWN", "name": ""})
        joined.append({"sector": sector["sector"], "name": sector["name"], **row})
    return joined


def latest_date(details: list[dict]) -> str:
    dates = sorted({row["date"] for row in details if row.get("date")})
    if not dates:
        raise ValueError("no dates found in stock details history")
    return dates[-1]


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def quarterly_lookup(
    store: dict[str, dict],
    as_of: str,
    allow_snapshot_backfill: bool = False,
) -> dict[str, dict]:
    as_of_date = parse_iso_date(as_of)
    lookup = {}
    for symbol, record in store.items():
        try:
            scraped_date = datetime.fromisoformat(
                record["scraped_at"].replace("Z", "+00:00")
            ).date()
        except (AttributeError, KeyError, ValueError):
            continue
        snapshot_backfill = scraped_date > as_of_date
        if snapshot_backfill and not allow_snapshot_backfill:
            continue

        eligible = [
            row
            for row in quality_periods(record["data"])
            if parse_iso_date(row["fiscal_end_date"]) <= as_of_date
        ]
        if not eligible:
            continue

        selected = eligible[-1]
        debt_to_equity = selected.get("debt_to_equity")
        quality_note = ""
        if debt_to_equity is not None and debt_to_equity < 0:
            debt_to_equity = None
            quality_note = "negative debt-to-equity excluded"

        fiscal_end = parse_iso_date(selected["fiscal_end_date"])
        lookup[symbol.strip().upper()] = {
            **selected,
            "debt_to_equity": debt_to_equity,
            "available_date": "" if snapshot_backfill else scraped_date.isoformat(),
            "date_basis": (
                "user_approved_snapshot_backfill"
                if snapshot_backfill
                else "scraped_at"
            ),
            "age_days": (as_of_date - fiscal_end).days,
            "quality_note": quality_note,
        }
    return lookup


def history_by_symbol(rows: list[dict]) -> dict[str, list[tuple[date, Optional[float]]]]:
    deduplicated: dict[str, dict[date, Optional[float]]] = defaultdict(dict)
    for row in rows:
        symbol = row.get("symbol", "")
        row_date = row.get("date", "")
        if not symbol or not row_date:
            continue
        deduplicated[symbol][parse_iso_date(row_date)] = parse_number(row.get("price_close"))

    return {
        symbol: sorted(symbol_rows.items())
        for symbol, symbol_rows in deduplicated.items()
    }


def rolling_volatility(
    indexed_history: dict[str, list[tuple[date, Optional[float]]]],
    symbol: str,
    as_of: str,
    window: int = VOLATILITY_WINDOW,
    min_returns: int = VOLATILITY_MIN_RETURNS,
) -> tuple[Optional[float], int]:
    as_of_date = parse_iso_date(as_of)
    closes = [
        close
        for row_date, close in indexed_history.get(symbol, [])
        if row_date <= as_of_date and close is not None and close > 0
    ][-window:]
    returns = [
        (current / previous) - 1
        for previous, current in zip(closes, closes[1:])
    ]
    if len(returns) < min_returns:
        return None, len(returns)
    return statistics.stdev(returns) * 100, len(returns)


def volatility_label(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 67:
        return "low"
    if score >= 33:
        return "moderate"
    return "high"


def score_volatility(value: Optional[float], values: list[Optional[float]]) -> Optional[float]:
    valid = sorted(item for item in values if item is not None)
    if value is None or len(valid) < 2:
        return None
    below = sum(item < value for item in valid)
    equal = sum(item == value for item in valid)
    percentile = (below + (equal - 1) / 2) / (len(valid) - 1) * 100
    return 100 - percentile


def find_baseline_close(
    indexed_history: dict[str, list[tuple[date, Optional[float]]]],
    symbol: str,
    as_of: str,
    lookback_days: int,
) -> Optional[float]:
    as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
    start_date = as_of_date - timedelta(days=lookback_days)
    for row_date, close_price in indexed_history.get(symbol, []):
        if start_date <= row_date < as_of_date:
            return close_price
    return None


def add_calculated_fields(
    rows: list[dict],
    indexed_history: dict[str, list[tuple[date, Optional[float]]]],
    as_of: str,
    lookback_days: int,
    quarterly: Optional[dict[str, dict]] = None,
) -> list[dict]:
    quarterly = quarterly or {}
    calculated = []
    for row in rows:
        open_price = parse_number(row.get("price_open"))
        close_price = parse_number(row.get("price_close"))
        high_52wk = parse_number(row.get("high_52wk"))
        low_52wk = parse_number(row.get("low_52wk"))
        baseline_close = find_baseline_close(indexed_history, row["symbol"], as_of, lookback_days)
        volatility_daily, volatility_observations = rolling_volatility(
            indexed_history,
            row["symbol"],
            as_of,
        )

        daily_return = pct_change(open_price, close_price)
        period_return = pct_change(baseline_close, close_price)
        distance_high = pct_change(close_price, high_52wk)
        distance_low = pct_change(low_52wk, close_price)
        completeness_values = {
            field: parse_number(row.get(field))
            for field in CORE_COMPLETENESS_FIELDS.values()
        }
        completeness_count = sum(value is not None for value in completeness_values.values())
        if completeness_count == DATA_COMPLETENESS_TOTAL:
            completeness_label = "complete"
        elif completeness_count >= DATA_COMPLETENESS_PARTIAL_MIN:
            completeness_label = "partial"
        else:
            completeness_label = "low"
        quarterly_row = quarterly.get(row["symbol"].strip().upper(), {})

        calculated.append({
            **row,
            "_daily_return": daily_return,
            "_period_return": period_return if period_return is not None else daily_return,
            "_distance_high": distance_high,
            "_distance_low": distance_low,
            "_data_completeness_count": completeness_count,
            "_data_completeness_label": completeness_label,
            "_market_cap_num": parse_number(row.get("market_cap")),
            "_weekly_volume_num": parse_number(row.get("weekly_avg_volume")),
            "_free_float_pct_num": parse_number(row.get("free_float_pct")),
            "_dividend_yield_num": completeness_values["dividend_yield"],
            "_eps_num": completeness_values["eps"],
            "_net_margin_num": completeness_values["net_income_margin"],
            "_pbv_num": (
                completeness_values["price_to_book"]
                if completeness_values["price_to_book"] is not None
                and completeness_values["price_to_book"] > 0
                else None
            ),
            "_pe_num": (
                completeness_values["price_to_earnings"]
                if completeness_values["price_to_earnings"] is not None
                and completeness_values["price_to_earnings"] > 0
                else None
            ),
            "_peg_num": (
                completeness_values["peg_ratio"]
                if completeness_values["peg_ratio"] is not None
                and completeness_values["peg_ratio"] > 0
                else None
            ),
            "_quality_debt_to_equity": quarterly_row.get("debt_to_equity"),
            "_quality_roe": quarterly_row.get("roe"),
            "_quality_current_ratio": quarterly_row.get("current_ratio"),
            "_quality_revenue_growth": quarterly_row.get("revenue_growth"),
            "_quality_net_profit_growth": quarterly_row.get("net_profit_growth"),
            "_quarterly_fiscal_period": quarterly_row.get("fiscal_period", ""),
            "_quarterly_fiscal_end_date": quarterly_row.get("fiscal_end_date", ""),
            "_quarterly_available_date": quarterly_row.get("available_date", ""),
            "_quarterly_date_basis": quarterly_row.get("date_basis", ""),
            "_quarterly_age_days": quarterly_row.get("age_days"),
            "_quarterly_quality_note": quarterly_row.get("quality_note", ""),
            "_volatility_daily_pct": volatility_daily,
            "_volatility_observations": volatility_observations,
        })
    return calculated


def label_trend(period_return: Optional[float], daily_return: Optional[float]) -> str:
    signal = period_return if period_return is not None else daily_return
    if signal is None:
        return "unknown"
    if signal >= 5:
        return "strong_up"
    if signal >= 1:
        return "up"
    if signal <= -5:
        return "strong_down"
    if signal <= -1:
        return "down"
    return "flat"


def key_reason(row: dict) -> str:
    reasons = []
    if row.get("data_completeness_label") == "low":
        reasons.append(
            f"limited data {row['data_completeness_count']}/{row['data_completeness_total']}"
        )
    quality_score = parse_number(row.get("quality_score"))
    quality_count = int(row.get("quality_metric_count") or 0)
    if quality_score is not None and quality_count >= 3:
        if quality_score >= 70:
            reasons.append(f"strong quality {row['quality_score']} ({quality_count}/5)")
        elif quality_score <= 30:
            reasons.append(f"weak quality {row['quality_score']} ({quality_count}/5)")
    if parse_number(row["period_return_pct"]) is not None:
        reasons.append(f"{row['period_return_pct']}% period return")
    if row.get("price_to_earnings"):
        reasons.append(f"PE {row['price_to_earnings']}")
    if row.get("eps"):
        reasons.append(f"EPS {row['eps']}")
    if row.get("net_income_margin"):
        reasons.append(f"margin {row['net_income_margin']}%")
    return "; ".join(reasons[:4])


def score_sector(rows: list[dict], news: dict[tuple[str, str], dict]) -> list[dict]:
    confidence = sector_confidence(len(rows))
    confidence_note = (
        f"{len(rows)} scored members; {confidence} peer-count confidence"
    )
    values = defaultdict(list)
    for row in rows:
        for field in (
            "_daily_return",
            "_period_return",
            "_distance_high",
            "_distance_low",
            "_market_cap_num",
            "_weekly_volume_num",
            "_free_float_pct_num",
            "_dividend_yield_num",
            "_eps_num",
            "_net_margin_num",
            "_pbv_num",
            "_pe_num",
            "_peg_num",
            "_quality_debt_to_equity",
            "_quality_roe",
            "_quality_current_ratio",
            "_quality_revenue_growth",
            "_quality_net_profit_growth",
            "_volatility_daily_pct",
        ):
            values[field].append(row.get(field))

    scored = []
    for row in rows:
        trend_score = average([
            score_percentile(row.get("_daily_return"), values["_daily_return"]),
            score_percentile(row.get("_period_return"), values["_period_return"]),
            score_percentile(row.get("_distance_high"), values["_distance_high"], higher_is_better=False),
            score_percentile(row.get("_distance_low"), values["_distance_low"]),
        ])
        valuation_score = average([
            score_percentile(row.get("_pe_num"), values["_pe_num"], higher_is_better=False),
            score_percentile(row.get("_pbv_num"), values["_pbv_num"], higher_is_better=False),
            score_percentile(row.get("_peg_num"), values["_peg_num"], higher_is_better=False),
        ])
        profitability_score = average([
            score_percentile(row.get("_eps_num"), values["_eps_num"]),
            score_percentile(row.get("_net_margin_num"), values["_net_margin_num"]),
        ])
        liquidity_score = average([
            score_percentile(row.get("_market_cap_num"), values["_market_cap_num"]),
            score_percentile(row.get("_weekly_volume_num"), values["_weekly_volume_num"]),
            score_percentile(row.get("_free_float_pct_num"), values["_free_float_pct_num"]),
        ])
        income_score = score_percentile(row.get("_dividend_yield_num"), values["_dividend_yield_num"])
        quality_parts = []
        for field, higher_is_better in (
            ("_quality_debt_to_equity", False),
            ("_quality_roe", True),
            ("_quality_current_ratio", True),
            ("_quality_revenue_growth", True),
            ("_quality_net_profit_growth", True),
        ):
            valid_values = [value for value in values[field] if value is not None]
            if row.get(field) is not None and len(valid_values) >= 2:
                quality_parts.append(
                    score_percentile(
                        row[field],
                        valid_values,
                        higher_is_better=higher_is_better,
                    )
                )
        quality_score = average(quality_parts) if quality_parts else None
        valid_volatility = [
            value for value in values["_volatility_daily_pct"] if value is not None
        ]
        volatility_score = score_volatility(
            row.get("_volatility_daily_pct"),
            valid_volatility,
        )
        quantitative_score, _active_axes, active_weight = weighted_axis_score(
            {
                "valuation": valuation_score,
                "profitability": profitability_score,
                "income": income_score,
                "trend": trend_score,
                "liquidity": liquidity_score,
                "quality": quality_score,
            }
        )
        news_row = find_news(news, row["sector"], row["symbol"])
        news_score = parse_number(news_row.get("news_score"))
        final_score = blend_news_score(quantitative_score, news_score)

        output = {
            "date": row["date"],
            "sector": row["sector"],
            "symbol": row["symbol"],
            "name": row.get("name", ""),
            "portfolio_status": "",
            "sector_count": str(len(rows)),
            "sector_confidence": confidence,
            "sector_confidence_note": confidence_note,
            "evidence_warning": "",
            "final_score": round_score(final_score),
            "quantitative_score": round_score(quantitative_score),
            "scoring_model_version": SCORING_MODEL_VERSION,
            "active_axis_weight_pct": format_number(active_weight * 100),
            "data_completeness_count": str(row["_data_completeness_count"]),
            "data_completeness_total": str(DATA_COMPLETENESS_TOTAL),
            "data_completeness_pct": round_score(
                (row["_data_completeness_count"] / DATA_COMPLETENESS_TOTAL) * 100
            ),
            "data_completeness_label": row["_data_completeness_label"],
            "news_score": format_number(news_score),
            "news_label": news_row.get("news_label", ""),
            "news_note": news_row.get("news_note", ""),
            "trend_score": round_score(trend_score),
            "valuation_score": round_score(valuation_score),
            "profitability_score": round_score(profitability_score),
            "liquidity_score": round_score(liquidity_score),
            "income_score": round_score(income_score),
            "quality_score": round_score(quality_score) if quality_score is not None else "",
            "quality_metric_count": str(len(quality_parts)),
            "quality_metric_total": str(len(QUALITY_METRICS)),
            "quality_completeness_pct": round_score(
                (len(quality_parts) / len(QUALITY_METRICS)) * 100
            ),
            "quarterly_fiscal_period": row["_quarterly_fiscal_period"],
            "quarterly_fiscal_end_date": row["_quarterly_fiscal_end_date"],
            "quarterly_available_date": row["_quarterly_available_date"],
            "quarterly_date_basis": row["_quarterly_date_basis"],
            "quarterly_age_days": format_number(row["_quarterly_age_days"]),
            "quarterly_debt_to_equity": format_number(row["_quality_debt_to_equity"]),
            "quarterly_roe": format_number(row["_quality_roe"]),
            "quarterly_current_ratio": format_number(row["_quality_current_ratio"]),
            "quarterly_revenue_growth": format_number(row["_quality_revenue_growth"]),
            "quarterly_net_profit_growth": format_number(row["_quality_net_profit_growth"]),
            "quarterly_quality_note": row["_quarterly_quality_note"],
            "volatility_daily_pct": format_number(row["_volatility_daily_pct"]),
            "volatility_annualized_pct": format_number(
                row["_volatility_daily_pct"] * math.sqrt(TRADING_DAYS_PER_YEAR)
                if row["_volatility_daily_pct"] is not None
                else None
            ),
            "volatility_observations": str(row["_volatility_observations"]),
            "volatility_window": str(VOLATILITY_WINDOW),
            "volatility_score": (
                round_score(volatility_score) if volatility_score is not None else ""
            ),
            "volatility_label": volatility_label(volatility_score),
            "daily_return_pct": format_number(row.get("_daily_return")),
            "period_return_pct": format_number(row.get("_period_return")),
            "distance_from_52w_high_pct": format_number(row.get("_distance_high")),
            "distance_from_52w_low_pct": format_number(row.get("_distance_low")),
            "market_cap": row.get("market_cap", ""),
            "weekly_avg_volume": row.get("weekly_avg_volume", ""),
            "price_to_earnings": row.get("price_to_earnings", ""),
            "price_to_book": row.get("price_to_book", ""),
            "peg_ratio": row.get("peg_ratio", ""),
            "eps": row.get("eps", ""),
            "net_income_margin": row.get("net_income_margin", ""),
            "dividend_yield": row.get("dividend_yield", ""),
            "trend_label": label_trend(row.get("_period_return"), row.get("_daily_return")),
        }
        output["evidence_warning"] = evidence_warning(output)
        output["key_reason"] = key_reason(output)
        scored.append(output)

    scored.sort(key=lambda item: (-parse_number(item["final_score"]), item["symbol"]))
    for rank, row in enumerate(scored, 1):
        row["sector_rank"] = str(rank)
    return scored


def build_scores(
    details_with_sector: list[dict],
    all_history: list[dict],
    as_of: str,
    lookback_days: int,
    news: dict[tuple[str, str], dict],
    quarterly: Optional[dict[str, dict]] = None,
) -> list[dict]:
    today_rows = [row for row in details_with_sector if row.get("date") == as_of]
    indexed_history = history_by_symbol(all_history)
    calculated = add_calculated_fields(
        today_rows,
        indexed_history,
        as_of,
        lookback_days,
        quarterly,
    )

    by_sector = defaultdict(list)
    for row in calculated:
        by_sector[row["sector"]].append(row)

    scored = []
    for sector in sorted(by_sector):
        scored.extend(score_sector(by_sector[sector], news))
    return scored


def export_llm_summary(scores: list[dict], top_per_sector: int) -> list[dict]:
    selected = []
    by_sector = defaultdict(list)
    for row in scores:
        by_sector[row["sector"]].append(row)
    for sector in sorted(by_sector):
        ranked = sorted(by_sector[sector], key=lambda row: int(row["sector_rank"]))
        selected.extend(ranked[:top_per_sector])
        selected.extend(
            row
            for row in ranked[top_per_sector:]
            if row.get("portfolio_status") == "held"
        )
    return selected


def run(
    as_of: Optional[str] = None,
    lookback_days: int = 30,
    top_per_sector: int = 5,
    all_dates: bool = False,
    quarterly_snapshot_backfill: bool = False,
) -> dict:
    if as_of and all_dates:
        raise ValueError("as_of and all_dates cannot be used together")

    validate_axis_weights(AXIS_WEIGHTS)
    details = read_csv(DETAILS_CSV)
    sectors = sector_lookup(read_csv(SECTORS_CSV))
    details_with_sector = join_sector(details, sectors)
    available_dates = sorted({row["date"] for row in details_with_sector if row.get("date")})
    if not available_dates:
        raise ValueError("no dates found in stock details history")

    scoring_dates = available_dates if all_dates else [as_of or available_dates[-1]]
    unknown_dates = set(scoring_dates) - set(available_dates)
    if unknown_dates:
        raise ValueError(
            "no stock details found for date(s): " + ", ".join(sorted(unknown_dates))
        )

    all_news = read_optional_csv(NEWS_CSV)
    quarterly_store = read_store(QUARTERLY_RATIOS_JSON, "ratios")
    held_symbols = None
    portfolio_summary = {
        "enabled": False,
        "matched": 0,
        "unmatched": 0,
        "invalid": 0,
        "duplicates": 0,
    }
    if PORTFOLIO_CSV.exists():
        if read_csv_fieldnames(PORTFOLIO_CSV) != ["symbol"]:
            raise ValueError("portfolio CSV must contain exactly one column: symbol")
        held_symbols, diagnostics = portfolio_lookup(
            read_csv(PORTFOLIO_CSV),
            set(sectors),
        )
        portfolio_summary = {"enabled": True, **diagnostics}

    scores_by_date = {}
    for scoring_date in scoring_dates:
        scores_by_date[scoring_date] = build_scores(
            details_with_sector,
            details,
            scoring_date,
            lookback_days,
            news_lookup(all_news, scoring_date),
            quarterly_lookup(
                quarterly_store,
                scoring_date,
                allow_snapshot_backfill=quarterly_snapshot_backfill,
            ),
        )

    scores = [
        row
        for scoring_date in scoring_dates
        for row in scores_by_date[scoring_date]
    ]
    latest_scored_date = scoring_dates[-1]
    latest_scores = add_portfolio_context(
        scores_by_date[latest_scored_date],
        held_symbols,
    )
    minimum_latest_rows = max(1, math.ceil(len(sectors) * MIN_RANKING_COVERAGE))
    validate_output_rows(
        latest_scores,
        SCORE_FIELDS,
        ["date", "sector", "symbol"],
        latest_scored_date,
        minimum_latest_rows,
    )
    llm_scores = export_llm_summary(latest_scores, top_per_sector)
    validate_output_rows(
        llm_scores,
        LLM_FIELDS,
        ["date", "sector", "symbol"],
        latest_scored_date,
        1,
    )
    affected_months = sorted({date.fromisoformat(value).strftime("%Y-%m") for value in scoring_dates})

    details_fields = ["sector", "name", "date", "symbol"] + DETAIL_FIELDS
    write_csv(DETAILS_WITH_SECTOR_CSV, details_with_sector, details_fields)
    upsert_csv(SCORES_HISTORY_CSV, scores, SCORE_FIELDS, ["date", "sector", "symbol"])
    score_history = read_csv(SCORES_HISTORY_CSV)
    monthly_rows = 0
    for month in affected_months:
        monthly_scores = add_portfolio_context(
            [row for row in score_history if row["date"].startswith(month)],
            held_symbols,
        )
        monthly_rows = len(monthly_scores)
        write_csv(MONTHLY_DIR / f"{month}_sector_scores.csv", monthly_scores, SCORE_FIELDS)
    write_csv(LATEST_RANKINGS_CSV, latest_scores, SCORE_FIELDS)
    write_csv(
        LLM_DIR / "latest_sector_summary.csv",
        llm_scores,
        LLM_FIELDS,
    )

    if all_dates:
        print(
            f"scored {len(scores)} stock-date rows across {len(scoring_dates)} dates; "
            f"latest: {latest_scored_date}"
        )
    else:
        print(f"scored {len(latest_scores)} stocks for {latest_scored_date}")
    print(f"latest rankings: {LATEST_RANKINGS_CSV}")
    print(f"LLM summary: {LLM_DIR / 'latest_sector_summary.csv'}")
    if portfolio_summary["enabled"]:
        print(
            "portfolio: "
            f"matched {portfolio_summary['matched']}, "
            f"unmatched {portfolio_summary['unmatched']}, "
            f"invalid {portfolio_summary['invalid']}, "
            f"duplicates {portfolio_summary['duplicates']}"
        )
    volatility_eligible = sum(bool(row["volatility_score"]) for row in latest_scores)
    quality_eligible = sum(bool(row["quality_score"]) for row in latest_scores)
    quarterly_stale = sum(
        (parse_number(row["quarterly_age_days"]) or 0) > QUARTERLY_STALE_DAYS
        for row in latest_scores
        if row["quality_score"]
    )
    coverage_pct = len(latest_scores) / len(sectors) * 100
    warnings = []
    if len(latest_scores) < len(sectors):
        warnings.append(
            f"market coverage {len(latest_scores)}/{len(sectors)} ({coverage_pct:.1f}%)"
        )
    if quality_eligible < len(latest_scores):
        warnings.append(
            f"quarterly quality unavailable for {len(latest_scores) - quality_eligible} stocks"
        )
    if quarterly_stale:
        warnings.append(f"quarterly fundamentals stale for {quarterly_stale} stocks")
    if volatility_eligible < len(latest_scores):
        warnings.append(
            f"volatility unavailable for {len(latest_scores) - volatility_eligible} stocks"
        )
    if not portfolio_summary["enabled"]:
        warnings.append("portfolio context unavailable")
    if not NEWS_CSV.exists():
        warnings.append("optional news input unavailable")
    print(
        f"volatility: {volatility_eligible} eligible, "
        f"{len(latest_scores) - volatility_eligible} unknown "
        f"(minimum {VOLATILITY_MIN_RETURNS} returns)"
    )
    return {
        "as_of": latest_scored_date,
        "scoring_model_version": SCORING_MODEL_VERSION,
        "scored": len(latest_scores),
        "dates_scored": len(scoring_dates),
        "score_rows_written": len(scores),
        "portfolio": portfolio_summary,
        "warnings": warnings,
        "sources": {
            "daily_market": {
                "effective_date": latest_scored_date,
                "input_rows": len(details),
                "selected_rows": len(latest_scores),
                "coverage_pct": round(coverage_pct, 2),
            },
            "quarterly_fundamentals": {
                "eligible_rows": quality_eligible,
                "stale_rows": quarterly_stale,
            },
            "portfolio": portfolio_summary,
        },
        "volatility": {
            "eligible": volatility_eligible,
            "unknown": len(latest_scores) - volatility_eligible,
            "minimum_returns": VOLATILITY_MIN_RETURNS,
        },
        "latest_rankings": str(LATEST_RANKINGS_CSV),
        "latest_rows": len(latest_scores),
        "llm_summary": str(LLM_DIR / "latest_sector_summary.csv"),
        "llm_rows": len(llm_scores),
        "monthly_file": str(
            MONTHLY_DIR
            / f"{date.fromisoformat(latest_scored_date).strftime('%Y-%m')}_sector_scores.csv"
        ),
        "monthly_rows": monthly_rows,
    }


def main() -> None:
    args = parse_args()
    run(
        as_of=args.as_of,
        lookback_days=args.lookback_days,
        top_per_sector=args.top_per_sector,
        all_dates=args.all_dates,
        quarterly_snapshot_backfill=args.quarterly_snapshot_backfill,
    )


if __name__ == "__main__":
    main()
