# Stock Strategy Lab

COMP4145 PD2 Idea 1: an enhanced educational stock strategy application.

## Three additional features

1. **Portfolio analysis**: 1–20 USD stocks; equal or custom weights; portfolio equity, CAGR, volatility, Sharpe, maximum drawdown and correlation.
2. **Strategy comparison**: the course golden-cross baseline, SMA trend with a stop and downward-cross exit, and RSI reversion, compared with buy and hold. Fees and slippage apply to each fill.
3. **SQLite experiment storage**: save configuration and result summaries, restore settings in the same browser session and export JSON. CSV exports cover metrics, trades and equity.

The four views are Portfolio overview, Strategy comparison, Prices and trades, and Saved experiments. Default prices are **synthetic demonstration data**, not actual market prices. Yahoo is a separate explicit choice; a failed request never silently falls back to synthetic prices.

## Run in VS Code

On the prepared Windows computer, double-click `Start_Stock_Strategy_Lab.cmd` in File Explorer. It uses the prepared environment and opens the app in your browser. Keep its terminal window open. Starting it yourself gives the app the normal network access of your terminal; a coding assistant's background preview may have temporary or restricted network access.

Install Python 3.12 and open this folder in VS Code. In the VS Code terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open <http://localhost:8501>. No API key is required. The optional Python extension and supplied `.vscode/launch.json` enable F5 after selecting the `.venv` interpreter. The terminal commands also work without extensions.

For the prepared local copy on this computer, run `run_local.ps1`. It uses the environment prepared for this task when available, and otherwise creates a project virtual environment. It does not change your PowerShell execution policy. If scripts are disabled, use the terminal commands above.

## Test

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

`requirements.txt` pins directly used packages; `requirements-lock.txt` records the complete tested environment. The lock file contains platform-specific transitive versions and is evidence of the local environment, not a guarantee of identical cloud resolution.

## Methodology

- Course defaults: 50/200-day SMA crossover, 15% target and 60 calendar days. The original course Python cell is archived in `reference/course_single_stock.py`, with its source URL. It is not imported because it executes network requests at import time.
- The new engine uses the **previous close** to determine an order and the **next available open** to execute it. It never fills a close-derived signal at that same close. Gap risk means stops are not guaranteed fill prices.
- One long position per stock; no overlapping positions, leverage or shorting. Fractional shares are allowed. Each stock receives a fixed capital sleeve; sleeves are not rebalanced. Idle cash earns 0%.
- Buy fill = open × (1 + slippage); sell fill = open × (1 − slippage). Fee = notional × fee rate per side. Defaults: 10 bps fee and 5 bps slippage.
- Golden cross exits on target or time limit. SMA trend also exits on a stop or downward cross. RSI reversion buys at/below the low threshold and exits at/above the high threshold, or the target/stop/time limit. RSI uses simple rolling gains/losses, not Wilder smoothing.
- All strategies and buy and hold share the same warm-up and evaluation dates. Opening a position after the final close is impossible; open positions are valued at the final close and excluded from closed-trade win rates. Final open positions incur no hypothetical sale fee.
- Only shared, positive, finite daily Open/Close observations are used; removed rows are reported. Prices are never forward-filled. Yahoo's `auto_adjust=True` uses adjusted historical prices; these are a return approximation and do not model dividend cash flows or taxes separately.
- CAGR uses elapsed calendar years. Volatility and Sharpe use 252 trading periods/year; Sharpe assumes a 0% risk-free rate. Zero volatility produces N/A Sharpe. Maximum drawdown includes initial capital.
- Yahoo stocks must have verified USD currency metadata. A missing/invalid symbol or non-USD symbol rejects the whole request rather than changing the requested allocation. A 10-minute Streamlit cache and sequential requests reduce provider pressure.

## Yahoo connection troubleshooting

Failed requests are not cached. The adapter raises download failures before checking currency, retries transient connection or missing-data failures once with a fresh ticker, and stops the portfolio request on the first unresolved symbol. It does not retry known non-USD assets or rate limits, infer USD from a symbol, or substitute synthetic prices. If Yahoo provides prices without currency metadata, the message identifies missing metadata separately.

If a preview launched by a coding assistant fails with DNS or connection errors, stop that preview and launch `Start_Stock_Strategy_Lab.cmd` from File Explorer, or run the commands above in your own VS Code terminal. This avoids depending on the assistant process's temporary network permissions. If the independently launched app still fails, check its terminal error and the provider connection. `Currency metadata missing` alone is not evidence that the stock is quoted in another currency.

The initial build evidence remains in `docs/verification.json`. The subsequent networking correction and regression checks are recorded in `docs/network_fix_verification.md`.

## Save and restore

SQLite is created at `data/experiments.sqlite3`. Each browser session receives a random owner token, and every read is filtered by that token. This is session separation, not user authentication. New sessions cannot retrieve earlier sessions' records. Do not use this prototype to store personal financial information.

Click **Save experiment**, select a saved record, then **Restore saved settings** and **Run analysis**. Restoring parameters may produce different results when Yahoo data changes; the saved summary preserves the previous result. Download JSON before closing the session or redeploying. Cloud-local storage may reset; persistent authenticated storage is a future requirement.

## Deploy

See `docs/DEPLOYMENT.md`. The public URL is **not created yet** because no GitHub repository or Streamlit account was available. Localhost is not a cloud submission URL.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit controls, charts, exports and session state |
| `engine.py` | Validation, indicators, portfolio simulation and metrics |
| `data_source.py` | Synthetic demo and Yahoo adapters |
| `storage.py` | Parameterized SQLite operations |
| `tests/` | Numerical, isolation and UI checks |
| `docs/` | Deployment, development record and verification evidence |
| `reference/` | Original course baseline source |

This is an educational research prototype. Historical or synthetic returns are not investment advice or evidence of future profitability.
