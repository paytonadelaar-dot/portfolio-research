"""Strict adjusted-close ingestion with a reproducible local snapshot."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import numpy as np
import pandas as pd


def validate_prices(prices):
    if prices.empty or prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError('Prices must have unique, sorted dates and nonempty data.')
    if prices.isna().any().any() or not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('Missing, nonfinite or nonpositive prices: repair the source, not the returns.')
    return prices


def load_prices(tickers, start, end, directory, refresh=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path, meta = directory / 'prices.csv', directory / 'provenance.json'
    requested = dict(tickers=tickers, start=start, end_exclusive=end)
    if path.exists() and meta.exists() and not refresh:
        metadata = json.loads(meta.read_text())
        if metadata['request'] != requested:
            raise ValueError('Cached request differs. Use --refresh to obtain the requested dates/universe.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('Snapshot hash mismatch.')
        return validate_prices(pd.read_csv(path, index_col=0, parse_dates=True))
    series = []
    for ticker in tickers:
        query = urlencode(dict(period1=int(pd.Timestamp(start, tz='UTC').timestamp()),
                               period2=int(pd.Timestamp(end, tz='UTC').timestamp()), interval='1d'))
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{query}'
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=30) as response:
            result = json.load(response)['chart']['result'][0]
        dates = pd.to_datetime(result['timestamp'], unit='s', utc=True).tz_convert('America/New_York').normalize().tz_localize(None)
        values = result['indicators']['adjclose'][0]['adjclose']
        s = pd.Series(values, index=dates, name=ticker)
        s = s.loc[(s.index >= start) & (s.index < end)]
        series.append(s)
        print(f'Downloaded {ticker}: {len(s)} rows', flush=True)
    prices = validate_prices(pd.concat(series, axis=1))
    if list(prices.columns) != tickers:
        raise ValueError('Unexpected ticker alignment.')
    prices.index.name = 'Date'
    prices.to_csv(path, float_format='%.12g')
    meta.write_text(json.dumps(dict(request=requested, source='Yahoo Finance chart API; dividend/split-adjusted close',
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(), first_date=str(prices.index[0].date()),
        last_date=str(prices.index[-1].date()), rows=len(prices), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        missing_value_policy='Fail; no forward-filling or silently dropped sessions'), indent=2))
    return validate_prices(pd.read_csv(path, index_col=0, parse_dates=True))
