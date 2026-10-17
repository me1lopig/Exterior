"""
app.py — Consulta de propiedades de suelos
==========================================
Aplicación Streamlit de consulta de parámetros geotécnicos del terreno.
Una pestaña por documento/fuente; el usuario elige el documento aplicable.
Los valores de distintas fuentes NO se comparan ni se mezclan.

Ejecutar:  streamlit run app.py
"""
from __future__ import annotations
import pandas as pd
import streamlit as st

import soil_params_engine as eng

st.set_page_config(page_title="Consulta de propiedades de suelos",
                   page_icon="🪨", layout="wide")


# --------------------------------------------------------------------------- #
#  Utilidades de UI                                                            #
# --------------------------------------------------------------------------- #
def filtra(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    if not texto:
        return df
    texto = texto.strip().lower()
    mascara = df.apply(
        lambda fila: fila.astype(str).str.lower().str.contains(texto).any(),
        axis=1)
    return df[mascara]


def pinta_fuente(meta: dict) -> None:
    fid = meta["fuente_id"]
    st.subheader(meta["nombre"])
    st.caption(f"📖 Fuente: {meta['cita']}")
    if meta.get("nota"):
        st.info(meta["nota"], icon="ℹ️")

    df = eng.tabla_formateada(fid)

    busca = st.text_input("Buscar tipo de suelo",
                          key=f"buscar_{fid}",
                          placeholder="p. ej. arcilla, grava, tosco…")
    vista = filtra(df, busca)

    st.caption(f"{len(vista)} de {len(df)} filas")
    st.dataframe(vista, width="stretch", hide_index=True)

    # descarga de tabla en CSV (desactivada por ahora)
    #csv = eng.tabla(fid).to_csv(index=False).encode("utf-8")
    #st.download_button("⬇️ Descargar tabla (CSV)", data=csv,
    #                  file_name=f"{fid}.csv", mime="text/csv",
    #                  key=f"dl_{fid}")


# --------------------------------------------------------------------------- #
#  Barra lateral                                                               #
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("🪨 Propiedades de suelos")
    st.write("Base de datos de parámetros del terreno tabulados por fuente.")
    st.warning("Valores **orientativos**. No sustituyen la caracterización "
               "geotécnica específica de cada emplazamiento mediante ensayos.",
               icon="⚠️")

    with st.expander("Fuentes incluidas"):
        for m in eng.lista_fuentes():
            st.markdown(f"**{m['id']}. {m['nombre']}**  \n"
                        f"<small>{m['cita']}</small>", unsafe_allow_html=True)




# --------------------------------------------------------------------------- #
#  Cuerpo: una pestaña por fuente                                              #
# --------------------------------------------------------------------------- #
st.title("Consulta de propiedades de suelos")
st.caption("Selecciona el documento aplicable. Cada pestaña es una fuente "
           "independiente.")
st.markdown("Realizado según directriva ITQ404")

metas = eng.lista_fuentes()
pestanas = st.tabs([m["nombre"] for m in metas])
for pestana, meta in zip(pestanas, metas):
    with pestana:
        pinta_fuente(meta)
