import streamlit as st
from engine.finance import GBM
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Delta Hedging", layout="wide")
st.title("Cobertura Dinámica (Delta Hedging), Versión Beta")

st.sidebar.header("Parámetros del Mercado")
s0 = st.sidebar.number_input("Precio inicial (S0)", value=100.0)
sigma = st.sidebar.slider("Volatilidad (sigma)", min_value=0.0, max_value=1.0, value=0.2)
r = st.sidebar.slider("Tasa de interés (r)", 0.0, 0.1, 0.03)
K = st.sidebar.number_input("Precio de Strike (K)", value=100.0)
T = st.sidebar.number_input("Tiempo total (T)", value=1.0)
mu = st.sidebar.slider("Deriva (mu)", min_value=-1.0, max_value=1.0, value=0.05)

st.sidebar.divider()
tipo_opcion = st.sidebar.selectbox("Selecciona el tipo de opción para la cobertura", ("Call", "Put", "Straddle", "Binary"))
frecuencia = st.sidebar.selectbox("Frecuencia de rebalanceo", ("Diaria", "Semanal", "Quincenal", "Mensual"))

st.sidebar.subheader("Configuración de la simulación")
medida = st.sidebar.radio("Medida de Probabilidad",
         ["$\mathbb{Q}$ (Riesgo-Neutral)", "$\mathbb{P}$ (Mundo Real)"],
         key = "medida_persistente",
         help = "Q usa r como deriva, P usa mu.")

if st.sidebar.button("Simular Delta Hedging"):
    st.rerun()
es_riesgo_neutral = "$\\mathbb{Q}$ (Riesgo-Neutral)" in medida

N_pasos = 252
modelo = GBM(S0 = s0, mu = mu, sigma = sigma, T = T, N = N_pasos)
S = modelo.simulate(n_paths=1, use_risk_neutral=es_riesgo_neutral).flatten()
tiempos = modelo.time_grid

freq_map = {"Diaria": 1, "Semanal": 5, "Quincenal": 10, "Mensual": 21}
pasos = freq_map[frecuencia]
if tipo_opcion == "Binary":
    st.warning(" **Caso Patológico:** La cobertura de opciones binarias es extremadamente inestable cerca del strike al vencimiento. " \
    "Se ha aplicado un límite temporal previo al strike a la Delta para estabilizar la simulación.")

if es_riesgo_neutral:
    st.info("**Modo Verificación ($\mathbb{Q}$):** El activo evoluciona con deriva $r$.")
else:
    st.warning("**Modo Real ($\mathbb{P}$):** El activo evoluciona con deriva $\mu$.")
prima_inicial = modelo.black_scholes_price(K = K, r = r, option_type = tipo_opcion)
delta_t = modelo.get_delta(S[0], K, r, sigma, T, option_type=tipo_opcion)
caja = prima_inicial - delta_t * S[0]

hist_cartera = [prima_inicial]
hist_bs_teorico = [prima_inicial]
hist_deltas = [delta_t]

for t in range(1, len(tiempos)):
    dt_step = tiempos[t] - tiempos[t-1]
    T_restante = max(T - tiempos[t], 0.0)
    caja *= np.exp(r * dt_step)

    if t%pasos == 0 or t == len(tiempos)-1:
        nueva_delta = modelo.get_delta(S[t], K, r, sigma, T_restante, option_type=tipo_opcion)
        compra_venta = nueva_delta - delta_t
        caja -= compra_venta * S[t]
        delta_t = nueva_delta

    valor_total_cartera = caja + delta_t * S[t]
    hist_cartera.append(valor_total_cartera)

    valor_bs_teorico = modelo.black_scholes_price(K, r, S[t], T_restante, option_type=tipo_opcion)
    hist_bs_teorico.append(valor_bs_teorico)

    hist_deltas.append(delta_t)


valor_final = hist_cartera[-1]
payoff_final = hist_bs_teorico[-1] 
pnl_final = valor_final - payoff_final
error_abs = abs(pnl_final)

diff_temporal = np.abs(np.array(hist_cartera) - np.array(hist_bs_teorico))
tracking_error = np.mean(diff_temporal) 
error_vs_prima = (error_abs / prima_inicial * 100) if prima_inicial > 0 else 0.0
error_vs_payoff = (error_abs / payoff_final * 100) if payoff_final > 0 else 0.0

st.subheader(f"Análisis de Riesgos: {tipo_opcion} con Rebalanceo {frecuencia}")
m1,m2,m3,m4 = st.columns(4)
m1.metric(
    label="P&L Final", 
    value=f"{error_abs:.2f} €", 
    help="Resultado neto para el emisor. (Cartera Final - Payoff). Un valor positivo indica beneficio por encima de la prima cobrada."
)

m2.metric(
    label="Tracking Error Promedio", 
    value=f"{tracking_error:.2f} €",
    help="Distancia media por cada step entre el valor de la cartera y el precio teórico BS. Mide la estabilidad de la réplica."
)

m3.metric(
    label="Error vs Prima Inicial", 
    value=f"{error_vs_prima:.2f} %",
    help="Error porcentual de seguimiento en relación al presupuesto inicial (Prima)."
)

m4.metric(
    label="Error vs Payoff Final", 
    value=f"{error_vs_payoff:.2f} %" if payoff_final > 0.1 else "Sin Payoff",
    help="Desviación porcentual respecto al valor de liquidación de la opción al vencimiento."
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=tiempos, y=hist_cartera, name="Valor Cartera de Réplica",
                         line=dict(color='#00ff00', width=3)))

fig.add_trace(go.Scatter(x=tiempos, y=hist_bs_teorico, name="Valor Teórico de la Opción",
                         line=dict(color='white', dash='dash', width=1)))

fig.update_layout(template="plotly_dark", title="Evolución de la Cartera vs Precio Teórico",
                  xaxis_title="Tiempo (Años)", yaxis_title="Valor (€)")
st.plotly_chart(fig, use_container_width=True)

fig_delta = go.Figure()
fig_delta.add_trace(go.Scatter(x=tiempos, y=hist_deltas, name="Delta (Exposición)",
                              line=dict(color='cyan')))
fig_delta.update_layout(template="plotly_dark", title="Exposición al Activo (Delta)",
                        xaxis_title="Tiempo", yaxis_title="Número de Acciones")
st.plotly_chart(fig_delta, use_container_width=True)