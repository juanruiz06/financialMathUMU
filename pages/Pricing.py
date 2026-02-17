import streamlit as st
from ..engine.finance import GBM
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Simulación de Procesos Estocásticos", layout="wide")
st.title("Simulación de Procesos Estocásticos")

st.sidebar.header("Parámetros de la Simulación")
n_sims = st.sidebar.number_input("Número de Simulaciones", 1,10000, 1000)
n_show = st.sidebar.slider("Número de Simulaciones a Mostrar", 1, 100, 50)
s0 = st.sidebar.number_input("Precio inicial (S0)", value=100.0)
mu = st.sidebar.slider("Deriva (mu)", min_value=-1.0, max_value=1.0, value=0.05)
sigma = st.sidebar.slider("Volatilidad (sigma)", min_value=0.0, max_value=1.0, value=0.2)
t_final = st.sidebar.number_input("Tiempo total (T)", value=1.0)
K = st.sidebar.number_input("Precio de Strike (K)", value=100.0)
r = st.sidebar.slider("Tasa de interés (r)", 0.0, 0.1, 0.03)


st.sidebar.subheader("Tipo de Opción")
tipo_opcion = st.sidebar.selectbox("Selecciona el tipo de opción", ("Call", "Put", "Straddle", "Binary"))


modelo = GBM(S0 = s0, mu = mu, sigma = sigma, T = t_final, N = 252)
start_time = time.perf_counter()
precios = modelo.simulate(n_paths=n_sims)
end_time = time.perf_counter()

duration = end_time - start_time

precio_mc = modelo.calculate_mc_price(K = K, r = r, simulated_paths = precios, option_type = tipo_opcion)

precios_finales = precios[-1,:]
if tipo_opcion == "Call" or tipo_opcion == "Binary":
    itm_count = np.sum(precios_finales > K)
elif tipo_opcion == "Put":
    itm_count = np.sum(precios_finales < K)
elif tipo_opcion == "Straddle":
    itm_count = np.sum(np.abs(precios_finales - K) > precio_mc) # Sabemos que siempre se va a mover del strike, pero queremos saber si se mueve lo suficiente para superar el precio de la opción

prob_itm = (itm_count / n_sims)*100

st.subheader(f"Resultados: {tipo_opcion} Europea")
col1, col2 = st.columns(2)
col1.metric (label="Precio de la Opción (Monte Carlo)", value=f"${precio_mc:.2f} €")
col2.metric(label="Probabilidad de estar In The Money", value=f"{prob_itm:.2f} %")

with st.expander("Detalles de la Simulación"):
    st.write(f"Tiempo de simulación: {duration:.2f} segundos")
    st.write(f"Número de simulaciones: {n_sims}")

fig = go.Figure()
for i in range(min(n_show, n_sims)):
    fig.add_trace(go.Scatter(x=modelo.time_grid, y=precios[:,i],
                              mode='lines', line=dict(width=1), showlegend=False))

fig.add_hline(y=K, line=dict(color='red', width=2, dash='dash'), name='Strike Price (K)')

fig.update_layout(template = "plotly_dark", title="Simulación de un Proceso de Movimiento Browniano Geométrico (GBM)", xaxis_title="Tiempo", yaxis_title="Precio del Activo")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Distribución de precios al vencer")
n_bins = max(20, min(int(np.sqrt(n_sims)), 100))
precios_finales = precios[-1,:]
fig_hist = go.Figure(data=[go.Histogram(x=precios_finales, nbinsx=n_bins, marker_color='blue', opacity=0.75)])
fig_hist.update_layout(template = "plotly_dark", title="Precio Final")
st.plotly_chart(fig_hist, use_container_width=True)