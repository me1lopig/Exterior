# Dossier de validacion v0.6: Wolff/Peck, Shioi-Fukui y D'Appolonia

**Fecha:** 21/10/2026. No equiparar prueba aritmetica a validacion de campo. Las ecuaciones japonesas son reconstrucciones basadas en manual especializado; el original (Shioi y Fukui, 1982, ESOPT II, pp. 159-164) no se ha cotejado integramente.

## Wolff (1989) / Peck-Hanson-Thornburn (1974)

- Relacion `phi'=27.1+0.3*(N1)60-0.00054*((N1)60)^2`, grados.
- Entrada: `(N1)60`, corregido en energia y confinamiento. No usar `N60` directo.
- Fuente reproducible y dominio sugerido 0-60: https://groundhog.readthedocs.io/en/main/site_investigation/spt_correlations.html
- Se acepta para arenas limpias fina/media y gruesa por criterio operativo del programa.
- Caso de prueba `(N1)60=20` -> `32.884 grados`; `(N1)60=40` -> `38.236 grados`. Con `(N1)60>60` no se devuelve valor.

## Shioi y Fukui (1982), dos variantes

- Carreteras y puentes: `phi'=15+sqrt(18*N70)` (grados).
- Ferrocarriles: `phi'=27+0.36*N70` (grados).
- La fuente emplea SPT a eficiencia de energia **70%**: `N70=N60*60/70` con los mismos factores instrumentales. NO emplear `(N1)60` ni `CN`. En la GUI se exhibe el valor transformado.
- Fuente: Manual especializado ZSoil 2025, tabla 3.10: https://www.zsoil.com/zsoil_manual/Rep-HS-model.pdf
- Registro de la obra original, no texto cotejado: https://eurekamag.com/research/091/197/091197826.php
- Se mantiene distincion de referencia: estos metodos usan fuente tecnica secundaria; no se les atribuye condicion normativa.
- Restricciones **operativas**: puentes `0<N70<=50`, limitando phi a 45 grados sin truncar resultados; ferrocarriles `0<N70<=60` para evitar extrapolaciones arbitrarias. No son rangos calibrados documentados de los autores.
- Caso numerico: para `Ncampo=20`, ER=70% y factores instrumentales 1, se obtiene `N70=20`; por tanto `phi_puentes=15+sqrt(360)=33.97366596 grados`, `phi_ferrocarriles=34.2 grados`.

## D'Appolonia-D'Appolonia-Brissette (1970), modulo M

- Es un **modulo M para el metodo de calculo de asientos**, no un Young E obtenido directamente.
- `M_NC (tsf) = 196+7.9*N_medio_bruto`; `M_precargada (tsf)=416+10.9*N_medio_bruto`.
- `N_medio_bruto`: valor medio **sin correccion** del ensayo SPT desde la base de la zapata hasta una profundidad B adicional; `B` es el ancho de cimentacion.
- Conversion: `1 tsf = 0.09576051796 MPa` (short ton-force / square foot). No aplicar el factor kgf/cm2 = 0.0980665 MPa, pues seria **otra unidad**.
- Referencias del metodo y ecuaciones: FHWA-HRT-15-080, seccion D'Appolonia https://www.fhwa.dot.gov/publications/research/infrastructure/structures/bridge/15080/004.cfm ; recopilacion de Paikowsky (ecs. 2.43 y 2.44), reproducida en https://paperzz.com/doc/6951188/settlement-of-shallow-foundations-on-granular-soils y manual US DOT https://rosap.ntl.bts.gov/view/dot/20506/dot_20506_DS1.pdf .
- En una recopilacion espanola se citan otras expresiones E en kgf/cm2 (215+10.6 N, 540+13.5 N). **No se sustituyen** por las expresiones de M ni se mezclan con ellas sin justificar el procedimiento. Esta version solo implementa M identificado en la bibliografia del metodo de asientos.
- Caso contraste: `N_medio=11` -> `M_NC=282.9 tsf = 27.0916 MPa`, muy proximo al valor grafico `285 tsf` de un ejemplo publicado en recopilacion del metodo (<1% de discrepancia, al tratarse de lectura de grafico).
- Si no se conoce la historia tensional o el promedio bruto, no se calcula. `0<N<=60` es restriccion operativa declarada.

## Comprobaciones

- Se han ejecutado tests de formulas, normalizaciones, dominios, unidades, incompatibilidad de material/historia, diferencias entre `N70` y `(N1)60`, limites, fuente y ruta simulada de entrada de datos.
- 84 pruebas en total usando `python -m unittest discover -s tests -q`.
- No se ha ejecutado navegador/Streamlit real ni se han contrastado muestras de campo del usuario.
