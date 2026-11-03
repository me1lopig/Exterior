"""Punto de entrada Streamlit de GeoPerfil 2D."""

import importlib.util
from pathlib import Path
import sys


# Permite ejecutar la aplicacion aunque la carpeta se renombre en el despliegue.
CARPETA_APLICACION = Path(__file__).resolve().parent
RAIZ_PAQUETE = CARPETA_APLICACION.parent
if str(RAIZ_PAQUETE) not in sys.path:
    sys.path.insert(0, str(RAIZ_PAQUETE))
if "perfil_geologico" not in sys.modules and CARPETA_APLICACION.name != "perfil_geologico":
    especificacion = importlib.util.spec_from_file_location(
        "perfil_geologico",
        CARPETA_APLICACION / "__init__.py",
        submodule_search_locations=[str(CARPETA_APLICACION)],
    )
    if especificacion is None or especificacion.loader is None:
        raise ImportError("No se pudo registrar el paquete local de GeoPerfil 2D.")
    paquete = importlib.util.module_from_spec(especificacion)
    sys.modules["perfil_geologico"] = paquete
    especificacion.loader.exec_module(paquete)

def main() -> None:
    """Configura Streamlit y ejecuta la interfaz."""
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


if __name__ == "__main__":
    main()
