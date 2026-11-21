# Auditoria defensiva de entradas

## Alcance

La auditoria comprueba las rutas de entrada del caso base y del barrido parametrico antes de ejecutar la busqueda de superficies. Los errores bloquean el calculo; los avisos permiten continuar, pero requieren revision del proyectista.

## Controles implantados

| Grupo | Condicion controlada | Respuesta |
|---|---|---|
| Geometria | `H <= 0`, pendiente fuera de 10-85 grados o profundidad del modelo menor que H | Error bloqueante |
| Agua | Profundidad del NF negativa o mayor que la profundidad del modelo | Error bloqueante |
| Numeros | `NaN` o infinito en geometria, suelos, calculo, espesores o barridos | Error bloqueante |
| Estratigrafia | Tabla sin capas o espesor de cualquier capa no positivo | Error bloqueante |
| Estratigrafia | Suma de espesores menor que la profundidad del modelo | Error con cuantificacion de la cobertura restante |
| Estratigrafia | Suma de espesores igual o mayor que la profundidad del modelo | Entrada valida |
| Estratigrafia | Capa menor que el 3 % de `H` | Aviso de sensibilidad a dovelas |
| Suelos | Nombre vacio, peso no positivo, `gamma_sat < gamma_seco`, `c' < 0`, `phi'` fuera de 0-50 grados | Error bloqueante |
| Suelos | `c'=0` y `phi'=0`, `c' > 100 kPa` o `phi' > 45 grados` | Aviso tecnico |
| Suelos | Pesos unitarios fuera de intervalos orientativos o `gamma_sat <= gamma_agua` | Aviso de unidades o material no habitual |
| Calculo | Dovelas, tolerancia, iteraciones, profundidad minima o FS objetivo fuera de dominio | Error bloqueante |
| Agua | Profundidad NF igual a cero, es decir, NF en coronacion | Aviso sobre agua exterior/filtracion no modelada |
| Sensibilidad | Ninguna variable activa, limites iguales/invertidos o fuera de dominio | Error bloqueante |
| Sensibilidad | Mas de 100 combinaciones | Aviso de coste computacional |

## Comportamiento de la interfaz

- Los mensajes se muestran antes de los resultados.
- `Calcular caso base` se deshabilita mientras existan errores del caso.
- `Ejecutar sensibilidad` se deshabilita ante errores del caso o del barrido.
- Los resultados anteriores se conservan, pero se advierte cuando las entradas actuales han cambiado.
- La configuracion del ultimo barrido se compara con los controles actuales para identificar sensibilidades obsoletas.
- El informe DOCX y el libro XLSX se generan a partir del ultimo caso calculado correctamente.
- Los barridos de coste elevado requieren confirmacion expresa segun densidad y numero de combinaciones.

## Riesgos residuales

- Los limites fisicos plausibles de `c'`, `phi'` y pesos unitarios dependen del material y del proyecto; los valores altos se avisan, no se sustituyen.
- La aplicacion no determina si corresponde un analisis drenado o no drenado.
- Una entrada numericamente valida puede seguir siendo geotecnicamente no representativa.
- La busqueda discreta no garantiza el minimo global y debe comprobarse con densidad y numero de dovelas. Las mallas son anidadas para que una densidad superior no descarte candidatos anteriores.
- Las capas se consideran horizontales y la propiedad resistente de la base se toma en el punto medio de cada dovela.
- No se modelan agua exterior, filtracion no hidrostatica, sismo, sobrecargas, refuerzos ni fases constructivas.

## Regresion

La bateria incluida cubre calculo manual de Fellenius, convergencia de Bishop, efecto del agua, NF bajo el pie, perfiles multicapa, cobertura del dominio, anidamiento de busqueda, sensibilidad, generacion DOCX/XLSX y entradas adversariales.
