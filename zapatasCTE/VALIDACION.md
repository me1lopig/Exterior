# Registro de verificacion - v4

- Motor: Steinbrenner estratificado aproximado, corregido `1 - nu - 2 nu^2`.
- Bulbo de tensiones: formula cerrada rectangular de Boussinesq, contrastada numericamente con integracion independiente.
- Asientos por capas: calculo a presion neta escogida; suma igual al asiento total del motor.
- Presion neta/bruta: se separa la sobrecarga de contorno q0 y la tension preexistente de excavacion; calculo inicial auto o introduccion manual.
- Normativa de referencia: CTE DB-SE-C 2019, art. 4.4, para criterios de influencia de presiones.
- Regresiones: cinco casos publicados de la guia ministerial de Eurocodigo 7 reproducidos dentro de tolerancia de redondeo de 0.1 mm.
- 34 tests unitarios/funcionales superados en el entorno de desarrollo (ver registro y ejecutar `python -m unittest discover -s tests -v`).
- No se realizo prueba de interfaz con Streamlit en navegador (biblioteca no disponible en este entorno); se realizo smoke test logico con doble de Streamlit.
- **NO** se acredita cumplimiento normativo global: aun faltan acciones inclinadas/excentricas, modelos avanzados de asiento, rigidez de zapata, solape de tensiones, consolidacion y comprobacion externa de seguridad de caso real.

Detalles de ecuaciones, fuentes y supuestos en `METODOLOGIA_ASIENTOS.md`.
