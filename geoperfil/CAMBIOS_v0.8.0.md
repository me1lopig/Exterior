# Cambios v0.8.0 respecto a v0.7.0

1. `servicios/importar_campana.py`: nuevo adaptador multifichero con identificacion por encabezados, cota/PK, validacion y auditoria.
2. `calculos/terreno.py`: construccion del terreno a partir de todas las cotas de los reconocimientos, excluyendo origen STA.
3. `modelos/dominio.py` y `servicios/persistencia.py`: persistencia de capas, textos, escala de penetracion y tablas adicionales.
4. `paginas/vistas.py`: interfaz de carga/validacion/aplicacion, datos complementarios, capas y controles, exportaciones coherentes. La importacion clasica sigue disponible.
5. `componentes/minicad.py`, `calculos/zonas.py` y `calculos/presentacion.py`: dominio/topografia y guitarra compatibles con campana por PK.
6. `visualizacion/perfil_plotly.py`: etiquetas SPT, muestras y laboratorio opcionales.
7. `servicios/exportacion.py`: SPT/muestras/laboratorio en PDF/PNG/SVG y capas editables de DXF, con aviso explicito si la vista imprimible se adapta por legibilidad.
8. `tests/test_campana_multifichero_v08.py`: 16 pruebas nuevas y ejemplos sinteticos en cinco libros.

Validaciones: 60 tests de suite completa superados y exportacion-integracion verificada con los cinco originales aportados. Falta smoke test Streamlit real en el ordenador del usuario y comprobacion en AutoCAD.
