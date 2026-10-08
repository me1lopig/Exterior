"""Catalogo de referencias y formulaciones visibles en la aplicacion."""

from models.domain import Reference


REFERENCES = (
    Reference("CTE2019", "Ministerio de Fomento (2019). CTE DB-SE-C Cimientos.", "https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf", "Normativa oficial", "Tablas D.23, D.24, D.29, F.2 y ecuaciones E.6-E.8."),
    Reference("FHWA2002", "Sabatini, P. J. et al. (2002). FHWA Geotechnical Engineering Circular No. 5: Evaluation of Soil and Rock Properties, FHWA-IF-02-034.", "https://highways.dot.gov/sites/fhwa.dot.gov/files/FHWA-IF-02-034.pdf", "Manual tecnico oficial", "Correcciones del SPT y uso de N60."),
    Reference("NCHRP651", "Transportation Research Board (2010). NCHRP Report 651, LRFD Design and Construction of Shallow Foundations.", "https://nap.nationalacademies.org/catalog/14381/lrfd-design-and-construction-of-shallow-foundations-for-highway-bridge-structures", "Informe tecnico", "Sintesis de correlaciones entre (N1)60 y phi'."),
    Reference("HATANAKA1996", "Hatanaka, M. y Uchida, A. (1996). Empirical correlation between penetration resistance and internal friction angle of sandy soils. Soils and Foundations, 36(4), 1-9.", "https://doi.org/10.3208/sandf.36.4_1", "Articulo primario", "Correlacion N1-phi' y dominio experimental."),
    Reference("SKEMPTON1957", "Skempton, A. W. (1957). Discussion: The planning and design of the new Hong Kong Airport.", "https://doi.org/10.1680/iicep.1957.2568", "Publicacion primaria", "Relacion lineal su/sigma'v0-IP para arcillas NC."),
    Reference("BJERRUM1960", "Bjerrum, L. y Simons, N. E. (1960). Comparison of shear strength characteristics of normally consolidated clays.", "https://www.issmge.org/uploads/publications/1/40/1960_01_0009.pdf", "Publicacion primaria", "Relacion su/sigma'v0 para arcillas NC de alta plasticidad."),
    Reference("MESRI1975", "Mesri, G. (1975). New Design Procedure for Stability of Soft Clays. Journal of the Geotechnical Engineering Division, 101(GT4).", "https://ascelibrary.org/doi/10.1061/AJGEB6.0005026", "Articulo primario", "su(mob)/sigma'p = 0.22."),
    Reference("COLLOTTA1989", "Collotta, T., Cantoni, R., Pavesi, U., Ruberl, E. y Moretti, P. C. (1989). A correlation between residual friction angle, gradation and the index properties of cohesive soils. Geotechnique, 39(2), 343-346.", "https://doi.org/10.1680/geot.1989.39.2.343", "Articulo primario", "Definicion de CALIP y correlacion grafica con resistencia residual."),
    Reference("TZAMPOGLOU2026", "Tzampoglou, P. et al. (2026). Investigation of a slow-moving landslide in Cretaceous bentonitic clay. Bulletin of Engineering Geology and the Environment.", "https://doi.org/10.1007/s10064-026-04992-2", "Articulo revisado por pares", "Apendice B, ecuacion B4: ajuste no lineal de los datos de corte anular de Collotta et al.; R2 > 0.99."),
    Reference("NAVFAC1982", "NAVFAC (1982). Soil Mechanics, Design Manual 7.1.", "https://www.tugraz.at/fileadmin/user_upload/Institute/IAG/Files/23_NAVFAC_DM_7_01.pdf", "Manual tecnico oficial historico", "Es/N para el procedimiento de asientos en suelos granulares."),
    Reference("STROUD1975", "Stroud, M. A. y Butler, F. G. (1975). The Standard Penetration Test and the Engineering Properties of Glacial Materials. Symposium on the Engineering Behaviour of Glacial Materials, University of Birmingham, pp. 124-135.", "https://www.geosolve.co.uk/refs/Stroud%2BButler_1975.pdf", "Publicacion primaria", "Figura 6: variacion de E'v/N con IP en materiales sobreconsolidados. Los polinomios de la aplicacion son una digitalizacion posterior."),
    Reference("WHITE2019", "White, F., Ingram, P., Nicholson, D., Stroud, M. y Betru, M. (2019). An update of the SPT-cu relationship proposed by M. Stroud in 1974.", "https://doi.org/10.32075/17ECSMGE-2019-0500", "Revision con participacion del autor original", "Advierte cambios del f1 por diferencias entre equipos y procedimientos SPT historicos y modernos."),
)


FORMULATIONS = (
    ("Correccion energetica SPT", "N60 = N*(ER/60)*CB*CR*CS", "N de campo, ER %, factores adimensionales", "FHWA2002", "No asumir que N*0.60 equivale a N60."),
    ("Normalizacion por sobrecarga", "(N1)60 = CN*N60; CN = min[sqrt(pa/sigma'v0), CN,max]", "sigma'v0 y pa en kPa", "FHWA2002", "El limite CN,max es una seleccion explicita del usuario."),
    ("Resistencia no drenada", "su = (0.11 + 0.0037*IP)*sigma'v0", "IP %, sigma'v0 kPa", "SKEMPTON1957", "Arcillas NC, veleta; no contiene logaritmo."),
    ("Resistencia movilizada", "su(mob) = 0.22*sigma'p", "sigma'p kPa", "MESRI1975", "sigma'p es presion efectiva de preconsolidacion."),
    ("Rozamiento de arenas", "phi' = 27.1 + 0.3*(N1)60 - 0.00054*(N1)60^2", "(N1)60", "NCHRP651", "Atribucion Wolff (1989) en la sintesis NCHRP."),
    ("Rozamiento de arenas", "phi' = 20 + sqrt(20*(N1)60)", "(N1)60", "HATANAKA1996", "Dominio publicado: 3.5 <= (N1)60 <= 30."),
    ("Rozamiento de arenas", "phi' = 20 + sqrt(15.4*(N1)60)", "(N1)60", "NCHRP651", "Modificacion de Mayne et al. (2001) basada en Hatanaka-Uchida."),
    ("CALIP", "CF = 100*CA/P40; IP = LL-LP; CALIP = CF^2*LL*IP*10^-5", "Porcentajes", "COLLOTTA1989", "La fuente presenta una correlacion grafica; no se usa un polinomio no publicado."),
    ("Rozamiento residual secante", "phi_R = 21.2/exp(0.008*CALIP^1.5) + 7.7", "CALIP; phi_R en grados", "TZAMPOGLOU2026", "Ajuste de corte anular a Collotta; sigma'n de la base aproximadamente 100-500 kPa."),
    ("Modulo NAVFAC", "Es = alpha*N [tsf], alpha = 4, 7, 10 o 12", "N historico NAVFAC", "NAVFAC1982", "Convertido con 1 tsf = 0.0957605 MPa."),
    ("Stroud: E'v inferior", "E'v = N*(-0.003*IP^3 + 0.859*IP^2 - 72.04*IP + 2410)", "N historico, IP %, E'v kPa", "STROUD1975", "Digitalizacion posterior de la Figura 6; no es ecuacion original."),
    ("Stroud: E'v superior", "E'v = N*(-0.008*IP^3 + 1.732*IP^2 - 127.2*IP + 3703)", "N historico, IP %, E'v kPa", "STROUD1975", "Digitalizacion posterior de la Figura 6; no es ecuacion original."),
    ("Tabla D.23: qu y E", "Y = Yi + (Yi+1-Yi)*(N-Ni)/(Ni+1-Ni)", "N SPT; qu en kPa; E en MPa", "CTE2019", "Interpolacion adoptada por la herramienta; rechazo definido por el usuario."),
    ("Balasto rectangular", "ksBL = ksB*(1+B/(2L))", "k en MN/m3; B,L m", "CTE2019", "B es el lado menor y B <= L."),
)
