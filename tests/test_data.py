import sys
from types import SimpleNamespace
import pandas as pd
import pytest
from data_source import YahooDataError, yahoo_prices


def fake_yahoo(monkeypatch, tmp_path, currencies):
    class Ticker:
        def __init__(self, ticker):
            self.ticker = ticker
        def history(self, **kwargs):
            assert kwargs['auto_adjust'] is True
            assert kwargs['raise_errors'] is True
            return pd.DataFrame({'Open':[10,11], 'Close':[11,12]}, index=pd.bdate_range('2024-01-01',periods=2))
        def get_history_metadata(self):
            return {'currency':currencies[self.ticker]}
    monkeypatch.setenv('STOCK_LAB_YAHOO_CACHE',str(tmp_path/'cache'))
    monkeypatch.setitem(sys.modules,'yfinance',SimpleNamespace(Ticker=Ticker,set_tz_cache_location=lambda _:None))


def test_non_usd_rejects_whole_portfolio(monkeypatch,tmp_path):
    fake_yahoo(monkeypatch,tmp_path,{'MSFT':'USD','SAP.DE':'EUR'})
    with pytest.raises(ValueError,match='No portfolio was calculated'):
        yahoo_prices(['MSFT','SAP.DE'],'2y')


def test_unknown_currency_rejected(monkeypatch,tmp_path):
    fake_yahoo(monkeypatch,tmp_path,{'MSFT':None})
    monkeypatch.setattr('data_source.time.sleep',lambda _:None)
    with pytest.raises(YahooDataError,match='did not provide currency metadata'):
        yahoo_prices(['MSFT'],'2y')


def test_adjusted_usd_history_accepted(monkeypatch,tmp_path):
    fake_yahoo(monkeypatch,tmp_path,{'MSFT':'USD'})
    frames,note=yahoo_prices(['MSFT'],'2y')
    assert len(frames['MSFT']) == 2 and 'USD' in note


def scripted_yahoo(monkeypatch,tmp_path,events):
    calls = []
    class Ticker:
        def __init__(self,ticker):
            self.event = events[len(calls)]
            calls.append(ticker)
        def history(self,**kwargs):
            assert kwargs['raise_errors'] is True
            if isinstance(self.event,Exception):
                raise self.event
            return self.event[0]
        def get_history_metadata(self):
            if isinstance(self.event[1],Exception):
                raise self.event[1]
            return self.event[1]
    monkeypatch.setenv('STOCK_LAB_YAHOO_CACHE',str(tmp_path/'cache'))
    monkeypatch.setattr('data_source.time.sleep',lambda _:None)
    monkeypatch.setitem(sys.modules,'yfinance',SimpleNamespace(Ticker=Ticker,set_tz_cache_location=lambda _:None))
    return calls


def prices():
    return pd.DataFrame({'Open':[10,11],'Close':[11,12]},index=pd.bdate_range('2024-01-01',periods=2))


def test_transient_dns_error_recovers(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[OSError('Could not resolve host'),(prices(),{'currency':'USD'})])
    frames,_=yahoo_prices(['NVDA'],'2y')
    assert len(frames['NVDA']) == 2
    assert calls == ['NVDA','NVDA']


def test_persistent_dns_error_is_not_currency_error_and_stops_requests(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[OSError('Could not resolve host')]*2)
    with pytest.raises(YahooDataError,match='DNS failure') as caught:
        yahoo_prices(['NVDA','MSFT'],'2y')
    assert 'currency' not in str(caught.value).lower()
    assert calls == ['NVDA','NVDA']


def test_empty_prices_checked_before_currency(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[(pd.DataFrame(),AssertionError('Metadata must not be read'))]*2)
    with pytest.raises(YahooDataError,match='no historical prices'):
        yahoo_prices(['NVDA'],'2y')
    assert len(calls) == 2


def test_metadata_retry_uses_new_ticker(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[(prices(),{}),(prices(),{'currency':'USD'})])
    frames,_=yahoo_prices(['NVDA'],'2y')
    assert 'NVDA' in frames and len(calls) == 2


def test_non_usd_is_not_retried_or_assumed_usd(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[(prices(),{'currency':'EUR'})])
    with pytest.raises(YahooDataError,match='currency EUR'):
        yahoo_prices(['SAP.DE'],'2y')
    assert len(calls) == 1


def test_rate_limit_does_not_trigger_request_storm(monkeypatch,tmp_path):
    calls=scripted_yahoo(monkeypatch,tmp_path,[RuntimeError('Too Many Requests. Rate limited.')])
    with pytest.raises(YahooDataError,match='limited requests'):
        yahoo_prices(['NVDA','MSFT'],'2y')
    assert len(calls) == 1
