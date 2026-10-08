# Correlaciones geotecnicas

Aplicacion Streamlit para estimaciones preliminares de parametros geotecnicos. La revision corrige errores de formulacion del prototipo, hace explicita la base del SPT y separa interfaz, calculo y modelos.

## Alcance

- Correccion de `N` a `N60` y `(N1)60` con factores visibles.
- Estimacion de `su` con Skempton, Bjerrum-Simons y Mesri, conservando sus diferentes significados.
- Correlaciones de `phi'` para arenas basadas en `(N1)60`.
- Calculo de CALIP con `IP = LL - LP` y estimacion de `phi_R` residual secante mediante una regresion publicada de la curva de Collotta.
- Modulo de arenas del procedimiento historico NAVFAC DM 7.1.
- Banda digitalizada de modulo vertical drenado `E'v` de Stroud-Butler para materiales sobreconsolidados.
- Modulo no drenado, tablas orientativas y balasto del CTE DB-SE-C.
- Interpolacion lineal por tramos de `qu` y `E` dentro de la tabla D.23, con `N` de rechazo explicito.
- Pestaña de referencias y formulaciones con enlaces a las fuentes.

Los resultados son correlaciones empiricas. No constituyen por si solos valores caracteristicos, de calculo ni admisibles.

## Estructura

```text
parametrizacion_corregida/
|-- app.py
|-- calculations/
|   |-- correlations.py
|   `-- spt.py
|-- models/
|   |-- catalog.py
|   `-- domain.py
|-- tests/
|-- requirements.txt
`-- README.md
```

## Instalacion y ejecucion

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Pruebas

Desde la raiz del proyecto:

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren las correcciones principales: Skempton lineal, CALIP con indice de plasticidad, normalizacion SPT, dominios de `phi'`, bandas CTE F.2 y geometria del modulo de balasto.

## Decisiones tecnicas de la revision

- La tabla D.23 del CTE se conserva como intervalos y la herramienta aplica una interpolacion lineal adoptada. Se usa el origen para el primer tramo y un `N` equivalente al rechazo definido por el usuario para cerrar el ultimo tramo; estas dos condiciones no son valores prescritos por el CTE.
- Se separa `sigma'v0` de `sigma'p`: Mesri (1975) requiere la presion efectiva de preconsolidacion.
- Hatanaka-Uchida y la modificacion de Mayne et al. se presentan como formulaciones distintas, tal como las sintetiza NCHRP 651.
- Los polinomios de Stroud se identifican como una digitalizacion posterior de la Figura 6 de Stroud y Butler (1975), no como ecuaciones originales. Estiman `E'v` drenado, usan la base SPT historica y se limitan a `0 <= IP <= 60 %`.
- CALIP se transforma en `phi_R` mediante la ecuacion B4 de Tzampoglou et al. (2026): `phi_R = 21.2/exp(0.008*CALIP^1.5) + 7.7`. Es un ajuste de datos de corte anular de Collotta et al. (1989), no una ecuacion del articulo original.
- Las correlaciones con autoria, unidades o base SPT no verificables se han retirado del motor activo. Esto evita presentar precision numerica sin trazabilidad.

La bibliografia completa y los enlaces se muestran dentro de la propia aplicacion.
