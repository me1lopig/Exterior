# Zapatas Streamlit v4 - elasticidad y profundidad activa

Aplicacion de predimensionamiento de zapatas rectangulares B x L, con comparativa corrida historica. Reproduce el alcance funcional de la hoja SUELOS y corrige la formula de asientos del prototipo anterior.

## Arranque

1. Crear entorno virtual de Python 3.11+ y activarlo.
2. Ejecutar `pip install -r requirements.txt`.
3. Ejecutar `streamlit run app.py`.

## Interfaz

- **Datos iniciales:** datos del proyecto y malla `Bmin, Bmax, incrB, Lmin, Lmax, incrL`, con `0 < B <= L`.
- **Hundimiento:** parametros resistentes, condiciones de agua, q0 de contorno, talud, profundidad y seguridad.
- **Asientos:** asiento admisible, estratos E/nu, metodos `Superposicion 4 x (B/2 x L/2)` (defecto) o `Aproximacion 2 x (B x L)`, selector Cohesivo / Granular para Ksp30; tension inicial auto o manual; profundidad y paso del grafico del bulbo.
- **Resultados:** boton `Calcular`, resultados netos/brutos, mapas azules con anotaciones, tabla CSV, ficha y diagnostico del asiento de la zapata seleccionada. Seleccion de presion de referencia: servicio o limite por asientos.

## Nuevo en v4

- Steinbrenner corregido: `1 - nu - 2nu^2`, con regresion externa (cinco casos ministeriales).
- Presion previa de excavacion separada de `q0` del contorno, con opcion manual.
- Bulbo `Delta sigma_z(z)` (Boussinesq centro rectangular), umbral CTE y aviso de profundidad investigada insuficiente.
- Tabla de contribucion por estratos y asiento acumulado (mm / %), grafico vertical y barras.
- Exportacion CSV de contribuciones y del perfil de tensiones.
- Los resultados se calculan solo cuando se pulsa `Calcular` y se avisa si las entradas han cambiado.

## Comprobaciones

`python -m unittest discover -s tests -v`

Consultar `METODOLOGIA_ASIENTOS.md` para ecuaciones, controles, bibliografia y limitaciones. Consultar `VALIDACION.md` para el registro de las pruebas.

**Atencion:** modelo lineal elastico estratificado aproximado. Las condiciones de drenaje, descarga/recarga y profundidad del reconocimiento requieren criterio geotecnico. No se consideran consolidacion, distorsion angular, zapatas vecinas, cargas excentricas ni comportamiento plastico. La v4 no reproduce exactamente los resultados erroneos de la v3/Excel en el coeficiente de Poisson.
