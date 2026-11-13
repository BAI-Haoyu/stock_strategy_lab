from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from engine import Settings, parse_tickers, parse_weights, align_prices, backtest, run_portfolio, performance
from data_source import demo_prices
from storage import save_experiment, load_experiment, list_experiments


def prices(values, opens=None):
    return pd.DataFrame({"Open": values if opens is None else opens, "Close":values}, index=pd.bdate_range("2024-01-01", periods=len(values)))


def test_ticker_limit_and_deduplication():
    assert parse_tickers("msft, AAPL msft") == ["MSFT", "AAPL"]
    with pytest.raises(ValueError):
        parse_tickers(",".join(f"T{i}" for i in range(21)))


@pytest.mark.parametrize("value", ["", "^GSPC", "MSFT<script>"])
def test_invalid_tickers(value):
    with pytest.raises(ValueError):
        parse_tickers(value)


@pytest.mark.parametrize("value", ["60,30", "100,-1", "nan,100", "100", "foo,bar"])
def test_invalid_weights(value):
    with pytest.raises(ValueError):
        parse_weights(value, 2)


def test_weights():
    assert np.allclose(parse_weights("", 3), [1/3]*3)
    assert np.allclose(parse_weights("60,40", 2), [.6,.4])


def test_buy_hold_exact_costs():
    frame = prices([100.]*12)
    settings = Settings(short=2,long=4,rsi_period=2,fee_bps=100,slippage_bps=100)
    nav, trades, orders = backtest(frame, "Buy and hold", settings, 1000)
    assert nav.iloc[0] == 1000
    assert nav.iloc[-1] == pytest.approx(1000/1.01/1.01)
    assert len(orders) == 1
    assert trades.iloc[0]["Status"] == "Open at end"
    assert np.isnan(trades.iloc[0]["Net return"])


def test_signal_executes_on_next_open():
    frame = prices([10,9,8,7,8,10,12,13,14,15,16,17], [10,9,8,7,8,10,20,13,14,15,16,17])
    settings = Settings(short=2,long=4,rsi_period=2,fee_bps=0,slippage_bps=0,target=2,stop=.9,max_days=365)
    _, _, orders = backtest(frame,"Course golden cross",settings,1000)
    assert orders.iloc[0].Date == frame.index[6]
    assert orders.iloc[0].Price == 20
    assert len(orders) == 1


def test_future_changes_do_not_change_past_nav():
    frames,_ = demo_prices(["MSFT"])
    frame = frames["MSFT"]
    settings = Settings()
    original,_,_ = backtest(frame,"SMA trend",settings,1000)
    changed = frame.copy()
    changed.iloc[600:] *= 3
    altered,_,_ = backtest(changed,"SMA trend",settings,1000)
    pd.testing.assert_series_equal(original.loc[:frame.index[599]],altered.loc[:frame.index[599]])


def test_alignment_does_not_forward_fill():
    a = prices([10.]*12)
    b = a.copy()
    b.iloc[5,0] = np.nan
    aligned,removed = align_prices({"A":a,"B":b})
    assert len(aligned["A"]) == 11
    assert a.index[5] not in aligned["B"].index
    assert removed == {"A":1,"B":1}


def test_weighted_sleeves_match_hand_calculation():
    a = prices([100.]*12)
    b = prices([100.]*5+[110.]*7)
    settings = Settings(short=2,long=4,rsi_period=2,fee_bps=0,slippage_bps=0)
    result=run_portfolio({"A":a,"B":b},[.6,.4],settings,1000)
    assert result["equity"]["Buy and hold"].iloc[-1] == pytest.approx(1040)


def test_drawdown_uses_initial_capital():
    nav=pd.Series([100,80,90], index=pd.bdate_range("2024-01-01",periods=3))
    assert performance(nav)["Max drawdown"] == pytest.approx(-.2)
    assert performance(nav)["Total return"] == pytest.approx(-.1)


def test_no_trade_is_valid_cash_result():
    nav,trades,orders = backtest(prices([10.]*12),"SMA trend",Settings(short=2,long=4,rsi_period=2),1000)
    assert (nav == 1000).all() and trades.empty and orders.empty
    assert np.isnan(performance(nav)["Sharpe (rf 0%)"])


def test_sqlite_roundtrip_and_session_isolation(tmp_path):
    path=tmp_path/"records.sqlite3"
    identifier=save_experiment(path,"alice","Robert'); DROP TABLE experiments;--",{"stock":"MSFT"},{"value":100})
    assert load_experiment(path,"alice",identifier)["config"]["stock"] == "MSFT"
    assert list_experiments(path,"bob") == []
    with pytest.raises(ValueError):
        load_experiment(path,"bob",identifier)


def test_short_history_is_rejected():
    with pytest.raises(ValueError):
        backtest(prices([10.]*12),"SMA trend",Settings(),1000)


def test_duplicate_dates_rejected():
    frame=prices([10.]*12)
    with pytest.raises(ValueError):
        align_prices({"A":pd.concat([frame,frame.iloc[:1]])})


def test_demo_is_deterministic_and_per_symbol_stable():
    first,_=demo_prices(["MSFT","AAPL"])
    second,_=demo_prices(["AAPL","MSFT"])
    pd.testing.assert_frame_equal(first["MSFT"],second["MSFT"])


def test_twenty_stocks_are_supported():
    frames={f"T{i}": prices([10.]*12) for i in range(20)}
    result=run_portfolio(frames,[.05]*20,Settings(short=2,long=4,rsi_period=2),1000)
    assert len(result["equity"].columns) == 4


def test_exit_costs_and_no_overlapping_positions():
    frames,_=demo_prices(["MSFT"])
    _,trades,orders=backtest(frames["MSFT"],"RSI reversion",Settings(),1000)
    assert len(orders) > 2
    assert list(orders.Side) == ["Buy" if i%2 == 0 else "Sell" for i in range(len(orders))]
    first=trades.iloc[0]
    assert first["Net return"] == pytest.approx(first["Exit price"]*(1-.001)/(first["Entry price"]*(1+.001))-1)


def test_bad_window_is_rejected():
    with pytest.raises(ValueError):
        replace(Settings(),short=200,long=50).validate()
