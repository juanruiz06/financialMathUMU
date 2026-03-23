import streamlit as st
from engine.finance import GBM
import numpy as np
import plotly.graph_objects as go
import time
import requests
import os

st.set_page_config(page_title="Simulación de Procesos Estocásticos", layout="wide")
st.title("Simulación de Procesos Estocásticos")

st.sidebar.header("Parámetros de la Simulación")
n_sims = st.sidebar.number_input("Número de Simulaciones", 1, 2000, 100)
n_show_default = min(50, max(1, int(n_sims * 0.1)))
n_show = st.sidebar.slider("Número de Simulaciones a Mostrar", 1, min(100, int(n_sims)), n_show_default)
s0 = st.sidebar.number_input("Precio inicial (S0)", value=100.0)
mu = st.sidebar.slider("Deriva (mu)", min_value=-1.0, max_value=1.0, value=0.05)
sigma = st.sidebar.slider("Volatilidad (sigma)", min_value=0.0, max_value=1.0, value=0.2)
t_final = st.sidebar.number_input("Tiempo total (T)", value=1.0)
K = st.sidebar.number_input("Precio de Strike (K)", value=100.0)
r = st.sidebar.slider("Tasa de interés (r)", 0.0, 0.1, 0.03)


st.sidebar.subheader("Tipo de Opción")
tipo_opcion = st.sidebar.selectbox("Selecciona el tipo de opción", ("Call", "Put", "Straddle", "Binary"))

if st.sidebar.button("Simular"):
    st.rerun()
st.sidebar.divider()
modelo = GBM(S0 = s0, mu = mu, sigma = sigma, T = t_final, N = 252)
start_time = time.perf_counter()
payload = {
    "S0": float(s0),
    "mu": float(mu),
    "sigma": float(sigma),
    "T": float(t_final),
    "N": int(modelo.N),
    "n_paths": int(n_sims),
    "n_show": int(n_show),
    "K": float(K),
    "r": float(r),
    "tipo_opcion": tipo_opcion,
}
backend_base_url = os.getenv("BACKEND_URL", "http://localhost:3000").rstrip("/")
api_url = f"{backend_base_url}/api/pricing"
try:
    response = requests.post(api_url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar con el backend de pricing. Verifica que el API Gateway esté activo en http://localhost:3000.")
    st.stop()
except requests.exceptions.HTTPError:
    st.error("El backend devolvió un error al calcular el pricing. Inténtalo de nuevo en unos segundos.")
    st.stop()
except requests.exceptions.RequestException:
    st.error("Ocurrió un problema de red al consultar el backend de pricing.")
    st.stop()
except ValueError:
    st.error("La respuesta del backend no tiene un formato JSON válido.")
    st.stop()

if "simulated_paths" not in data or "final_prices" not in data or "black_scholes_price" not in data:
    st.error("La respuesta del backend no contiene los campos esperados de pricing.")
    st.stop()

try:
    precios = np.array(data["simulated_paths"], dtype=float)
except (TypeError, ValueError):
    st.error("El backend devolvió una simulación en un formato inválido.")
    st.stop()

try:
    precios_finales = np.array(data["final_prices"], dtype=float)
except (TypeError, ValueError):
    st.error("El backend devolvió los precios finales en un formato inválido.")
    st.stop()

# Normalizamos a (N+1, n_paths), que es la forma esperada por el resto de la UI.
if precios.ndim == 1:
    precios = precios.reshape(-1, 1)
elif precios.ndim == 2 and precios.shape[0] != len(modelo.time_grid) and precios.shape[1] == len(modelo.time_grid):
    precios = precios.T
elif precios.ndim != 2:
    st.error("La simulación devuelta por el backend no tiene una forma compatible.")
    st.stop()

if precios.shape[0] != len(modelo.time_grid):
    st.error("La simulación devuelta por el backend no coincide con la grilla temporal esperada.")
    st.stop()

end_time = time.perf_counter()

duration = end_time - start_time
api_latency_ms = response.elapsed.total_seconds() * 1000

if tipo_opcion == "Call":
    payoffs = np.maximum(precios_finales - K, 0)
elif tipo_opcion == "Put":
    payoffs = np.maximum(K - precios_finales, 0)
elif tipo_opcion == "Straddle":
    payoffs = np.abs(precios_finales - K)
elif tipo_opcion == "Binary":
    payoffs = (precios_finales > K).astype(float)
else:
    payoffs = np.zeros_like(precios_finales)

precio_mc = float(np.exp(-r * t_final) * np.mean(payoffs))
precio_bs = float(data["black_scholes_price"])
diff = abs(precio_mc - precio_bs)

media_precios = (precio_mc + precio_bs) / 2
error_relativo = diff / media_precios if media_precios > 0 else 0.0

if tipo_opcion == "Call":
    itm_count = np.sum(precios_finales > K)
elif tipo_opcion == "Put":
    itm_count = np.sum(precios_finales < K)
elif tipo_opcion == "Straddle":
    itm_count = np.sum(np.abs(precios_finales - K) > precio_mc) # Sabemos que siempre se va a mover del strike, pero queremos saber si se mueve lo suficiente para superar el precio de la opción
elif tipo_opcion == "Binary":
    itm_count = np.sum(precios_finales > K) # Para la opción binaria, el payoff es 1 si el precio final supera el strike, y 0 en caso contrario

prob_itm = (itm_count / len(precios_finales))*100 if len(precios_finales) > 0 else 0.0
prob_bs = modelo.black_scholes_itm_probability(K = K, r = r, option_type = tipo_opcion, use_real_world=False)

st.subheader(f"Resultados: {tipo_opcion} Europea")
st.caption(f"Backend de pricing: {api_url} | Latencia API: {api_latency_ms:.0f} ms")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric (label="Precio de la Opción (MC)", value=f"${precio_mc:.2f} €")
col2.metric(label="Precio de la Opción (Black-Scholes)", value=f"${precio_bs:.2f} €")
col3.metric(
    label="Diferencia (MC vs BS)", 
    value=f"{diff:.2f} €",
    delta=f"{error_relativo:.2f} %",
    delta_color="normal" if error_relativo < 0.05 else "inverse"
)
col4.metric(label="Prob. ITM (MC)", value=f"{prob_itm:.2f} %")
col5.metric(
    label="Prob. ITM (BS - Medida Q)", 
    value=f"{prob_bs:.2f} %"
)

with st.expander("Detalles de la Simulación"):
    st.write(f"Tiempo de simulación: {duration:.2f} segundos")
    st.write(f"Número de simulaciones: {len(precios_finales)}")

fig = go.Figure()
for i in range(min(n_show, precios.shape[1])):
    fig.add_trace(go.Scatter(x=modelo.time_grid, y=precios[:,i],
                              mode='lines', line=dict(width=1), showlegend=False))

fig.add_hline(y=K, line=dict(color='red', width=2, dash='dash'), name='Strike Price (K)')

fig.update_layout(template = "plotly_dark", title="Simulación de un Proceso de Movimiento Browniano Geométrico (GBM)", xaxis_title="Tiempo", yaxis_title="Precio del Activo")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Distribución de precios al vencer")
n_bins = max(20, min(int(np.sqrt(len(precios_finales))), 100))
fig_hist = go.Figure(data=[go.Histogram(x=precios_finales, nbinsx=n_bins, marker_color='blue', opacity=0.75)])
fig_hist.update_layout(template = "plotly_dark", title="Precio Final")
st.plotly_chart(fig_hist, use_container_width=True)