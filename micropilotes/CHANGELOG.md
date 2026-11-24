# Historial

## 0.5.0 — 2026-11-24
- Selector de armaduras estable y tabla compacta.
- Separación de tracción y pandeo; corrección de prueba de catálogo.
- Proyecto JSON versionado recuperable; recálculo de entradas.
- Exportaciones XLSX, DOCX, PDF bajo demanda y control de obsolescencia.
- Auditoría focalizada y pruebas automatizadas, CI y smoke test.

## 0.4.2 — 2026-11-24
- 74 perfiles CS550/CSTM80, propiedades y cargas comerciales diferenciadas; sección personalizada.
- Calidades y fy de referencia, tablas 2.3, 2.4, 3.4–3.7, y compatibilidad nominal.
- Selección múltiple de armaduras y combinación con diámetros. Límite parcial de acero, sección compuesta opcional, cruces exactos y exportaciones.
- Pruebas de catálogo, tablas y cálculo. Pendiente validación independiente y visual.

## 0.4.1 — 2026-11-24
- Configuración integrada al principio de Geotecnia: ocho pestañas generales.
- Importación CSV plegada; tabla editable y tabla derivada diferenciadas, sin repetir entradas.
- Profundidad reconocida y efectiva, longitud axial de cada tramo y nota de IU a 5 m.
- Perfil con zona no atravesada sombreada y línea de punta; formato de resultados a dos decimales sin cambiar el motor.
- Cuatro pruebas específicas de tabla, inclinación y perfil.

## 0.4.0 — 2026-11-24
- Nueve pestañas generales, selector de D nominal según tabla 4.1 y perforación editable +10%.
- Barrido regular con nodos de cambio y acciones opcionales; resultados separados de compresión y tracción.
- Punta +15% solo hipótesis máxima no verificada, fuera de verificaciones y envolvente parcial.
- Eliminación de casilla obligatoria de adherencias; se conserva control avanzado opcional y aviso.
- Exportación CSV/JSON del barrido, gráficos interactivos SVG. Peso propio y rozamiento negativo externos al barrido. Sección estructural única y provisional.

## 0.3.3 — 2026-11-24
- Tabla simplificada: unidad, espesor, tipo de inyeccion, adherencia limite, Fr y fuste activo. Vista de solo lectura de adherencias admisibles efectivas.
- Fr comun segun tabla 3.2; minoracion una sola vez en el motor. IU adicional solo donde es necesaria por la regla de los primeros 5 m.
- Presiones fuera de la tabla principal, control numerico opcional con declaracion de aplicabilidad obligatoria y aviso si no se ejecuta.
- Compatibilidad con CSV anteriores y seis pruebas de regresion adicionales.

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
