"""Data sources: explicitly synthetic demo or adjusted Yahoo daily prices."""
import numpy as np
import pandas as pd
from pathlib import Path
import os
import time

DEMO_TICKERS = ("MSFT", "AAPL", "GOOGL", "AMZN", "NVDA")


class YahooDataError(ValueError):
    """A provider failure, kept separate from invalid experiment settings."""

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def _provider_error(exc):
    if isinstance(exc, YahooDataError):
        return exc
    detail = str(exc)
    lower = detail.lower()
    if "resolve" in lower or "dns" in lower:
        reason = "The app process could not resolve Yahoo's server address (DNS failure)."
    elif "timeout" in lower or "timed out" in lower:
        reason = "Yahoo did not respond before the request timed out."
    elif "429" in lower or "rate limit" in lower or "too many requests" in lower:
        return YahooDataError("Yahoo temporarily limited requests. Wait before trying again.")
    elif "connect" in lower or "network" in lower:
        reason = "The app process could not connect to Yahoo."
    else:
        return YahooDataError(f"Yahoo could not supply usable historical data. Details: {detail}")
    return YahooDataError(reason, retryable=True)


def _yahoo_stock(yf, ticker, period):
    # A fresh Ticker prevents a failed history/metadata result surviving a retry.
    for attempt in range(2):
        try:
            stock = yf.Ticker(ticker)
            frame = stock.history(period=period, interval="1d", auto_adjust=True,
                                  timeout=12, raise_errors=True)
            # yfinance can otherwise log a transport error and return an empty frame.
            # Check prices before currency so failed downloads aren't mislabelled.
            if frame is None or frame.empty:
                raise YahooDataError("Yahoo returned no historical prices. The symbol or data service may be unavailable.", retryable=True)
            metadata = stock.get_history_metadata() or {}
            currency = metadata.get("currency")
            if not currency:
                raise YahooDataError("Prices arrived, but Yahoo did not provide currency metadata. USD could not be verified; the app will not guess the currency.", retryable=True)
            if currency != "USD":
                raise YahooDataError(f"Yahoo reports currency {currency}; only verified USD assets are supported.")
            return frame[["Open", "Close"]]
        except Exception as exc:
            failure = _provider_error(exc)
            if not failure.retryable or attempt == 1:
                raise failure from exc
            time.sleep(0.5)


def demo_prices(tickers):
    unknown = set(tickers) - set(DEMO_TICKERS)
    if unknown:
        raise ValueError("Demo supports MSFT, AAPL, GOOGL, AMZN and NVDA. Use Yahoo for other stocks.")
    dates = pd.bdate_range("2023-01-02", periods=900)
    result = {}
    for ticker in tickers:
        k = DEMO_TICKERS.index(ticker)
        rng = np.random.default_rng(4145+k)
        t = np.arange(len(dates))
        close = (90+k*30)*np.exp(0.0004*t + 0.23*np.sin(t/52+k/3) + np.cumsum(rng.normal(0, 0.008, len(t))))
        opening = np.r_[close[0], close[:-1]] * np.exp(rng.normal(0, 0.003, len(t)))
        result[ticker] = pd.DataFrame({"Open": opening, "Close": close}, index=dates)
    return result, "Synthetic demonstration data; not actual market prices."


def yahoo_prices(tickers, period):
    import yfinance as yf
    cache = Path(os.environ.get("STOCK_LAB_YAHOO_CACHE", str(Path(__file__).parent / "data" / "yahoo_cache")))
    cache.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    frames = {}
    for ticker in tickers:
        try:
            frames[ticker] = _yahoo_stock(yf, ticker, period)
        except YahooDataError as exc:
            # Stop the whole request immediately; don't query 19 more symbols
            # when the data source is already unavailable.
            raise YahooDataError(f"Yahoo data unavailable for {ticker}. No portfolio was calculated. {exc}") from exc
    return frames, "Yahoo Finance via yfinance; adjusted daily prices in USD."
