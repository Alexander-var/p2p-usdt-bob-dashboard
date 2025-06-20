# ================================
# Proyecto Dashboards Binance – Streamlit
#   • dashboard_p2p.py   → precios P2P USDT/BOB
#   • # ----------  btc_dashboard.py  ----------
"""
Streamlit dashboard: BTC/USDT Spot (auto‑refresh 5 s)
Robusto frente a fallos de la API Binance (rate‑limit, bloqueos, etc.)
"""
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go

REFRESH_SEC = 5  # intervalo de actualización
BINANCE_BASE = "https://api.binance.com/api/v3"
HEADERS = {"User-Agent": "Mozilla/5.0"}

st.set_page_config(page_title="BTC/USDT Spot – Live", layout="wide")

# ------------------ Helper ------------------
def get_json(url: str):
    """Wrapper con control de errores y timeout"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error al llamar API Binance: {e}")
        return None

# ---------------- Auto-refresh --------------
if 'last_run' not in st.session_state:
    st.session_state.last_run = time.time()
else:
    if time.time() - st.session_state.last_run >= REFRESH_SEC:
        st.session_state.last_run = time.time()
        st.experimental_rerun()

# ---------------- Precio actual -------------
price_data = get_json(f"{BINANCE_BASE}/ticker/price?symbol=BTCUSDT")
price = float(price_data.get('price')) if price_data and 'price' in price_data else None

# ---------------- Candles -------------------
kl_data = get_json(f"{BINANCE_BASE}/klines?symbol=BTCUSDT&interval=1m&limit=100")

if price is None or kl_data is None:
    st.stop()  # Termina la ejecución y muestra errores previos

cols = ['open_time','open','high','low','close','volume','close_time','qav','n_trades','tb_base','tb_quote','ignore']
df_c = pd.DataFrame(kl_data, columns=cols)
df_c['open_time'] = pd.to_datetime(df_c['open_time'], unit='ms')
for col in ['open','high','low','close']:
    df_c[col] = df_c[col].astype(float)

# ---------------- UI ------------------------
st.title(f"📈 BTC/USDT Spot – Precio en tiempo real (auto {REFRESH_SEC}s)")
st.metric("Precio actual", f"${price:,.2f}")

fig_c = go.Figure(data=[go.Candlestick(x=df_c['open_time'],
                                       open=df_c['open'], high=df_c['high'],
                                       low=df_c['low'], close=df_c['close'],
                                       increasing_line_color='green',
                                       decreasing_line_color='red')])
fig_c.update_layout(title='Velas BTC/USDT – 1 min (últimas 100)',
                    xaxis_title='Hora', yaxis_title='Precio (USDT)',
                    template='plotly_dark', xaxis_rangeslider_visible=False,
                    height=600)
st.plotly_chart(fig_c, use_container_width=True)

st.caption("Página recargada automáticamente cada 5 s usando st.experimental_rerun. Manejo de errores incluido para la API Binance.")
# ---------- End btc_dashboard.py ----------
