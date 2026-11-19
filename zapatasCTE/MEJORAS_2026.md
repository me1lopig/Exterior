# Mejoras ZapatasCTE · 19/11/2026

Este cambio parte **exclusivamente de la versión original restaurada**
(commit `b036d38d9203606718ba9a3f66313ec887f775ff`).
No sustituye componentes ni modifica por defecto los datos de un proyecto.

## Implementado

- **MOD-01:** entrada alternativa `gamma_sat` o `gamma'`, con `gamma'=gamma_sat-9.81` kN/m³.
  La opción inicial sigue siendo la entrada directa de `gamma'`.
- **MOD-02:** el mapa de calor B x L ofrece además presión bruta de hundimiento,
  presión bruta por asientos y presión bruta de servicio; las 9 variables
  utilizan valores ya obtenidos por el motor original.
- **MOD-03:** escala de azules más clara y texto oscuro para valores
  numéricos del mapa; se conserva la escala categórica de limitaciones.
- **PROP-02:** la ficha detalla `gamma_k` y el caso CTE F.16/F.17,
  distinguiendo los regímenes del nivel freático.
- **PROP-03:** `gamma_agua=9.81` kN/m³ compartido para tensiones iniciales,
  corrección F.17 y comprobación de gradiente. Esta modificación **sí puede
  afectar** a cálculos con flujo ascendente previamente efectuados con 10.0.
- **PROP-04:** aviso reforzado cuando el perfil de deformabilidad es
  insuficiente respecto a la profundidad activa determinada en el eje.
- **PROP-05:** sección y bulbo 2D de tensiones con isobaras 70, 50, 30,
  20, 10 y 5 % de la **presión neta de referencia**.
  Representación de estratos disponibles a partir de la base y NF.
  Modelo de Boussinesq para área finita B x L o banda infinita ideal.
  El modo corrida independiente no reutiliza longitudes arbitrarias de
  la comparación histórica de cálculo.

## PROP-06: gráfico de presiones para cimentaciones corridas

En **Resultados → Tabla general y curvas → Comparativa de zapatas corridas**,
debajo de la tabla se representan las presiones de hundimiento, asientos
y servicio frente a la anchura B, con selector **Netas / Brutas**.
El gráfico reutiliza `tabla_malla(corridas)` y no efectúa nuevos cálculos
geotécnicos. Si no existe presión de servicio válida, la curva muestra
un hueco, no un valor artificial igual a cero.

Como la tabla histórica, utiliza longitudes diferentes para los
dos cálculos: `L_asientos=100 m` y `L_hundimiento=1000 m`.
No representa una única cimentación corrida física, ni la solución de
banda infinita del nuevo gráfico de isobaras.

## Alcance y limitaciones

- Las isobaras son **incrementos de tensión vertical total** respecto a
  la carga neta. No se etiquetan como tensiones efectivas salvo que
  `Delta u=0`; no se calcula variación de presión intersticial.
- Se dibujan las capas con los nombres y límites del perfil de asientos
  medidos desde la **base**. No se infiere la estratigrafía sobre la base.
- La solución de tensiones supone **semiespacio elástico homogéneo**.
  Superponer capas o NF es informativo, sin cambiar las isobaras;
  no resuelve interacción entre cimentaciones ni asientos adicionales.
- La presión para la corrida ideal es editable. Su valor inicial es la
  presión de referencia de la zapata elegida, y **no constituye** un
  resultado de la comparativa de corridas (L=100 m / L=1000 m).
- La mayor profundidad de la figura no añade capas ni recalcula asientos
  fuera del perfil investigado.

## PROP-01: E.6, E.7 y E.8, pendiente de decisión técnica

Se ha mantenido **sin alterar** la conversión original de balasto:
para B=L se aplica E.6 o E.7 y para B<L se añade E.8.
Esta decisión causa un salto al pasar de L=B a L>B si se mantiene
un valor fijo de `k_s,BL`. Se recomienda contrastar el dominio de aplicación
de E.8 con el Anejo E del CTE y los resultados de referencia antes de
cambiar la formulación. No se introduce un tratamiento no literal de manera
silenciosa.

## Verificación

Pruebas nuevas en `tests/test_mejoras_2026.py`:
conversión y límites de gamma, F.16/F.17, los 9 campos del mapa,
comparación de influencias Boussinesq 1D/2D, simetría de isobaras y
límite de banda infinita. Se mantiene la batería original de pruebas;
ejecutar con `python -m unittest discover -s tests -v` desde `zapatasCTE`.

El programa continúa siendo una herramienta de predimensionamiento
sujeta a revisión geotécnica y validación profesional.

## PROP-13: compendio de fórmulas y memoria numérica de cálculo

La tercera subpestaña de Resultados se denomina **Metodología y formulaciones**.
Contiene cuatro apartados: **Hundimiento**, **Asientos (Steinbrenner)**,
**Servicio y balasto** y **Controles y advertencias**. Los factores
ampliables documentan las ecuaciones usadas por el motor de ZapatasCTE,
los límites de aplicación, las unidades y las referencias identificables.

La memoria numérica B × L se vincula a la geometría seleccionada en la
ficha del mapa. Incluye N, s, d, t, γR, γk, términos de cohesión,
sobrecarga, peso específico y talud, descarga de excavación, flexibilidad
de asiento, presiones y balasto. La función `elaborar_memoria` recomputa
esos términos y contrasta hundimiento y asiento con la salida original;
no altera las presiones ni interpreta la comparativa histórica de corridas
como una única geometría física. Si cambian las entradas, se avisa de que
los resultados visualizados corresponden al último cálculo guardado.

**Importante:** la memoria refleja el algoritmo implementado, incluido su
uso de γR como divisor de la suma total, y **no acredita una verificación
normativa integral** de todos los casos. Para asientos estratificados se
mantiene la aproximación de Steinbrenner por saltos en interfaces sin
solución rigurosa de continuidad multicapa. La transición E.6-E.8 de
balasto sigue pendiente de auditoría.

Pruebas específicas: `tests/test_memoria_calculo.py`, además del conjunto
original `python -m unittest discover -s tests -v`.

## PROP-07, PROP-08 y PROP-17: resultados separados por geometría

**Resultados** contiene tres subpestañas:
1. **Zapatas B × L**: mapa de calor de nueve variables, ficha individual,
   geometría, bulbo y asientos, tabla de resultados, curvas frente a L, balasto,
   sensibilidad al nivel freático y descargas CSV.
2. **Zapatas corridas · aproximación**: mapa de calor de **una columna**
   (mismas nueve variables), ficha específica B, tabla y gráfico de presiones
   netas/brutas frente a B, curvas de balasto, bulbo 2D para banda infinita,
   análisis de convergencia y comparativa de modelos.
3. **Metodología y formulaciones**: conserva PROP-13 y su memoria B × L.

El mapa de corridas y su ficha leen los resultados históricos existentes;
las celdas inválidas se representan como tales, sin inventar ceros.
La comparativa de corridas sigue usando **L_asientos=100 m** y
**L_hundimiento=1000 m**; el bulbo de banda infinita es independiente.

## PROP-09 y PROP-10: auditoría exploratoria y convergencia

Se incorpora un barrido de relaciones L/B = 2, 5, 10, 20, 50, 100,
200 y 500 usando zapatas rectangulares **finitas** y los mismos parámetros
geotécnicos. Se muestra el cambio relativo de la presión neta por asiento
entre las dos mayores longitudes y se exporta una tabla de resultados.
Un cambio menor del 1 % **no demuestra la convergencia matemática en
L infinito**, la adecuación del método estratificado, ni validez como ELS.

## PROP-11 y PROP-12: contraste limitado, no nuevo cálculo ELS de B × ∞

Se incorpora el **límite algebraico del término de hundimiento**
cuando B/L -> 0 dentro de la formulación ya implementada, y se compara
con la corrida histórica y una zapata rectangular finita L/B=200.
La solución límite de hundimiento se presenta sin presión por asientos
ni servicio: **no se ha implementado un modelo de asiento específico
de deformación plana validado**. PROP-11 permanece parcialmente pendiente
de un modelo documentado y pruebas de referencia para asientos B × ∞.
Las nuevas tablas y gráficas están etiquetadas como diagnósticas, no
sustituyen la comprobación de proyecto.

## PROP-14 a PROP-16: agua y balasto

- Vista preliminar dinámica de gamma_k con B seleccionable, que responde
  a NF, profundidad D, gamma', gamma_sat (si corresponde), gamma aparente
  y gradiente ascendente sin pulsar Calcular. No recalcula automáticamente
  los resultados globales, que conservan el control de obsolescencia.
- Curvas de ks,BL y Ksp30 para corridas frente a B y para B × L frente
  a L con ancho B fijo, con unidades MN/m3 y geometrías etiquetadas.
- Análisis paramétrico de nivel freático en la zapata B × L seleccionada:
  gamma_k, hundimiento neto y bruto frente a NF, manteniendo constantes
  los demás parámetros del modelo. No se alteran E y nu, no se acopla
  infiltración ni se incorpora asentamiento adicional; se exporta CSV.

## Verificación y alcance

Pruebas nuevas: `tests/test_propuestas_07_17.py` para mapas, casos sin
servicio, balasto, convergencia, límite de hundimiento, comparación
histórica, influencia de NF y flujo ascendente. Ejecutar toda la suite
con `python -m unittest discover -s tests -v`.

Las mejoras solo añaden visualización y diagnósticos basados en
funciones existentes. **No se modifica el motor principal de presiones
admisibles ni el algoritmo de asientos**. El desarrollo matemático y
la validación externa de asientos de banda infinita siguen pendientes.
