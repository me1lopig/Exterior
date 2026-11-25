"""Figuras de resultados paramétricos; todas las resistencias provienen del motor."""
from html import escape
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .graficas import _estilo, COLORES, seccion_transversal
from calculos.limites_acero import envolvente
from resultados.parametricos import curvas_parciales, CAMPOS

INYECCION={'IU':'#64748b','IR':'#2563eb','IRS':'#0d9488','Inactivo':'#cbd5e1'}

def etiquetas(g):
    return [f"{escape(str(r.unidad))} · {r.z_inicio_m:.2f}–{r.z_fin_m:.2f} m · {r.inyeccion_efectiva}" for r in g.itertuples()]

def barras_unitarias(df,modo):
    fig=go.Figure();campo='qc_kN_m' if modo=='c' else 'qt_kN_m'
    grupos=list(df.groupby('D_mm',sort=True))
    for i,(d,g) in enumerate(grupos):
        labels=etiquetas(g)
        color=[INYECCION.get(x,'#64748b') for x in g.inyeccion_efectiva] if len(grupos)==1 else COLORES[i%len(COLORES)]
        fig.add_bar(y=labels,x=g[campo],orientation='h',name=f'Ø {d:g} mm',
            marker_color=color,customdata=g[['admisible_kPa','L_axial_m']].to_numpy(),
            hovertemplate='%{y}<br>%{x:.2f} kN/ml<br>Adherencia: %{customdata[0]:.2f} kPa<extra>%{fullData.name}</extra>')
    _estilo(fig,'Resistencia unitaria por tramo',max(400,130+len(df.tramo.unique())*max(55,19*len(grupos))))
    fig.update_layout(barmode='group',margin=dict(l=190,r=30,t=70,b=80))
    fig.update_yaxes(autorange='reversed');fig.update_xaxes(title='Resistencia unitaria (kN/ml)',rangemode='tozero')
    return fig

def perfil_unitario(df,modo):
    fig=make_subplots(rows=1,cols=3,shared_yaxes=True,column_widths=[.25,.25,.5],
        subplot_titles=['Tramo / inyección','Adherencia (kPa)','Resistencia (kN/ml)'],horizontal_spacing=.07)
    campo='qc_kN_m' if modo=='c' else 'qt_kN_m'
    base=df[df.D_mm==df.D_mm.iloc[0]]
    for r in base.itertuples():
        fig.add_shape(type='rect',x0=0,x1=1,y0=r.z_inicio_m,y1=r.z_fin_m,
            line=dict(color='#cbd5e1',width=.7),fillcolor=INYECCION.get(r.inyeccion_efectiva,'#64748b'),
            opacity=.19,row=1,col=1)
        fig.add_annotation(x=.5,y=(r.z_inicio_m+r.z_fin_m)/2,text=escape(str(r.unidad))+' · '+r.inyeccion_efectiva,
            showarrow=False,font=dict(size=10),row=1,col=1)
    def escalon(g,col):
        x=[];y=[]
        for r in g.itertuples():
            x.extend([getattr(r,col)]*2);y.extend([r.z_inicio_m,r.z_fin_m])
        return x,y
    x,y=escalon(base,'admisible_kPa')
    fig.add_scatter(x=x,y=y,mode='lines',line=dict(color='#475569',width=2),name='Admisible',showlegend=False,row=1,col=2)
    for i,(d,g) in enumerate(df.groupby('D_mm',sort=True)):
        x,y=escalon(g,campo)
        fig.add_scatter(x=x,y=y,mode='lines',line=dict(color=COLORES[i%len(COLORES)],width=2.5),
            name=f'Ø {d:g} mm',row=1,col=3)
    _estilo(fig,'Perfil de resistencia unitaria',max(520,110+len(base)*33))
    fig.update_xaxes(range=[0,1],visible=False,row=1,col=1)
    fig.update_xaxes(rangemode='tozero',row=1,col=2);fig.update_xaxes(rangemode='tozero',row=1,col=3)
    fig.update_yaxes(range=[float(base.z_fin_m.max()),0])
    fig.update_yaxes(title='Profundidad vertical (m)',row=1,col=1)
    return fig

def multiples(b,alternativas,modo,carga=None):
    fig=go.Figure()
    for i,(n,L,R,lim) in enumerate(curvas_parciales(b,alternativas,modo)):
        # Usar el cruce exacto, sin interpolar sobre un intervalo ya limitado.
        x,y=envolvente(L,R,lim)
        fig.add_scatter(x=x,y=y,name=n,mode='lines',line=dict(color=COLORES[i%len(COLORES)],width=2.6))
    if carga is not None: fig.add_hline(y=carga,line_dash='dash',line_color='#b45309',annotation_text='Acción')
    _estilo(fig,'Envolventes parciales terreno–armadura',510)
    fig.update_xaxes(title='Longitud axial (m)');fig.update_yaxes(title='Capacidad parcial (kN)',rangemode='tozero')
    return fig

def barras_acero(alternativas):
    fig=go.Figure()
    for campo,n,c in [('limite_c_kN','Compresión','#2563eb'),('limite_t_kN','Tracción','#0d9488')]:
        fig.add_bar(y=[a['alternativa'] for a in alternativas],x=[a.get(campo) for a in alternativas],orientation='h',name=n,marker_color=c)
    _estilo(fig,'Límites adoptados de armadura (no carga comercial)',max(420,130+len(alternativas)*45))
    fig.update_layout(barmode='group');fig.update_yaxes(autorange='reversed');fig.update_xaxes(title='Capacidad (kN)')
    return fig

def inversa(b,alternativas,modo):
    fig=go.Figure()
    for i,(n,L,R,lim) in enumerate(curvas_parciales(b,alternativas,modo)):
        x,y=envolvente(L,R,lim);xx=[];yy=[]
        # Cada segmento creciente es una rama de la inversa; los escalones nulos
        # no se conectan artificialmente ni se extrapolan.
        for j in range(len(x)-1):
            if y[j+1]>y[j]:
                xx.extend([y[j],y[j+1],None]);yy.extend([x[j],x[j+1],None])
        if not xx: xx=[y[0]];yy=[x[0]]
        fig.add_scatter(x=xx,y=yy,mode='lines+markers',name=n,line=dict(color=COLORES[i%len(COLORES)],width=2),marker=dict(size=3))
    _estilo(fig,'Longitud axial necesaria dentro del intervalo',500)
    fig.update_xaxes(title='Acción (kN)');fig.update_yaxes(title='Longitud axial (m)')
    return fig

def mapa(m):
    fig=go.Figure(go.Heatmap(z=m.to_numpy(),x=m.columns.tolist(),y=m.index.tolist(),
        colorscale=[[0,'#e8f3ef'],[.5,'#2d887d'],[.50001,'#f5d6bd'],[1,'#b45309']],
        zmin=0,zmax=200,colorbar=dict(title='%'),hovertemplate='%{x}<br>L=%{y:.2f} m<br>%{z:.2f}%<extra></extra>'))
    _estilo(fig,'Aprovechamiento respecto a capacidad parcial',520)
    fig.update_yaxes(title='Longitud axial (m)',autorange='reversed');fig.update_xaxes(title='Alternativa')
    return fig

def grafica_sensibilidad(df,diam,modo):
    fig=go.Figure();g=df[(df.D_mm-diam).abs()<1e-7]
    campo=CAMPOS[modo][0]
    for n,c,dash in [('Inferior','#64748b','dash'),('Central','#2563eb','solid'),('Superior','#0d9488','dash')]:
        h=g[g.escenario==n]
        fig.add_scatter(x=h.L_m,y=h[campo],name=n,mode='lines',line=dict(color=c,dash=dash,width=2.5))
    _estilo(fig,'Escenarios deterministas de adherencia',460)
    fig.update_xaxes(title='Longitud axial (m)');fig.update_yaxes(title='Resistencia por fuste (kN)')
    return fig
