# ================================
# Proyecto Dashboards Binance – Streamlit
#   • dashboard_p2p.py   → precios P2P USDT/BOB
#   • btc_dashboard.py   → precios Spot BTC/USDT en vivo (5 s)
# ================================
# Requisitos (añade estas líneas a requirements.txt)
# --------------------------------------------------
# streamlit
# streamlit_autorefresh
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

precio_buy = obtener_precio_p2p('BUY')
precio_sell = obtener_precio_p2p('SELL')
now = datetime.now()

if precio_buy and precio_sell:
    st.session_state.datos.append({
        'hora': now,
        'compra': precio_buy,
        'venta': precio_sell
    })

df = pd.DataFrame(st.session_state.datos)

c1, c2 = st.columns(2)
c1.metric("🟢 Precio COMPRA (BUY)", f"{precio_buy:.2f} BOB")
c2.metric("🔴 Precio VENTA (SELL)", f"{precio_sell:.2f} BOB")

if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['hora'], y=df['compra'], name='Compra', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=df['hora'], y=df['venta'], name='Venta', mode='lines+markers', line=dict(dash='dot')))
    fig.update_layout(title='Fluctuación precios USDT/BOB (P2P)', xaxis_title='Hora', yaxis_title='Precio en BOB', template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

with st.expander("📄 Datos históricos"):
    st.dataframe(df[::-1], use_container_width=True)

st.caption("Los datos se actualizan cada visita / F5 (cache 60 s).")

# ----------  btc_dashboard.py  ----------
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="BTC/USDT Spot – Live", layout="wide")

# refresco automático cada 5 s
st_autorefresh(interval=5000, key="btc_refresh")

# precio spot actual
price_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
price = float(requests.get(price_url, timeout=10).json()['price'])

# últimas 100 velas de 1 min
kl_url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=100"
klines = requests.get(kl_url, timeout=10).json()

cols = ['open_time','open','high','low','close','volume','close_time','qav','n_trades','tb_base','tb_quote','ignore']
df_c = pd.DataFrame(klines, columns=cols)
df_c['open_time'] = pd.to_datetime(df_c['open_time'], unit='ms')
for c in ['open','high','low','close']:
    df_c[c] = df_c[c].astype(float)

st.title("📈 BTC/USDT Spot – Precio en tiempo real")
st.metric("Precio actual", f"${price:,.2f}")

fig_c = go.Figure(data=[go.Candlestick(x=df_c['open_time'],
                                       open=df_c['open'],
                                       high=df_c['high'],
                                       low=df_c['low'],
                                       close=df_c['close'],
                                       increasing_line_color='green',
                                       decreasing_line_color='red')])
fig_c.update_layout(title='Gráfico de velas BTC/USDT – 1 min (auto 5 s)',
                    xaxis_title='Hora', yaxis_title='Precio (USDT)',
                    template='plotly_dark', xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig_c, use_container_width=True)

st.caption("La página se recarga automáticamente cada 5 s para mostrar velas y precio en vivo.")
