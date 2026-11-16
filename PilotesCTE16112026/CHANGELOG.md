# Historial de cambios

## 3.0.0 — 16/11/2026

- Integrada la limitación de punta 5.11 para capas finas inferiores reconocidas.
- Separados `Tipo suelo` y `Condición` **para elegir el límite por fuste**; la comparación automática de escenarios sigue pendiente deliberadamente.
- Revisión de la homogeneización en 6D/3D y 2D/2D; aviso obligatorio en perfiles mixtos y criterio conservador auditado.
- Límite del fuste de 100 kPa en finos drenados y 120 kPa en granulares, por integración de tensiones.
- `γR` según tabla 2.1 y situación de dimensionado; override manual con justificación.
- Secciones circular maciza, tubular hincada y perfil H metálico con áreas de punta y estructural independientes.
- Validaciones fortalecidas para valores ausentes, NaN/infinito, magnitudes incompatibles y límites de investigación.
- Rozamiento negativo opcional con β por tipo específico, franja definida y no superposición con fuste positivo.
- Informe Word ampliado con gráficos independientes de Kaleido y auditoría detallada.
- Módulos `core.py` y `report.py` independientes de Streamlit.
- Suite automatizada de pruebas, documentación técnica y README actualizado.

## Respecto a 2.x

Se mantiene la elección de nivel freático con/sin NF y la prohibición de extrapolación bajo el sondeo. El archivo `PilotesCTE_2.py` se conserva únicamente como lanzador compatible: el motor ahora requiere la carpeta `src/` que se incluye en el ZIP.

**Fuera de alcance:** apoyo en roca, cálculo independiente automático de corto/largo plazo, comprobación completa Ed≤Rd, asientos, grupos, arrancamiento y cargas horizontales.
