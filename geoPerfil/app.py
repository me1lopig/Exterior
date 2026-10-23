"""Punto de entrada Streamlit de GeoPerfil 2D."""

from pathlib import Path
import sys


# Permite ejecutar `streamlit run app.py` desde la carpeta distribuida.
RAIZ_PAQUETE = Path(__file__).resolve().parent.parent
if str(RAIZ_PAQUETE) not in sys.path:
    sys.path.insert(0, str(RAIZ_PAQUETE))

import streamlit as st

from perfil_geologico.paginas.vistas import ejecutar_aplicacion


st.set_page_config(
    page_title="GeoPerfil 2D",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

css = Path(__file__).with_name("estilos.css").read_text(encoding="utf-8")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

ejecutar_aplicacion()
