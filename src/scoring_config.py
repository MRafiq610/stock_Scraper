"""Versioned policy constants for sector-relative stock scoring."""

AXIS_NAMES = (
    "valuation",
    "profitability",
    "income",
    "trend",
    "liquidity",
    "quality",
)

AXIS_WEIGHTS = {
    "valuation": 0.25,
    "profitability": 0.20,
    "income": 0.20,
    "trend": 0.15,
    "liquidity": 0.10,
    "quality": 0.10,
}

SCORING_MODEL_VERSION = "v3_quarterly_quality"
NEWS_WEIGHT = 0.15
WEIGHT_SUM_TOLERANCE = 1e-9
SECTOR_CONFIDENCE_MODERATE_MIN = 5
SECTOR_CONFIDENCE_HIGH_MIN = 15
MIN_RANKING_COVERAGE = 0.90
QUARTERLY_STALE_DAYS = 180
