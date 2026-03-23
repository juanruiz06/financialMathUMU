import streamlit as st
from engine.finance import GBM
import numpy as np
import plotly.graph_objects as go
import requests
import os

st.set_page_config(page_title="Delta Hedging", layout="wide")
st.title("Cobertura Dinámica (Delta Hedging)")

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

if st.sidebar.button("Simular Delta Hedging"):
    st.rerun()

N_pasos = 252
modelo = GBM(S0 = s0, mu = mu, sigma = sigma, T = T, N = N_pasos)

freq_map = {"Diaria": 1, "Semanal": 5, "Quincenal": 10, "Mensual": 21}
pasos = freq_map[frecuencia]
if tipo_opcion == "Binary":
    st.warning(" **Caso Patológico:** La cobertura de opciones binarias es extremadamente inestable cerca del strike al vencimiento. " \
    "Se ha aplicado un límite temporal previo al strike a la Delta para estabilizar la simulación.")

payload = {
    "S0": float(s0),
    "mu": float(mu),
    "sigma": float(sigma),
    "T": float(T),
    "K": float(K),
    "r": float(r),
    "tipo_opcion": tipo_opcion,
    "frecuencia": int(pasos),
    "use_risk_neutral": True,
}
backend_base_url = os.getenv("BACKEND_URL", "http://localhost:3000").rstrip("/")
api_url = f"{backend_base_url}/api/hedging"

try:
    response = requests.post(api_url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.ConnectionError:
    st.error("No se pudo conectar con el backend de hedging. Verifica que el API Gateway esté activo en http://localhost:3000.")
    st.stop()
except requests.exceptions.HTTPError:
    st.error("El backend devolvió un error al calcular el delta hedging. Inténtalo de nuevo en unos segundos.")
    st.stop()
except requests.exceptions.Timeout:
    st.error("El backend tardó demasiado en responder para delta hedging.")
    st.stop()
except requests.exceptions.RequestException:
    st.error("Ocurrió un problema de red al consultar el backend de hedging.")
    st.stop()
except ValueError:
    st.error("La respuesta del backend de hedging no tiene un formato JSON válido.")
    st.stop()

required_keys = ("tiempos", "hist_cartera", "hist_bs_teorico", "hist_deltas", "metrics")
if any(key not in data for key in required_keys):
    st.error("La respuesta del backend no contiene los campos esperados de delta hedging.")
    st.stop()

try:
    tiempos = np.array(data["tiempos"], dtype=float)
    hist_cartera = np.array(data["hist_cartera"], dtype=float)
    hist_bs_teorico = np.array(data["hist_bs_teorico"], dtype=float)
    hist_deltas = np.array(data["hist_deltas"], dtype=float)
except (TypeError, ValueError):
    st.error("El backend devolvió datos de delta hedging en un formato inválido.")
    st.stop()

if not (len(tiempos) == len(hist_cartera) == len(hist_bs_teorico) == len(hist_deltas)):
    st.error("Las series devueltas por el backend no tienen la misma longitud.")
    st.stop()

metrics = data["metrics"]
if not isinstance(metrics, dict):
    st.error("El backend devolvió métricas de delta hedging en un formato inválido.")
    st.stop()

try:
    pnl_final = float(metrics["pnl_final"])
    tracking_error = float(metrics["tracking_error"])
    error_vs_prima = float(metrics["error_vs_prima"])
    error_vs_payoff = float(metrics["error_vs_payoff"])
except (KeyError, TypeError, ValueError):
    st.error("El backend no devolvió métricas completas para delta hedging.")
    st.stop()

payoff_final = float(hist_bs_teorico[-1]) if len(hist_bs_teorico) > 0 else 0.0

st.subheader(f"Análisis de Riesgos: {tipo_opcion} con Rebalanceo {frecuencia}")
m1,m2,m3,m4 = st.columns(4)
m1.metric(
    label="P&L Final", 
    value=f"{pnl_final:.2f} €", 
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
                         line=dict(color='purple', dash='dash', width=1)))

fig.update_layout(template="plotly_dark", title="Evolución de la Cartera vs Precio Teórico",
                  xaxis_title="Tiempo (Años)", yaxis_title="Valor (€)")
st.plotly_chart(fig, use_container_width=True)

fig_delta = go.Figure()
fig_delta.add_trace(go.Scatter(x=tiempos, y=hist_deltas, name="Delta (Exposición)",
                              line=dict(color='cyan')))
fig_delta.update_layout(template="plotly_dark", title="Exposición al Activo (Delta)",
                        xaxis_title="Tiempo", yaxis_title="Número de Acciones")
st.plotly_chart(fig_delta, use_container_width=True)