# ================================
# Proyecto Dashboards Binance – Streamlit
#   • dashboard_p2p.py   → precios P2P USDT/BOB
#   • btc_dashboard.py   → precios Spot BTC/USDT en vivo (auto 60 s)
# ================================
# Requisitos (requirements.txt)
# --------------------------------------------------
# streamlit
# requests
# pandas
# plotly
# --------------------------------------------------

# ----------  dashboard_p2p.py  ----------
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Mercado P2P USDT/BOB", layout="wide")

@st.cache_data(ttl=60)
def obtener_precio_p2p(operacion='BUY'):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {'Content-Type': 'application/json'}
    data = {
        "page": 1,
        "rows": 10,
        "payTypes": [],
        "asset": "USDT",
        "fiat": "BOB",
        "tradeType": operacion,
        "merchantCheck": False
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        anuncios = r.json().get('data', [])
        precios = [float(a['adv']['price']) for a in anuncios[:5]]
        return sum(precios) / len(precios) if precios else None
    except Exception:
        return None

st.title("\U0001F4CA Dashboard P2P USDT/BOB – Binance")
if "datos" not in st.session_state:
    st.session_state.datos = []

buy = obtener_precio_p2p('BUY')
sell = obtener_precio_p2p('SELL')
now = datetime.now()
if buy and sell:
    st.session_state.datos.append({'hora': now, 'compra': buy, 'venta': sell})

df = pd.DataFrame(st.session_state.datos)
col1, col2 = st.columns(2)
col1.metric("🟢 Compra (BUY)", f"{buy:.2f} BOB")
col2.metric("🔴 Venta (SELL)", f"{sell:.2f} BOB")

if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['hora'], y=df['compra'], name='Compra', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=df['hora'], y=df['venta'], name='Venta', mode='lines+markers', line=dict(dash='dot')))
    fig.update_layout(title='Fluctuación USDT/BOB (P2P)', xaxis_title='Hora', yaxis_title='Precio (BOB)', template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

with st.expander("📄 Historial"):
    st.dataframe(df[::-1], use_container_width=True)

st.caption("Datos refrescados a intervalos de 1 min (cache 60 s).")

# ----------  btc_dashboard.py  ----------
"""
Dashboard BTC/USDT Spot (Streamlit)
• Auto‑refresh cada 60 s usando st.experimental_rerun
• Manejo de errores 451 / 403 con múltiples dominios Binance
"""
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go

REFRESH_SEC = 60  # intervalo de actualización
BINANCE_BASES = [
    "https://api.binance.com/api/v3",
    "https://api1.binance.com/api/v3",
    "https://api2.binance.com/api/v3",
    "https://api3.binance.com/api/v3",
    "https://data-api.binance.vision/api/v3"  # fallback público
]
HEADERS = {"User-Agent": "Mozilla/5.0"}

st.set_page_config(page_title="BTC/USDT Spot – Live", layout="wide")

# ---------- helpers ----------
def get_json(path: str):
    for base in BINANCE_BASES:
        url = f"{base}{path}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return r.json()
            else:
                st.warning(f"{r.status_code} desde {base}")
        except Exception as e:
            st.warning(f"Error {e} con {base}")
    return None

# ---------- auto‑refresh ----------
if 'last_run' not in st.session_state:
    st.session_state.last_run = time.time()
else:
    if time.time() - st.session_state.last_run >= REFRESH_SEC:
        st.session_state.last_run = time.time()
        st.experimental_rerun()

# ---------- data ----------
price_json = get_json("/ticker/price?symbol=BTCUSDT")
klines_json = get_json("/klines?symbol=BTCUSDT&interval=1m&limit=100")

if price_json is None or klines_json is None or 'price' not in price_json:
    st.error("No se pudo obtener datos de Binance. Reintenta más tarde.")
    st.stop()

price = float(price_json['price'])
cols = ['open_time','open','high','low','close','volume','close_time','qav','n_trades','tb_base','tb_quote','ignore']
df_c = pd.DataFrame(klines_json, columns=cols)
df_c['open_time'] = pd.to_datetime(df_c['open_time'], unit='ms')
for c in ['open','high','low','close']:
    df_c[c] = df_c[c].astype(float)

# ---------- UI ----------
st.title(f"📈 BTC/USDT Spot – auto {REFRESH_SEC}s")
st.metric("Precio actual", f"${price:,.2f}")

fig = go.Figure(data=[go.Candlestick(x=df_c['open_time'], open=df_c['open'], high=df_c['high'], low=df_c['low'], close=df_c['close'], increasing_line_color='green', decreasing_line_color='red')])
fig.update_layout(title='Velas BTC/USDT – 1 min (últimas 100)', xaxis_title='Hora', yaxis_title='Precio (USDT)', template='plotly_dark', xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

st.caption("Se intentan múltiples dominios para evitar bloqueos y se actualiza cada 60 s.")
