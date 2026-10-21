from __future__ import annotations

from collections import defaultdict

import pandas as pd
import streamlit as st

from calculos.correlaciones import estadisticos_validos
from modelos.esquemas import EstadoRevision, ResultadoCorrelacion
from servicios.exportacion import resultados_a_csv


def cabecera_pestana(titulo: str, descripcion: str, aviso: str | None = None) -> None:
    st.subheader(titulo)
    st.caption(descripcion)
    if aviso:
        st.warning(aviso)


def _tabla(resultados: list[ResultadoCorrelacion]) -> pd.DataFrame:
    filas = []
    for resultado in resultados:
        filas.append(
            {
                "Autor / fuente": resultado.autor,
                "Aplicación": resultado.aplicacion,
                "Resultado": resultado.valor if resultado.valor is not None else None,
                "Unidad": resultado.unidad,
                "Parámetros": resultado.parametros,
                "Aplicabilidad": "Aplica" if resultado.aplicable else "No aplica",
                "Estado": resultado.estado.value,
                "Criterio": resultado.criterio,
            }
        )
    return pd.DataFrame(filas)


def mostrar_resultados(resultados: list[ResultadoCorrelacion], clave: str, mostrar_estadisticos: bool = False, mostrar_grafico: bool = True) -> None:
    if not resultados:
        st.info("No hay resultados para las entradas indicadas.")
        return

    if mostrar_estadisticos:
        stats = estadisticos_validos(resultados)
        columnas = st.columns(4)
        columnas[0].metric("Correlaciones válidas", stats["n"])
        columnas[1].metric("Mínimo", "-" if stats["mínimo"] is None else f"{stats['mínimo']:.3f}")
        columnas[2].metric("Media", "-" if stats["media"] is None else f"{stats['media']:.3f}")
        columnas[3].metric("Máximo", "-" if stats["máximo"] is None else f"{stats['máximo']:.3f}")

    st.dataframe(
        _tabla(resultados),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Resultado": st.column_config.NumberColumn(format="%.3f"),
            "Aplicabilidad": st.column_config.TextColumn(width="small"),
            "Estado": st.column_config.TextColumn(width="medium"),
        },
    )

    por_unidad: dict[str, list[ResultadoCorrelacion]] = defaultdict(list)
    for resultado in resultados:
        if resultado.aplicable and resultado.valor is not None and resultado.valor >= 0:
            por_unidad[resultado.unidad].append(resultado)
    for unidad, grupo in por_unidad.items() if mostrar_grafico else []:
        if len(grupo) < 2:
            continue
        grafico = pd.DataFrame(
            {
                "Correlación": [f"{i + 1}. {r.autor}" for i, r in enumerate(grupo)],
                f"Resultado ({unidad})": [r.valor for r in grupo],
            }
        ).set_index("Correlación")
        st.bar_chart(grafico, horizontal=True, color="#e55555")

    with st.expander("Formulación, trazabilidad y limitaciones", expanded=False):
        for indice, resultado in enumerate(resultados, start=1):
            st.markdown(f"**{indice}. {resultado.autor} - {resultado.aplicacion}**")
            st.latex(resultado.formula)
            detalle = f"Parámetros: {resultado.parametros}. Estado: {resultado.estado.value}."
            if resultado.criterio:
                detalle += f" Criterio: {resultado.criterio}."
            st.caption(detalle)
            if resultado.nota:
                if resultado.estado == EstadoRevision.REVISAR or not resultado.aplicable:
                    st.warning(resultado.nota)
                else:
                    st.info(resultado.nota)
            st.caption(f"Referencia: {resultado.referencia}")
            st.divider()

    st.download_button(
        "Descargar resultados CSV",
        data=resultados_a_csv(resultados),
        file_name=f"{clave}.csv",
        mime="text/csv",
        key=f"descarga_{clave}",
        use_container_width=False,
    )


def estado_revision() -> None:
    st.markdown("#### Estado")
    st.info("Cu: 4 relaciones bibliográficas y 2 consultas CTE; φ y E-arenas con fuentes FHWA y opciones secundarias justificadas.")
    st.caption("Metodología y restricciones documentadas por correlación. Versión v0.5, revisión computacional.")
