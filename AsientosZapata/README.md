# Aplicación de asientos elásticos

Aplicación Streamlit para calcular el asiento elástico inmediato de una cimentación rectangular mediante Steinbrenner multicapa y un modelo tridimensional elástico de OpenSeesPy.

## Selección del método

La casilla **Activar cálculo MEF (OpenSees 3D)** está desmarcada por defecto. Sin MEF se calculan Steinbrenner, la comprobación analítica ELS y el informe Word sin ejecutar OpenSees. Al activar MEF se muestran los parámetros de discretización, se resuelve OpenSees y, si se elige, se realiza sensibilidad numérica. Los resultados analíticos de Steinbrenner se mantienen en ambos modos. La comprobación ELS analítica no supone validar las hipótesis geotécnicas ni la sensibilidad a la profundidad de corte.

## Alcance

- Carga vertical centrada y presión neta de servicio.
- Terreno elástico lineal e isótropo por estratos.
- Cimentación flexible o rígida y lisa.
- Asiento inmediato. No incluye consolidación, fluencia, plasticidad ni capacidad portante.
- La evaluación de distorsión angular se ha eliminado completamente.

### Cautelas del método clásico

- Las expresiones de Holl y Steinbrenner se han contrastado con integración numérica independiente de Boussinesq.
- La suma multicapa es una aproximación por semiespacios homogéneos equivalentes; no reproduce la redistribución de tensiones entre estratos.
- El punto característico `(0.37·B, 0.37·L)` es orientativo para zapatas rígidas en perfiles estratificados.
- El criterio `delta_sigma_z <= 0.20 sigma'_v0` define una profundidad convencional; debe comprobarse la sensibilidad aumentando `z_max`.
- El factor de Mayne-Poulos aplicado a rectángulos multicapa mediante diámetro equivalente es una extensión aproximada.

## Instalación

Se recomienda Python 3.11 o 3.12 en un entorno virtual.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows, la activación se realiza con `.venv\\Scripts\\activate`.

## Ejecución

```bash
streamlit run app.py
```

## Controles técnicos incorporados

- La aplicación combinada exige `0 <= nu < 0.5` por el FEM; la rutina clásica admite el límite analítico `nu = 0.5`.
- La comprobación queda bloqueada si el perfil termina antes de alcanzar `delta_sigma_z <= 0.20 sigma'_v0`.
- Para ELS se exige `z_max >= z_i`.
- El fondo del dominio MEF se sitúa por debajo de `z_max` mediante `factor_prof`.
- El veredicto ELS requiere sensibilidad de malla, extensión lateral y profundidad dentro de la tolerancia adoptada.
- En zapatas rígidas, Steinbrenner no extrapola el campo de asientos fuera del área cargada.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

La ejecución de las pruebas analíticas no sustituye la calibración de los parámetros geotécnicos ni la revisión del modelo por el proyectista.
