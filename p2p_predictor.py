# ================================
# Proyecto Dashboards Binance – Streamlit
#   • dashboard_p2p.py   → precios P2P USDT/BOB (BUY & SELL)
#   • btc_dashboard.py   → precios Spot BTC/USDT en vivo (auto 60 s)
#   • p2p_predictor.py   → gráfico USDT/BOB + probabilidad subida/bajada (auto 60 s)
# ================================
# Requisitos (requirements.txt)
# --------------------------------------------------
streamlit
requests
pandas
plotly
scikit-learn
# --------------------------------------------------

# ----------  dashboard_p2p.py  ----------
[UNMODIFIED CONTENT REDACTED]

# ----------  btc_dashboard.py  ----------
[UNMODIFIED CONTENT REDACTED]

# ----------  p2p_predictor.py  ----------
"""
Streamlit dashboard:
USDT/BOB P2P – gráfico y probabilidad de movimiento
• Consulta el precio BUY + SELL promedio cada minuto
• Guarda histórico en CSV (en disco del contenedor)
• Calcula probabilidad de subida usando un modelo de regresión logística
    – Características: retornos de los últimos 5, 15 y 30 minutos
    – Variable objetivo: 1 si precio sube en minuto siguiente, 0 si baja/igual
• Se re‑entrena en cada ejecución si hay ≥ 200 muestras
"""
import streamlit as st
import pandas as pd
import requests, os, time
from datetime import datetime
import plotly.graph_objects as go
from sklearn.linear_model import LogisticRegression
import numpy as np

REFRESH_SEC = 60
CSV_FILE = "hist_p2p_usdt_bob.csv"
HEADERS = {"Content-Type": "application/json"}
API_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

st.set_page_config(page_title="P2P Predictor USDT/BOB", layout="wide")

# ---------- funciones ---------
def obtener_precio():
    data = {
        "page": 1,
        "rows": 10,
        "payTypes": [],
        "asset": "USDT",
        "fiat": "BOB",
        "tradeType": "BUY",
        "merchantCheck": False
    }
    try:
        r = requests.post(API_URL, json=data, headers=HEADERS, timeout=10)
        anuncios = r.json().get('data', [])
        precios = [float(a['adv']['price']) for a in anuncios[:5]]
        buy = sum(precios) / len(precios) if precios else None
        data["tradeType"] = "SELL"
        r2 = requests.post(API_URL, json=data, headers=HEADERS, timeout=10)
        anuncios2 = r2.json().get('data', [])
        precios2 = [float(a['adv']['price']) for a in anuncios2[:5]]
        sell = sum(precios2) / len(precios2) if precios2 else None
        if buy and sell:
            return (buy + sell) / 2  # precio promedio
    except Exception as e:
        st.warning(f"API P2P error: {e}")
    return None

# ---------- auto-refresh ----------
if 'last_run' not in st.session_state:
    st.session_state.last_run = time.time()
else:
    if time.time() - st.session_state.last_run >= REFRESH_SEC:
        st.session_state.last_run = time.time()
        st.experimental_rerun()

# ---------- cargar/crear histórico ----------
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, parse_dates=['hora'])
else:
    df = pd.DataFrame(columns=['hora','precio'])

# ---------- nueva observación ----------
precio = obtener_precio()
now = datetime.utcnow()
if precio:
    if df.empty or (now - df.iloc[-1]['hora']).total_seconds() >= 55:
        df = pd.concat([df, pd.DataFrame([[now, precio]], columns=['hora','precio'])], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)

# ---------- cálculo de retornos ----------
if len(df) > 1:
    df['ret'] = df['precio'].pct_change()

# ---------- entrenar modelo ----------
prob_up = None
if len(df) >= 200:
    # features: rolling sum of positive returns
    for win in [5,15,30]:
        df[f'ma{win}'] = df['ret'].rolling(win).mean()
    df.dropna(inplace=True)
    df['target'] = (df['ret'].shift(-1) > 0).astype(int)
    X = df[['ma5','ma15','ma30']].values
    y = df['target'].values
    model = LogisticRegression()
    model.fit(X, y)
    last_feat = df[['ma5','ma15','ma30']].iloc[-1].values.reshape(1,-1)
    prob_up = model.predict_proba(last_feat)[0][1]

# ---------- UI ----------
st.title("📊 USDT/BOB P2P – Predictor 1 min")

col1, col2 = st.columns(2)
col1.metric("Precio actual promedio", f"{precio:.2f} BOB" if precio else "–")
if prob_up is not None:
    col2.metric("Probabilidad subida próximo min", f"{prob_up*100:.1f}%")
else:
    col2.write("Se necesitan al menos 200 datos para el modelo")

# gráfico precio
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['hora'], y=df['precio'], mode='lines+markers', name='Precio'))
fig.update_layout(title='Precio USDT/BOB P2P', xaxis_title='Hora (UTC)', yaxis_title='Precio (BOB)', template='plotly_white')
st.plotly_chart(fig, use_container_width=True)

# gráfico retornos
if 'ret' in df.columns:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df['hora'], y=df['ret']*100, name='% retorno'))
    fig2.update_layout(title='Retornos minuto a minuto', xaxis_title='Hora', yaxis_title='%')
    st.plotly_chart(fig2, use_container_width=True)

st.caption("Datos cada 1 min. Modelo logístico con medias de retornos (5/15/30 min). Se re‑entrena en cada ejecución si hay suficientes datos.")
# ---------- End p2p_predictor.py ----------
