# GeoPerfil 2D v0.9.1 - Importación de SPT con rechazo

## Correcciones

- Reconocimiento de cabeceras `Estación` y `Estaciones` en PERFIL1 (insensible a mayúsculas y acentos).
- En incrementos `ISPT_INC1` a `ISPT_INC4` y `SPT (valores centrales)`, los textos `R` y `RECHAZO` se interpretan como el mismo **estado cualitativo de rechazo**.
- Un rechazo **no se convierte en 0 ni en un N-SPT numérico**. Los golpes numéricos, incrementos ausentes y longitudes de penetración se conservan separados.
- La tabla `SPT` incorpora `estado`, `rechazo`, `inc*_estado`, `inc*_original`, `n_central_estado`, `n_central_original`, `secuencia_original`, `ispt_seat_original`, `espesor_ensayo_mm`, y archivo/hoja de origen.
- Se conserva la grafía del rechazo y la secuencia literal de `Valores ensayos` cuando existe. Los nombres originales de los archivos constan en `Fuentes` y `SPT.archivo_origen`.
- Las salidas JSON, XLSX y XDATA DXF reciben los nuevos campos desde la tabla SPT. Los formatos gráficos muestran la secuencia `R` sin sustituirla por un valor numérico.
- Vista previa de SPT y recuento de rechazos durante la validación de campaña.

## Verificación

- Se probaron los cinco XLSX aportados en el importador: 3 sondeos, 12 intervalos, 8 SPT y 3 rechazos (DPRG vacío).
- 119 pruebas automatizadas correctas, incluidas nuevas regresiones con rechazo en distintos incrementos, `R`/`RECHAZO`/espacios/minúsculas, valores nulos y 0, preservación de penetraciones y JSON/XLSX/DXF.
- DXF generado con los libros aportados y reabierto mediante ezdxf: 8 entidades SPT, con atributos de rechazo y penetraciones parciales.
- JSON comprobado mediante ida y vuelta, y paquete ZIP de exportación con manifest verificado.

## Limitaciones

- No se atribuye un criterio normativo de rechazo ni un número de golpes equivalente a `R`. La clasificación técnica de un rechazo requiere el procedimiento de campo.
- Los archivos Excel de campaña no se reescriben ni se incluyen dentro del ZIP del programa. Consérvelos como originales.
- No se realizó una sesión gráfica completa de Streamlit ni se abrió el DXF en AutoCAD en este entorno.
