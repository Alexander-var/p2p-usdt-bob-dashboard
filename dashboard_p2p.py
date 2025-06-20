# dashboard_p2p.py
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
        response = requests.post(url, json=data, headers=headers, timeout=10)
        anuncios = response.json().get('data', [])
        precios = [float(anuncio['adv']['price']) for anuncio in anuncios[:5]]
        return sum(precios) / len(precios) if precios else None
    except:
        return None

st.title("\U0001F4CA Dashboard P2P USDT/BOB - Binance")

if "datos" not in st.session_state:
    st.session_state.datos = []

precio_compra = obtener_precio_p2p('BUY')
precio_venta = obtener_precio_p2p('SELL')
ahora = datetime.now()

if precio_compra and precio_venta:
    st.session_state.datos.append({
        'hora': ahora,
        'compra': precio_compra,
        'venta': precio_venta
    })

df = pd.DataFrame(st.session_state.datos)

col1, col2 = st.columns(2)
col1.metric("\U0001F7E2 Precio de COMPRA (BUY)", f"{precio_compra:.2f} BOB")
col2.metric("\U0001F534 Precio de VENTA (SELL)", f"{precio_venta:.2f} BOB")

if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['hora'], y=df['compra'], name='Compra (BUY)', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=df['hora'], y=df['venta'], name='Venta (SELL)', mode='lines+markers', line=dict(dash='dot')))
    fig.update_layout(title='Fluctuación de precios USDT/BOB (P2P)',
                      xaxis_title='Hora',
                      yaxis_title='Precio en BOB',
                      template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

with st.expander("\U0001F4C4 Ver datos históricos"):
    st.dataframe(df[::-1], use_container_width=True)

st.caption("Actualiza cada vez que entras a la página o presionas F5. Los datos se almacenan por sesión del navegador.")
