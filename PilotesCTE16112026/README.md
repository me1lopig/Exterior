# PilotesCTE · v3.0.0

**Cálculo analítico preliminar de resistencia axial de pilotes conforme a los modelos de referencia del CTE DB-SE-C.** Aplicación de código abierto en Python + Streamlit, reorganizada en módulos independientes.

> **Estado:** PROTOTIPO EN REVISIÓN. Motor sometido a pruebas automatizadas con ejemplos sintéticos, sin validación de campo ni homologación. La aplicación **no verifica por sí sola el dimensionamiento profesional** ni sustituye al estudio geotécnico, al proyecto estructural o a la revisión por especialista.

## Puesta en marcha

Requiere Python 3.11 o posterior.

```bash
python -m venv .venv
# En Windows: .venv\Scripts\activate
# En Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Se conserva un lanzador de compatibilidad:

```bash
streamlit run PilotesCTE_2.py
```

Pruebas desde la carpeta del proyecto:

```bash
python -m pytest -q
```

## Estructura

```text
PilotesCTE_v3/
  app.py                   # Streamlit: edición, visualización, matrices, descargas
  PilotesCTE_2.py           # Lanzador de compatibilidad
  src/pilotes_cte/
    __init__.py
    core.py                # Geometría, validadores, tensiones, punta, fuste y RN
    report.py              # Memoria Word con gráficas y auditoría
  tests/
    conftest.py
    test_motor.py
    test_informe.py
    test_interfaz_simulada.py
  requirements.txt
  README.md
  NOTAS_TECNICAS.md
```

## Entradas

En la **tabla de estratos**, definir nombre, espesor (m), γ seco y γ saturado (kN/m³), **tipo de suelo** (`Fino` / `Granular`), **condición de cálculo seleccionada para el estrato** (`Corto Plazo` / `Largo Plazo`), resistencia sin drenaje `cu` (kPa) y ángulo efectivo `φ` (°). Los suelos finos requieren `cu > 0` también cuando se elige largo plazo para poder evaluar la eventual regla 5.11 de capas inferiores.

La columna **Clase RN** se usa únicamente si se activa el rozamiento negativo: arcilla/limo blando (β=0,25), arena floja (β=0,10), arena densa (β=0,80); *No definida* obliga a completar la caracterización en los estratos afectados. Es una clasificación para la ecuación 5.4, **no** una correlación automática a partir de `cu` o `φ`.

En la barra lateral se configuran método constructivo, material, geometría, nivel freático opcional, zona de fuste nulo, matriz de longitudes y diámetros equivalentes, situación de dimensionado y coeficiente parcial. En metálicos hincados se puede seleccionar **circular macizo, tubular o perfil H**. El perfil H usa dimensiones reales fijas y por ello la matriz tiene una sola columna de diámetro equivalente.

Los datos iniciales de la pantalla son **sintéticos** y solo sirven para aprender el flujo de trabajo. No representan un terreno real.

## Qué ha cambiado en v3

| N.º seleccionado | Implementación | Alcance y cautelas |
|---|---|---|
| 1 | Límite de punta ante capas finas inferiores: `qp ≤ 6(1+H/D)² cu` (5.11). | Considera los estratos finos **reconocidos** bajo la punta y adopta el límite más restrictivo; no extrapola más allá del sondeo. |
| 5 | Límite del fuste drenado: **120 kPa granular**, **100 kPa fino**. | Tipo de suelo independiente de condición de cálculo, sin detectar tipo a partir de `cu=0`. |
| 6 | `φ` equivalente ponderado sobre **6D/3D** para punta drenada, `cu` equivalente sobre **2D/2D** para punta fina sin drenaje. | Para mezclas de unidades drenadas y finas sin drenaje en una misma ventana se adopta una **cota conservadora** y se emite aviso: criterio de ingeniería **no definido textualmente por el CTE**. |
| 7 | `γR` automático tabla 2.1: 3,0 a largo plazo/mezcla, 2,0 para modelo íntegramente corto plazo; extraordinaria 2,0. | El valor manual exige justificación escrita. No se generan automáticamente los dos escenarios de suelos finos. |
| 9 | Área de punta, área estructural y perímetro exterior diferenciados. | Circular macizo; tubo hincado con área de punta circunscrita (5.3.4.1.2); perfil H con `Ap=min(bh,1,5b²)` y perímetro `2(b+h)`. |
| 10 | Validación de espesores, γ, cu, φ, NaN/infinito, rangos geométricos, NF y bulbo. | Si una combinación requiere `L+3D` por debajo del reconocimiento se muestra **N/D** con causa. |
| 11 | **Rozamiento negativo opcional**, desactivado por defecto. | Ecuación 5.4: integrar `β·σ'v·p dz` en el intervalo declarado. El fuste positivo se excluye de dicho intervalo. La elección de la zona y del factor de acción debe justificarse externamente. |
| 12 | Memoria Word ampliada. | Incluye hipótesis, estratigrafía, tensiones, gráficas, matrices, auditoría por tramo, parámetros equivalentes, RN y limitaciones. |
| 13 | Arquitectura modular. | `core.py` sin Streamlit y `report.py` separado. |
| 14 | Tests de motor, documentos, límites y recorrido simulado de UI. | Ejecutables con pytest. No se ha hecho ensayo de campo ni validación independiente de proyecto. |
| 15 | README y notas técnicas actualizadas. | Documentan método, supuestos, pruebas y pendientes. |

## Criterios principales

- **F.30:** `qp = fp·σ'vp·Nq ≤ 20 MPa`, `fp=3` para hincados y `fp=2,5` para hormigonados in situ; `Nq=((1+senφ)/(1-senφ))·exp(π tanφ)`.
- **F.32:** `qp=9·cu` en suelo fino sin drenaje; `cu` representativo en **2D/2D**.
- **F.31:** `τf = σ'v·Kf·f·tanφ`, con los topes según terreno; integración exacta por tramos de tensión lineal, incluso al alcanzarse el tope.
- **F.33:** `τf=100·cu/(100+cu)` a corto plazo en finos; factor `0,8` con fuste de acero.
- **5.11:** tope de punta ante capa cohesiva más débil inferior.
- **5.2.2:** rozamiento negativo y elección explícita de β por clase de suelo.
- **Tabla 2.1:** `γR` según situación y método.

**Definición de D:** en secciones no circulares se usa el diámetro equivalente asociado al área efectiva de punta (misma área). Todas las profundidades se miden hacia abajo desde la cabeza en contacto con el terreno; el nivel freático, si existe, se expresa desde ese origen.

**Resistencia axial:** se presentan `Rpk`, `Rfk`, `Rck`, `Rcd = Rck/γR`, tope axial estructural simplificado y, si procede, `Fneg,k` y `Fneg,d`. La **capacidad de cabeza orientativa** descuenta el rozamiento negativo del mínimo entre `Rcd` y el tope axial simplificado. **No equivale a una comprobación completa `Ed≤Rd`** y no debe interpretarse como carga admisible de proyecto.

## Precauciones importantes

1. **Apoyo en roca deshabilitado:** no se implementan F.41–F.43.
2. **Corto/largo plazo:** se mantiene una condición por estrato para compatibilidad con el programa original. En suelos finos, el CTE exige examinar las dos situaciones que correspondan; **la app aún no compara automáticamente ambos escenarios**.
3. **Heterogeneidad:** el promedio de parámetros y los topes en transiciones son una convención documentada que debe revisar el proyectista; el CTE no formula explícitamente una única regla numérica para mezclas de suelos con formulaciones distintas.
4. **Rozamiento negativo:** la aplicación no predice asientos relativos, plano neutro ni profundidad de movilización; deben determinarse mediante evaluación externa. La acción negativa **no es resistencia positiva** y nunca se duplica en el mismo intervalo.
5. **Tope estructural:** la comparación axial con `σtope·Aestructural` es orientativa; no abarca flexocompresión, corrosión, pandeo, juntas ni otros estados límite.
6. **Fuera de alcance:** acciones Ed y combinaciones, asientos, grupo, arrancamiento, sismo, acciones laterales, interacción y deformaciones.
7. **Agua:** tensión intersticial hidrostática; no hay gradientes de flujo ni variaciones estacionales.
8. **Datos de ejemplo:** eliminar o sustituir antes de cualquier estudio real.

## Validaciones realizadas

- Casos de referencia calculados **independientemente** para integrales de tensión vertical, F.30, F.32, F.33, 5.11, límites F.31, geometría tubular/H y RN por tramos.
- Pruebas de borde con nivel freático ausente, en superficie, dentro de estrato, bajo sondeo y profundidad de consulta fuera del reconocimiento.
- Generación de memoria `.docx` con tablas y gráficos mediante `python-docx` y Matplotlib.
- Recorrido de interfaz mediante sustituto de Streamlit (smoke test simulado); **no es prueba de navegador real**.

Para saber el número exacto de pruebas superadas en un entorno, ejecute `python -m pytest -q`.

## Fuente normativa

[CTE DB-SE-C, documento oficial PDF (20 de diciembre de 2019)](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf), especialmente tabla 2.1, apartados 5.2.2, 5.3.4.1.2 y anexo F.2.1. Confirmar condiciones normativas del proyecto y vigencia antes de utilizarlo.
