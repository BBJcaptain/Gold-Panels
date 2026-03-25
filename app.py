from flask import Flask, jsonify
from flask_cors import CORS
import requests
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

API_KEY = 'YOUR_ALPHA_VANTAGE_KEY'   # Replace with your actual key
AV_BASE = 'https://www.alphavantage.co/query'


def fetch_av_exchange_rate(from_currency, to_currency):
    """Calls Alpha Vantage CURRENCY_EXCHANGE_RATE and returns a float price."""
    url = (
        f'{AV_BASE}?function=CURRENCY_EXCHANGE_RATE'
        f'&from_currency={from_currency}'
        f'&to_currency={to_currency}'
        f'&apikey={API_KEY}'
    )
    resp = requests.get(url, timeout=10)
    data = resp.json()
    rate_info = data.get('Realtime Currency Exchange Rate', {})
    raw_price = rate_info.get('5. Exchange Rate')
    if raw_price is None:
        return None
    return float(raw_price)


@app.route('/xau-usd')
def get_xau_usd():
    """Returns current XAU/USD spot price as { price: float }."""
    price = fetch_av_exchange_rate('XAU', 'USD')
    if price is None:
        return jsonify({'error': 'Failed to fetch XAU/USD'}), 503
    return jsonify({'price': price})


@app.route('/forex/<from_currency>/<to_currency>')
def get_forex(from_currency, to_currency):
    """Returns current exchange rate for any currency pair as { price: float }."""
    price = fetch_av_exchange_rate(from_currency, to_currency)
    if price is None:
        return jsonify({'error': f'Failed to fetch {from_currency}/{to_currency}'}), 503
    return jsonify({'price': price})


@app.route('/stock-data/<ticker>')
def get_stock_data(ticker):
    """
    Returns the latest close price and daily change percentage for a ticker.
    Response: { price: float, change_pct: float }
    Uses yfinance with a 5-day lookback so the previous close is always available.
    """
    try:
        df = yf.download(
            ticker,
            period='5d',
            interval='1d',
            progress=False,
            auto_adjust=True
        )
        if df.empty:
            return jsonify({'error': 'No data returned'}), 404

        close_col = df['Close']
        if isinstance(close_col, pd.DataFrame):
            closes = close_col.squeeze('columns').dropna()
        else:
            closes = close_col.dropna()

        if len(closes) < 1:
            return jsonify({'error': 'Insufficient data'}), 404

        price = float(closes.iloc[-1])
        result = {'price': price}

        if len(closes) >= 2:
            prev_close = float(closes.iloc[-2])
            result['change_pct'] = round(
                ((price - prev_close) / prev_close) * 100, 4
            )

        return jsonify(result)

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    app.run(debug=True)
