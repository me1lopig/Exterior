# Zapatas B × L — aplicación Streamlit (v3)

**Estado:** prototipo técnico, con motor numérico contrastado mediante pruebas de regresión y casos controlados. **No es una herramienta certificada de cálculo geotécnico ni acredita cumplimiento integral del CTE DB-SE-C.** Deben verificarse las hipótesis y revisarse los resultados por el técnico responsable.

## Funcionalidades

La aplicación amplía la hoja `SUELOS` del Excel original a una **malla de zapatas rectangulares** de anchura `B` y longitud `L`. Las cuadradas son `B=L`. Se introducen `Bmin`, `Bmax`, `incrB`, `Lmin`, `Lmax`, `incrL`, y se generan únicamente combinaciones `0<B<=L` (hasta 2.500). Si un máximo no es alcanzable con el incremento, no se fuerza una última separación irregular.

Pestañas:

- **Datos iniciales:** identificación del caso, barrido geométrico y restricción `B<=L`.
- **Hundimiento:** parámetros resistentes, agua, profundidad, sobrecargas, talud y situación de seguridad. Se ha eliminado la opción circular parcialmente implementada de la v1: este producto es rectangular/cuadrado, más una comparación de corrida.
- **Asientos:** hasta tantas capas como necesite el usuario, con `z` desde la base, `E` y `nu`; dos métodos de asiento en el centro, selector de balasto **Cohesivo / Granular**.
- **Resultados:** botón **Calcular** (ejecución sólo bajo demanda), mapa de calor B×L para presiones por hundimiento, asientos, servicio, módulos de balasto y limitación; ficha de geometría; tabla conjunta completa; curvas a B fijo; comparación con la aproximación de zapata corrida; descarga CSV. Se ha suprimido la banda de cuatro indicadores superiores y el título redundante.

### Cambios de la versión 3

- **Calcular** ejecuta la malla y guarda los últimos resultados en la sesión. Al cambiar entradas, los resultados conservados se identifican como **pendientes de actualizar** y se suspende la exportación hasta recalcular.
- En Hundimiento se presenta **q₀ = γ_sobrecarga × h_sobrecarga** (kN/m² = kPa), que se actualiza al cambiar los campos sin ejecutar el cálculo general. Ejemplo `18 × 0,50 = 9 kN/m²`. Si se desactiva la sobrecarga, q₀ se muestra igual a cero.
- Mapas con escala **azul claro → azul oscuro** y número de cada cálculo **dentro de la celda**, con tres decimales para presiones y dos para balasto, y gris para B>L. El mapa del estado límite conserva una paleta categórica.
- La corrección rectangular de balasto E.8 **sólo se aplica a B<L**; en B=L se usan directamente las ecuaciones para la zapata cuadrada E.6/E.7. Esto evita multiplicar por 1,5 el módulo de una zapata que ya es cuadrada.
- Para **sin drenaje** se adopta `N_c = 5,14` según F.1.1.2; el módulo legado conserva las expresiones de la hoja para las pruebas históricas.
- En perfil lineal `cu(z)`, el dato `cu_inicial` se asocia a la profundidad `z0` elegida y la limitación `2*c0` se refiere correctamente al valor **extrapolado a la superficie**, como en F.1.1.2.
- Nuevas alertas para nivel freático, q₀ efectivo/total y heterogeneidad del perfil elástico.


En la ficha se puede seleccionar la geometría mediante un desplegable y, en entornos Streamlit compatibles, mediante el gráfico interactivo.

## Instalación

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux y macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Los tests del motor sólo requieren las librerías numéricas de `requirements.txt` y pueden ejecutarse sin Streamlit mediante `python -m unittest discover -s tests -v`.

## Cálculos

**Hundimiento:** ecuación 4.8 CTE DB-SE-C y factores de forma F.3-F.5. En cálculo sin drenaje se usa `phi=0`, y para talud sin drenaje la corrección `-2 beta cu` (beta en radianes). Se conserva la división de la presión característica **bruta** por `gamma_R` utilizada en la hoja de partida. En situaciones sin drenaje el CTE permite también otras formas de aplicar `gamma_R` (Anejo F.1.1.2.5); no se implementan en esta versión.

**Asientos elásticos**, en cm, por capas con fórmula de Steinbrenner:

- **Superposición 4 × (B/2 × L/2)** (por defecto): `s_centro = 4 s_esquina(B/2,L/2)`.
- **Aproximación 2 × (B × L)** (compatibilidad histórica): `s_centro = 2 s_esquina(B,L)`.

**Presiones comparables:** se distinguen netas y brutas. El cálculo de asientos representa respuesta al **incremento de presión neta**. Por tanto:

```
q0 = sobrecarga al nivel de la base (MPa)
q_hundimiento_bruta_d = q_hundimiento_bruta_k / gamma_R
q_hundimiento_neta_d = q_hundimiento_bruta_d - q0
q_asientos_neta = asiento_admisible / asiento_calculado(q_neta=1 MPa)
q_servicio_neta = min(q_hundimiento_neta_d, q_asientos_neta)
q_servicio_bruta = q_servicio_neta + q0
```

Si el margen neto por hundimiento es menor o igual que cero, se marca el caso **No válido**, sin inventar una presión de servicio positiva. Las presiones se expresan en MPa.

**Balasto:** `k_s,BL = q_asientos_neta / (s_adm / 100)` en MN/m³; se convierte a módulo equivalente de placa de 30 cm con las ecuaciones **E.6/E.7 (material)** para cuadradas (`B=L`), y **E.8** antes de E.6/E.7 para rectangulares propiamente dichas (`B<L`). Es una conversión orientativa especialmente limitada en perfiles estratificados.

**Corrida histórica, sin entrada del usuario:** el Excel y la primera app empleaban internamente **L_hundimiento = 1000 m** y **L_asientos = 100 m**. Se preservan esos dos valores en la vista separada de **comparación corrida**, no como una geometría B×L única: la tabla de corridas indica las dos longitudes. Para una zapata rectangular real, hundimiento y asiento usan siempre la misma longitud L.

## Validaciones y avisos

- Entradas positivas y finitas, rango geométrico, malla `B<=L`.
- Estratos sin huecos ni solapes, primer estrato bajo base `z=0`, `E>0`, `0<=nu<0,5`.
- Obligatoriedad de `phi=0` en sin drenaje.
- Bloqueo de factores de profundidad para `D<2 m` y proximidad a talud.
- Advertencia sobre insuficiencia de profundidad elástica respecto a `2B` (indicio, **no** criterio normativo concluyente).
- Avisos sobre consolidación no calculada, acciones inclinadas y excéntricas, influencia del nivel freático, incertidumbre del balasto estratificado, y otras limitaciones.

## Limitaciones principales

No considera fuerzas horizontales ni momentos, deslizamiento, vuelco, capacidad estructural, asiento diferencial, consolidación ni asientos secundarios. Las dimensiones `B,L` deben ser equivalentes calculadas previamente cuando haya excentricidades. La interpretación de un perfil elástico finito exige revisión profesional. El límite de 5 cm es un **dato predeterminado de ejemplo**, no un valor general exigido por el CTE. El campo `tipo de suelo para balasto` no modifica por sí mismo la resistencia drenada/sin drenaje. El procedimiento de Steinbrenner por diferencias de estrato aproxima la deformación pero no impone rigurosamente la continuidad de esfuerzos y deformaciones en interfaces entre materiales de distinta rigidez. En cálculo drenado, q₀ y los pesos efectivos requieren considerar las presiones intersticiales; para cálculo sin drenaje se emplean las tensiones totales. Cuando el nivel freático afecta al estrato, verifique que `γ'` es peso específico **sumergido**, no aparente.

La relación `profundidad de perfil >= 2B` es solamente un indicador visual, no la comprobación normativa completa de la zona de influencia de tensiones. Tampoco se valida la permanencia de sobrecargas superiores ni el régimen real de presiones intersticiales.

## Organización

- `app.py`: interfaz Streamlit y resultados.
- `modelos/`: validación de parámetros y geometrías.
- `calculos/`: capacidad portante, asientos, presión neta/bruta y balasto.
- `visualizacion/`: mapas de calor, curvas y ficha gráfica.
- `utiles/`: tablas y exportación.
- `tests/`: regresión original + ensayos de geometría, presiones, balasto, avisos y smoke test con simulador de Streamlit.
- `VALIDACION.md`: cobertura, trazabilidad y pruebas.

## Fuente normativa

[CTE DB-SE-C — Documento Básico Seguridad Estructural: Cimientos (20/12/2019)](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf), apartados 4.3, 4.4, Anejo E.5 y Anejo F.1.1.
