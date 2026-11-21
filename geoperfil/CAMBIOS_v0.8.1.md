# Cambios v0.8.1 respecto a v0.8.0

1. **STA es un punto de terreno**, no un reconocimiento ni un origen ficticio: se integra su PK y su cota en la linea del terreno y en la guitarra; no crea sondeo, penetracion ni SPT.
2. La tabla Estaciones identifica ahora el tipo de punto (`terreno` para STA y `reconocimiento` para trabajos de campo). Los libros BKFL/DPRG/ISPT/ListadoLab no pueden referirse a STA como si fuera un ensayo.
3. Los proyectos JSON de v0.8.0 con el campo historico `es_origen` se migran para identificar STA correctamente como punto topografico.
4. **Unica entrada de datos: multifichero**. Se elimina de la interfaz la importacion Excel unico, la descarga de la plantilla clasica y la edicion manual de tablas de datos. El eje se consulta en modo solo lectura.
5. La aplicacion se inicia **sin datos demostrativos**. Las pestanas de perfil y exportacion requieren una campana cargada; el boton de reset ahora vacia la campana tras confirmacion.
6. La validacion pendiente se invalida al cambiar el contenido de los libros seleccionados para evitar aplicar por error una campana anterior.
7. Se mantienen las exportaciones y el guardado/recuperacion JSON; el Excel de salida es un **exportado de datos procesados**, no una plantilla de entrada.
8. Se actualizan pruebas y documentacion; el ejemplo de entrada Excel unico deja de distribuirse.

**Limitaciones:** no se ha validado una sesion completa de Streamlit en macOS ni el DXF en AutoCAD. Geometrias geologicas y escala de plano requieren revision tecnica.
