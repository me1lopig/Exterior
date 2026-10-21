# Cambios GeoCorrelaciones v0.7

- Se conservan exactamente las siete pestañas de v0.6; no se recuperan Cc, Cs, K0 ni la pestaña OCR.
- Nueva sección 'Webb (1969/1970)' dentro de E-Arenas con tres relaciones por tipo de material, N bruto independiente y resultado en MPa.
- Nueva sección 'Stroud y Butler (1975)' dentro de E-Arcillas, **M edométrico y mv** en vez de un falso Young; se requieren N bruto, IP, f2 aportado por usuario y confirmación de procedencia.
- Documentación fuente, fórmulas y condiciones en cada resultado; fuentes secundarias marcadas como tales.
- Bloqueo de extrapolación fuera de dominios operativos. No se interpolan coeficientes f2 a partir de la figura histórica.
- Se conservan las correcciones SPT anteriores y la presentación simple de avisos, sin nuevos mensajes repetitivos.
- Nuevos archivos `calculos/webb_stroud.py`, `tests/test_webb_stroud_v07.py`, `tests/test_app_v07_routes.py` y `VALIDACION_WEBB_STROUD_v07.md`.
- 103 pruebas de código y regresión superadas; Streamlit gráfico real no ejecutado (paquete no instalado en el entorno).
