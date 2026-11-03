# GeoPerfil 2D v0.8.5 — Correccion MiniCAD, guitarra y personalizacion de unidades

Aplicacion Python/Streamlit para dibujar perfiles geologicos manualmente a partir de sondeos y ensayos de campo. La geologia se interpreta mediante contactos y lentejones en el MiniCAD; los ensayos no generan correlaciones geologicas automaticas.

## Importacion unica: libros originales de campana

- **Importacion simultanea de varios archivos Excel**: `PERFIL1.xlsx` define PK y cotas reales, `BKFL.XLSX` litologias, `DPRG.XLSX` penetracion dinamica, `ISPT.XLSX` SPT y `ListadoLab.XLSX` laboratorio.
- Reconocimiento por **cabeceras del archivo**, no por nombre literal. PERFIL1 es obligatorio; los cuatro restantes son opcionales. Para un perfil geologico dibujable es necesario al menos BKFL.
- Interfaz de **validar antes de aplicar**. Se informa del numero de sondeos, curvas, ensayos y muestras; el usuario confirma expresamente antes de sustituir la campana o descartar contactos anteriores.
- La columna **Cota** de PERFIL1 indica la elevacion real de cada punto (m). Cero es valido; vacio es error. La columna **Distancia** es el PK acumulado (m). **STA es un punto topografico del terreno**, no un sondeo, penetracion ni otro trabajo de campo. Su PK y su cota forman parte de la superficie del perfil.
- La topografia observada procede de **todos los puntos de PERFIL1**, incluido STA, sin inventar cotas fuera del primer y ultimo punto; entre PK se interpola linealmente.
- Los intervalos BKFL se conservan con estrato, descripcion y origen. Los codigos `EST_*` no se equiparan automaticamente a unidades geotecnicas `UG-*` del laboratorio.
- DPRG conserva los golpes originales separados por profundidad de 0,20 m; **el subtipo de penetracion debe confirmarse**. No interpreta rechazo ni convierte los golpes en SPT. La tabla interna se denomina `Ensayos_DPSH` por compatibilidad con v0.7, aunque se registra el tipo como `PENETROMETRO (subtipo no confirmado)`.
- Los SPT se muestran como **`SPT 24/13/4/4`** a su cota, sin reemplazar los incrementos por N. Se deduplican los SPT presentes tanto en ISPT como en ListadoLab, dando prioridad a ISPT y avisando si hay discrepancias.
- Muestras no SPT y resultados de laboratorio resumidos disponibles como **capas optativas**, con codigo UG, USCS, IP, RCS donde existan datos. Se guardan los registros completos de ListadoLab en el proyecto.
- Controles de visibilidad de terreno, sondeos, contactos, rellenos, curvas de penetracion, SPT, muestras, laboratorio y guitarra. Tamano de letra **general, ensayos y guitarra** de 6 a 18 pt; parametros serializados en JSON.
- Exportaciones HTML, PNG, SVG, PDF y DXF comparten estas capas. En DXF, los SPT, muestras y laboratorio son textos editables en capas CAD especificas.
- **Solo existe la entrada multifichero**. Se han retirado la plantilla Excel unica, la edicion de tablas de entrada y el inicio automatico con datos demostrativos. Los proyectos JSON guardados siguen siendo recuperables.

## Interfaz v0.8.5

- Cabecera azul oscuro con operaciones **Nuevo**, **Abrir** (proyecto JSON) y **Guardar** (descarga del proyecto). Nuevo y Abrir solicitan confirmación antes de sustituir trabajo existente. El guardado MiniCAD se mantiene independiente de la descarga del JSON.
- Pestañas superiores en este orden: **Datos**, **Trazado**, **Perfil**, **Unidades**, **Interpretación** y **Exportar**. Los metadatos y las escalas del proyecto están en un apartado desplegable de **Datos**.
- Panel **izquierdo** contextual: capas geológicas, capas de ensayos, guitarra y tres tamaños de letra (general, ensayos y guitarra). El perfil y sus exportaciones usan estas preferencias. Las preferencias se restauran correctamente al abrir otro proyecto.
- Barra horizontal de herramientas del MiniCAD **encima del lienzo**, agrupada en Dibujo, Rellenos y Vista. Incluye seleccionar, dibujar/borrar contacto, dibujar/borrar lentejón, finalizar, rellenar/quitar relleno, limpiar, deshacer/rehacer, mover, encuadrar y ajuste magnético. El desplazamiento con la mano es adicional a **Mayús+arrastrar** y al botón central; el zoom con rueda sigue disponible.
- Los puntos **STA solo aportan PK/cota a la superficie**: no se dibujan símbolos ni etiquetas STA en el trazado, en el MiniCAD, en el perfil ni en la guitarra. La topografía sigue incluyendo esos datos de forma exacta.
- **Unidades** permite cambiar **nombre** y **color** con selector visual. El codigo BKFL (`unidad_id`) permanece fijo y permite seguir vinculando intervalos y contactos. Se ha retirado la columna Observaciones de Unidades. Los cambios se guardan en el proyecto JSON y actualizan las zonas clasificadas. La clasificación de polígonos sigue siendo manual en Interpretación.
- Las modificaciones estéticas no cambian el motor de contactos, cotas, SPT, lectura DPRG, construcción de zonas ni las coordenadas de exportación.

## Instalacion

En macOS o Linux, dentro de la carpeta `perfil_geologico`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

En Windows, active `.venv\Scripts\activate` y ejecute `python -m pip install -r requirements.txt` y `python -m streamlit run app.py`.

## Procedimiento con varios archivos

1. Abra la pestaña **Datos** y seleccione **Importar campana desde varios archivos Excel**.
2. Seleccione juntos `PERFIL1.xlsx`, `BKFL.XLSX`, `DPRG.XLSX`, `ISPT.XLSX` y/o `ListadoLab.XLSX`. Los nombres pueden ser diferentes, pero las cabeceras deben coincidir con los formatos reconocidos.
3. Pulse **Validar archivos**, revise estaciones y advertencias y confirme la sustitucion.
4. Pulse **Aplicar campana validada**. Las tablas derivadas quedan bloqueadas para impedir inconsistencias con PERFIL1. Para corregir datos, modifique el original y vuelva a importar. La interpretacion anterior se descarta solo tras confirmacion.
5. En **Trazado**, revise el eje de PK acumulados y la guitarra. El eje es de solo lectura para una campana importada por PK.
6. En **Interpretación**, utilice la barra MiniCAD horizontal (selección, contactos, lentejones, rellenos, desplazamiento y ajuste magnético).
7. En **Unidades**, edite los nombres y seleccione los colores a su gusto; guarde para actualizar zonas y leyendas. En **Perfil**, active las capas y ajuste los tamaños de letra desde el panel lateral izquierdo; cambie la escala gráfica de golpes en la zona central.
8. En **Exportar**, descargue PDF, PNG, SVG, DXF, HTML, Excel o proyecto JSON. Guarde el JSON para poder reabrir la campana y su interpretacion.

La carpeta `ejemplos/campana_multifichero_sintetica/` contiene cinco libros inventados expresamente para probar el importador. No se entrega ninguna plantilla de entrada unica.

## Trazabilidad de los datos

Las tablas internas derivadas que usa el motor (`Sondeos`, `Intervalos`, `Unidades`, `Ensayos_DPSH`, `Lecturas_DPSH`, `Eje`) se mantienen para el motor de GeoPerfil. Ademas, la nueva importacion agrega `Estaciones`, `SPT`, `Muestras`, `Laboratorio`, `Laboratorio_original` y `Fuentes`. Las tablas contienen nombre del archivo, numero de fila e identificadores donde corresponde. `Fuentes` incluye hash SHA-256 del libro; la aplicacion **no guarda los bytes originales del Excel en el JSON**. Conserve sus originales separadamente.

SPT y laboratorio son datos observados de campo/ensayo. Las zonas geologicas dibujadas y clasificadas constituyen interpretacion del tecnico, no medicion de los libros.

## Pruebas

Desde la carpeta superior que contiene `perfil_geologico`:

```bash
python3 -m pytest -q perfil_geologico/tests
python3 -m compileall -q perfil_geologico
```

La versión **v0.8.5 ha superado 97 pruebas automatizadas** (incluidas las 88 anteriores). Incluye regresiones del importador, topografia con STA, guardado, capas y DXF, ademas de pruebas de navegador del MiniCAD y una prueba integral con los cinco libros aportados en esta conversacion. El DXF fue releido con `ezdxf`; las imagenes fueron generadas y revisadas. No se pudo ejecutar una sesión completa de Streamlit aquí porque Streamlit no estaba instalado y no se pudo descargar sin acceso de red. La regresión específica construye el modelo de MiniCAD con la misma firma de la interfaz mediante un adaptador simulado, y comprueba que no vuelve a darse el TypeError del argumento duplicado. Se comprobó el MiniCAD en Chromium mediante Playwright, incluyendo que las bocas y puntos de inicio estén sobre la línea del terreno, pero no toda la interfaz Streamlit. Debe validarse localmente en macOS antes de usarlo en un trabajo real; la apertura del DXF en AutoCAD sigue pendiente.

## Correccion v0.8.3: posicion real de los reconocimientos

- Sondeos y penetrómetros comienzan **exactamente en el PK y la Cota indicados en PERFIL1**, sin desplazamiento vertical de la geometría. Los datos de entrada nunca se alteran automáticamente.
- La cota del terreno de PDF/PNG/SVG se obtiene ahora de **todos los puntos de PERFIL1**, como en MiniCAD, Plotly y DXF. Se ha corregido un error anterior del PDF que utilizaba únicamente cotas de sondeos.
- Se representa la posición de inicio de cada reconocimiento con una marca de boca y, en el caso del penetrómetro, un eje fino desde la cota de inicio hasta la profundidad final. La curva de golpes sigue comenzando en la **primera lectura real**, normalmente 0,20 m por debajo, sin inventar una lectura N20 a profundidad 0.
- Los puntos STA contribuyen a la geometría de la línea del terreno **sin símbolos ni etiquetas individuales**.
- La aplicación verifica diferencias de más de **0,001 m** entre la cota de los reconocimientos y la superficie interpolada de PERFIL1. Si hay discrepancia bloquea la representación para solicitar corrección en el archivo, sin mover el ensayo automáticamente.
- Se incluyen pruebas de regresión con terreno quebrado, con los Excel aportados por el usuario, la salida DXF y el componente MiniCAD en Chromium.

## Correccion v0.8.5: MiniCAD, guitarra y Unidades

- Corregido el **TypeError** al entrar en Interpretación: `modelo_minicad` recibia el argumento `dpsh` como posicional y ademas como keyword. Se ha eliminado esa duplicidad.
- La guitarra se organiza en **cuatro filas**: PK, cota del terreno, sondeos y penetrómetros. S-01 y P-01 a P-04 aparecen en sus PK exactos, mientras que STA solo afecta a la topografia y no se etiqueta como reconocimiento. Esta estructura es comun a Plotly, PDF, PNG, SVG y DXF.
- En **Unidades** se editan nombre y color por codigo BKFL. El selector de color incluye una muestra visual y su referencia hexadecimal. Los cambios recolorean las zonas asignadas, se conservan tras guardar/cargar JSON y no alteran los libros Excel originales.
- Retirada **Observaciones de la tabla Unidades** y añadida migración para abrir los antiguos JSON que la contengan. Esto no suprime las observaciones de campo existentes en los archivos de ensayo originales.
- 97 pruebas superadas; comprobacion integral con los cinco Excel del caso y lectura de entidades GUITARRA en el DXF. La prueba integrada completa en Streamlit Cloud/Mac queda pendiente.

## Limitaciones importantes

- Las escalas H/V aplican la exageracion en la visualizacion, pero en perfiles muy cortos y profundos la composicion de PDF/PNG/SVG se ajusta para ser legible. **Esa salida ajustada NO garantiza escala fisica de impresion** y se rotula expresamente. Para planos medidos, revise el DXF y su ventana de impresion.
- Los reconocimientos de PERFIL1 se ubican sobre un **perfil definido por PK**. Esta modalidad no crea coordenadas UTM reales: X se utiliza internamente como PK e Y=0. La entrada clasica con coordenadas XY se ha eliminado de la interfaz; el proyecto usa PK y cotas de PERFIL1.
- Si solo hay un sondeo litologico BKFL, las superficies fuera del sondeo siguen siendo interpretacion manual; no se infiere continuidad lateral.
- El terreno se interpola entre cotas de todos los puntos de PERFIL1 (incluido STA); no sustituye un modelo digital del terreno.
- El nivel freatico indicado como cero en libros de ensayo no se dibuja automaticamente como nivel de agua.
- Las etiquetas densas pueden solaparse al activar muchas capas y letras grandes. En tal caso desactive capas o reduzca la fuente.
- El DXF usa coordenadas de perfil X=PK, Y=cota, no coordenadas UTM. Las tramas HATCH de unidades geologicas dependen de la interpretacion que el usuario complete.
- La aplicacion aun requiere validacion funcional completa con navegador + Streamlit local y revision del perfil por profesional geotecnico.

## Novedades v0.8.4 - contactos hasta los bordes y penetraciones contenidas

- El MiniCAD permite terminar contactos en la topografia, en el borde izquierdo,
  el derecho y el limite inferior sin sobrepasarlos. Las guias azules aparecen
  durante el modo de dibujo y permiten captura exacta a cualquier nivel de zoom.
- Las curvas N20 se ajustan automaticamente al espacio disponible sin cambiar
  el PK del penetrómetro, la cota de inicio ni las lecturas. El ensayo extremo
  derecho puede dibujar su curva hacia la izquierda. La escala horizontal de
  **representacion de golpes** puede reducirse respecto a la solicitada para
  respetar los limites del perfil.
- Los valores observados siempre tienen prioridad en la captura magnetica.
- Consulte `CAMBIOS_v0.8.4.md` y ejecute `pytest -q` antes de uso.
