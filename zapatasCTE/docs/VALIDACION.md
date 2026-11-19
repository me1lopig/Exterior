# Auditoría de entrega v4.2 reconstruida

- **41 pruebas superadas** (2026-11-19, Python 3.13, NumPy 2.3.5, pandas 2.2.3, Plotly 6.5.2, pytest 9.0.2).
- Incluye 500 escenarios aleatorios de inversión de factores E.6/E.7/E.8 por dos criterios, pruebas de continuidad/discontinuidad, unidades, tensiones, asientos, hundimiento, perfiles, errores y exports.
- `tests/test_smoke_interfaz.py`: recorrido lógico de app.py mediante una **simulación de Streamlit**, sin abrir navegador.
- Referencias sintéticas reproducidas: zapata B=2 m, L=3 m, q_neta=0,2 MPa, asiento para E=20 MPa y nu=.30 (0–10 m) = 21,75765 mm; perfil E=15/1200 MPa (0–2,5 m / 2,5–10 m) = 19,17689 mm.
- **No ejecutado**: Streamlit real (no está instalado en este entorno), render en navegador, comparación automática con fuente original íntegra de GitHub ni con el Excel original, revisión y firma de geotécnico sobre caso real.
- **No certificado**: cumplimiento completo del CTE DB-SE-C, equivalencia exacta a la aplicación v4 original o validez en proyectos reales.

La comparación funcional con la fuente original es aproximada porque el ZIP de GitHub no pudo descargarse en este entorno. El paquete contiene código real, de nueva implementación, y no únicamente un generador o parches.
