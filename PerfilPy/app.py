from __future__ import annotations

import hashlib
import re

import pandas as pd
import streamlit as st

from calculos.ejes import calcular_limites_verticales
from modelos.configuracion import OpcionesGraficas, PRESETS_GRAFICOS, validar_opciones_graficas
from modelos.datos import DatosProyecto, EstadoNF, Severidad
from modelos.validacion import incidencias_dataframe, validar_datos
from servicios.excel import ErrorDatos, cargar_proyecto, expandir_archivos, exportar_excel_corregido
from visualizacion.dxf import OpcionesDXF, generar_dxf
from visualizacion.preview import crear_vista_previa


st.set_page_config(page_title="Geocempy | Perfiles geotecnicos", layout="wide")

st.markdown(
    """
    <style>
    :root { --accent: #e65357; --ink: #10253d; --muted: #667085; --line: #d9dee7; }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px; }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-size: 2rem !important; }
    div[data-testid="stMetric"] { border-top: 2px solid var(--line); padding-top: 0.7rem; }
    div[data-testid="stMetricValue"] { color: var(--ink); font-size: 1.35rem; }
    .status-ok { padding: .75rem 1rem; background: #e8f6ee; color: #17653a; border-left: 4px solid #2a9d62; }
    .status-error { padding: .75rem 1rem; background: #fdeced; color: #8f2530; border-left: 4px solid var(--accent); }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


def _signature(datos: DatosProyecto, options: tuple[object, ...]) -> str:
    digest = hashlib.sha256(repr(options).encode("utf-8"))
    for frame in datos.tablas().values():
        digest.update(pd.util.hash_pandas_object(frame.fillna(""), index=True).values.tobytes())
    return digest.hexdigest()


def _editor_key(name: str) -> str:
    return f"editor_{st.session_state.get('revision', 0)}_{name}"


def _load_files(uploaded: list[object]) -> None:
    files = expandir_archivos(uploaded)
    if not files:
        raise ErrorDatos("No se encontraron archivos XLSX.")
    data = cargar_proyecto(files)
    st.session_state["datos"] = data
    st.session_state["original"] = data.copy()
    st.session_state["revision"] = st.session_state.get("revision", 0) + 1
    st.session_state.pop("dxf", None)
    st.session_state.pop("dxf_signature", None)


with st.sidebar:
    st.subheader("Archivos")
    uploads = st.file_uploader(
        "XLSX o ZIP del proyecto",
        type=["xlsx", "zip"],
        accept_multiple_files=True,
        help="El ZIP puede contener los archivos base y uno o varios perfiles.",
    )
    if st.button("Cargar y revisar", type="primary", use_container_width=True):
        try:
            _load_files(uploads)
        except ErrorDatos as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"No se pudieron cargar los datos: {exc}")
        else:
            st.rerun()

    st.divider()
    st.subheader("Criterio de dibujo")
    mode_options = ["Litologia", "UGEO", "Ambos"]
    mode = st.radio("Columnas", mode_options, horizontal=True)
    show_boreholes = st.checkbox("Mostrar sondeos", value=True)
    show_dpsh = st.checkbox("Mostrar DPSH", value=True)
    annotate_absent = st.checkbox("Anotar NF no detectado", value=True)
    st.divider()
    with st.expander("Configuracion grafica", expanded=False):
        graphic_preset = st.selectbox("Configuracion inicial", list(PRESETS_GRAFICOS), index=1)
        base_graphics = PRESETS_GRAFICOS[graphic_preset]
        st.caption("Alturas y separaciones expresadas en metros del modelo DXF.")
        graphic_options = OpcionesGraficas(
            texto_ejes_m=st.number_input(
                "Texto de ejes",
                min_value=0.05,
                max_value=5.0,
                value=base_graphics.texto_ejes_m,
                step=0.01,
                format="%.2f",
                key=f"graphic_axis_{graphic_preset}",
            ),
            nombre_prospeccion_m=st.number_input(
                "Nombre de prospeccion",
                min_value=0.05,
                max_value=5.0,
                value=base_graphics.nombre_prospeccion_m,
                step=0.01,
                format="%.2f",
                key=f"graphic_name_{graphic_preset}",
            ),
            texto_estratos_m=st.number_input(
                "Texto de litologia / UGEO",
                min_value=0.05,
                max_value=5.0,
                value=base_graphics.texto_estratos_m,
                step=0.01,
                format="%.2f",
                key=f"graphic_strata_{graphic_preset}",
            ),
            texto_ensayos_m=st.number_input(
                "Texto de ensayos",
                min_value=0.05,
                max_value=5.0,
                value=base_graphics.texto_ensayos_m,
                step=0.01,
                format="%.2f",
                key=f"graphic_assay_{graphic_preset}",
            ),
            titulo_m=st.number_input(
                "Titulo del perfil",
                min_value=0.05,
                max_value=5.0,
                value=base_graphics.titulo_m,
                step=0.01,
                format="%.2f",
                key=f"graphic_title_{graphic_preset}",
            ),
            separacion_horizontal_m=st.number_input(
                "Separacion horizontal de textos",
                min_value=0.0,
                max_value=20.0,
                value=base_graphics.separacion_horizontal_m,
                step=0.05,
                format="%.2f",
                key=f"graphic_horizontal_{graphic_preset}",
            ),
            separacion_vertical_ensayos_m=st.number_input(
                "Separacion de ensayos coincidentes",
                min_value=0.0,
                max_value=20.0,
                value=base_graphics.separacion_vertical_ensayos_m,
                step=0.05,
                format="%.2f",
                key=f"graphic_vertical_{graphic_preset}",
            ),
            separacion_nombre_m=st.number_input(
                "Separacion del nombre sobre rasante",
                min_value=0.0,
                max_value=20.0,
                value=base_graphics.separacion_nombre_m,
                step=0.05,
                format="%.2f",
                key=f"graphic_name_offset_{graphic_preset}",
            ),
        )

st.title("Perfiles geologico-geotecnicos")
st.caption("Revision de datos, control de coherencia y exportacion CAD trazable")

if "datos" not in st.session_state:
    st.info("Carga los XLSX individuales o el ZIP completo para iniciar la revision.")
    st.stop()

datos: DatosProyecto = st.session_state["datos"]
profile_names = list(datos.perfiles["perfil"].dropna().astype(str).drop_duplicates())
selected_profiles = st.multiselect("Perfiles incluidos", profile_names, default=profile_names)

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Perfiles", len(profile_names))
metric2.metric("Sondeos", datos.litologia["sondeo"].nunique())
metric3.metric("DPSH", datos.dpsh["ensayo"].nunique())
metric4.metric("Ensayos", len(datos.ensayos))

if datos.archivos_ignorados:
    st.caption("Archivos auxiliares reconocidos y no tratados como perfiles: " + ", ".join(datos.archivos_ignorados))

st.subheader("Revision de datos")
st.caption("Las ediciones se aplican a la sesion y no modifican los libros originales.")
tabs = st.tabs(["Perfil", "Litologia", "Ensayos", "DPSH", "UGEO", "Nivel freatico"])

with tabs[0]:
    datos.perfiles = st.data_editor(
        datos.perfiles,
        key=_editor_key("perfiles"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "tipo": st.column_config.SelectboxColumn(
                "Tipo", options=["Punto de terreno", "Sondeo", "DPSH"], required=True
            ),
            "distancia_m": st.column_config.NumberColumn("Distancia (m)", format="%.2f"),
            "cota_m": st.column_config.NumberColumn("Cota (m)", format="%.2f"),
            "orden": st.column_config.NumberColumn("Orden", step=1),
        },
    )

with tabs[1]:
    datos.litologia = st.data_editor(
        datos.litologia,
        key=_editor_key("litologia"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "profundidad_inicial_m": st.column_config.NumberColumn("Prof. inicial (m)", format="%.2f"),
            "profundidad_final_m": st.column_config.NumberColumn("Prof. final (m)", format="%.2f"),
            "descripcion": st.column_config.TextColumn("Descripcion completa", width="large"),
        },
    )

with tabs[2]:
    datos.ensayos = st.data_editor(
        datos.ensayos,
        key=_editor_key("ensayos"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["SPT", "MA", "MI", "TP", "OTRO"]),
            "profundidad_m": st.column_config.NumberColumn("Profundidad (m)", format="%.2f"),
            "phi_deg": st.column_config.TextColumn("Phi (deg)"),
            "cohesion_kpa": st.column_config.TextColumn("Cohesion (kPa)"),
        },
    )

with tabs[3]:
    datos.dpsh = st.data_editor(
        datos.dpsh,
        key=_editor_key("dpsh"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "profundidad_m": st.column_config.NumberColumn("Profundidad (m)", format="%.2f"),
            "golpes": st.column_config.NumberColumn("N20", format="%.0f", min_value=0),
        },
    )

with tabs[4]:
    datos.ugeo = st.data_editor(
        datos.ugeo,
        key=_editor_key("ugeo"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "profundidad_inicial_m": st.column_config.NumberColumn("Prof. inicial (m)", format="%.2f"),
            "profundidad_final_m": st.column_config.NumberColumn("Prof. final (m)", format="%.2f"),
        },
    )

with tabs[5]:
    st.info(
        "Un cero importado es ambiguo. Selecciona Detectado para representar NF a 0,00 m, "
        "o No detectado/No medido para conservar correctamente el significado de la observacion."
    )
    datos.nivel_freatico = st.data_editor(
        datos.nivel_freatico,
        key=_editor_key("nf"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "estado": st.column_config.SelectboxColumn(
                "Estado",
                options=[item.value for item in EstadoNF],
                required=True,
            ),
            "profundidad_m": st.column_config.NumberColumn(
                "Profundidad bajo boca (m)", format="%.2f", min_value=0.0
            ),
        },
    )

st.session_state["datos"] = datos
issues = validar_datos(datos, selected_profiles)
graphic_errors = validar_opciones_graficas(graphic_options)
axis_limits: dict[str, tuple[float, float, float]] = {}
axis_errors: list[str] = []
st.subheader("Escala vertical")
st.caption(
    "El modo automatico utiliza la cota del fondo mas bajo y añade un margen proporcional. "
    "Los limites se aplican por igual a la vista previa y al DXF."
)
with st.expander("Limites verticales por perfil", expanded=False):
    for profile_name in selected_profiles:
        try:
            automatic = calcular_limites_verticales(datos, profile_name)
        except ValueError as exc:
            axis_errors.append(str(exc))
            continue
        st.markdown(f"**{profile_name}**")
        manual = st.checkbox(
            "Ajuste manual",
            key=f"axis_manual_{st.session_state.get('revision', 0)}_{profile_name}",
        )
        if manual:
            col_min, col_max, col_step = st.columns(3)
            axis_min = col_min.number_input(
                "Cota minima (m)",
                value=float(automatic.minimo),
                key=f"axis_min_{st.session_state.get('revision', 0)}_{profile_name}",
            )
            axis_max = col_max.number_input(
                "Cota maxima (m)",
                value=float(automatic.maximo),
                key=f"axis_max_{st.session_state.get('revision', 0)}_{profile_name}",
            )
            axis_step = col_step.number_input(
                "Paso vertical (m)",
                min_value=0.01,
                value=float(automatic.paso),
                key=f"axis_step_{st.session_state.get('revision', 0)}_{profile_name}",
            )
        else:
            axis_min, axis_max, axis_step = automatic.minimo, automatic.maximo, automatic.paso
            st.caption(
                f"Automatico: {axis_min:g} a {axis_max:g} m; paso {axis_step:g} m. "
                f"Fondo mas bajo: {automatic.cota_fondo_minima:.2f} m; "
                f"margen inferior: {automatic.margen_inferior:.2f} m."
            )
        if axis_max <= axis_min:
            axis_errors.append(f"{profile_name}: la cota maxima debe superar a la minima.")
        elif axis_step <= 0:
            axis_errors.append(f"{profile_name}: el paso vertical debe ser positivo.")
        elif axis_min > automatic.cota_fondo_minima:
            axis_errors.append(f"{profile_name}: el limite inferior deja una prospeccion fuera del marco.")
        elif axis_max < automatic.cota_terreno_maxima:
            axis_errors.append(f"{profile_name}: el limite superior deja parte del terreno fuera del marco.")
        elif (axis_max - axis_min) / axis_step > 1000:
            axis_errors.append(f"{profile_name}: el paso genera mas de 1000 divisiones verticales.")
        axis_limits[profile_name] = (float(axis_min), float(axis_max), float(axis_step))

error_count = (
    sum(issue.severidad == Severidad.ERROR for issue in issues)
    + len(axis_errors)
    + len(graphic_errors)
)
warning_count = sum(issue.severidad == Severidad.AVISO for issue in issues)

st.subheader("Control de coherencia")
if error_count:
    st.markdown(
        f'<div class="status-error">{error_count} errores bloqueantes y {warning_count} avisos.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="status-ok">Datos aptos para exportacion. {warning_count} avisos no bloqueantes.</div>',
        unsafe_allow_html=True,
    )
if issues:
    st.dataframe(incidencias_dataframe(issues), use_container_width=True, hide_index=True)
for message in axis_errors:
    st.error(message)
for message in graphic_errors:
    st.error(message)

preview_tab, export_tab = st.tabs(["Vista previa", "Exportacion"])
with preview_tab:
    if selected_profiles:
        preview_profile = st.selectbox("Perfil mostrado", selected_profiles)
        preview_ugeo = st.toggle("Vista UGEO", value=mode == "UGEO", disabled=datos.ugeo.empty)
        figure = crear_vista_previa(
            datos,
            preview_profile,
            usar_ugeo=preview_ugeo,
            mostrar_sondeos=show_boreholes,
            mostrar_dpsh=show_dpsh,
            limites_verticales=axis_limits.get(preview_profile),
            graficos=graphic_options,
        )
        st.pyplot(figure, use_container_width=True)
    else:
        st.warning("Selecciona al menos un perfil.")

with export_tab:
    output_name = st.text_input("Nombre del DXF", value="Perfil_geotecnico")
    options_tuple = (
        selected_profiles,
        mode,
        show_boreholes,
        show_dpsh,
        annotate_absent,
        output_name,
        sorted(axis_limits.items()),
        graphic_options,
    )
    current_signature = _signature(datos, options_tuple)
    generate_disabled = bool(error_count or not selected_profiles or (mode in {"UGEO", "Ambos"} and datos.ugeo.empty))
    if st.button("Generar DXF validado", type="primary", disabled=generate_disabled):
        try:
            st.session_state["dxf"] = generar_dxf(
                datos,
                OpcionesDXF(
                    perfiles=selected_profiles,
                    modo_columna=mode,
                    mostrar_sondeos=show_boreholes,
                    mostrar_dpsh=show_dpsh,
                    anotar_nf_ausente=annotate_absent,
                    limites_verticales=axis_limits,
                    graficos=graphic_options,
                ),
            )
            st.session_state["dxf_signature"] = current_signature
        except Exception as exc:
            st.error(f"No se pudo generar el DXF: {exc}")
        else:
            st.success("DXF generado y auditado.")

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", output_name).strip("_") or "Perfil_geotecnico"
    if st.session_state.get("dxf") and st.session_state.get("dxf_signature") == current_signature:
        st.download_button(
            "Descargar DXF",
            st.session_state["dxf"],
            file_name=f"{safe_name}.dxf",
            mime="application/dxf",
        )
    elif st.session_state.get("dxf"):
        st.caption("Los datos u opciones han cambiado. Regenera el DXF antes de descargarlo.")

    st.download_button(
        "Descargar datos corregidos",
        exportar_excel_corregido(datos, st.session_state.get("original")),
        file_name=f"{safe_name}_datos_corregidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
