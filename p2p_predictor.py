# ================================
# Proyecto Dashboards Binance – Streamlit
#   • dashboard_p2p.py   → precios P2P USDT/BOB (BUY & SELL)
#   • btc_dashboard.py   → precios Spot BTC/USDT en vivo (auto 60 s)
#   • p2p_predictor.py   → gráfico USDT/BOB + modelo logístico (auto 60 s)
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
# (sin cambios desde la versión previa – ver archivo en el repo)

# ----------  btc_dashboard.py  ----------
# (sin cambios desde la versión previa – ver archivo en el repo)

# ----------  p2p_predictor.py  ----------
"""
Dashboard Streamlit: USDT/BOB P2P – Predictor minuto a minuto
-------------------------------------------------------------
• Consulta cada 60 s el precio promedio (BUY + SELL) en el mercado P2P
• Guarda el histórico en un CSV local (`hist_p2p_usdt_bob.csv`)
• Muestra dos gráficos: precio y retornos porcentuales
• Entrena un modelo de regresión logística cuando hay ≥ 200 datos 
  con medias de retornos (5 min, 15 min, 30 min) para estimar la
  probabilidad de que el precio SUBA en el próximo minuto.
"""
import os, time, requests, streamlit as st, pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from sklearn.linear_model import LogisticRegression
import numpy as np

# ---------------- Config ----------------
REFRESH_SEC = 60
CSV_FILE = "hist_p2p_usdt_bob.csv"
API_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
HEADERS = {"Content-Type": "application/json"}

st.set_page_config(page_title="P2P Predictor USDT/BOB", layout="wide")

# ---------------- Funciones -------------

def obtener_precio_promedio() -> float | None:
    """Devuelve el precio promedio BUY+SELL de USDT/BOB o None si falla."""
    def _precio(tipo: str):
        data = {
            "page": 1,
            "rows": 10,
            "payTypes": [],
            "asset": "USDT",
            "fiat": "BOB",
            "tradeType": tipo,
            "merchantCheck": False
        }
        r = requests.post(API_URL, json=data, headers=HEADERS, timeout=10)
        r.raise_for_status()
        anuncios = r.json().get('data', [])
        precios = [float(a['adv']['price']) for a in anuncios[:5]]
        return sum(precios) / len(precios) if precios else None

    try:
        buy = _precio("BUY")
        sell = _precio("SELL")
        if buy and sell:
            return (buy + sell) / 2
    except Exception as e:
        st.warning(f"API P2P error: {e}")
    return None

# ---------------- Auto‑refresh ----------
if 'last_run' not in st.session_state:
    st.session_state.last_run = time.time()
else:
    if time.time() - st.session_state.last_run >= REFRESH_SEC:
        st.session_state.last_run = time.time()
        st.experimental_rerun()

# ---------------- Cargar histórico ------
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, parse_dates=['hora'])
else:
    df = pd.DataFrame(columns=['hora', 'precio'])

# ---------------- Añadir nueva fila -----
precio_actual = obtener_precio_promedio()
now = datetime.utcnow()
if precio_actual is not None:
    if df.empty or (now - df.iloc[-1]['hora']).total_seconds() >= (REFRESH_SEC - 5):
        df = pd.concat([df, pd.DataFrame([[now, precio_actual]], columns=['hora', 'precio'])], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)

# ---------------- Calcular retornos -----
if len(df) > 1:
    df['ret'] = df['precio'].pct_change()

# ---------------- Modelo predictivo -----
prob_up: float | None = None
if len(df) >= 200:
    for win in [5, 15, 30]:
        df[f'ma{win}'] = df['ret'].rolling(win).mean()
    df.dropna(inplace=True)
    df['target'] = (df['ret'].shift(-1) > 0).astype(int)
    X = df[['ma5', 'ma15', 'ma30']].values
    y = df['target'].values
    model = LogisticRegression()
    model.fit(X, y)
    last_feat = df[['ma5', 'ma15', 'ma30']].iloc[-1].values.reshape(1, -1)
    prob_up = model.predict_proba(last_feat)[0][1]

# ---------------- UI --------------------
st.title("📊 USDT/BOB P2P – Predictor 1 min")

col1, col2 = st.columns(2)
col1.metric("Precio promedio actual", f"{precio_actual:.2f} BOB" if precio_actual else "–")
if prob_up is not None:
    col2.metric("Probabilidad ↑ en el próximo minuto", f"{prob_up*100:.1f}%")
else:
    col2.write("Esperando al menos 200 registros para el modelo…")

# ---------- Gráfico precio -------------
fig_price = go.Figure()
fig_price.add_trace(go.Scatter(x=df['hora'], y=df['precio'], mode='lines+markers', name='Precio'))
fig_price.update_layout(title='Precio USDT/BOB P2P', xaxis_title='Hora (UTC)', yaxis_title='Precio (BOB)', template='plotly_white')
st.plotly_chart(fig_price, use_container_width=True)

# ---------- Gráfico retornos -----------
if 'ret' in df.columns:
    fig_ret = go.Figure()
    fig_ret.add_trace(go.Bar(x=df['hora'], y=df['ret']*100, name='% ret'))
    fig_ret.update_layout(title='Retornos (%) por minuto', xaxis_title='Hora (UTC)', yaxis_title='%')
    st.plotly_chart(fig_ret, use_container_width=True)

st.caption("Datos actualizados cada minuto. Modelo logístico con medias móviles de retornos a 5, 15 y 30 minutos.")
# ---------- end p2p_predictor.py ----------
