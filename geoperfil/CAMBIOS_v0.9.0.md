# GeoPerfil 2D v0.9.0 - Integridad de exportaciones

## Contrato de salida

- El JSON es el estado maestro y contiene una huella SHA-256 canonica y estable.
- La exportacion genera un paquete ZIP con todos los archivos y un manifest verificable.
- Todos los formatos comparten el mismo identificador del estado del proyecto.

## Formatos tabulares

- El XLSX incorpora proyecto, contactos, vertices, zonas, anillos, hipotesis, configuracion, esquema y manifest.
- Los CSV de contactos y zonas conservan atributos completos y generan cabeceras aunque no haya registros.

## Formatos graficos

- PDF, PNG y SVG no generan rellenos si la capa esta desactivada ni infieren unidades sin zonas clasificadas.
- Los documentos incluyen proyecto, escalas, sistema de referencia y huella.
- El HTML es autonomo e incorpora el JSON maestro y el manifest.

## DXF

- Se exportan intervalos litologicos por sondeo.
- Contactos, zonas, ensayos y resultados incorporan XDATA `GEOPERFIL`.
- El dibujo contiene un registro de metadatos y la huella del estado canonico.
