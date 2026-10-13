# Auditoria defensiva de entradas

## Alcance

La auditoria comprueba las rutas de entrada del caso base y del barrido parametrico antes de ejecutar la busqueda de superficies. Los errores bloquean el calculo; los avisos permiten continuar, pero requieren revision del proyectista.

## Controles implantados

| Grupo | Condicion controlada | Respuesta |
|---|---|---|
| Geometria | `H <= 0`, pendiente fuera de 10-85 grados, NF fuera de 0-H | Error bloqueante |
| Numeros | `NaN` o infinito en geometria, suelos, calculo, espesores o barridos | Error bloqueante |
| Estratigrafia | Espesor superior o inferior no positivo | Error bloqueante |
| Estratigrafia | Suma de espesores menor que `H` | Error con cuantificacion del hueco |
| Estratigrafia | Suma de espesores mayor que `H` | Error con cuantificacion del solape |
| Estratigrafia | Contacto incoherente con el espesor superior | Error bloqueante |
| Estratigrafia | Capa menor que el 3 % de `H` | Aviso de sensibilidad a dovelas |
| Suelos | Nombre vacio, peso no positivo, `gamma_sat < gamma_seco`, `c' < 0`, `phi'` fuera de 0-50 grados | Error bloqueante |
| Suelos | `c'=0` y `phi'=0`, `c' > 100 kPa` o `phi' > 45 grados` | Aviso tecnico |
| Calculo | Dovelas, tolerancia, iteraciones, profundidad minima o FS objetivo fuera de dominio | Error bloqueante |
| Agua | NF en coronacion | Aviso sobre agua exterior/filtracion no modelada |
| Sensibilidad | Ninguna variable activa, limites iguales/invertidos o fuera de dominio | Error bloqueante |
| Sensibilidad | Mas de 100 combinaciones | Aviso de coste computacional |

## Comportamiento de la interfaz

- Los mensajes se muestran antes de los resultados.
- `Calcular caso base` se deshabilita mientras existan errores del caso.
- `Ejecutar sensibilidad` se deshabilita ante errores del caso o del barrido.
- Los resultados anteriores se conservan, pero se advierte cuando las entradas actuales han cambiado.
- El informe y los CSV se generan solo a partir del ultimo caso calculado correctamente.

## Riesgos residuales

- Los limites fisicos plausibles de `c'`, `phi'` y pesos unitarios dependen del material y del proyecto; los valores altos se avisan, no se sustituyen.
- La aplicacion no determina si corresponde un analisis drenado o no drenado.
- Una entrada numericamente valida puede seguir siendo geotecnicamente no representativa.
- La busqueda discreta no garantiza el minimo global y debe comprobarse con densidad y numero de dovelas.
- No se modelan agua exterior, filtracion no hidrostatica, sismo, sobrecargas, refuerzos ni fases constructivas.

## Regresion

La bateria incluida cubre calculo manual de Fellenius, convergencia de Bishop, efecto del agua, segundo estrato, geometria, sensibilidad, generacion DOCX y entradas adversariales.
