# GeoPerfil 2D v0.8.5 — Mantenimiento de interfaz y resultados

## 1. Bloqueo de Interpretacion corregido

`paginas/vistas.py`: `modelo_minicad(...)` recibia `dpsh` dos veces, una como sexto argumento posicional y otra como keyword. Python lanzaba `TypeError: modelo_minicad() got multiple values for argument 'dpsh'` al abrir Interpretacion con una campana valida. Se ha eliminado la keyword duplicada y se añadio una prueba de humo que construye el modelo del componente con los mismos argumentos de la interfaz.

## 2. Guitarra completa

Cuatro filas compartidas por Plotly, PDF, PNG, SVG y DXF: PK, cota del terreno, Sondeos y Penetrometros. Reconocimientos en su PK real; STA permanece como punto topografico sin etiqueta de trabajo de campo. En la campaña aportada aparecen S-01 y P-01, P-02, P-03 y P-04.

## 3. Unidades editables

La pestaña Unidades ofrece nombre editable y selector de color con swatch/hex visible. Los codigos de estrato permanecen constantes, se actualizan los colores de las zonas previamente clasificadas y se guarda la preferencia en el JSON. Los originales BKFL se conservan como fuente no modificada. Las entradas vacias y colores invalidos se rechazan sin alterar el estado.

## 4. Campo retirado

Se elimina `Observaciones` solamente del catalogo de Unidades; los proyectos antiguos se migran automaticamente en la carga JSON. No se eliminan datos brutos de observaciones del campo y laboratorio.

## 5. Validacion

- 97 pruebas automatizadas aprobadas (88 anteriores y 9 nuevas), incluidas pruebas Playwright/Chromium del MiniCAD.
- Comprobacion integral con cinco libros Excel aportados: 1 sondeo, 4 penetraciones, 6 puntos de terreno, 6 SPT; 5 etiquetas de trabajos de campo en la guitarra y ninguna STA.
- PNG/PDF/SVG generados; DXF reabierto con `ezdxf`, con la guitarra editable y cuatro filas.
- Prueba de guardado/recuperacion JSON de nombres y colores.
- **Pendiente**: ejecucion real de Streamlit en Mac/Cloud y apertura del DXF en AutoCAD. Streamlit no estaba instalado en este entorno y la descarga de dependencias estaba bloqueada por DNS.

## Como probar en Streamlit Cloud

Publique los archivos de esta revision (no mezcle archivos de diferentes ZIP) y reinicie la aplicacion; suba los cinco libros, visite Interpretacion, Unidades y Perfil y descargue un proyecto JSON para comprobar la persistencia.
