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
