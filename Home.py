import streamlit as st


st.set_page_config(page_title="Inicio", layout="wide")
st.markdown("---")
st.subheader("Acceso a Simuladores")
col1= st.columns(1)

with col1:
    if st.button("Pricing"):
        st.switch_page("pages/pricing.py")
