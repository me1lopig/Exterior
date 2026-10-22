# Trazabilidad y validación — versión 3

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
| Balasto E.6, E.7 y E.8 | `calculos.servicio.convertir_ksbl_a_ksp30` | Cohesivo/granular, caso cuadrado sin E.8 y B<L con E.8; pasa |
| Malla dimensiones | `modelos.geometrias.generar_geometrias` | 26 combinaciones en ejemplo, sin B>L; pasa |
| Visualización y tabla | `visualizacion.graficos_malla`, `utiles.tablas_malla` | Escala azul, 3 decimales en presión, celda B>L sin cálculo, hover detallado; pasa. Mapa renderizado en navegador aislado y revisado visualmente |
| Flujo del botón Calcular y aviso por cambios | `app.py` | Smoke con Streamlit simulado, sin Streamlit real; prueba sin cálculo, pulsación, persistencia y obsolescencia; pasa |
| Sobrecarga q₀ | `app.py`, `calculos.capacidad_portante` | γ × h = 18 × 0,50 = 9 kPa; interruptor en cero; pasa |
| Cu en perfil lineal | `calculos.capacidad_portante._cohesion_representativa` | Referencia z0 y límite 2·c0 superficial; pasa |
| Sin drenaje F.1.1.2 | `calcular_hundimiento_rectangular` | Nq=1, Nc=5,14, Ngamma=0 y talud −2β·cu; pasa |

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
- Zapatas circulares (no implementadas en esta v3).
- Módulos avanzados de acciones, análisis de sensibilidad y PDF (fuera del alcance acordado para v3).

## Ejecutar las pruebas

```bash
python -m unittest discover -s tests -v
```

Al preparar esta entrega se completaron **25 pruebas** sin errores, incluidos 6 contrastes nuevos. El test de interfaz simula Streamlit. Se generó y revisó una captura de un mapa de calor Plotly en Chromium, pero **no** se pudo instalar ni ejecutar Streamlit real debido a que el entorno bloquea las descargas de paquetes. Por tanto, no se afirma validación visual de todas las pestañas ni interacción real de selección en Streamlit.

## Contraste normativo puntual, 22/10/2026

Documento consultado: https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf (edición 20/12/2019). Se contrastaron visualmente las páginas SE-C-130, SE-C-131, SE-C-135 y SE-C-136 del PDF oficial.

- **Hundimiento:** 4.8 y F.3-F.5: factores geométricos rectangulares correctos; F.13-F.15: `N_q`, `N_c`, `N_γ` en drenado correctos. F.1.1.2: sin drenaje `N_c=5,14`, `N_q=1`, `N_γ=0`; corrección de talud `−2βcu` aplicada antes de dividir por `γR` como convención del modelo.
- **Niveles de q₀:** resultado visible γ·h en kPa. El modelo NO determina por sí mismo las presiones intersticiales bajo la sobrecarga: q₀ ha de representar presión efectiva en drenado y total en no drenado. No incorporar carga de otra naturaleza silenciosamente.
- **Balasto:** E.6 y E.7 confirman dos reglas diferentes para cohesivo y granular; E.8 confirma factor geométrico de rectangulares. Su aplicación literal a B=L sería incoherente con el valor de k_sB ya definido para una zapata cuadrada en E.6/E.7; se ha implementado E.6/E.7 directamente en B=L y E.8 sólo en B<L, dejando esta decisión técnica explícita.
- **Asientos:** la fórmula de Steinbrenner es un modelo elástico aproximado, no una solución completa por capas adheridas; no sustituye consolidación, asiento diferencial ni comprobación completa de profundidad de influencia. La comparación con Excel valida equivalencia en el modo histórico, no demuestra exactitud física.

**Importante:** en condición no drenada el CTE F.1.1.2 también permite que `γR` afecte sólo al término cohesivo; esta alternativa no se ha activado porque rompería la convención conservadora de división por `γR` del total usada en la hoja original. Debe validarse la elección con los criterios del proyecto antes de uso profesional.
