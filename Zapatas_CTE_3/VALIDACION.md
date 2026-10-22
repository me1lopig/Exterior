# Trazabilidad y validación — versión 2

## Estado

**Prototipo numérico contrastado**, no certificado. La validación comprende pruebas unitarias, pruebas de comportamiento físico limitadas y regresión con celdas de la hoja `SUELOS` para las funciones originales. No incluye revisión geotécnica por tercera parte ni funcionamiento comprobado en un navegador con Streamlit real.

## Matriz resumida de trazabilidad

| Función de origen / normativa | Implementación | Prueba / estado |
|---|---|---|
| Hundimiento original, cuadrada | `calculos.capacidad_portante.calcular_presiones_hundimiento` (legado) | `test_regresion_excel` con valores guardados; pasa |
| Hundimiento rectangular, 4.8 y F.3–F.5 CTE | `calculos.capacidad_portante.calcular_hundimiento_rectangular` | Factores B/L y control caso cuadrado; pasa; ver limitaciones |
| `GoalSeek` asentamiento central, Excel | `calculos.asientos` con método `excel` | Regresión con VBA para cinco anchos; pasa |
| Asiento central por cuatro cuadrantes | `calculos.asientos` con `superposicion` | Monotonía en estratos y convergencia en semiespacio homogéneo; pasa |
| Presiones brutas/netas | `calculos.malla.calcular_geometria` | Identidades `bruta = neta + q0`; pasa |
| Balasto E.6, E.7 y E.8 | `calculos.servicio.convertir_ksbl_a_ksp30` | Cohesivo/granular y B×L; pasa |
| Malla dimensiones | `modelos.geometrias.generar_geometrias` | 26 combinaciones en ejemplo, sin B>L; pasa |
| Visualización y tabla | `visualizacion.graficos_malla`, `utiles.tablas_malla` | Integridad objetos Plotly y filas; pasa |
| Construcción interfaz por defecto | `app.py` | Smoke con Streamlit simulado, sin browser; pasa |

## Supuestos y diferencias frente al Excel

1. La malla rectangular y el modo por defecto de cuatro cuadrantes amplían y corrigen la interpretación del original. Comparar con valores Excel requiere escoger `Aproximación 2 × (B × L)`.
2. A diferencia de la hoja de partida, el límite de servicio se obtiene al comparar magnitudes **netas**; la salida incluye también las brutas. Es un cambio consciente de criterio y puede cambiar las cifras.
3. Se fuerzan `phi=0` en sin drenaje y restricciones a factores de profundidad (`D>=2 m`, sin talud), de acuerdo con restricciones del Anejo F.
4. La comparación corrida conserva las **dos longitudes originales** `1000 m (hundimiento)` y `100 m (asientos)` sin permitir edición. **No** se considera equivalente a una zapata física de longitud única, de ahí su tabla independiente.
5. No se aplica automáticamente cambio de cu o E con nivel freático más allá de las fórmulas heredadas: el técnico debe aportar parámetros coherentes.

## PENDIENTE / exclusiones

- Ensayo de funcionamiento interactivo y renderizado en navegador Streamlit real.
- Validación integral de la norma, acciones inclinadas, excentricidades y estabilidad global.
- Modelado del asiento por consolidación y asientos diferenciales.
- Verificación completa de las tensiones inducidas/profundidad de influencia según CTE.
- Zapatas circulares (no implementadas en esta v2).
- Módulos avanzados de acciones, análisis de sensibilidad y PDF (fuera del alcance acordado para v2).

## Ejecutar las pruebas

```bash
python -m unittest discover -s tests -v
```

Al preparar esta entrega se completaron **19 pruebas** sin errores en el entorno disponible. El test de interfaz simula Streamlit; no implica que se haya abierto la aplicación en un navegador.
