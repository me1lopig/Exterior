# Matriz técnica de decisiones · v0.5

Fecha: 2026-10-21. Este documento distingue fuente que valida la ecuación de prueba numérica del código. La disponibilidad de una referencia por sí sola **no** implica calibración local.

| Grupo | Expresión/método | Estado v0.5 | Entradas y restricciones | Fuente |
|---|---|---|---|---|
| Cu | Skempton NC VST | Activa condicionada | IP %, σ'v0 kPa, NC | Skempton/Bowles, ver `cu_validado.py` |
| Cu | Bjerrum-Simons NC | Activa condicionada | IP>50%, σ'v0, NC | Bowles |
| Cu | Karlsson-Viberg NC | Activa condicionada | LL>20%, σ'v0, NC | Bowles |
| Cu | Mesri resistencia movilizada | Activa condicionada | σ'p medido, arcilla blanda inorgánica | Mesri/ASCE |
| Cu | Intervalos de consistencia | Consulta de rango | Consistencia; qu/2 bajo hipótesis no drenada | CTE D.3 |
| Cu | Intervalos por NSPT | Consulta de rango | N; qu/2 condicionado; tabla mixta | CTE D.23 |
| φ | Hatanaka-Uchida adaptada a N1_60 | Activa condicionada | 3.5≤N1_60≤30, arena limpia fina/media | FHWA NHI-16-072, Hatanaka 1996 |
| φ | Schmertmann/Kulhawy-Mayne | Activa condicionada | N60, σ'v0, arena limpia | FHWA NHI-16-009 v1, ec. 5-14 |
| φ | Intervalos por litología | Consulta de rango | Grava, arena, limo o arcilla | CTE D.27 |
| E arenas | E/pa=5N60 | Activa condicionada | Arenas con finos, N60<=60 | FHWA NHI-05-037 |
| E arenas | E/pa=10N60 | Activa condicionada | Arena limpia NC, N60<=60 | FHWA NHI-05-037 |
| E arenas | E/pa=15N60 | Activa condicionada | Arena limpia OC, N60<=60 | FHWA NHI-05-037 |
| E arenas | Begemann N<15 | Activa, fuente secundaria | N histórico, 0<N<15, suelo granular | Anejo técnico Euskadi |
| E arenas | Begemann N>15 | Activa, fuente secundaria | N histórico, 15<N<=50, suelo granular; signo corregido | Anejo técnico Euskadi |
| E arcillas | Eu/cu | Activa condicionada | IP, OCR≥1, cu de ensayo, arcilla OC | CTE F.2 |
| E arcillas | Eu=fP Gmax | Activa condicionada | IP, Gmax cross-hole/down-hole, arcilla OC | CTE F.1 |
| E CTE | Tablas D.23, E y qu | Consulta + interpolación declarada | N<10 o N>50, intervalo sin resultado único; intermedio valor propio | CTE D.23 |
| Poisson | 4 valores típicos | Consulta | Tipo de terreno | CTE D.24 |
| K30 | 4 resultados | Activa | B, L, k30, L≥B | CTE E.6-E.8 |

## No incorporadas tras el contraste

| Grupo | Incidencia identificada | Razón de exclusión |
|---|---|---|
| φ | Wolff/Peck, JNR/JRB, Shioi-Fukui | Variantes de normalización SPT y trazabilidad desigual según publicación consultada |
| φ | Otras ocho referencias del Excel | Ecuación, año o dominio no demostrados desde fuente original |
| E arenas | Denver | Copias técnicas discrepan sobre radical/variable en la fórmula; sin fuente original |
| E arenas | Bowles (resto), Webb, Meigh-Nixon, Wrench-Nowatzki | Unidad original o definición N y dominio de la variante no suficientemente establecidos |
| E arenas | D'Appolonia | Se requiere precisar si se estima M, Es de placa o E de Young, además del tipo de terreno |
| E arcillas | Stroud y Stroud-Butler | Relaciones referidas a cu y mv; no se habilitan como E de Young |

**Error corregido:** para Begemann N>15 se usa `40+12*(N-6)` y no `40+12*(N+6)`; 1 kgf/cm²=0,0980665 MPa. La fuente accesible es **secundaria**, por lo que se etiqueta diferente de una ecuación directamente cotejada con la publicación original.

**SPT:** Ncampo, N60 y N1_60 son variables distintas. Conocer N60 no permite reconstruir Ncampo sin los factores originales: por eso se pregunta N histórico separado para Begemann. La limitación CN=1,7 es opción operativa, no una propiedad de Hatanaka-Uchida ni regla única de normalización.

## Comprobaciones (casos sintéticos)

- Ncampo=20, ER=75%, CB=1,05, CR=0,8, CS=1 => N60=21; σ'=100 => CN=1 y N1_60=21.
- φ'(Hatanaka) con N1_60=20 => `20+sqrt(15,4*20)≈37,55°`, no `20+sqrt(20*20)=40°` cuando el N es (N1)60.
- φ'(Schmertmann/Kulhawy) para N60=20, σ'v=100 kPa => `atan((20/(12,2+20,3))^0,34)` en grados; se comprueba contra cálculo matemático independiente.
- E arena FHWA para N60=20: arena con finos `10 MPa`, limpia NC `20 MPa`, limpia OC `30 MPa`.
- E Begemann N=20: `[40+12(20−6)]*0,0980665=20,397832 MPa`; N=15 no arroja valor numérico.
- Cu por consistencia Firme (CTE D.3): qu=100–200 kPa => cu=50–100 kPa si cu=qu/2 resulta aplicable.
- CTE F.1: IP 25/40/60%, Gmax=50 MPa => Eu=60/80/95 MPa.
- CTE D.23 para N=10 asigna tramo 10–25 y E interpolado 8 MPa.

Se han ejecutado 64 pruebas de regresión y de extremos usando `python -m unittest discover -s tests -v`, sin fallos (incluidos dos recorridos simulados de la interfaz, no gráficos). No se probó la interfaz visual real por ausencia de Streamlit en el entorno.

**Incidencia de integracion reparada:** en v0.4 la interfaz importaba `K30_TABLA` inexistente. En v0.5 se incorpora explicitamente la tabla D.29 (12 clases) y se cubre mediante una prueba de importacion de `app.py` y casos de entrada alternativos.
