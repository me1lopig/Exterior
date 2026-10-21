# GeoCorrelaciones v0.7 - Recuperación de Webb y Stroud-Butler

Fecha: 21/10/2026. Alcance: consultas de apoyo, no selección automática de parámetros de proyecto.

## 1. Webb (1969, publicación de actas 1970)

**Fuentes:**

- Webb, D. L., *Settlement of Structures on Deep Alluvial Sandy Sediments in Durban, South Africa*, In Situ Investigations in Soils and Rocks, pp. 181–188 (1970). Registro bibliográfico: https://trid.trb.org/View/125002
- Wagh, J. D. y Bambole, A. N. (2024), *Improved correlation of soil modulus with SPT N values*, *Open Engineering*, tabla de relaciones 5a, 5b y 5c. DOI https://doi.org/10.1515/eng-2024-0046 ; texto https://www.degruyterbrill.com/document/doi/10.1515/eng-2024-0046/html
- Otra recopilación histórica, *Settlement of Shallow Foundations on Granular Soils* (fuente secundaria): https://www.scribd.com/document/336590106/Settlement-of-Shallow-Foundations-on-Granular-Soils

**Formulaciones programadas** según la revisión moderna en kPa (se dividen por 1000 para MPa):

| Tipo | E en kPa | E en MPa con N=20 (caso SINTÉTICO) |
|---|---|---:|
| Arena saturada | 500 (N+15) | 17.50 |
| Arena arcillosa | 330 (N+5) | 8.25 |
| Perfil arenoso medio | 400 (N+12) | 12.80 |

- Se pide **N SPT bruto independiente**; no se utiliza N60 o (N1)60 por defecto.
- El trabajo se refiere a módulos inferidos de ensayos con placa helicoidal y a problemas de asientos. Denominación 'módulo de deformación E' acorde con la revisión; no asumir módulo de Young único para cualquier deformación, profundidad y carga.
- Se muestran solo valores de la variante elegida. La regla 0 < N <= 60 es **restricción operativa de la app**, no un límite experimental publicado por Webb.
- Algunas recopilaciones antiguas usan toneladas-fuerza/pie² y conversiones que difieren algunos puntos porcentuales de los coeficientes redondeados de la revisión 2024. Se ha elegido **una versión explícita y trazable**, evitando mezclar expresiones.
- **Nivel documental:** secundario contrastado; el registro de la publicación primaria existe, pero las tres ecuaciones no se han cotejado con el texto íntegro original de Webb. Por tanto, no se afirma validación primaria.

## 2. Stroud y Butler (1975)

**Fuente primaria reproducida:** M. A. Stroud y F. G. Butler, *The Standard Penetration Test and the Engineering Properties of Glacial Materials*, *The Engineering Behaviour of Glacial Materials* (1975), pp. 124–135.
Texto/figuras: https://www.geosolve.co.uk/refs/Stroud%2BButler_1975.pdf

- Fig. 4: correlación entre N y coeficiente de compresibilidad mv.
- Fig. 5: variación de f2 = 1/(mv N) con el índice de plasticidad, material y dispersión.
- Tabla 4: ejemplos de London Clay (IP 50, f2 440 kPa) y material glacial típico (IP 15, f2 700 kPa).
- Artículo: los coeficientes mv se interpretan para un incremento de carga edométrica de 100 kPa **adicional a la presión vertical efectiva in situ**.

Ecuaciones que se han incorporado:

```
m_v [1/kPa] = 1 / (f2 [kPa] * N [-])
M [kPa] = f2 [kPa] * N [-]
M [MPa] = f2 * N / 1000
m_v [1/MPa] = 1000/(f2 * N)
```

- El usuario introduce N bruto histórico, IP y f2 en kPa y confirma que conoce su procedencia; el software **no inventa un ajuste f2(IP)** ni automatiza la lectura de figura 5.
- El tipo de depósito debe ser arcilla glacial/till o glacial laminada de condiciones compatibles. Rango 15 <= IP <= 60 aproximado por la figura y 0 < N <= 100 como **regla operativa**, no dominio normativo.
- Si faltan datos, el método permanece sin cálculo. Las antiguas expresiones de Stroud/Butler del Excel `E=5N` y `E=6N` no son sustituidas de forma silenciosa por M, sino que se mantienen excluidas de E.
- **M** es módulo edométrico o confinado y **mv** el coeficiente de compresibilidad volumétrica; no se convierten a un E de Young sin datos y modelo adicionales.
- **Nivel documental:** ecuaciones contrastadas en reproducción primaria, implementación comprobada aritmética y dimensionalmente. No constituye validación experimental de material local.

## 3. Pruebas

El proyecto dispone de 103 pruebas de regresión, aritmética, dominio y recorridos simulados del programa (en entorno de preparación). Casos añadidos específicamente:

- Webb: los tres materiales para N=20, pendiente de la recta con N=10 a 30, N=0 y valores >60, material incorrecto, negativos y valores no finitos.
- Stroud-Butler: caso sintético N=20, IP=23, f2=450 kPa -> M=9 MPa y mv=0.111111 (1/MPa); comprobación M*mv=1, límites, f2 inválido, origen no confirmado y material incompatible.
- Recorrido simulado de interfaz activa para las dos familias. NO es un test visual de Streamlit.

## 4. Pendientes no habilitados

Meigh–Nixon (1961) por discrepancias de procedencia y unidades; Denver (1982), Wrench–Nowatzki, polinomios Stroud digitalizados, otras variantes Webb sin atribución y otras correlaciones históricas que carecen de respaldo suficiente. Webb queda documentado como referencia **secundaria**, mientras Stroud–Butler posee ecuación primaria reproducida. La app no debe usarse para inferir automáticamente parámetros característicos de cálculo.
