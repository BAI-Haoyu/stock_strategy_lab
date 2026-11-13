"""Streamlit UI for the COMP4145 PD2 strategy research prototype."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import uuid
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data_source import YahooDataError, demo_prices, yahoo_prices
from engine import Settings, parse_tickers, parse_weights, align_prices, run_portfolio, indicators, STRATEGIES
from storage import save_experiment, list_experiments, load_experiment

st.set_page_config(page_title="Stock Strategy Lab", page_icon="📈", layout="wide")
COLORS = ["#0E7490", "#7C3AED", "#D97706", "#64748B"]
DB = Path(os.environ.get("STOCK_LAB_DB", str(Path(__file__).parent / "data" / "experiments.sqlite3")))
DEFAULTS = {"source": "Synthetic demo", "tickers": "MSFT, AAPL, GOOGL", "weights": "",
            "period": "5y", "capital": 10000.0, **asdict(Settings())}
if "pending_config" in st.session_state:
    for key, value in st.session_state.pop("pending_config").items():
        if key in DEFAULTS:
            st.session_state[key] = value
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("owner", uuid.uuid4().hex)


@st.cache_data(ttl=600, show_spinner=False)
def fetch(source, tickers, period):
    frames, description = demo_prices(tickers) if source == "Synthetic demo" else yahoo_prices(tickers, period)
    return frames, description, datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


st.title("Stock Strategy Lab")
st.write("Compare strategies. Understand portfolio risk. Keep a record of your experiments.")
st.caption("COMP4145 · PD2 Idea 1 | Educational research prototype · No order execution")
with st.sidebar:
    st.header("Build your experiment")
    st.selectbox("Data source", ["Synthetic demo", "Yahoo Finance"], key="source")
    st.text_input("Stock symbols · maximum 20", key="tickers")
    st.text_input("Weights in % · blank for equal weights", key="weights")
    st.selectbox("Requested history", ["2y", "5y", "10y"], key="period")
    st.number_input("Starting capital · USD", 100.0, 10000000.0, step=1000.0, key="capital")
    with st.expander("Strategy and cost settings"):
        st.number_input("Short moving average", 2, 249, key="short")
        st.number_input("Long moving average", 3, 250, key="long")
        st.number_input("RSI window", 2, 100, key="rsi_period")
        st.slider("RSI buy threshold", 5, 45, key="oversold")
        st.slider("RSI sell threshold", 55, 95, key="overbought")
        st.number_input("Profit target · fraction", 0.01, 2.0, step=0.01, key="target")
        st.number_input("Stop loss · fraction", 0.01, 0.90, step=0.01, key="stop")
        st.number_input("Maximum holding days · calendar", 1, 365, key="max_days")
        st.number_input("Fee · basis points per side", 0.0, 100.0, step=1.0, key="fee_bps")
        st.number_input("Slippage · basis points per side", 0.0, 100.0, step=1.0, key="slippage_bps")
    run = st.button("Run analysis", type="primary", use_container_width=True)
    st.caption("1 basis point = 0.01%. Yahoo results are cached for 10 minutes. All stocks must be quoted in USD.")

config = {key: st.session_state[key] for key in DEFAULTS}
if run or "result" not in st.session_state:
    try:
        tickers = parse_tickers(config["tickers"])
        weights = parse_weights(config["weights"], len(tickers))
        settings = Settings(**{key: config[key] for key in asdict(Settings())})
        settings.validate()
        with st.spinner("Loading data and comparing strategies…"):
            raw, source_note, fetched = fetch(config["source"], tuple(tickers), config["period"])
            frames, removed = align_prices(raw)
            result = run_portfolio(frames, weights, settings, config["capital"])
        st.session_state.result = {**result, "frames": frames, "weights": weights, "removed": removed,
                                   "source_note": source_note, "fetched": fetched, "config": config.copy(),
                                   "fingerprint": fingerprint(config)}
    except YahooDataError as exc:
        st.error(str(exc))
        st.info("Click Run analysis to retry the request. Failed requests are not cached. You can explicitly select Synthetic demo to explore the app with simulated prices.")
        st.caption("If this app was launched by a coding assistant, its background process may have temporary network permissions. Restart it from your own VS Code terminal using the README instructions.")
        st.stop()
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        st.info("Correct the inputs, retry Yahoo later, or explicitly select Synthetic demo.")
        st.stop()

result = st.session_state.result
if fingerprint(config) != result["fingerprint"]:
    st.warning("Settings have changed. Click Run analysis to update the results below.")
if result["config"]["source"] == "Synthetic demo":
    st.info("DEMO DATA · These prices are generated for testing. Results do not describe real stock performance. The history selector applies only to Yahoo.")
else:
    st.info("Historical Yahoo data may be delayed or incomplete. Past performance does not predict future returns.")
equity, metrics, frames = result["equity"], result["metrics"], result["frames"]
settings = Settings(**result["settings"])
st.caption(f"{result['source_note']} | Retrieved {result['fetched']} | Evaluation {equity.index[0].date()} to {equity.index[-1].date()} · {len(frames)} stocks")
if any(result["removed"].values()):
    st.warning("Only common valid dates are used; no prices are forward-filled. Removed rows: " + str(result["removed"]))

overview, strategies, price_tab, records = st.tabs(["Portfolio overview", "Strategy comparison", "Prices and trades", "Saved experiments"])
with overview:
    selected = st.selectbox("Strategy to inspect", STRATEGIES, key="overview_strategy")
    row = metrics.loc[selected]
    cols = st.columns(4)
    for col, label in zip(cols, ["Total return", "CAGR", "Max drawdown", "Annual volatility"]):
        col.metric(label, f"{row[label]:.2%}")
    st.subheader("Portfolio value after costs")
    fig = px.line(equity[[selected, "Buy and hold"]], color_discrete_sequence=[COLORS[0], COLORS[3]], labels={"value": "USD", "index": "Date", "variable": "Strategy"})
    fig.update_layout(legend_title_text="", margin=dict(l=10,r=10,t=10,b=10), height=340)
    st.plotly_chart(fig, use_container_width=True)
    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("Initial capital allocation")
        weights_frame = pd.DataFrame({"Stock": list(frames), "Weight": result["weights"]})
        st.dataframe(weights_frame.style.format({"Weight": "{:.1%}"}), hide_index=True, use_container_width=True)
        st.caption("Each stock receives a fixed capital sleeve. There is no cross-stock rebalancing; idle cash earns 0%.")
    with right:
        st.subheader("Daily return correlation")
        closes = pd.DataFrame({t: f["Close"] for t,f in frames.items()}).loc[equity.index[0]:]
        corr = closes.pct_change().dropna().corr()
        if len(frames) > 1:
            st.plotly_chart(px.imshow(corr, zmin=-1, zmax=1, color_continuous_scale="RdBu_r", text_auto=".2f", aspect="auto"), use_container_width=True)
        else:
            st.caption("Add another stock to compare correlations.")

with strategies:
    st.subheader("Same capital and evaluation dates for every strategy")
    st.dataframe(metrics.style.format({c: "${:,.2f}" if c == "Ending value" else "{:.2f}" if c == "Sharpe (rf 0%)" else "{:.2%}" for c in metrics.columns}, na_rep="N/A"), use_container_width=True)
    st.plotly_chart(px.line(equity/equity.iloc[0]*100, color_discrete_sequence=COLORS, labels={"value":"Indexed value · start 100", "index":"Date", "variable":"Strategy"}), use_container_width=True)
    dd = equity/equity.cummax()-1
    chart = px.line(dd, color_discrete_sequence=COLORS, labels={"value":"Drawdown", "index":"Date", "variable":"Strategy"})
    chart.update_yaxes(tickformat=".0%")
    st.plotly_chart(chart, use_container_width=True)
    st.download_button("Download performance CSV", metrics.to_csv().encode(), "strategy_metrics.csv", "text/csv")
    with st.expander("How to interpret the strategies and metrics", expanded=True):
        st.markdown("""
**Course golden cross:** buy after the short MA crosses above the long MA; exit at the profit target or calendar-day limit. Defaults preserve the course's 50/200 MA, 15% target and 60-day rule.

**SMA trend:** adds a stop loss and a downward MA-cross exit. **RSI reversion:** buys at or below the RSI low threshold; exits at the high threshold, target, stop or time limit. RSI uses simple rolling average gains/losses.

Every signal uses the previous close and fills at the next available open with fees and adverse slippage. Stop levels are not guaranteed execution prices. One position per stock; no leverage, short selling or tax model. Fractional shares are allowed. Open positions are marked to the last close, without a hypothetical final sale fee.

All strategies use the same warm-up and evaluation period. CAGR uses elapsed calendar years; volatility and Sharpe use 252 trading periods per year. Sharpe assumes a 0% risk-free rate and is N/A for zero volatility. No parameter optimization or out-of-sample validation has been performed.
""")

with price_tab:
    c1, c2 = st.columns(2)
    ticker = c1.selectbox("Stock", list(frames))
    strategy = c2.selectbox("Trading rule", STRATEGIES)
    lines = indicators(frames[ticker], settings)
    chart = go.Figure()
    for column, color in zip(["Close", "Short MA", "Long MA"], [COLORS[0], COLORS[1], COLORS[2]]):
        chart.add_trace(go.Scatter(x=lines.index, y=lines[column], name=column, line=dict(color=color)))
    orders = result["orders"]
    if not orders.empty:
        orders = orders[(orders.Ticker == ticker) & (orders.Strategy == strategy)]
        for side, symbol, color in [("Buy","triangle-up","#15803D"),("Sell","triangle-down","#B91C1C")]:
            subset = orders[orders.Side == side]
            chart.add_trace(go.Scatter(x=subset.Date,y=subset.Price,mode="markers",name=side,marker=dict(symbol=symbol,color=color,size=11)))
    chart.update_layout(yaxis_title="Adjusted price · USD", xaxis_title="Date", height=420)
    st.plotly_chart(chart, use_container_width=True)
    trades = result["trades"]
    if not trades.empty:
        trades = trades[(trades.Ticker == ticker) & (trades.Strategy == strategy)]
    if trades.empty:
        st.info("No trades for this stock and strategy during this period.")
    else:
        closed = trades[trades["Status"] != "Open at end"]
        st.caption(f"Closed trades: {len(closed)} | Open trades: {len(trades)-len(closed)} | Win rate: " + (f"{(closed['Net return'] > 0).mean():.1%}" if len(closed) else "N/A"))
        st.dataframe(trades.style.format({"Net return":"{:.2%}", "Entry price":"{:.2f}", "Exit price":"{:.2f}"}, na_rep="—"), hide_index=True, use_container_width=True)
    st.download_button("Download all trades CSV", result["trades"].to_csv(index=False).encode(), "trades.csv", "text/csv")
    st.download_button("Download equity CSV", equity.to_csv().encode(), "portfolio_equity.csv", "text/csv")

with records:
    st.subheader("Save and revisit an experiment")
    st.caption("SQLite records are isolated to this browser session. A new session cannot retrieve them. Cloud storage can reset on redeployment; download the JSON record for a durable copy. Do not store personal financial information.")
    record = {"config": result["config"], "summary": {"metrics": json.loads(metrics.to_json(orient="index")), "source": result["source_note"], "retrieved": result["fetched"], "start": str(equity.index[0].date()), "end": str(equity.index[-1].date())}}
    name = st.text_input("Experiment name", "My portfolio comparison")
    if st.button("Save experiment"):
        try:
            identifier = save_experiment(DB, st.session_state.owner, name, **record)
            st.success(f"Experiment {identifier} saved.")
        except (ValueError, OSError, sqlite3.Error) as exc:
            st.error(str(exc))
    st.download_button("Download experiment JSON", json.dumps(record, indent=2), "experiment.json", "application/json")
    try:
        saved = list_experiments(DB, st.session_state.owner)
        if saved:
            chosen = st.selectbox("Saved record", saved, format_func=lambda x:f"{x['id']} · {x['name']} · {x['created']}")
            item = load_experiment(DB, st.session_state.owner, chosen["id"])
            st.json(item["summary"], expanded=False)
            if st.button("Restore saved settings"):
                st.session_state.pending_config = item["config"]
                st.rerun()
    except (ValueError, OSError, sqlite3.Error) as exc:
        st.warning(f"Saved records are unavailable: {exc}")

st.divider()
st.caption("Research tool for learning and comparison. This app does not recommend trades or connect to a brokerage. Diversification and historical backtests do not guarantee returns.")
