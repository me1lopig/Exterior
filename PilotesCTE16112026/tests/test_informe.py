import io
from docx import Document
from pilotes_cte.core import Estrato,Configuracion,Geometria,calcular_pilote
from pilotes_cte.report import generar_informe


def test_word_completo_con_figuras_y_tabulacion():
    e=[Estrato('G1',30,18,20,'Granular','Largo Plazo',0,30,'Arena floja')]
    cfg=Configuracion(nivel_freatico=5,fuste_nulo=1,
                     rozamiento_negativo=True,rn_desde=0,rn_hasta=2,factor_rn=1.1)
    a=calcular_pilote(e,Geometria(diametro=.6),10,cfg)
    b=calcular_pilote(e,Geometria(diametro=.6),12,cfg)
    out=generar_informe(e,cfg,'Persistente/transitoria','Tabla 2.1',a.seccion.descripcion,
                        [a,b],a,[],{'proyecto':'Caso de control','sondeo':'S-01'})
    assert out[:2]==b'PK'
    doc=Document(io.BytesIO(out))
    text='\n'.join(p.text for p in doc.paragraphs)
    assert 'Caso de control' in text
    assert 'Fneg,d' in '\n'.join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert 'Condiciones' in text or 'Hipótesis' in text
    assert len(doc.inline_shapes)>=2


def test_word_incluye_columnas_nd():
    e=[Estrato('G1',15,18,20,'Granular','Largo Plazo',0,30)]
    cfg=Configuracion(nivel_freatico=None,fuste_nulo=0)
    r=calcular_pilote(e,Geometria(diametro=.6),10,cfg)
    errores=[{'D_eq (m)':1.0, 'L (m)':14.0, 'Causa':'Bulbo L+3D supera el sondeo'}]
    out=generar_informe(e,cfg,'Persistente/transitoria','Tabla 2.1',r.seccion.descripcion,
                        [r],r,errores,{})
    doc=Document(io.BytesIO(out))
    texto='\n'.join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert '1.00 m' in texto and 'N/D' in texto
