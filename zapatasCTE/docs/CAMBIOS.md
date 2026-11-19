# Cambios implementados en esta versión autónoma

## Balasto v4.1 integrado

- Selector manual de tipo de suelo: únicamente Cohesivo o Granular.
- Balasto real `ks,BL` calculado mediante presión neta y asiento.
- `Ksp30` equivalente, con referencia a E.6 (cohesivos), E.7 (granulares) y E.8 (rectangulares).
- Criterio `literal_cte` predeterminado; criterio `continuo` opcional, explícitamente NO literal.
- Factores de escala, factores geométricos, `ks,B` intermedio, unidades y advertencias visibles y exportables.
- Comparación directa entre ambos criterios para cada zapata.
- Validación estricta de datos numéricos, incluido rechazo de valores booleanos.

## Mapas v4.2 integrados

- Nueve variables representadas: servicio/hundimiento/asientos, neto/bruto (6); ks,BL (1); Ksp30 (1); criterio gobernante (1).
- Desplegable de geometría y selección sobre el mapa.
- Hover con todas las presiones netas y brutas, ambos coeficientes de balasto y dimensiones.
- Ficha simultánea de tres pares neto/bruto, sin cambiar de gráfico.
- Exportación de malla CSV y ficha JSON con advertencias.

## Reconstrucción completa

- Nueva aplicación Streamlit local autónoma (no depende de ejecutar un generador que descargue GitHub).
- Motor de hundimiento, asientos, balasto, Boussinesq, barrido paramétrico, curvas y vista corrida histórica.
- Huella SHA-256 de entradas y aviso de cálculos desactualizados.
- Datos sintéticos de prueba, validación y documentación.

No se ha editado ni subido nada al repositorio GitHub original.
