"""Comparación de procedimientos; se reutiliza el barrido y el límite resistente existente."""
import pandas as pd
from calculos.axial import calcular
from calculos.barrido import barrido
from calculos.limites_acero import longitud_cruce
from resultados.parametricos import unitarios, longitudes, matriz_parcial, aprovechamiento

def adaptar_armaduras(b,alternativas):
    out=[]
    for original in alternativas:
        a=dict(original)
        g=b[b.D_mm.sub(a['D_mm']).abs()<1e-7].sort_values('L_m')
        if g.empty: continue
        for modo,campo,pref in [('c','Rc_fuste_kN','Rc'),('t','Rt_fuste_kN','Rt')]:
            lim=a.get('limite_'+modo+'_kN')
            a['L_cruce_'+modo+'_m']=longitud_cruce(g.L_m.tolist(),g[campo].tolist(),lim) if lim is not None else None
            a[pref+'_parcial_Lmax_kN']=min(g[campo].iloc[-1],lim) if lim is not None else None
        out.append(a)
    return out

def calcular_escenario(estratos,detalle,geometria,lmin,lmax,paso,angulo,meses,alterna,punta,alternativas):
    filas=[]; casos={}
    for d in geometria:
        filas.extend(barrido(d/1000,lmin,lmax,paso,angulo,estratos,meses,alterna,punta))
        casos[d]=calcular(d/1000,lmax,angulo,estratos,meses,alterna)
    b=pd.DataFrame(filas)
    return dict(barrido=b,unitarios=unitarios(detalle,casos),armaduras=adaptar_armaduras(b,alternativas),detalle=detalle,casos=casos)

def filas_comparativas(datos):
    out=[]
    for nombre,r in datos.items():
        g=r['barrido'].groupby('D_mm',as_index=False).tail(1).copy()
        g.insert(0,'procedimiento',nombre);out.append(g)
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def combinar(datos,campo):
    out=[]
    for nombre,r in datos.items():
        v=pd.DataFrame(r[campo]).copy()
        if v.empty: continue
        v.insert(0,'procedimiento',nombre);out.append(v)
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()
