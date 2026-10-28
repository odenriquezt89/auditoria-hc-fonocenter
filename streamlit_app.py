"""
Lanzador de Streamlit Cloud - FONOCENTER IPS.
Permite desplegar la aplicación completa de Auditoría Médica directamente en Streamlit Community Cloud (share.streamlit.io).
"""

import os
import streamlit as st
import streamlit.components.v1 as components

# Configuración de página a ancho completo
st.set_page_config(
    page_title="FONOCENTER IPS - Sistema de Auditoría Médica",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo para maximizar el área visible y eliminar bordes innecesarios
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }
    iframe {
        border: none !important;
        width: 100% !important;
        min-height: 100vh !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Cargar index.html
base_dir = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(base_dir, "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()

    # Renderizar la aplicación interactiva
    components.html(html_code, height=1200, scrolling=True)
else:
    st.error("Archivo index.html no encontrado.")
