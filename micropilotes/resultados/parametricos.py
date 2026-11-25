"""Transformaciones de resultados, sin modificar las formulaciones resistentes."""
from math import pi, isfinite
import pandas as pd

CAMPOS={'c':('Rc_fuste_kN','limite_c_kN'),'t':('Rt_fuste_kN','limite_t_kN')}

def unitarios(filas, casos):
    """Por metro axial, sobre tramos efectivos del motor; no se aplica Fr otra vez."""
    out=[]
    for diam,caso in casos.items():
        for i,t in enumerate(caso['tramos']):
            z=(t['z_inicio']+t['z_fin'])/2
            f=next(f for f in filas if f['inicio_m']<=z<f['fin_m'])
            activo=bool(f['activo'])
            q=pi*float(diam)/1000*t['r_calculo'] if activo else 0.
            out.append(dict(tramo=i+1,unidad=f['nombre'],z_inicio_m=t['z_inicio'],
                z_fin_m=t['z_fin'],L_axial_m=t['longitud_axial'],
                inyeccion_seleccionada=f['inyeccion'],
                inyeccion_efectiva=('IU' if t['z_inicio']<5 else f['inyeccion']) if activo else 'Inactivo',
                activo=activo,admisible_kPa=t['r_calculo'],D_mm=float(diam),
                qc_kN_m=q,qt_kN_m=q*caso['eta'],Rc_tramo_kN=t['compresion'],Rt_tramo_kN=t['traccion']))
    return pd.DataFrame(out)

def matriz_unitaria(df,modo):
    idx=['tramo','unidad','z_inicio_m','z_fin_m','inyeccion_efectiva','admisible_kPa']
    p=df.pivot(index=idx,columns='D_mm',values='qc_kN_m' if modo=='c' else 'qt_kN_m').reset_index()
    p.columns=[f'Ø {x:g} mm' if isinstance(x,(float,int)) else x for x in p.columns]
    return p

def matriz_fuste(b,modo):
    p=b.pivot(index='L_m',columns='D_mm',values=CAMPOS[modo][0]).sort_index()
    p.columns=[f'Ø {x:g} mm' for x in p.columns]
    return p

def curvas_parciales(b,alternativas,modo):
    campo,tope=CAMPOS[modo]
    for a in alternativas:
        lim=a.get(tope)
        if lim is None or not isfinite(lim) or lim<0: continue
        g=b[(b.D_mm-float(a['D_mm'])).abs()<1e-7].sort_values('L_m')
        if g.empty: continue
        yield a['alternativa'],g.L_m.to_numpy(),g[campo].to_numpy(),float(lim)

def matriz_parcial(b,alternativas,modo):
    # Mantener las alternativas no evaluadas como celdas vacías.
    p=pd.DataFrame(index=sorted(b.L_m.unique()))
    p.index.name='L_m'
    for a in alternativas: p[a['alternativa']]=float('nan')
    for n,L,R,lim in curvas_parciales(b,alternativas,modo):
        p.loc[L,n]=[min(v,lim) for v in R]
    return p

def primera_longitud(L,R,objetivo):
    if objetivo<0 or not isfinite(objetivo): raise ValueError('Acción inválida')
    if not len(L) or objetivo>R[-1]: return None
    if objetivo<=R[0]: return float(L[0])
    for a,b,u,v in zip(L,L[1:],R,R[1:]):
        if u<objetivo<=v: return float(a+(b-a)*(objetivo-u)/(v-u))
    return None

def longitudes(b,alternativas,modo,ed):
    if ed is None: return pd.DataFrame()
    campo,tope=CAMPOS[modo]
    out=[]
    for a in alternativas:
        g=b[(b.D_mm-float(a['D_mm'])).abs()<1e-7].sort_values('L_m')
        lim=a.get(tope)
        if lim is None or not isfinite(lim): L=None; estado='No evaluada'
        elif ed>lim: L=None; estado='Límite de armadura'
        else:
            L=primera_longitud(g.L_m.to_numpy(),g[campo].to_numpy(),ed)
            estado='Alcanzada (parcial)' if L is not None else 'Fuste insuficiente en intervalo'
        out.append(dict(alternativa=a['alternativa'],Ed_kN=ed,L_necesaria_m=L,estado=estado))
    return pd.DataFrame(out)

def aprovechamiento(matriz,ed):
    """Sin división por cero: NaN indica no evaluado o capacidad nula."""
    if ed is None: return pd.DataFrame()
    return ed/matriz.where(matriz>0)*100

def sensibilidad(b,porcentaje):
    if not isfinite(porcentaje) or not 0<=porcentaje<=100: raise ValueError('Variación inválida')
    out=[]
    for nombre,factor in [('Inferior',1-porcentaje/100),('Central',1.),('Superior',1+porcentaje/100)]:
        g=b[['D_mm','L_m','Rc_fuste_kN','Rt_fuste_kN']].copy()
        g[['Rc_fuste_kN','Rt_fuste_kN']]*=factor
        g['escenario']=nombre;g['factor']=factor;out.append(g)
    return pd.concat(out,ignore_index=True)
