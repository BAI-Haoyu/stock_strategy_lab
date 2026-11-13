from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_default_ui_and_saved_record(tmp_path,monkeypatch):
    monkeypatch.setenv("STOCK_LAB_DB",str(tmp_path/"ui.sqlite3"))
    app=AppTest.from_file(str(Path(__file__).parents[1]/"app.py"),default_timeout=40).run()
    assert not app.exception
    assert len(app.metric) == 4
    assert any("DEMO DATA" in x.value for x in app.info)
    next(b for b in app.button if b.label == "Save experiment").click().run()
    assert not app.exception
    assert any("saved" in x.value for x in app.success)
    next(b for b in app.button if b.label == "Restore saved settings").click().run()
    assert not app.exception


def test_invalid_input_visible_to_user(tmp_path,monkeypatch):
    monkeypatch.setenv("STOCK_LAB_DB",str(tmp_path/"ui.sqlite3"))
    app=AppTest.from_file(str(Path(__file__).parents[1]/"app.py"),default_timeout=40).run()
    app.text_input(key="tickers").set_value(",".join(f"T{i}" for i in range(21)))
    next(b for b in app.button if b.label == "Run analysis").click().run()
    assert not app.exception
    assert any("20" in x.value for x in app.error)


def test_provider_failure_is_explained_and_retry_is_not_cached(tmp_path,monkeypatch):
    from data_source import YahooDataError,demo_prices
    calls=[]
    def provider(tickers,period):
        calls.append(tickers)
        if len(calls) == 1:
            raise YahooDataError('App process DNS failure')
        return demo_prices(tickers)
    monkeypatch.setenv('STOCK_LAB_DB',str(tmp_path/'ui.sqlite3'))
    monkeypatch.setattr('data_source.yahoo_prices',provider)
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=40).run()
    app.selectbox(key='source').select('Yahoo Finance')
    app.text_input(key='tickers').set_value('NVDA')
    app.selectbox(key='period').select('2y')
    next(b for b in app.button if b.label=='Run analysis').click().run()
    assert not app.exception
    assert any('DNS failure' in e.value for e in app.error)
    assert any('Failed requests are not cached' in e.value for e in app.info)
    assert not any('Correct the inputs' in e.value for e in app.info)
    next(b for b in app.button if b.label=='Run analysis').click().run()
    assert not app.exception and not app.error
    assert len(app.metric)==4 and len(calls)==2
