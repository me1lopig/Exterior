# GeoCorrelaciones v0.7 · Webb y Stroud-Butler

Aplicación **Streamlit** de consulta de correlaciones geotécnicas (España). Siete pestañas, correspondientes a los módulos conservados del Excel original. Se excluyen **Cc, Cs, K0 y el cálculo de OCR**. El OCR se introduce como dato independiente únicamente en E de arcillas.

## Arranque

Python 3.11+:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

Streamlit Community Cloud: subir el **contenido descomprimido** del ZIP a GitHub, escoger `app.py` e instalar `requirements.txt`. El código no descarga datos de obras ni persiste resultados en servidor; el usuario puede exportar CSV. No se necesita el Excel en ejecución.

## Resumen de métodos/fuentes implementados

| Pestaña | Métodos/relaciones disponibles | Contexto |
|---|---:|---|
| Cu | 4 relaciones + 2 consultas CTE | Skempton, Bjerrum-Simons, Karlsson-Viberg, Mesri; CTE D.3 y D.23 |
| φ | 5 relaciones + 1 consulta CTE | FHWA (2), Wolff/Peck (1), Shioi-Fukui (2), CTE D.27 |
| E arenas | 3 relaciones E FHWA + 2 ramas E Begemann + 3 variantes Webb; 2 ramas de M D'Appolonia | Los modulos de compresibilidad M no son directamente el modulo Young E |
| E arcillas | 2 métodos CTE + 1 método de compresibilidad (2 resultados) | Eu/cu tabla F.2 y Eu=fP Gmax tabla F.1; Stroud-Butler M y mv diferenciados de E |
| E CTE | 8 filas de resultado por intervalos | Tabla D.23; interpolaciones de E y qu declaradas como derivación no normativa |
| Poisson | 4 valores tabulados | Tabla D.24 |
| K30 | 4 transformaciones | Tabla D.29, fórmulas E.6-E.8 |

**No se cuentan como ecuaciones independientes** todas las filas de tablas, variantes por terreno o ramas de una relación definida a trozos. Según el material y los datos de entrada, algunas alternativas aparecerán como «No aplica», sin número.

## Normalización SPT y datos añadidos

Se evita usar el golpeo de campo como si fuera N60 o (N1)60:

- `N60=Ncampo*(ER/60)*CB*CR*CS`, con `ER` (%) y factores de equipo declarados. Los factores toman 1 por defecto solo como hipótesis visible.
- `(N1)60 = CN*N60`, con `CN=(100 kPa/σ'v0)^0,5`. El usuario puede optar por `CN ≤ 1,7` (límite práctico) o por no imponer ese tope; también puede introducir (N1)60 ya calculado.
- Entradas independientes de `N60` corregido cuando no se dispone del N bruto. Para Begemann, se pregunta N separado cuando solo se conoce N60, **sin reconvertirlo automáticamente**.
- Entradas de material, consolidación, tensión efectiva, IP, LL, presión de preconsolidación, Gmax y OCR donde cada método las requiere.

Estos factores están sujetos al procedimiento, calibración y condiciones del ensayo SPT. `Ncampo`, `N60`, `(N1)60` y `N70` **no son intercambiables**. En Shioi-Fukui se emplea `N70=N60*60/70` (corrección por energía, no por confinamiento); en D'Appolonia se pide por separado el `N bruto medio` en un espesor B bajo la cimentación.

## Nuevas correlaciones v0.7

- **Webb**: selector de arena saturada, arena arcillosa o perfil medio; N **bruto** independiente, E(kPa)=500(N+15), 330(N+5) o 400(N+12) respectivamente, convertido a MPa. Fuente secundaria: Wagh y Bambole (2024), https://doi.org/10.1515/eng-2024-0046 . El artículo original está identificado por TRID, pero sus tres coeficientes no se cotejaron directamente en él. El valor de E procede de ensayos con placa para estimación de asientos y no debe verse como E universal.
- **Stroud-Butler**: método edométrico para materiales glaciares (m_v = 1/(f2 N), M = f2 N). La app necesita IP, N bruto y un f2 en kPa procedente de fuente o ensayo. Exige confirmar f2; no digitaliza automáticamente la figura 5 original. Fuente primaria: https://www.geosolve.co.uk/refs/Stroud%2BButler_1975.pdf . El módulo M y el coeficiente m_v no se presentan como Young ni como Eu.
- Ver `VALIDACION_WEBB_STROUD_v07.md`, `CAMBIOS_v07.md` y `AUDITORIA_CORRELACIONES_v07.md`.

## Condiciones de aplicación y decisiones de validación

- **Cu:** cuatro ecuaciones con controles de consolidación, plasticidad, tensión efectiva y tipo de arcilla. Añadidas consultas CTE D.3 por consistencia y D.23 por NSPT; `cu=qu/2` solo bajo hipótesis de compresión simple no drenada en arcilla saturada, mostrando **rangos**.
- **φ:** Hatanaka-Uchida: `φ'=20+√(15,4 (N1)60)` según FHWA (adaptación a 60 % de energía), únicamente arenas limpias finas/medias y `3,5 ≤ (N1)60 ≤ 30`. Schmertmann/Kulhawy-Mayne: `φ'=atan{[N60/(12,2+20,3σ'v0/pa)]^0,34}` expresado en grados, con `pa=100 kPa`, para arena limpia. CTE D.27 como consulta de ángulos por material, sin convertir un intervalo en valor único. Wolff/Peck: `φ=27,1+0,3(N1)60−0,00054[(N1)60]^2`, rango recomendado `(N1)60≤60` en arenas. Shioi-Fukui: `φ=15+√(18N70)` en carreteras/puentes y `φ=27+0,36N70` en ferrocarriles; ambos requieren `N70` a energía 70%, sin corrección por confinamiento, con límites operativos conservadores para la consulta. Fuente especializada secundaria (ZSoil), **no fórmulas del CTE**.
- **E arenas:** FHWA: `E/pa ≈ 5N60` (arena con finos), `10N60` (arena limpia NC) o `15N60` (arena limpia OC), con `pa=100 kPa`. Para evitar extrapolación a rechazo se usa restricción operativa `N60≤60` (**no normativa**). Begemann: `E=12(N+6)` si N<15; `E=40+12(N−6)` si N>15, originalmente en kgf/cm², convertido con `1 kgf/cm²=0,0980665 MPa`. No se calcula a N=15, por discontinuidad entre ramas y falta de regla publicada. El N histórico procede de fuente **secundaria** (anejo técnico de Euskadi): no se presenta como fuente original verificada. **D'Appolonia (1970):** se calcula `M` en lugar de convertirlo a `E`, con `M=(196+7,9·Nmedio)` tsf para arenas normalmente cargadas o `M=(416+10,9·Nmedio)` tsf para precargadas. `Nmedio` es el promedio bruto sin corrección entre base de cimentación y profundidad B adicional; 1 tsf = 0,09576051796 MPa. El resultado de `M` se muestra en un desplegable independiente, con estado de carga y ancho B explícitos. No se obtiene automáticamente con un único `N60` del sondeo.
- **E arcillas:** CTE F.2, depende de `IP, OCR, cu` y arcilla OC; CTE F.1 requiere `Gmax` realmente obtenido de cross-hole/down-hole e `IP`, arcilla OC. No se habilitan las cuatro polinómicas Stroud/Butler de la planilla como módulo E de Young.
- **E CTE:** se conserva interpolación propia en 10≤N≤50, con N=10 correctamente en el tramo 10–25; N>50 muestra intervalos oficiales sin extrapolar.
- **Poisson/K30:** se conservan tablas/ecuaciones anteriores, con referencias y condiciones.

## Fuentes identificadas

1. CTE DB SE-C, edición 20/12/2019 (D.3, D.23, D.24, D.27, D.29, F.1, F.2, E.6-E.8): https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf
2. FHWA, *Geotechnical Site Characterization*, NHI-16-072, 2016, secc. 7.6: https://www.fhwa.dot.gov/engineering/geotech/pubs/nhi16072.pdf
3. FHWA, *Design and Construction of Driven Pile Foundations*, NHI-16-009 v1, ecuaciones 5-14/5-15: https://www.fhwa.dot.gov/engineering/geotech/pubs/gec12/nhi16009_v1.pdf
4. FHWA, *Geotechnical Aspects of Pavements*, NHI-05-037, cap. 4 (Kulhawy y Mayne): https://www.fhwa.dot.gov/engineering/geotech/pubs/05037/04b.cfm
5. Hatanaka y Uchida, 1996, *Soils and Foundations*, 36(4), pp. 1-9: https://doi.org/10.3208/sandf.36.4_1
6. Liao y Whitman, 1986, *Journal of Geotechnical Engineering*, 112(3), 373-377: https://doi.org/10.1061/(ASCE)0733-9410(1986)112:3(373)
7. Begemann (1974), reproducido en anejo técnico público (fuente secundaria): https://www.euskadi.eus/contenidos/informacion/subestacion_elec_gernika/es_def/adjuntos/TTE-IS-24001-PWS-SBS-ANX-0005.pdf
8. Wolff/Peck, ecuación y rango sugerido en Groundhog: https://groundhog.readthedocs.io/en/main/site_investigation/spt_correlations.html
9. Shioi-Fukui (1982), variantes reconstruidas según manual ZSoil (pág. 103 de edición 2025): https://www.zsoil.com/zsoil_manual/Rep-HS-model.pdf ; ficha del original: https://eurekamag.com/research/091/197/091197826.php
10. D'Appolonia (1970): fuente estadounidense de la familia de ecuaciones: https://rosap.ntl.bts.gov/view/dot/20506/dot_20506_DS1.pdf ; método y significado físico de M: https://www.fhwa.dot.gov/publications/research/infrastructure/structures/bridge/15080/004.cfm ; ecuaciones exactas en Paikowsky reproducidas también en https://paperzz.com/doc/6951188/settlement-of-shallow-foundations-on-granular-soils
11. Cu: referencias originales/secundarias dentro de `calculos/cu_validado.py` y `VALIDACION_CU_v04.md`.

## Pendientes que **no** se implementan como cálculos activos

Variantes de Shioi-Fukui que no coinciden con las dos reconstruidas, Muromachi, Montenegro-González y otras ecuaciones φ cuya normalización de N o publicación original no se pudo establecer con suficiencia; Denver (ecuaciones contradictorias entre compendios), Bowles (convención de N), Meigh-Nixon (inconsistencia de escala), Wrench-Nowatzki y antiguas fórmulas de Stroud/Butler como E de Young (se ofrece m_v y M diferenciados). **No** se incluyen como E las ecuaciones alternativas `215+10,6 N` y `540+13,5 N` en kgf/cm2 atribuidas a D'Appolonia porque difieren del método M de asientos localizado. La trazabilidad está en `AUDITORIA_CORRELACIONES_v06.md` y el histórico en `AUDITORIA_CORRELACIONES_v05.md`.

## Pruebas y nivel de garantía

**103 pruebas automatizadas satisfactorias** al generar este archivo, incluidas 20 comprobaciones nuevas de Wolff, Shioi-Fukui, D'Appolonia y entrada simulada de la interfaz. Se comprobaron importaciones del motor, sintaxis de `app.py` y tres recorridos de arranque simulados sin interfaz gráfica. Los valores de referencia en las pruebas son cálculos manuales independientes de la implementación, basados en las ecuaciones y tablas documentadas; **no constituyen validación experimental**.

**Limitación de entorno:** no se pudo instalar Streamlit en el entorno de generación (repositorio de paquetes inaccesible), por lo que no se verificó el arranque visual interactivo real. Recomendable ejecutar `streamlit run app.py` localmente o en Streamlit Community Cloud antes de uso compartido.
