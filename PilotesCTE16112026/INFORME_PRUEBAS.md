# Registro de validación computacional

- Fecha de ejecución: 16/11/2026.
- Python: 3.13.5.
- Comando: `python -m pytest -q`.
- Resultado: **59 pruebas superadas**.
- `python -m compileall -q app.py PilotesCTE_2.py src`: correcto.
- Memoria Word de ejemplo sintético: generada, convertida a 4 páginas y revisada visualmente sin recortes evidentes.
- Recorrido simulado de Streamlit: realizado con doble de métodos; permite comprobar que el flujo por defecto calcula y genera el Word.
- **Limitación:** el entorno no dispone de Streamlit y no permitió instalarlo desde el índice de paquetes; no se ejecutó prueba de navegador real.
- **Limitación:** sin contraste independiente con campaña de campo ni casos de proyecto revisados por terceros.

Pruebas incluidas: tensión total y efectiva, agua y sondeo, fórmula F.30, F.32, F.33, tope F.31, 5.11, equivalencias de sección H y tubular, rozamiento negativo por tramos, coeficiente de resistencia, estados N/D, valores extremos, generación Word y regresiones sintéticas con soluciones manuales.

Recomendación para entrega a explotación: instalar dependencias en entorno del usuario, ejecutar `pytest`, iniciar `streamlit run app.py`, comprobar interacción real del editor y el informe, y contrastar con un caso real supervisado por técnico responsable antes de su adopción en proyecto.
