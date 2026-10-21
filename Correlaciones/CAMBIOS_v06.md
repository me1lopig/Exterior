# Cambios v0.6 respecto a v0.5

**Alcance:** recuperacion documentada de correlaciones para phi y de M para el metodo de D'Appolonia, manteniendo las siete pestanas y Cu, E, Poisson, K30 anteriores.

| Pestaña | Metodo recuperado | Variable imprescindible | Identificacion |
|---|---|---|---|
| phi | Wolff / Peck (1989) | (N1)60 | `27.1+0.3*N1_60-0.00054*N1_60**2` |
| phi | Shioi-Fukui (1982), carreteras/puentes | N70 | `15+sqrt(18*N70)` |
| phi | Shioi-Fukui (1982), ferrocarriles | N70 | `27+0.36*N70` |
| E arenas / cuadro independiente M | D'Appolonia (1970), normalmente cargada | N bruto medio en B bajo zapata | `M=(196+7.9*Nmedio)*0.09576051796` MPa |
| E arenas / cuadro independiente M | D'Appolonia (1970), precargada | N bruto medio en B bajo zapata | `M=(416+10.9*Nmedio)*0.09576051796` MPa |

- Se mantienen separadas `N`, `N60`, `(N1)60` y `N70`.
- Para Shioi-Fukui, `N70=N60*(60/70)` si se parte de N60; **no** se usa la correccion CN.
- Para D'Appolonia hay campos nuevos: anchura `B`, numero **medio bruto sin corregir** desde la base de la zapata hasta B metros bajo ella, y estado de carga (NC/precargada). El modulo `M` es especifico del metodo de asientos y **no** se rotula como Young `E`.
- El componente de resultados conserva la formula, fuente, dominio y conversion. Se evita extrapolar datos fuera del limite operativo visible.
- Fuentes primarias y secundarias diferenciadas en `VALIDACION_RECUPERADAS_v06.md`.
- Pruebas automatizadas totales: 84; tres recorridos simulados de interfaz. Streamlit no comprobado visualmente.
