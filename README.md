Stock Scraper Pipeline
======================

This project collects KMIALLSHR stock data, joins each stock to its PSX sector,
scores stocks against other stocks in the same sector, and writes compact files
for monthly LLM review.

Daily Command
-------------

Run the complete pipeline:

```powershell
uv run src/daily_pipeline.py
```

By default it skips Saturday and Sunday because the market is closed.

For testing on a weekend:

```powershell
uv run src/daily_pipeline.py --force --details-limit 5 --details-delay 0
```

For a faster full run:

```powershell
uv run src/daily_pipeline.py --details-delay 0
```

Pipeline Stages
---------------

1. `src/get_stocks.py`
   Refreshes `data/kmiallshr_companies.csv`.

2. `src/psx_sector_mapper.py`
   Refreshes `data/kmiallshr_by_sector.csv`.

3. `src/stock_details_scraper.py`
   Appends or updates the daily stock snapshot in
   `data/stock_details_history.csv`.

4. `src/sector_score_pipeline.py`
   Builds sector-relative rankings and LLM exports.

Manual Quarterly Fundamentals
-----------------------------

Quarterly fundamentals are refreshed manually and are not part of the daily
pipeline:

```powershell
uv run src/quarterly_fundamentals_scraper.py
```

The default refreshes the companies already supported by each AskAnalyst
endpoint: currently 216 result companies and 196 ratio companies. To retry one
company or discover newly supported companies:

```powershell
uv run src/quarterly_fundamentals_scraper.py --symbol EFERT
uv run src/quarterly_fundamentals_scraper.py --discover
```

Only two quarterly source files are maintained:

```text
data/quarterly_results.json
data/quarterly_ratios.json
```

Each company record retains its own `scraped_at` timestamp. The API does not
provide a filing-publication date, so scoring uses `scraped_at` as a
conservative, lower-confidence availability date. A score cannot use data
collected after its `as_of` date. Source period labels such as `Mar-26` are
preserved rather than guessing the company's fiscal-quarter numbering.

Private Ownership Context
-------------------------

Copy `data/portfolio.example.csv` to the ignored `data/portfolio.csv` and list
only the ticker symbols you currently own:

```csv
symbol
EFERT
OGDC
```

Quantity, average cost, owner, allocation, and other portfolio values are
intentionally unsupported. An alternate private path may be supplied locally:

```powershell
$env:PORTFOLIO_CSV="C:\private\portfolio.csv"
```

When the file exists, the latest ranking and LLM summary report only
`portfolio_status` as `held` or `not_held`. When it is absent, the status is
`unknown`. Monthly exports also show this current status on every dated row;
it must not be interpreted as historical ownership. Score history leaves the
field blank. Portfolio context never affects scores or ranks. The LLM summary
keeps every held symbol even when it falls below the normal top-per-sector
cutoff.

The real file is ignored by Git. Generated latest/LLM outputs reveal which
symbols are held, so use them only in a repository and review workflow where
that disclosure is acceptable. No cloud portfolio delivery is configured.

Rolling Volatility Context
--------------------------

The scoring pipeline automatically measures recent price volatility from the
daily close history. It uses up to 30 valid trading observations ending on the
score date, calculates consecutive close-to-close returns, and reports their
sample standard deviation. At least 20 returns are required.

`volatility_daily_pct` is the daily standard deviation.
`volatility_annualized_pct` multiplies it by `sqrt(252)`.
`volatility_observations` shows the number of returns available, and
`volatility_window` records the 30-observation limit.

Within each sector, eligible stocks receive a `volatility_score` where higher
means more stable. Percentile scores of 67-100 are labeled `low` volatility,
33-66 `moderate`, and below 33 `high`. Stocks without enough history, or
without another eligible sector peer, are `unknown`. These are informational
fields only and do not affect any score, weight, or rank.

Volatility measures price movement, not total investment risk. Infrequently
traded stocks can appear artificially stable because their closing price may
remain unchanged; interpret this context alongside liquidity.

Pipeline Safety and Latest-Run Manifest
---------------------------------------

CSV outputs are written to a temporary file in the destination directory and
atomically replaced only after the write completes. Before latest rankings are
replaced, the scorer requires valid schemas, unique date/sector/symbol keys,
the expected as-of date, and at least 90% coverage of the mapped symbol
universe. A failed or severely partial scrape therefore preserves the previous
valid ranking files.

The automated daily pipeline writes one privacy-safe status file:

```text
data/manifests/latest_pipeline_run.json
```

It records the run status and timestamps, score date, input/output row counts,
failed-symbol count, source coverage, output paths, and concise warnings. It
does not contain credentials, raw third-party payloads, portfolio symbols or
values, or failed-symbol names. The file is replaced on every run; dated
manifest archives and external monitoring are intentionally omitted.

`evidence_warning` appears in full, monthly, and LLM score exports. It flags
missing quarterly quality, quarterly data older than 180 days, insufficient
volatility history, and small sector peer groups. These warnings never alter
scores or ranks.

Optional News Input
-------------------

If you want news/current affairs to affect rankings, add rows to:

```text
data/news_scores.csv
```

Format:

```csv
date,sector,symbol,news_score,news_label,news_note
2026-07-31,CEMENT,ACPL,70,positive,Strong sector demand and company-specific update
2026-07-31,CEMENT,,40,negative,Sector pressure from higher energy costs
```

Use `symbol` for company-specific news. Leave `symbol` blank for sector-wide
news. `news_score` is 0-100, where 50 is neutral. If no news row exists, the
ranking uses only quantitative data.

Important Output Files
----------------------

Raw daily history:

```text
data/stock_details_history.csv
```

Raw daily history with sector/name:

```text
data/stock_details_with_sector.csv
```

All sector scores over time:

```text
data/sector_scores_history.csv
```

Latest full ranking:

```text
data/latest_sector_rankings.csv
```

Small LLM-friendly monthly review file:

```text
data/llm/latest_sector_summary.csv
```

Monthly score archive:

```text
data/monthly/YYYY-MM_sector_scores.csv
```

How Scoring Works
-----------------

Stocks are ranked only against stocks in the same sector.

Sector-size confidence makes the peer-group limitation explicit:

```text
fewer than 5 scored members: low
5 through 14 scored members: moderate
15 or more scored members: high
```

`sector_count` is the number of daily rows scored in that sector, not the
number of exchange listings or the valid peer count for every individual
metric. `sector_confidence` and `sector_confidence_note` are informational and
never change scores or ranks. The `UNKNOWN` sector follows the same thresholds
but still indicates that its sector mapping is unavailable.

The V2 quantitative model uses these configured base weights:

```text
25% valuation
20% profitability
20% income
15% trend
10% liquidity
10% quality
```

The policy lives in `src/scoring_config.py`. Phase 2 history is labeled
`v2_value_income`; scores produced with quarterly-quality integration are
labeled `v3_quarterly_quality`. Changing the weights or axis meaning changes
ranking semantics and requires a new `SCORING_MODEL_VERSION`.

Quality requires eligible quarterly evidence and arrives in Phase 3. Until it
is available, it is excluded rather than assigned a neutral value. The five
available axes carry 90% of the base weight, and the quantitative score divides
their weighted sum by `0.90`. This keeps the result on a 0-100 scale.
`active_axis_weight_pct` reports the contributing base-weight coverage.

When quarterly ratios are eligible, quality averages sector-relative
percentiles for debt-to-equity (lower is better), ROE, current ratio, revenue
growth, and net-profit/PAT growth (higher is better). A metric contributes only
when at least two stocks in that sector have comparable values. Negative
debt-to-equity is excluded rather than rewarded. Stocks without eligible
quality evidence remain blank and continue using the normalized five-axis
score.

Missing values receive a neutral score of 50 so incomplete fundamentals do not
automatically become the best or worst stock in a sector.

Each scored row also reports evidence coverage for these six daily fundamental
fields: P/E, P/B, PEG, EPS, net margin, and dividend yield. The additive
`data_completeness_count`, `data_completeness_total`,
`data_completeness_pct`, and `data_completeness_label` columns appear in score
history, latest rankings, monthly exports, and the compact LLM summary.

Completeness describes evidence coverage, not score quality:

- `low` means fewer than three of the six fields are populated.
- `partial` means three to five fields are populated.
- `complete` means all six fields are populated.

Zero and negative numeric values count as present, even when a particular
scoring metric requires a positive value. Blank, invalid, NaN, and infinite
values count as missing. A high score with sparse evidence should be reviewed
cautiously. Missing metrics may still receive V1's neutral percentile value;
completeness does not change the score or constitute an investment
recommendation.

If a matching news row exists, the final score becomes:

```text
85% quantitative score
15% news score
```

The news blend remains separate from the quantitative axis weights. Without
valid news, the final score equals the quantitative score.

To intentionally recalculate every historical date from its matching daily
snapshot:

```powershell
uv run src/sector_score_pipeline.py --all-dates
```

The July 2026 quarterly snapshot was explicitly approved for the existing July
daily history despite lacking publication dates. That one-time migration uses:

```powershell
uv run src/sector_score_pipeline.py --all-dates --quarterly-snapshot-backfill
```

Affected rows record `quarterly_date_basis=user_approved_snapshot_backfill`
and leave `quarterly_available_date` blank. Normal scoring does not enable this
exception and continues enforcing the conservative `scraped_at` rule.

Monthly LLM Workflow
--------------------

Once per month, give the LLM these files:

```text
data/llm/latest_sector_summary.csv
data/monthly/YYYY-MM_sector_scores.csv
```

Avoid sending the full raw history unless you need deep debugging. The LLM
summary is designed for low token usage and high signal.

Local Windows Scheduling
------------------------

Use Windows Task Scheduler:

1. Create Basic Task.
2. Trigger: daily, Monday-Friday.
3. Action: Start a program.
4. Program/script:

```text
powershell.exe
```

5. Arguments:

```text
-ExecutionPolicy Bypass -File "C:\Users\rafique_\Desktop\New folder\Stock_Scraper\scripts\run_daily_pipeline.ps1"
```

Cloud Deployment Idea
---------------------

Recommended first deployment: GitHub Actions.

Why:

- your laptop can stay off
- weekday scheduling is built in
- output CSVs can be committed back to the repo
- output CSVs are also uploaded as workflow artifacts
- success/failure notifications can use repository secrets

The workflow file is:

```text
.github/workflows/daily-stock-pipeline.yml
```

It runs Monday-Friday at `13:00 UTC`, which is `18:00 Pakistan time`.

Manual run:

1. Push this repo to GitHub.
2. Open the repo on GitHub.
3. Go to Actions.
4. Select `Daily Stock Pipeline`.
5. Click `Run workflow`.

Notification Setup
------------------

The pipeline supports Email, Telegram, or a generic webhook.

Recommended free option: Email.

Email secrets:

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
EMAIL_TO
EMAIL_FROM
```

For Gmail, typical values are:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
EMAIL_TO=your_email@gmail.com
EMAIL_FROM=your_email@gmail.com
```

Use an app password, not your normal email password.

Telegram secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Generic webhook secret:

```text
NOTIFY_WEBHOOK_URL
```

Add them in GitHub:

```text
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret
```

If no notification secrets are set, the pipeline still runs normally, but no
message is sent.

Success notification includes:

```text
date
fetched count
failed count
new rows
updated rows
scored count
ranking file path
monthly file path
LLM summary path
```

Failure notification includes the exception type and error message.

Other Deployment Options
------------------------

A small VM also works, but it is more maintenance. You would run:

```powershell
uv run src/daily_pipeline.py
```

Use a VM only if GitHub Actions cannot reach the target sites reliably or you
want full control over storage/runtime.
