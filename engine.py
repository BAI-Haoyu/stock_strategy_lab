"""Auditable long-only backtests. Signals at close; execution next open."""
from dataclasses import dataclass, asdict
import re
import numpy as np
import pandas as pd

STRATEGIES = ("Course golden cross", "SMA trend", "RSI reversion")


@dataclass(frozen=True)
class Settings:
    short: int = 50
    long: int = 200
    rsi_period: int = 14
    oversold: int = 30
    overbought: int = 70
    target: float = 0.15
    stop: float = 0.08
    max_days: int = 60
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def validate(self):
        if not (2 <= self.short < self.long <= 250):
            raise ValueError("Moving averages must satisfy 2 <= short < long <= 250.")
        if not (2 <= self.rsi_period <= self.long):
            raise ValueError("RSI period must be between 2 and the long MA window.")
        if not (0 < self.oversold < self.overbought < 100):
            raise ValueError("RSI thresholds must satisfy 0 < low < high < 100.")
        if not (0 < self.target <= 2 and 0 < self.stop < 1 and 1 <= self.max_days <= 365):
            raise ValueError("Invalid profit target, stop loss or holding period.")
        if not (0 <= self.fee_bps <= 100 and 0 <= self.slippage_bps <= 100):
            raise ValueError("Fees and slippage must be between 0 and 100 basis points.")


def parse_tickers(text):
    values = [x.upper() for x in re.split(r"[\s,;]+", text.strip()) if x]
    tickers = list(dict.fromkeys(values))
    if not 1 <= len(tickers) <= 20:
        raise ValueError("Enter between 1 and 20 unique stock symbols.")
    if any(not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", x) for x in tickers):
        raise ValueError("Use stock symbols such as MSFT, AAPL or BRK-B.")
    return tickers


def parse_weights(text, count):
    if not text.strip():
        return np.ones(count) / count
    try:
        weights = np.array([float(x.strip()) for x in text.split(",")])
    except ValueError as e:
        raise ValueError("Weights must be comma-separated numbers.") from e
    if len(weights) != count or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("Provide one positive, finite weight per unique stock.")
    if not np.isclose(weights.sum(), 100, atol=0.01, rtol=0):
        raise ValueError("Weights must add up to 100 percent.")
    return weights / weights.sum()


def indicators(frame, settings):
    close = frame["Close"]
    short = close.rolling(settings.short).mean()
    long = close.rolling(settings.long).mean()
    delta = close.diff()
    # Simple rolling RSI, deliberately documented rather than called Wilder RSI.
    gain = delta.clip(lower=0).rolling(settings.rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(settings.rsi_period).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100).mask((loss == 0) & (gain == 0), 50)
    return pd.DataFrame({"Close": close, "Short MA": short, "Long MA": long,
                         "RSI": rsi, "Cross up": (short > long) & (short.shift() <= long.shift()),
                         "Cross down": (short < long) & (short.shift() >= long.shift())})


def align_prices(frames):
    if not frames:
        raise ValueError("No price data available.")
    clean = {}
    original = {}
    for ticker, frame in frames.items():
        data = frame.loc[:, ["Open", "Close"]].copy()
        data.index = pd.DatetimeIndex(data.index).tz_localize(None).normalize()
        if data.index.has_duplicates:
            raise ValueError(f"Duplicate daily prices for {ticker}.")
        data = data.sort_index().apply(pd.to_numeric, errors="coerce")
        original[ticker] = len(data)
        data = data.replace([np.inf, -np.inf], np.nan).dropna()
        data = data[(data > 0).all(axis=1)]
        clean[ticker] = data
    common = next(iter(clean.values())).index
    for frame in clean.values():
        common = common.intersection(frame.index)
    if len(common) < 3:
        raise ValueError("Too few shared valid dates across the selected stocks.")
    return {t: f.loc[common] for t, f in clean.items()}, {t: n-len(common) for t, n in original.items()}


def backtest(frame, strategy, settings, capital):
    settings.validate()
    if strategy not in (*STRATEGIES, "Buy and hold"):
        raise ValueError("Unknown strategy.")
    if not np.isfinite(capital) or capital <= 0:
        raise ValueError("Starting capital must be positive.")
    if len(frame) <= settings.long + 5:
        raise ValueError(f"Need more than {settings.long + 5} common price rows; choose a longer period.")
    signals = indicators(frame, settings)
    cash, shares = float(capital), 0.0
    entry_date = entry_price = entry_value = None
    fee = settings.fee_bps / 10000
    slip = settings.slippage_bps / 10000
    nav = {frame.index[settings.long - 1]: cash}
    trades, orders = [], []
    for i in range(settings.long, len(frame)):
        date, prev = frame.index[i], frame.index[i - 1]
        open_price, close_price = frame.iloc[i][["Open", "Close"]]
        prior_close = frame.iloc[i - 1]["Close"]
        signal = signals.iloc[i - 1]
        sell_reason = None
        # Only information available at the previous close is consulted.
        if shares and strategy != "Buy and hold":
            if prior_close >= entry_price * (1 + settings.target):
                sell_reason = "Profit target"
            elif strategy != "Course golden cross" and prior_close <= entry_price * (1 - settings.stop):
                sell_reason = "Stop loss"
            elif (prev - entry_date).days >= settings.max_days:
                sell_reason = "Time limit"
            elif strategy == "SMA trend" and signal["Cross down"]:
                sell_reason = "Cross down"
            elif strategy == "RSI reversion" and signal["RSI"] >= settings.overbought:
                sell_reason = "RSI high"
        if shares and sell_reason:
            fill = open_price * (1 - slip)
            cash = shares * fill * (1 - fee)
            trades.append({"Entry date": entry_date, "Exit date": date, "Entry price": entry_price,
                           "Exit price": fill, "Net return": cash / entry_value - 1,
                           "Days": (date-entry_date).days, "Status": sell_reason})
            orders.append({"Date": date, "Side": "Sell", "Price": fill, "Shares": shares,
                           "Fee": shares * fill * fee, "Reason": sell_reason})
            shares = 0.0
        elif not shares:
            buy = ((strategy == "Buy and hold" and i == settings.long)
                   or (strategy in STRATEGIES[:2] and signal["Cross up"])
                   or (strategy == "RSI reversion" and signal["RSI"] <= settings.oversold))
            if buy:
                fill = open_price * (1 + slip)
                entry_value, entry_date, entry_price = cash, date, fill
                shares = cash / (fill * (1 + fee))
                cash = 0.0
                orders.append({"Date": date, "Side": "Buy", "Price": fill, "Shares": shares,
                               "Fee": shares * fill * fee, "Reason": strategy})
        nav[date] = cash + shares * close_price
    if shares:
        trades.append({"Entry date": entry_date, "Exit date": pd.NaT, "Entry price": entry_price,
                       "Exit price": np.nan, "Net return": np.nan,
                       "Days": (frame.index[-1] - entry_date).days, "Status": "Open at end"})
    return pd.Series(nav, name=strategy), pd.DataFrame(trades), pd.DataFrame(orders)


def performance(equity):
    returns = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    ratio = equity.iloc[-1] / equity.iloc[0]
    vol = returns.std(ddof=1)
    return {"Total return": ratio-1, "CAGR": ratio**(1/years)-1 if years > 0 else np.nan,
            "Annual volatility": vol*np.sqrt(252),
            "Sharpe (rf 0%)": returns.mean()/vol*np.sqrt(252) if vol > 1e-12 else np.nan,
            "Max drawdown": (equity/equity.cummax()-1).min(), "Ending value": equity.iloc[-1]}


def run_portfolio(frames, weights, settings, capital):
    if len(frames) != len(weights) or not np.isclose(sum(weights), 1):
        raise ValueError("Portfolio weights must match the stock count and sum to one.")
    curves, all_trades, all_orders = {}, [], []
    for strategy in (*STRATEGIES, "Buy and hold"):
        sleeves = []
        for (ticker, frame), weight in zip(frames.items(), weights):
            nav, trades, orders = backtest(frame, strategy, settings, capital * weight)
            sleeves.append(nav)
            if not trades.empty:
                trades["Ticker"], trades["Strategy"] = ticker, strategy
                all_trades.append(trades)
            if not orders.empty:
                orders["Ticker"], orders["Strategy"] = ticker, strategy
                all_orders.append(orders)
        curves[strategy] = pd.concat(sleeves, axis=1).sum(axis=1)
    equity = pd.DataFrame(curves)
    metrics = pd.DataFrame({s: performance(equity[s]) for s in equity}).T
    return {"equity": equity, "metrics": metrics,
            "trades": pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(),
            "orders": pd.concat(all_orders, ignore_index=True) if all_orders else pd.DataFrame(),
            "settings": asdict(settings)}
