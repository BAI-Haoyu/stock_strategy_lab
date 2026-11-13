# Yahoo request handling correction

13 November 2026. Follow-up to the initial build and the user's NVDA error report.

## Observations

- The original assistant-launched Streamlit process was still running and logged DNS failures for Yahoo, then emitted empty price results and misleading `Currency is unknown` messages.
- On the same computer, a newly authorized diagnostic process resolved both Yahoo query hosts and returned 501 daily NVDA price rows over two years, with Yahoo metadata identifying USD and exchange NMS.
- The original browser preview still failed while that diagnostic succeeded. This points to process-specific network access; it does not establish a failure of the user's internet connection.

## Changes

- Enable yfinance's `raise_errors=True` and check empty prices before checking currency.
- Separate transport failures, unavailable prices, missing currency metadata and verified non-USD currency.
- Retry transient failures once with a fresh ticker, stop at the first unresolved symbol, and avoid retrying rate limits or verified non-USD currency.
- Explain provider failures separately from invalid form inputs. Failed requests are not cached and never silently replaced with synthetic data.
- Add `Start_Stock_Strategy_Lab.cmd` for the user to launch from File Explorer, using a normal terminal rather than an assistant-managed background preview.

## Verification

The complete test suite passed: **36 passed in 10.46s**.

The seven additional checks cover transient DNS recovery, repeated DNS failure without a false currency diagnosis, empty prices checked before metadata, fresh metadata retry, non-USD rejection without retry, rate-limit fail-fast behavior, and the UI retry journey with uncached failures.

After the correction, a live NVDA request again returned 501 two-year daily observations and verified USD metadata.

A follow-up request for MSFT, AAPL and NVDA returned 501 aligned observations per stock; all four strategies completed with non-missing metrics.

The original assistant-launched server was stopped. The user then launched the new CMD file through Windows Run and skipped the optional Streamlit email prompt. Browser verification against that independently launched server succeeded for Yahoo Finance / NVDA / 2y. The rendered page identified Yahoo adjusted USD prices, retrieval at 2026-11-13 07:15:21 UTC, and evaluation dates 2025-09-03 through 2026-11-12, with no request error. This confirms the user-launched process worked at that checkpoint; it is not a guarantee of continuous provider availability.

The initial report's 29-test record and historical portfolio results refer to the original build checkpoint; this file records the later correction separately. No trading rules or portfolio arithmetic changed.
