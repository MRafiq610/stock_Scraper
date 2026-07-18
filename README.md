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

The final score is:

```text
30% trend
25% valuation
25% profitability
10% liquidity
10% income
```

Missing values receive a neutral score of 50 so incomplete fundamentals do not
automatically become the best or worst stock in a sector.

If a matching news row exists, the final score becomes:

```text
85% quantitative score
15% news score
```

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
