# Diseño funcional — Geo_App Micropilotes paramétrico

La interfaz final tendrá ocho pestañas. La versión 0.3.2 conserva las entradas actuales y añade cinco pestañas de resultados gráficos; la reorganización completa queda pendiente.

| Pestaña | Contenido | Gráficos |
|---|---|---|
| 01 Proyecto | Identificación, autor, revisor, fecha, revisión, logotipo, nuevo/guardar/abrir | Resumen del proyecto |
| 02 Modelo geotécnico | UG, litología, espesor vertical, adherencias límite IU/IR/IRS, tipo por tramo, fuste activo, controles avanzados de aplicabilidad | Perfil estratigráfico e inyección, curvas de adherencia disponible y aplicada; línea 5 m |
| 03 Catálogo y geometría | Selección múltiple de tuberías, calidad, propiedades nominales y certificadas, D nominal y de perforación diferenciados, manguitos y recubrimientos | Secciones transversales a escala |
| 04 Configuración | Longitud mínima/máxima/paso, inclinación, duración, Fr, régimen de tracción, punta opcional, peso, corrosión, ejecución, pandeo, cargas opcionales | Tabla de coeficientes con referencia |
| 05 Resistencia geotécnica | Barrido de longitudes; compresión y tracción por fuste, detalle por tramo; punta y peso por separado | Curvas por diámetro, adherencias efectivas, contribución por tramo y resistencia acumulada |
| 06 Resistencia estructural | Sección residual, materiales, uniones, pandeo, resistencias axiales | Secciones y comparación por armadura |
| 07 Comparación | Envolvente parcial geotécnica/estructural por modo, longitud necesaria, alternativas no verificadas, condicionante | Curvas comparativas, cruces, cargas y aprovechamientos |
| 08 Informes | Selección de contenido, exportación, recuperación de proyecto | Vista previa de ficha y memoria |

## Archivos previstos
- XLSX: Proyecto, Geotecnia, Armaduras, Coeficientes, Compresión, Tracción, Estructural, Comparativa, Detalle, Advertencias y Gráficas. Tablas numéricas con unidades y datos intermedios.
- DOCX/PDF: ficha individual y memoria completa con hipótesis, formulación, datos, tablas, figuras, resultados parciales, advertencias, revisión y referencias. DOCX editable; PDF maquetado.
- JSON: entradas, catálogo seleccionado, opciones, resultados, versión del esquema y del motor, advertencias. La recarga todavía no está implementada.
- CSV: intercambio de estratos, nodos de curvas y detalle por tramos; en el futuro, tabla regular de longitudes por alternativa.
- SVG/PNG: cada figura técnica independiente. SVG disponible desde Plotly en 0.3.2; PNG y exportación conjunta pendientes.
- DXF: perfil y sección en una fase posterior.

## Reglas
- Primeros 5 m verticales: IU; dividir tramos automáticamente.
- No extrapolar más allá de la estratigrafía reconocida. Incluir nodos de cambio de estrato, inyección y zona IU aunque no coincidan con el paso regular.
- Las capacidades de fuste no dependen de la armadura cuando se mantiene el diámetro nominal y demás parámetros. No duplicar curvas equivalentes.
- Punta desactivada por defecto; límite 15% del fuste no es un valor automático. Verificar condiciones en cada longitud que se estudie.
- No declarar conformidad global a partir de la envolvente parcial; pandeo, corrosión y uniones se deben justificar y evaluar para cada alternativa.
- Las calidades del catálogo no acreditan disponibilidad por geometría; el valor certificado se mantiene separado.
- Las cargas son opcionales para obtener capacidades en la interfaz final.
- No introducir datos de obra confidenciales en el repositorio público.
