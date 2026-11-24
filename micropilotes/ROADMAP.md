# Hoja de ruta priorizada

- [x] v0.1.1: contraste focalizado de ecuaciones, controles de geometria, trazabilidad y pruebas de regresion.
- [x] v0.2: filtro de presiones, punta condicional, predimensionamiento por fuste, CSV de adherencias externas, accion externa de rozamiento negativo.
- [x] v0.3: seccion axial tubular preliminar, seleccion parcial de perfiles, corrosion y CR justificados manualmente, factores de union y ejecucion.
- [ ] Validacion independiente con memorias externas, pruebas de carga y revision especializada (bloqueante para uso profesional).
- [ ] v0.3.1: automatizar tabla 2.4 y seleccion de CR/zonas libres, verificar empalmes certificados, ampliar catalogo y materiales, control de recubrimiento.
- [x] v0.3.2: graficos interactivos del caso, curvas de fuste por diametro nominal y exportacion CSV de nodos/SVG.
- [ ] v0.4: interfaz completa de ocho pestanas, perfil con todas las adherencias disponibles, seleccion multiple de armaduras/perforaciones, barrido regular de longitudes, sensibilidad y pruebas de interfaz. Ver [diseno funcional](docs/DISENO_PARAMETRICO.md).
- [ ] v0.5: informe Word/PDF, ficha resumen, Excel, recarga JSON.
- [ ] v0.6: optimizacion de longitudes, diametros, inyecciones y armaduras.
- [ ] v0.7: roca, flexion y cortante.
- [ ] v0.8: asientos, acciones laterales y grupo.
- [ ] v0.9: calculo por lotes, mediciones, CAD.
- [ ] v1.0: validacion integral, documentacion, revision y publicacion estable.

## v0.4.0 — diseño paramétrico
- [x] Nueve pestañas, diámetros de tabla 4.1, Dp editable +10%, longitudes por intervalo, acciones opcionales, sin casilla obligatoria de adherencias.
- [x] Barrido por fuste, curva máxima hipotética de punta 15%, resultados separados y CSV/JSON.
- [ ] Ejecución completa de pruebas y validación visual, múltiples armaduras, corrosión/pandeo por longitud, informes Excel/Word/PDF y recarga JSON.

## v0.4.1 — simplificación de interfaz
- [x] Configuración dentro de Geotecnia, ocho pestañas, importación plegada, tablas de entradas/resultados diferenciadas, cotas efectivas, perfil reconocido y zona no atravesada.
- [ ] Verificación visual de Streamlit desplegado y validación integral del motor.

## v0.4.2
- [x] Catálogo completo, selección múltiple, propiedades, tablas de guía aplicables a cálculo axial, envolvente parcial de acero y exportación.
- [ ] Verificación de materiales, manguitos/recubrimiento real, pandeo variable por tramo y longitud, validación independiente, informes Excel/Word/PDF.

## v0.5.0
- [x] Excel, Word/PDF de resumen, recuperación JSON esquema 1, simplificación de catálogo, revisión focalizada y CI.
- [ ] Validación visual, casos externos de referencia, pandeo por longitud, recubrimientos/empalmes acreditados, informes ampliados por alternativa y normativa específica de obra.
