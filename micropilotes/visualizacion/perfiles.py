"""Series de visualización desde entradas o resultados existentes."""
from math import isfinite

COLORES={'IU':'#64748b','IR':'#2563eb','IRS':'#0d9488','Mixto':'#7c3aed'}
TRAZOS={'IU':'dot','IR':'dash','IRS':'solid','Mixto':'dashdot'}

def _serie(nombre,tramos):
    xs=[];ys=[]
    for valor,za,zb in tramos:
        xs.extend([valor,valor]);ys.extend([za,zb])
    return dict(nombre=nombre,x=xs,y=ys,color=COLORES[nombre],dash=TRAZOS[nombre])

def series_entrada(filas,metodos):
    """Adherencias originales del perfil reconocido; no aplica criterios resistentes."""
    out=[]
    for n in metodos:
        tramos=[]
        for f in filas:
            v=f.get(n+'_MPa')
            try: v=float(v)
            except (TypeError,ValueError): v=None
            if v is not None and (not isfinite(v) or v<0): v=None
            tramos.append((None if v is None else v*1000,f['inicio_m'],f['fin_m']))
        if any(v is not None for v,_,_ in tramos): out.append(_serie(n,tramos))
    return out

def series_efectivas(datos,metodos,diam,campo):
    """Resultados de escenarios evaluados, hasta la punta, sin recalcular."""
    if campo not in ('r_lim','r_calculo','qc_kN_m','qt_kN_m'):
        raise ValueError('Magnitud de perfil desconocida.')
    out=[]
    for n in metodos:
        if n not in datos: continue
        r=datos[n]
        if campo in ('r_lim','r_calculo'):
            caso=r['casos'].get(diam)
            if caso is None: continue
            tramos=[(t[campo],t['z_inicio'],t['z_fin']) for t in caso['tramos']]
        else:
            g=r['unitarios']
            g=g[g.D_mm.sub(diam).abs()<1e-7].sort_values('z_inicio_m')
            tramos=[(getattr(t,campo),t.z_inicio_m,t.z_fin_m) for t in g.itertuples()]
        if tramos: out.append(_serie(n,tramos))
    return out
