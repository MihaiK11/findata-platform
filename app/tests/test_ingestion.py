from app.ingestion.fetch import (
    fetch_from_yahoo,
    fetch_asset
)


def test_fetch_normalization():

    df = fetch_from_yahoo("AAPL")

    assert "symbol" in df.columns
    assert "close" in df.columns
    assert len(df) > 0


def test_provider_fallback():

    df, source = fetch_asset("AAPL")

    assert source is not None
    assert len(df) > 0


def test_idempotent_rerun():

    df1 = fetch_from_yahoo("AAPL")
    df2 = fetch_from_yahoo("AAPL")

    assert len(df1) == len(df2)