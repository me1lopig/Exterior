"""Estilo común para comparaciones de inyección."""
import plotly.graph_objects as go
from visualizacion.graficas import _estilo
from calculos.limites_acero import envolvente

COLORES_INY={'Mixto':'#7c3aed','IU':'#64748b','IR':'#2563eb','IRS':'#0d9488'}
TRAZOS={'Mixto':'dashdot','IU':'dot','IR':'dash','IRS':'solid'}

def curvas_inyeccion(datos,d,modo,alternativa=None,ed=None):
    fig=go.Figure();campo='Rc_fuste_kN' if modo=='c' else 'Rt_fuste_kN'
    for n,r in datos.items():
        g=r['barrido'][r['barrido'].D_mm.sub(d).abs()<1e-7].sort_values('L_m')
        if g.empty: continue
        L=g.L_m.tolist();R=g[campo].tolist()
        if alternativa is not None:
            a=next((x for x in r['armaduras'] if x['alternativa']==alternativa),None)
            lim=a.get('limite_'+modo+'_kN') if a else None
            if lim is None: continue
            L,R=envolvente(L,R,lim)
        fig.add_scatter(x=L,y=R,name=n,mode='lines',line=dict(color=COLORES_INY[n],dash=TRAZOS[n],width=2.6))
    if ed is not None: fig.add_hline(y=ed,line_dash='dash',line_color='#b45309',annotation_text='Acción')
    _estilo(fig,'Comparación por procedimiento · '+('capacidad parcial' if alternativa else 'fuste'),480)
    fig.update_xaxes(title='Longitud axial (m)');fig.update_yaxes(title='Resistencia (kN)',rangemode='tozero')
    return fig

def barras_inyeccion(datos,d,modo):
    fig=go.Figure();campo='qc_kN_m' if modo=='c' else 'qt_kN_m'
    for n,r in datos.items():
        g=r['unitarios'][r['unitarios'].D_mm.sub(d).abs()<1e-7]
        labels=[f'{x.unidad} · {x.z_inicio_m:.2f}–{x.z_fin_m:.2f} m' for x in g.itertuples()]
        fig.add_bar(y=labels,x=g[campo],name=n,orientation='h',marker_color=COLORES_INY[n],
            customdata=g[['inyeccion_efectiva','admisible_kPa']].to_numpy(),
            hovertemplate='%{y}<br>%{x:.2f} kN/ml<br>Inyección efectiva: %{customdata[0]}<br>Adherencia: %{customdata[1]:.2f} kPa<extra>%{fullData.name}</extra>')
    _estilo(fig,'Resistencia unitaria por tramo · procedimientos',max(420,130+max((len(r['unitarios'].tramo.unique()) for r in datos.values()),default=0)*75))
    fig.update_layout(barmode='group');fig.update_yaxes(autorange='reversed');fig.update_xaxes(title='Resistencia unitaria (kN/ml)',rangemode='tozero')
    return fig
