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
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

DATA_DIR = Path("data")
DETAILS_CSV = DATA_DIR / "stock_details_history.csv"
SECTORS_CSV = DATA_DIR / "kmiallshr_by_sector.csv"
NEWS_CSV = DATA_DIR / "news_scores.csv"
DETAILS_WITH_SECTOR_CSV = DATA_DIR / "stock_details_with_sector.csv"
SCORES_HISTORY_CSV = DATA_DIR / "sector_scores_history.csv"
LATEST_RANKINGS_CSV = DATA_DIR / "latest_sector_rankings.csv"
LLM_DIR = DATA_DIR / "llm"
MONTHLY_DIR = DATA_DIR / "monthly"

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

SCORE_FIELDS = [
    "date",
    "sector",
    "symbol",
    "name",
    "sector_rank",
    "sector_count",
    "final_score",
    "quantitative_score",
    "news_score",
    "news_label",
    "news_note",
    "trend_score",
    "valuation_score",
    "profitability_score",
    "liquidity_score",
    "income_score",
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
    "sector_rank",
    "sector_count",
    "final_score",
    "quantitative_score",
    "news_score",
    "news_label",
    "trend_label",
    "period_return_pct",
    "daily_return_pct",
    "valuation_score",
    "profitability_score",
    "liquidity_score",
    "income_score",
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
    parser.add_argument("--as-of", help="score a specific date, default: latest scraped date")
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


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def upsert_csv(path: Path, rows: list[dict], fieldnames: list[str], key_fields: list[str]) -> None:
    existing = read_csv(path) if path.exists() else []
    merged = {tuple(row.get(k, "") for k in key_fields): row for row in existing}
    for row in rows:
        merged[tuple(row.get(k, "") for k in key_fields)] = row
    sorted_rows = sorted(merged.values(), key=lambda row: tuple(row.get(k, "") for k in key_fields))
    write_csv(path, sorted_rows, fieldnames)


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
        return float(text) * multiplier
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


def history_by_symbol(rows: list[dict]) -> dict[str, list[tuple[date, Optional[float]]]]:
    indexed: dict[str, list[tuple[date, Optional[float]]]] = defaultdict(list)
    for row in rows:
        symbol = row.get("symbol", "")
        row_date = row.get("date", "")
        if not symbol or not row_date:
            continue
        indexed[symbol].append((parse_iso_date(row_date), parse_number(row.get("price_close"))))

    for symbol_rows in indexed.values():
        symbol_rows.sort(key=lambda item: item[0])
    return indexed


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
) -> list[dict]:
    calculated = []
    for row in rows:
        open_price = parse_number(row.get("price_open"))
        close_price = parse_number(row.get("price_close"))
        high_52wk = parse_number(row.get("high_52wk"))
        low_52wk = parse_number(row.get("low_52wk"))
        baseline_close = find_baseline_close(indexed_history, row["symbol"], as_of, lookback_days)

        daily_return = pct_change(open_price, close_price)
        period_return = pct_change(baseline_close, close_price)
        distance_high = pct_change(close_price, high_52wk)
        distance_low = pct_change(low_52wk, close_price)

        calculated.append({
            **row,
            "_daily_return": daily_return,
            "_period_return": period_return if period_return is not None else daily_return,
            "_distance_high": distance_high,
            "_distance_low": distance_low,
            "_market_cap_num": parse_number(row.get("market_cap")),
            "_weekly_volume_num": parse_number(row.get("weekly_avg_volume")),
            "_free_float_pct_num": parse_number(row.get("free_float_pct")),
            "_dividend_yield_num": parse_number(row.get("dividend_yield")),
            "_eps_num": parse_number(row.get("eps")),
            "_net_margin_num": parse_number(row.get("net_income_margin")),
            "_pbv_num": positive_number(row.get("price_to_book")),
            "_pe_num": positive_number(row.get("price_to_earnings")),
            "_peg_num": positive_number(row.get("peg_ratio")),
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
        quantitative_score = (
            trend_score * 0.30
            + valuation_score * 0.25
            + profitability_score * 0.25
            + liquidity_score * 0.10
            + income_score * 0.10
        )
        news_row = find_news(news, row["sector"], row["symbol"])
        news_score = parse_number(news_row.get("news_score"))
        if news_score is None:
            final_score = quantitative_score
        else:
            final_score = quantitative_score * 0.85 + max(0.0, min(100.0, news_score)) * 0.15

        output = {
            "date": row["date"],
            "sector": row["sector"],
            "symbol": row["symbol"],
            "name": row.get("name", ""),
            "sector_count": str(len(rows)),
            "final_score": round_score(final_score),
            "quantitative_score": round_score(quantitative_score),
            "news_score": format_number(news_score),
            "news_label": news_row.get("news_label", ""),
            "news_note": news_row.get("news_note", ""),
            "trend_score": round_score(trend_score),
            "valuation_score": round_score(valuation_score),
            "profitability_score": round_score(profitability_score),
            "liquidity_score": round_score(liquidity_score),
            "income_score": round_score(income_score),
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
) -> list[dict]:
    today_rows = [row for row in details_with_sector if row.get("date") == as_of]
    indexed_history = history_by_symbol(all_history)
    calculated = add_calculated_fields(today_rows, indexed_history, as_of, lookback_days)

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
    return selected


def run(
    as_of: Optional[str] = None,
    lookback_days: int = 30,
    top_per_sector: int = 5,
) -> dict:
    details = read_csv(DETAILS_CSV)
    sectors = sector_lookup(read_csv(SECTORS_CSV))
    details_with_sector = join_sector(details, sectors)
    as_of = as_of or latest_date(details_with_sector)
    news = news_lookup(read_optional_csv(NEWS_CSV), as_of)

    scores = build_scores(details_with_sector, details, as_of, lookback_days, news)
    month = date.fromisoformat(as_of).strftime("%Y-%m")

    details_fields = ["sector", "name", "date", "symbol"] + DETAIL_FIELDS
    write_csv(DETAILS_WITH_SECTOR_CSV, details_with_sector, details_fields)
    upsert_csv(SCORES_HISTORY_CSV, scores, SCORE_FIELDS, ["date", "sector", "symbol"])
    score_history = read_csv(SCORES_HISTORY_CSV)
    monthly_scores = [row for row in score_history if row["date"].startswith(month)]
    write_csv(LATEST_RANKINGS_CSV, scores, SCORE_FIELDS)
    write_csv(MONTHLY_DIR / f"{month}_sector_scores.csv", monthly_scores, SCORE_FIELDS)
    write_csv(LLM_DIR / "latest_sector_summary.csv", export_llm_summary(scores, top_per_sector), LLM_FIELDS)

    print(f"scored {len(scores)} stocks for {as_of}")
    print(f"latest rankings: {LATEST_RANKINGS_CSV}")
    print(f"LLM summary: {LLM_DIR / 'latest_sector_summary.csv'}")
    return {
        "as_of": as_of,
        "scored": len(scores),
        "latest_rankings": str(LATEST_RANKINGS_CSV),
        "llm_summary": str(LLM_DIR / "latest_sector_summary.csv"),
        "monthly_file": str(MONTHLY_DIR / f"{month}_sector_scores.csv"),
    }


def main() -> None:
    args = parse_args()
    run(
        as_of=args.as_of,
        lookback_days=args.lookback_days,
        top_per_sector=args.top_per_sector,
    )


if __name__ == "__main__":
    main()
