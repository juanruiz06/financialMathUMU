import streamlit as st
import os

st.set_page_config(page_title="Modelización Financiera - UMU", layout="wide")


st.title("Modelización y Valoración de Derivados Financieros")
st.markdown("""
Esta aplicación ha sido desarrollada como material de apoyo para el estudio de las Matemáticas de los Mercados Financieros.
Proporciona herramientas interactivas para el análisis de activos bajo el modelo de Black-Scholes y técnicas de simulación.
""")

st.write("")
st.divider()
st.write("")


col1, col2 = st.columns(2, gap="large")

with col1:
    st.header("Valoración de Opciones")
    st.write("""
    Cálculo de primas mediante el modelo analítico de Black-Scholes 
    y simulaciones de Monte Carlo. Incluye análisis comparativo de medidas de probabilidad.
    """)
    if st.button("Acceder a Pricing", use_container_width=True):
        st.switch_page("pages/Option_Pricing.py")

with col2:
    st.header("Cobertura Dinámica")
    st.write("""
    Simulación de carteras de réplica (Delta Hedging). Permite analizar el 
    impacto de la frecuencia de rebalanceo y la volatilidad en el error de seguimiento.
    """)
    if st.button("Acceder a Hedging", use_container_width=True):
        st.switch_page("pages/Delta_Hedging.py")


st.write("")
st.write("")
st.write("")
st.divider()

f_col1, f_col2, f_col3 = st.columns([1, 1, 9], vertical_alignment="center")

with f_col1:
    if os.path.exists("assets/logo_umu.png"):
        st.image("assets/logo_umu.png", width=80)

with f_col2:
    if os.path.exists("assets/logo_matematicas.png"):
        st.image("assets/logo_matematicas.png", width=80)

with f_col3:
    st.markdown("""
        **Juan Ruiz** – Alumno Interno  
        Facultad de Matemáticas | Universidad de Murcia  
        *Grado en Matemáticas*
    """)