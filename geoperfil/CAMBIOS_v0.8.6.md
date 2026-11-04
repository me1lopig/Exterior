# GeoPerfil 2D v0.8.6 - Integridad y control de la interpretacion

## Persistencia

- Los proyectos nuevos se escriben como JSON estandar: `NaN` e infinitos se convierten en `null`.
- El JSON incorpora version de la aplicacion, version del formato y fecha UTC de guardado.
- Se mantienen compatibles los proyectos anteriores y se validan identificadores y coordenadas de zonas al abrir.

## Escalas y unidades

- Las escalas horizontal y vertical se guardan explicitamente y ya no se cuantiza la exageracion al abrir.
- El orden estratigrafico puede revisarse en Unidades y debe ser positivo y unico.
- Los cambios de paleta actualizan tambien los contactos asociados.

## Contactos

- La edicion numerica respeta el bloqueo.
- Un panel permite cambiar nombre, visibilidad y bloqueo.
- La visibilidad se aplica en perfil y exportaciones; los contactos ocultos siguen participando en la topologia.

## Calidad

- La version se obtiene de una unica fuente (`0.8.6`).
- Se incorpora un conjunto de regresiones v0.8.6 y dependencias de desarrollo separadas.
