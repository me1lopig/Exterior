# Auditoria tecnica focalizada — 24/11/2026

Fuente: [Guia DGC 2005](https://cdn.transportes.gob.es/portal-web-transportes/carreteras/normativa_tecnica/08.1_guias_tecnicas/0710200.pdf). Se revisaron apartados 1.2, 3.3.1.1, 3.3.2, 3.3.3.1, 3.4, 3.6.1-2 y 4.4.2. No se ha verificado toda la normativa aplicable a una obra determinada.

| Regla | Fuente | Implementacion |
|---|---|---|
| D nominal <= perforacion y D < 300 mm | 1.2, 3.3.1.1 nota 6 | motor/interfaz |
| rfc,d = rf,lim / Fr; Fr 1.45 hasta 6 meses, 1.65 resto | 3.3.2.4, tabla 3.2 | axial.py |
| AL = pi D L; profundidad = L cos(alpha) | 3.3.1.1 y geometria | axial.py |
| IU en z < 5 m | 3.3.2.4 | axial.py |
| Cavidades y camisa perdida: se anula fuste | 3.3.2.1, 3.4.2.1 | activo=false, sin excepcion de camisa |
| Eta .60 alternancia, .75 traccion exclusiva; peso/1.2 | 3.4 | axial.py |
| Punta <= .15 Rfc,d | 3.3.3.1 | axial.py |
| Punta: N>30 o qu>100 kPa, empotramiento >=6D, estimaciones 6D/3D | 3.3.1.1 | avanzado.py: filtro conservador (ambas zonas superan umbral); geometria y continuidad declaradas por usuario |
| Inyeccion IU/IR pi>=500 kPa; normalmente .5 Plim <= pi <= Plim; IRS pi>1000 kPa y pi>=Plim | 4.4.2 | avanzado.py: filtro conservador; no excepciones ni comprobacion de registro real |
| Nc,Rd = (.85 Ac fcd + Aa fyd) R/(1.2 Fe) | 3.6.1 | estructural.py, sin barras |
| Nt,Rd = Aa fyd / 1.10 | 3.6.2 | estructural.py, sin barras |
| Aa residual = pi/4 [(de-2re)^2-di^2] Fu | 3.6.1-2 | estructural.py |
| fcd=fck/1.5; fyd=fy/1.1; limite de 400 MPa solo en compresion | 3.6.1-2 | estructural.py |
| Fu,c / Fu,t, Fe y R=min(1,1.07-.027 CR) | tablas 3.4-3.7 | estructural.py, CR y re justificados externamente |

Ac se calcula descontando el acero nominal, sin atribuir lechada a la perdida por corrosion; se descuenta el hueco interior salvo confirmacion de relleno. Esto es una hipotesis conservadora. La reduccion por corrosion de tabla 2.4 y la eleccion de CR segun tabla 3.6 no se automatizan. Si el valor de R no es positivo se bloquea; requiere analisis especifico. Los limites certificados de union, cuando se aportan, limitan las resistencias calculadas. No se infiere Fu del nombre comercial.

Catalogo de referencia: Comercial de Sondeos, catalogo espanol CS550/CSTM80, tabla de dimensiones p. 6 impresa (p. 9 del PDF aportado); seleccion parcial de dimensiones. A e I se calculan geometricamente, no se usan cargas admisibles comerciales. Se requiere certificado del acero y de la union.

Validacion: pruebas sinteticas independientes, sin contrastar aun contra una prueba de carga o memoria externa completa. El filtro no verifica la ejecucion real, la representatividad de los ensayos, ni el conjunto de ELU/ELS. No declarar conformidad global.

## Revisión v0.5.0 (24/11/2026)
Contraste directo de las páginas 13, 16–17, 25, 29–30, 36–41 y 60 de la Guía DGC 2005. Se confirman las tablas 2.1, 2.3, 2.4, 3.2, 3.4, 3.5, 3.6, 3.7 y 4.1, y las expresiones de compresión y tracción. Acero solo: se omite deliberadamente la contribución positiva del cemento; no es capacidad estructural completa. El pandeo no se usa en tracción, que se calcula aunque CR falte o R no sea positivo. Compresión no evaluada en esos casos. La guía considera nulo el fuste en cavidades y camisa perdida (3.3.2.1/3.4.2.1): el técnico debe desactivar los tramos correspondientes; seleccionar Fe no elimina el fuste automáticamente. Pendiente contraste con memoria externa/ensayos y revisión de aplicabilidad de normas actuales. Pruebas de referencia manual y CI incorporadas; no se presume su ejecución por publicar código.
