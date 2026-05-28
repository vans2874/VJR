"""
India Stock Dashboard — Personal Investment Terminal
-----------------------------------------------------
Run:  streamlit run app.py
Deps: pip install streamlit yfinance pandas plotly pandas-ta
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIG — edit this section to customise
# ─────────────────────────────────────────────

WATCHLIST = {
    "APAR Industries":      "APARIND.NS",
    "GE Vernova T&D":       "GVT&D.NS",
    "Pace Digitek":         "PACEDIGITK.NS",
    "Filatex India":        "FILATEX.NS",
    "Belrise Industries":   "BELRISE.NS",
    "Hitachi Energy India": "POWERINVERX.NS",   # verify ticker
    "AGI Greenpac":         "AGIIL.NS",          # verify ticker
}

# Sectors of interest for the Boom Radar tab
BOOM_SECTORS = {
    "Defence & Aerospace": {
        "tickers": {"HAL": "HAL.NS", "BEL": "BEL.NS", "MTAR Tech": "MTARTECH.NS",
                    "Bharat Dynamics": "BDL.NS", "Zen Technologies": "ZENTEC.NS"},
        "status": "🔥 Booming",
        "cagr": "15–22%",
    },
    "Green Energy / BESS": {
        "tickers": {"Adani Green": "ADANIGREEN.NS", "Waaree Energies": "WAAREEENER.NS",
                    "NTPC Green": "NTPCGREEN.NS"},
        "status": "🔥 Booming",
        "cagr": "18–25%",
    },
    "AI & Semiconductor": {
        "tickers": {"Dixon Tech": "DIXON.NS", "Kaynes Technology": "KAYNES.NS",
                    "CG Power": "CGPOWER.NS", "Syrma SGS": "SYRMA.NS"},
        "status": "📈 Rising",
        "cagr": "14–20%",
    },
    "Pharma": {
        "tickers": {"Sun Pharma": "SUNPHARMA.NS", "Cipla": "CIPLA.NS",
                    "Divi's Labs": "DIVISLAB.NS", "Laurus Labs": "LAURUSLABS.NS"},
        "status": "📈 Rising",
        "cagr": "12–18%",
    },
    "Fintech / Banking": {
        "tickers": {"SBI": "SBIN.NS", "HDFC Bank": "HDFCBANK.NS",
                    "Bajaj Finance": "BAJFINANCE.NS", "PB Fintech": "POLICYBZR.NS"},
        "status": "🔥 Booming",
        "cagr": "12–20%",
    },
}

REFRESH_INTERVAL = 120   # seconds between auto-refresh (market hours only)
PERIOD_CHART     = "6mo" # default chart window

# ─────────────────────────────────────────────
# PAGE SETUP
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="India Stock Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CUSTOM CSS — minimal, readable
# ─────────────────────────────────────────────

st.markdown("""
<style>
/* Tighter header */
h1 { font-size: 1.4rem !important; font-weight: 600 !important; margin-bottom: 0 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }

/* Signal badges */
.signal-buy  { background:#d1fae5; color:#065f46; border-radius:6px;
               padding:3px 10px; font-weight:700; font-size:0.85rem; }
.signal-sell { background:#fee2e2; color:#991b1b; border-radius:6px;
               padding:3px 10px; font-weight:700; font-size:0.85rem; }
.signal-hold { background:#fef3c7; color:#92400e; border-radius:6px;
               padding:3px 10px; font-weight:700; font-size:0.85rem; }
.signal-na   { background:#f3f4f6; color:#6b7280; border-radius:6px;
               padding:3px 10px; font-size:0.85rem; }

/* Metric delta overrides */
[data-testid="stMetricDelta"] { font-size: 0.8rem; }

/* Divider */
hr { margin: 0.5rem 0 !important; }

/* Compact tabs */
.stTabs [data-baseweb="tab"] { font-size: 0.85rem; padding: 6px 16px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA FETCHING — cached with TTL
# ─────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_INTERVAL, show_spinner=False)
def fetch_stock(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    """Fetch OHLCV + computed indicators for one ticker."""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty:
            return None

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(subset=["Close"], inplace=True)

        # Indicators
        df["EMA20"]  = df["Close"].ewm(span=20,  adjust=False).mean()
        df["EMA50"]  = df["Close"].ewm(span=50,  adjust=False).mean()
        df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

        # RSI (14)
        delta = df["Close"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        df["RSI"] = 100 - 100 / (1 + rs)

        # Volume MA (5-day)
        df["VolMA5"] = df["Volume"].rolling(5).mean()

        return df

    except Exception:
        return None


@st.cache_data(ttl=REFRESH_INTERVAL, show_spinner=False)
def get_snapshot(ticker: str) -> dict:
    """Latest-row summary for the scoreboard."""
    df = fetch_stock(ticker)
    if df is None or df.empty:
        return {}

    last  = df.iloc[-1]
    prev  = df.iloc[-2] if len(df) > 1 else last
    price = float(last["Close"])
    chg   = ((price - float(prev["Close"])) / float(prev["Close"])) * 100

    # Signal logic
    ema50  = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    if price > ema200 and price > ema50:
        signal = "BUY"
    elif price < ema50:
        signal = "SELL"
    else:
        signal = "HOLD"

    vol_spike = float(last["Volume"]) > float(last["VolMA5"]) * 1.5 if last["VolMA5"] > 0 else False
    rsi_val   = float(last["RSI"]) if not pd.isna(last["RSI"]) else None

    return {
        "price":     price,
        "chg_pct":   chg,
        "ema50":     ema50,
        "ema200":    ema200,
        "rsi":       rsi_val,
        "signal":    signal,
        "vol_spike": vol_spike,
        "52w_high":  float(df["High"].max()),
        "52w_low":   float(df["Low"].min()),
        "updated":   datetime.now().strftime("%H:%M:%S"),
    }

# ─────────────────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────────────────

def build_chart(name: str, ticker: str, period: str) -> go.Figure | None:
    df = fetch_stock(ticker, period=period)
    if df is None or df.empty:
        return None

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.04,
        subplot_titles=[f"{name} — Price & EMAs", "RSI (14)", "Volume"],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", showlegend=False,
        increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
    ), row=1, col=1)

    colors = {"EMA20": "#f59e0b", "EMA50": "#3b82f6", "EMA200": "#8b5cf6"}
    for ema, color in colors.items():
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema], name=ema,
            line=dict(color=color, width=1.2),
        ), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"], name="RSI",
        line=dict(color="#06b6d4", width=1.4), showlegend=False,
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=0.8, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", line_width=0.8, row=2, col=1)

    # Volume bars — colour by up/down day
    vol_colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume",
        marker_color=vol_colors, showlegend=False, opacity=0.7,
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["VolMA5"], name="Vol MA5",
        line=dict(color="#f97316", width=1.2), showlegend=False,
    ), row=3, col=1)

    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.05, x=0, font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    return fig

# ─────────────────────────────────────────────
# SIGNAL BADGE HTML
# ─────────────────────────────────────────────

def signal_badge(signal: str) -> str:
    cls = {"BUY": "signal-buy", "SELL": "signal-sell",
           "HOLD": "signal-hold"}.get(signal, "signal-na")
    return f'<span class="{cls}">{signal}</span>'

# ─────────────────────────────────────────────
# ─── MAIN APP ────────────────────────────────
# ─────────────────────────────────────────────

# Header row
hcol1, hcol2, hcol3 = st.columns([3, 2, 1])
with hcol1:
    st.markdown("## 📊 India Stock Terminal")
    st.caption(f"Personal watchlist dashboard · Data: Yahoo Finance (15 min delay) · "
               f"Last refresh: {datetime.now().strftime('%d %b %Y, %H:%M')}")
with hcol2:
    auto_on = st.toggle("⟳ Auto-refresh every 2 min", value=True)
with hcol3:
    if st.button("Refresh now 🔄", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ─── TABS ─────────────────────────────────────
tab_board, tab_charts, tab_boom, tab_journal = st.tabs([
    "📋 Scoreboard", "📈 Charts", "🚀 Boom Sectors", "📓 My Notes"
])

# ════════════════════════════════════════════
# TAB 1 — SCOREBOARD
# ════════════════════════════════════════════
with tab_board:
    st.markdown("### Watchlist snapshot")
    st.caption("Signal: BUY = price above 200 EMA + 50 EMA  |  SELL = price below 50 EMA  |  HOLD = in between")

    cols_header = st.columns([2.2, 1, 1, 1, 1, 1, 1.2, 1])
    labels = ["Stock", "Price (₹)", "Day %", "RSI", "EMA 50", "EMA 200", "Signal", "Vol Spike?"]
    for col, lbl in zip(cols_header, labels):
        col.markdown(f"**{lbl}**")

    st.divider()

    for name, ticker in WATCHLIST.items():
        with st.spinner(f"Loading {name}…"):
            snap = get_snapshot(ticker)

        if not snap:
            st.warning(f"⚠ Could not fetch data for **{name}** (`{ticker}`). Verify ticker.")
            continue

        row = st.columns([2.2, 1, 1, 1, 1, 1, 1.2, 1])
        row[0].markdown(f"**{name}**  \n`{ticker}`")
        row[1].metric("", f"₹{snap['price']:,.2f}")

        chg = snap["chg_pct"]
        delta_color = "normal"
        row[2].metric("", f"{chg:+.2f}%", delta=f"{chg:+.2f}%", delta_color=delta_color)

        rsi = snap["rsi"]
        rsi_str = f"{rsi:.1f}" if rsi else "—"
        rsi_color = "🔴" if rsi and rsi > 70 else ("🟢" if rsi and rsi < 30 else "⚪")
        row[3].markdown(f"{rsi_color} **{rsi_str}**")

        row[4].markdown(f"₹{snap['ema50']:,.1f}")
        row[5].markdown(f"₹{snap['ema200']:,.1f}")
        row[6].markdown(signal_badge(snap["signal"]), unsafe_allow_html=True)
        row[7].markdown("⚡ Yes" if snap["vol_spike"] else "—")

    st.divider()
    st.caption("🔴 RSI > 70 = overbought  ·  🟢 RSI < 30 = oversold  ·  ⚡ Vol Spike = today's volume > 1.5× 5-day avg")

# ════════════════════════════════════════════
# TAB 2 — CHARTS
# ════════════════════════════════════════════
with tab_charts:
    c1, c2 = st.columns([2, 1])
    with c1:
        selected = st.selectbox("Select stock", list(WATCHLIST.keys()))
    with c2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

    ticker_sel = WATCHLIST[selected]
    snap = get_snapshot(ticker_sel)

    if snap:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current price", f"₹{snap['price']:,.2f}", f"{snap['chg_pct']:+.2f}%")
        m2.metric("RSI (14)", f"{snap['rsi']:.1f}" if snap['rsi'] else "—")
        m3.metric("EMA 50", f"₹{snap['ema50']:,.1f}")
        m4.metric("EMA 200", f"₹{snap['ema200']:,.1f}")
        m5.metric("Signal", snap["signal"])

    fig = build_chart(selected, ticker_sel, period)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Chart unavailable for {ticker_sel}. Verify ticker symbol.")

    # Signal explanation
    if snap:
        with st.expander("📖 Signal logic explained"):
            st.markdown(f"""
| Condition | Result |
|---|---|
| Price **above** EMA 200 **AND** EMA 50 | 🟢 **BUY** — uptrend confirmed |
| Price **below** EMA 50 | 🔴 **SELL** — momentum broken |
| Price between EMA 50 and EMA 200 | 🟡 **HOLD** — wait for clarity |
| Volume > 1.5× 5-day avg | ⚡ **Vol Spike** — move has conviction |
| RSI > 70 | Overbought — consider trimming on swing trades |
| RSI < 30 | Oversold — potential entry for long-term adds |

*These are rules-based signals to reduce emotional decisions. They are not buy/sell recommendations.*
""")

# ════════════════════════════════════════════
# TAB 3 — BOOM SECTORS
# ════════════════════════════════════════════
with tab_boom:
    st.markdown("### Boom sector radar")
    st.caption("Track rising sectors beyond your core watchlist. Click a sector to load live prices.")

    for sector_name, sector_data in BOOM_SECTORS.items():
        with st.expander(f"{sector_data['status']}  **{sector_name}**  ·  CAGR {sector_data['cagr']}"):
            sub_tickers = sector_data["tickers"]
            s_cols = st.columns(len(sub_tickers))

            for (sname, sticker), col in zip(sub_tickers.items(), s_cols):
                try:
                    snap_s = get_snapshot(sticker)
                    if snap_s:
                        col.metric(
                            sname,
                            f"₹{snap_s['price']:,.1f}",
                            f"{snap_s['chg_pct']:+.1f}%",
                        )
                    else:
                        col.caption(f"{sname}\n`{sticker}`\n⚠ Unavailable")
                except Exception:
                    col.caption(f"{sname}\n⚠ Error")

# ════════════════════════════════════════════
# TAB 4 — JOURNAL (persisted in session state)
# ════════════════════════════════════════════
with tab_journal:
    st.markdown("### Trade journal & thesis notes")
    st.caption("Notes persist until you close the app. Copy important entries to a separate file.")

    if "journal" not in st.session_state:
        st.session_state.journal = {name: "" for name in WATCHLIST}
        st.session_state.conviction = {name: 3 for name in WATCHLIST}
        st.session_state.target = {name: 0.0 for name in WATCHLIST}

    stock_j = st.selectbox("Stock to journal", list(WATCHLIST.keys()), key="journal_select")

    jcol1, jcol2 = st.columns(2)
    with jcol1:
        new_conv = st.slider("My conviction (1–5)", 1, 5,
                             st.session_state.conviction[stock_j], key=f"conv_{stock_j}")
        st.session_state.conviction[stock_j] = new_conv
    with jcol2:
        new_target = st.number_input("My target price (₹)", value=st.session_state.target[stock_j],
                                     min_value=0.0, key=f"target_{stock_j}")
        st.session_state.target[stock_j] = new_target

    new_note = st.text_area(
        "Thesis / notes",
        value=st.session_state.journal[stock_j],
        height=140,
        placeholder="Why am I watching this? What would change my mind? Key levels to watch...",
        key=f"note_{stock_j}",
    )
    st.session_state.journal[stock_j] = new_note

    if st.button("Save note ✓", type="primary"):
        st.success("Note saved to session.")

    st.divider()
    st.markdown("**All thesis notes at a glance:**")
    for sname, note in st.session_state.journal.items():
        if note.strip():
            conv = st.session_state.conviction[sname]
            tgt  = st.session_state.target[sname]
            stars = "★" * conv + "☆" * (5 - conv)
            tgt_str = f"  ·  Target ₹{tgt:,.0f}" if tgt > 0 else ""
            st.markdown(f"**{sname}** {stars}{tgt_str}")
            st.caption(note)
            st.divider()

# ─────────────────────────────────────────────
# AUTO-REFRESH (only when market is likely open)
# ─────────────────────────────────────────────
if auto_on:
    now = datetime.now()
    # NSE market hours: Mon–Fri, 09:15–15:30 IST (UTC+5:30)
    is_weekday     = now.weekday() < 5
    hour_min       = now.hour * 60 + now.minute
    market_open    = 9 * 60 + 15
    market_close   = 15 * 60 + 30
    in_market_hrs  = market_open <= hour_min <= market_close

    footer = st.empty()
    if in_market_hrs and is_weekday:
        footer.caption(f"⟳ Auto-refresh active · Next refresh in ~{REFRESH_INTERVAL}s · Market open")
        time.sleep(REFRESH_INTERVAL)
        st.cache_data.clear()
        st.rerun()
    else:
        footer.caption("⏸ Auto-refresh paused · Market closed (NSE: 09:15–15:30 IST, Mon–Fri)")
