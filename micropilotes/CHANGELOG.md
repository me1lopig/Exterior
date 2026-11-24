# Historial

## 0.3.2 — 2026-11-24
- Cinco pestanas de resultados graficos Plotly: perfil y adherencias, curvas por diametro nominal, contribuciones, seccion y comparacion parcial.
- Exportacion SVG desde las figuras y CSV/JSON de los nodos exactos de fuste.
- No modifica las ecuaciones del motor; la comparacion estructural usa una capacidad fija del caso, no un analisis de pandeo por longitud.
- Tres pruebas de figuras y nodos; pendiente verificacion de interfaz y suite completa en el entorno de despliegue.

## 0.3.1 — 2026-11-24
- Entrada de estratos por espesor vertical, sin cotas iniciales/finales editables.
- Conversion de CSV antiguos contiguos, nueva plantilla y cotas acumuladas en JSON.
- Se mantienen inyeccion por tramo, regla IU en primeros 5 m verticales y calculo inclinado.
- Cinco pruebas adicionales de migracion, acumulacion, validacion y calculo.

## 0.3.0 — 2026-11-24
- Motor de seccion axial segun 3.6.1 y 3.6.2, sin barras adicionales, con factores de ejecucion y union, reduccion por corrosion y pandeo con CR externo.
- Seleccion parcial de dimensiones comerciales y seccion personalizada.
- Resultados parciales, graficos por tramo y acumulados, JSON y CSV.
- No se certifica capacidad global; faltan verificacion independiente, automatizacion de corrosion/pandeo y comprobacion de conexiones.

## 0.2.0
- Filtro conservador de presiones, control de punta, predimensionamiento por fuste, importacion CSV.
- Rozamiento negativo como accion externa, no estimado por el motor.

## 0.1.1
- Contraste de coeficientes con la guia de 2005 y refuerzo de validaciones y pruebas.

## 0.1.0
- Prototipo axial original.
