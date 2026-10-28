# Metodologia y auditoria del modulo de asientos elasticos - v4

## Alcance

Cimentaciones rectangulares de dimensiones B <= L, carga vertical uniforme y centrada sobre un perfil de estratos horizontales elasto-lineales. Los asientos **no son totales**: excluyen consolidacion primaria, secundaria, fluencia, plasticidad, carga inclinada, interaccion de zapatas vecinas, rigidez real de la cimentacion y asiento diferencial.

## 1. Formula de Steinbrenner

Para una esquina de rectangulo de dimensiones `b x l`, la implementacion calcula:

- `m = z/b`, `n = l/b`, `t = sqrt(1 + n^2 + m^2)`.
- `F1 = [ln((t+n)/(t-n)) + n ln((t+1)/(t-1))]/pi`.
- `F2 = (m/pi) * arctan[n/(t*m)]` (y F2=0 en z=0).
- `u(z) = q b/(2E) * [(1 - nu^2) F1 - (1 - nu - 2 nu^2) F2]`.

**Correccion v4:** en v3 figuraba `1 - nu - nu^2`, que no se corresponde con esta variante de Steinbrenner. El termino correcto es `1 - nu - 2 nu^2`. Referencia: *Settlements of Footing Groups*, 2023, ecuacion (22), apartado 9.3.1.

Para un estrato de limites `z_sup, z_inf` bajo la base, el aporte del rectangulo-esquina es `u(z_sup)-u(z_inf)`. Se multiplica por 4 para el **centro** con cuatro cuadrantes de `B/2 x L/2` (recomendado); la opcion `2 x (B x L)` es aproximacion historica para contrastar la hoja anterior, y no metodo recomendado de perfil estratificado. La suma por estratos coincide exactamente con el calculo de asiento del motor.

**Limitacion importante:** esta suma estratificada por diferencias de soluciones homogeneas **no** impone una solucion elastica multicapa rigurosa (continuidad y transmision de esfuerzos/desplazamientos en las interfases). No se imponen deformaciones por debajo del ultimo estrato; extender el reconocimiento puede elevar el asiento calculado.

## 2. Presion admisible por asientos

La respuesta es lineal para una geometria y perfil fijados:

- `s = q_neta * f(B,L,capas,nu,E)`.
- `q_adm_asientos_neta = s_admisible / f`.

Los asientos detallados se calculan a la **presion neta de servicio** de la zapata seleccionada o, opcionalmente, a la **presion limite por asientos**. No extrapolar esta igualdad a comportamiento no lineal ni a asientos por consolidacion.

### Distincion q0 / tension preexistente

- `q0_contorno`: sobrecarga de contorno aplicada en la formula de hundimiento: gamma_sobrecarga * altura. Puede incluirse o no.
- `sigma_v0,exc`: tension vertical preexistente **total** en el plano de apoyo que se supone retirada al excavar, estimada con D y pesos especificos o introducida manualmente.

En la hipotesis simplificada de compensacion completa de la excavacion:

`q_neta = q_bruta - sigma_v0,exc`.

La v3 utilizaba `q0_contorno` para esta conversion; v4 separa ambas magnitudes. La estimacion automatica de `sigma_v0,exc` usa `gamma_aparente` sobre el nivel freatico y `gamma_sumergido + 9.81 kN/m3` bajo el nivel freatico. Para tensiones iniciales *efectivas*, usa `gamma_sumergido` bajo el NF. **Debe revisarse el estado del agua**, las etapas de obra, los estratos excavados y el peso real de la cimentacion para proyectos reales. La herramienta no es un analisis riguroso de descarga/recarga ni sustituto de combinaciones de acciones ELU/ELS. La resistencia de hundimiento mantiene las hipotesis heredadas de la v3 y requiere verificacion de sus factores de seguridad antes de aplicarse a un proyecto.

## 3. Bulbo de tensiones Boussinesq / Fadum

Para una carga superficial rectangular y vertical uniforme se obtiene `Delta sigma_z = q_neta * I(z)` bajo el eje central, mediante superposicion de cuatro rectangulos:

Sea `a=B/2`, `c=L/2`, `R=sqrt(a^2+c^2+z^2)`:

`I(z) = (2/pi) [atan(ac/(zR)) + (acz/R) * (1/(a^2+z^2) + 1/(c^2+z^2))]`.

En z=0 se toma `I=1` por limite. La expresion ha sido comprobada con **integracion numerica independiente** de cargas puntuales Boussinesq y con sus limites fisicos (en el campo lejano `I ~ 3BL/(2 pi z^2)`).

El grafico de tensiones es **independiente** del calculo de asiento por Steinbrenner. No se debe interpretar `Delta sigma_z * H/E` como equivalente al modelo elasto-3D sin otras hipotesis.

## 4. Profundidad activa, CTE DB-SE-C 4.4.3

El control automatico localiza la primera profundidad bajo la base con:

`Delta sigma_z <= min(0.10 q_neta, 0.05 sigma'_v0(z))`.

Se muestra el cruce interpolado del grafico del eje central. Se compara con la profundidad de la ultima capa introducida y se presenta aviso cuando no alcanza la cota activa. El eje central **no equivale** a un criterio espacial riguroso para toda la zona cargada, especialmente en presencia de otras zapatas, suelos no homogeneos o agua variable. La profundidad `2B` queda solo como orientacion adicional. La profundidad representada manualmente puede no alcanzar el cruce; en ese caso no se declara suficiente.

## 5. Desglose y graficos

Para cada geometria seleccionada se generan:

- Tabla con nombre, limites, `E`, `nu`, aporte al asiento en mm, acumulado y porcentaje.
- Bulbo `Delta sigma_z(z)` y umbral del CTE.
- Asiento acumulado **por suma de contribuciones de estrato** (no desplazamiento fisico punto a punto del terreno).
- Diagrama de porcentajes por capa.
- Profundidad de aporte del 90% **en limites de capa**. No se interpola dentro del estrato sin disponer de esa discretizacion.
- Dos descargas CSV: tabla de estratos y serie de tensiones.

## 6. Contrastes numericos

Tests automatizados `python -m unittest discover -s tests -v`:

- Cinco casos de la tabla 71 de la *Guia para el proyecto de cimentaciones en obras de carretera con Eurocodigo 7* del Ministerio de Transportes. Coinciden en el orden de 0.1 mm con las cifras redondeadas publicadas.
- Formula de Boussinesq comparada contra cuadratura de Gauss-Legendre de la carga puntual.
- Limite de superficie, decrecimiento del incremento de tension y comportamiento asintotico lejano.
- Igualdad asiento de capas = asiento total de Steinbrenner.
- Linealidad de asiento con la presion y cumplimiento de s_admisible al llegar al limite q_asientos.
- Distincion entre q0 resistente y descarga preexistente, aguas arriba/abajo NF, alerta perfil insuficiente.
- Flujo de boton Calcular y pruebas heredadas de capacidad/CTE.

## Fuentes consultadas

- CTE DB-SE-C, 20 de diciembre de 2019, apartado 4.4: https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf
- *Settlements of Footing Groups*, GEOTEC Software, 2023, apartado 9.3.1, ecuacion (22): https://geotecsoftware.com/jdownloads/Books/9-Settlements%20of%20footing%20groups-EN.pdf
- USACE EM 1110-1-1904, Boussinesq / Fadum para areas cargadas: https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-1-1904.pdf
- Ministerio de Transportes, *Guia para el proyecto de cimentaciones en obras de carretera con Eurocodigo 7*: https://cdn.mitma.gob.es/portal-web-drupal/carreteras/normativa/21_3/guia_cimentaciones_con_eurocodigo_7._ejemplos_cimentaciones_superficiales.pdf
- Calculadora GF de referencia funcional (sin equivalencia matematica directa asumida): https://calculosgeotecnicosgf.com/calculo-asientos-cimentacion/

**Estado:** prototipo con contraste computacional y ejemplos independientes limitados. No certificado, no apto como unica comprobacion de seguridad de un proyecto. Consolidacion primaria y secundaria excluidas expresamente.
