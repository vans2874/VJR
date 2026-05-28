# India Stock Terminal 📊

A personal, self-hosted stock dashboard for your Indian market watchlist.
Built with Streamlit + yfinance + Plotly. Runs locally in your browser.

---

## What this does

| Feature | Detail |
|---|---|
| **Scoreboard** | Live price, day %, RSI, EMA 50/200, BUY/SELL/HOLD signal, volume spike flag |
| **Charts** | Interactive candlestick + EMA lines + RSI + Volume. Switchable period. |
| **Boom Sectors** | Live prices for Defence, Green Energy, Semiconductor, Pharma, Fintech |
| **Journal** | Per-stock notes, conviction rating, target price — your investment thesis |
| **Auto-refresh** | Pulls fresh data every 2 min during NSE market hours. Pauses after close. |

---

## Setup (one-time, ~5 minutes)

### 1. Install Python
Download Python 3.11+ from https://python.org/downloads if you don't have it.

### 2. Install dependencies

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:

```bash
pip install streamlit yfinance pandas plotly
```

### 3. Download or clone this project

Put `app.py` and `requirements.txt` in a folder, e.g. `~/india_dashboard/`.

### 4. Run the dashboard

```bash
cd ~/india_dashboard
streamlit run app.py
```

Your browser will open automatically at **http://localhost:8501**

---

## Customise your watchlist

Open `app.py` in any text editor. Find the `WATCHLIST` dictionary near the top:

```python
WATCHLIST = {
    "APAR Industries":    "APARIND.NS",
    "GE Vernova T&D":     "GVT&D.NS",
    ...
}
```

- Ticker format for NSE: `TICKERSYMBOL.NS`  (e.g. `HDFCBANK.NS`)
- Ticker format for BSE: `TICKERSYMBOL.BO`  (e.g. `500180.BO`)
- To verify a ticker: search on https://finance.yahoo.com → use the exact symbol shown

To **add** a stock:
```python
"Bharat Electronics": "BEL.NS",
```

To **remove** a stock: delete its line.

---

## Verifying uncertain tickers

Some stocks in your original watchlist need ticker verification:

| Stock | Suggested Yahoo Finance ticker | Status |
|---|---|---|
| Central Mining | Search Yahoo Finance | Verify |
| Hyderabad Industries (Birlanu) | `HYDRINDUS.NS` | Verify |
| Bharat Coke | Search Yahoo Finance | Verify |
| Hitachi Energy India | `POWERINVERX.NS` | Verify |
| AGI Greenpac | `AGIIL.NS` | Verify |

To verify: go to https://finance.yahoo.com, search the company name, copy the symbol shown.

---

## Change refresh interval

Find this line in `app.py`:

```python
REFRESH_INTERVAL = 120   # seconds
```

Change `120` to any number of seconds you want.
Note: yfinance data is delayed ~15 min even at 30-second refresh.

---

## Deploy to Streamlit Cloud (access from phone/anywhere)

1. Create a free account at https://github.com
2. Upload `app.py` and `requirements.txt` to a new repository
3. Go to https://share.streamlit.io → "New app"
4. Connect your GitHub repo → Click "Deploy"
5. You get a permanent URL like `https://yourname-india-dashboard.streamlit.app`

The cloud version refreshes on a schedule too — but since it's public by default,
don't add any API keys or passwords directly in `app.py`. Use Streamlit Secrets.

---

## Signal logic

| Condition | Signal |
|---|---|
| Price > EMA 200 AND Price > EMA 50 | 🟢 BUY |
| Price < EMA 50 | 🔴 SELL |
| Price between EMA 50 and EMA 200 | 🟡 HOLD |

Volume spike = today's volume > 1.5× the 5-day average. Signals with a volume spike carry more weight.

These are rule-based filters to reduce emotional decisions. Always verify with fundamentals.

---

## Extending the dashboard (next steps)

### Add Telegram alerts

```python
import requests

def send_telegram(msg, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": msg})

# Inside the scoreboard loop:
if snap["signal"] == "BUY" and snap["vol_spike"]:
    send_telegram(f"🟢 BUY signal: {name} at ₹{snap['price']}", TOKEN, CHAT_ID)
```

### Add Motilal Oswal API (real-time data)

Replace the `fetch_stock()` function with Motilal Oswal REST API calls.
Their API docs: https://openapi.motilaloswal.com

### Add news feed

```python
import feedparser
feed = feedparser.parse(f"https://news.google.com/rss/search?q={name}+NSE&hl=en-IN")
for entry in feed.entries[:3]:
    st.write(f"• [{entry.title}]({entry.link})")
```

---

## Data note

yfinance uses Yahoo Finance data which is:
- Delayed ~15 minutes during market hours
- Free, no API key needed
- Accurate for historical prices and indicators
- Not suitable for intraday scalping — fine for daily monitoring

For real-time data, upgrade to Motilal Oswal API (free for their clients).
