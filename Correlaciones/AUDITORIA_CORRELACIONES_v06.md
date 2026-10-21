# Estado bibliografico y operativo v0.6

Se mantienen los siete modulos de la version v0.5. Este documento describe **solo** las cinco recuperaciones solicitadas. Los restantes metodos se mantienen como constaban en `AUDITORIA_CORRELACIONES_v05.md`.

| Grupo | Metodo | Situacion | Fuente directa para ecuacion | Restriccion y tratamiento |
|---|---|---|---|---|
| phi | Wolff/Peck | Activa y probada | Groundhog (expresion Wolff, rango sugerido 0-60) | Entrada `(N1)60`, arenas limpias |
| phi | Shioi-Fukui puentes/carreteras | Activa, fuente secundaria tecnica | ZSoil, tabla 3.10 | Entrada `N70`, limite operativo phi <=45 y N70<=50 |
| phi | Shioi-Fukui ferrocarriles | Activa, fuente secundaria tecnica | ZSoil, tabla 3.10 | Entrada `N70`, limite operativo N70<=60 |
| M para metodo de asientos | D'Appolonia arenas normalmente cargadas | Activa, fuente secundaria academica/tecnica | Paikowsky, FHWA; 196+7,9 N (tsf) | Promedio `N bruto`, espesor B y condicion NC |
| M para metodo de asientos | D'Appolonia arenas precargadas | Activa, fuente secundaria academica/tecnica | Paikowsky, FHWA; 416+10,9 N (tsf) | Promedio `N bruto`, espesor B y condicion precarga |

**Punto tecnico fundamental:** las ramas D'Appolonia se presentan como M, no como E; el N utilizado no se calcula desde un SPT aislado ni desde N60. No se han reactivado otras variantes que solo figuran en hojas secundarias o cuyo significado fisico es ambiguo.

Véase `VALIDACION_RECUPERADAS_v06.md` para formulas, conversiones, referencias y resultados de prueba.
