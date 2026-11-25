"""Figuras tecnicas de resultados calculados; no modifican las resistencias."""
from html import escape
from math import cos, radians, sin
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from calculos.estructural import seccion

AZUL='#2563eb'
VERDE='#0d9488'
NARANJA='#b45309'
COLORES=['#2563eb','#0d9488','#b45309','#7c3aed','#475569','#be185d','#0891b2']

def _estilo(fig, titulo, altura=470):
    fig.update_layout(template='plotly_white', title=dict(text=titulo,x=.02),
                      height=altura, margin=dict(l=58,r=28,t=85,b=68),
                      font=dict(family='Arial',size=12,color='#334155'),
                      legend=dict(orientation='h',y=-.2,x=0),
                      hovermode='closest')
    fig.update_xaxes(showgrid=True,gridcolor='#e2e8f0',zeroline=False)
    fig.update_yaxes(showgrid=True,gridcolor='#e2e8f0',zeroline=False)
    return fig

def perfil_adherencias(filas, r, longitud, angulo):
    """Profundidades verticales compartidas; micropilote de grosor simbolico."""
    zmax=filas[-1]['fin_m']
    xfin=longitud*sin(radians(angulo))
    margen=max(1.,zmax*.10)
    xmin,xmax=-margen,xfin+margen
    fig=make_subplots(rows=1,cols=2,shared_yaxes=True,
                      column_widths=[.52,.48],horizontal_spacing=.12,
                      subplot_titles=['Perfil longitudinal','Adherencias aplicadas'])
    paleta=['#e6ded0','#d3baa2','#f0e3b9','#c8c7b9','#d4e2e4']
    for i,f in enumerate(filas):
        za,zb=f['inicio_m'],f['fin_m']
        c=paleta[i%len(paleta)] if f['activo'] else '#e5e7eb'
        fig.add_trace(go.Scatter(x=[xmin,xmax,xmax,xmin,xmin],y=[za,za,zb,zb,za],
                      fill='toself',fillcolor=c,line=dict(color='#948a7b',width=.8),
                      name=escape(str(f['nombre'])),showlegend=False,
                      hovertemplate=escape(str(f['nombre']))+'<br>'+f'{za:.2f} a {zb:.2f} m'+'<extra></extra>'),row=1,col=1)
        fig.add_annotation(x=xmax,y=(za+zb)/2,text=escape(str(f['nombre']))+' · '+str(f['inyeccion']),
                           xanchor='right',showarrow=False,font=dict(size=10,color='#334155'),
                           bgcolor='rgba(255,255,255,.7)',row=1,col=1)
    fig.add_trace(go.Scatter(x=[0,xfin],y=[0,r['profundidad']],mode='lines+markers',
                  line=dict(color='#334155',width=7),marker=dict(size=6),name='Eje micropilote',
                  hovertemplate='x=%{x:.2f} m<br>z=%{y:.2f} m<extra></extra>'),row=1,col=1)
    for campo,nombre,color in [('r_lim','Adherencia limite',AZUL),('r_calculo','Adherencia de calculo',VERDE)]:
        xs,ys=[],[]
        for t in r['tramos']:
            xs.extend([t[campo],t[campo]])
            ys.extend([t['z_inicio'],t['z_fin']])
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color=color,width=3),name=nombre,
                      hovertemplate='%{x:.1f} kPa · z=%{y:.2f} m<extra></extra>'),row=1,col=2)
    zpunta=r['profundidad']
    if zmax-zpunta>1e-8:
        for col in (1,2):
            fig.add_hrect(y0=zpunta,y1=zmax,fillcolor='#94a3b8',opacity=.19,
                          line_width=0,layer='above',row=1,col=col)
        fig.add_annotation(x=(xmin+xmax)/2,y=(zpunta+zmax)/2,
                           text='Terreno reconocido<br>no atravesado',showarrow=False,
                           font=dict(size=11,color='#334155'),bgcolor='rgba(255,255,255,.85)',row=1,col=1)
    for col in (1,2):
        fig.add_hline(y=zpunta,line=dict(color=AZUL,dash='dot',width=1.6),row=1,col=col)
    fig.add_annotation(x=0.99,xref='x2 domain',y=zpunta,yref='y2',
                       text=f'L máxima: {longitud:.2f} m · z: {zpunta:.2f} m',
                       xanchor='right',yanchor='bottom',showarrow=False,
                       font=dict(size=10,color=AZUL),bgcolor='rgba(255,255,255,.9)')
    if zmax>=5:
        fig.add_hline(y=5,line=dict(color=NARANJA,dash='dash',width=1.5),row=1,col=1)
        fig.add_hline(y=5,line=dict(color=NARANJA,dash='dash',width=1.5),
                      annotation_text='Limite IU: 5 m',annotation_position='top right',row=1,col=2)
    _estilo(fig,'Perfil geotécnico reconocido y adherencias efectivas',540)
    fig.update_xaxes(title_text='Desplazamiento horizontal (m)',range=[xmin,xmax],row=1,col=1)
    fig.update_xaxes(title_text='Adherencia (kPa)',rangemode='tozero',row=1,col=2)
    fig.update_yaxes(title_text='Profundidad vertical (m)',range=[zmax,0],row=1,col=1)
    fig.update_yaxes(range=[zmax,0],row=1,col=2)
    return fig

def puntos_fuste(r):
    """Nodos exactos de la funcion lineal a trozos, sin punta ni peso."""
    L,C,T=[0.],[0.],[0.]
    for t in r['tramos']:
        L.append(L[-1]+t['longitud_axial'])
        C.append(C[-1]+t['compresion'])
        T.append(T[-1]+t['traccion'])
    return L,C,T

def curvas_fuste(casos, angulo):
    """casos: pares (etiqueta, resultado motor) con hipotesis propias."""
    fig=make_subplots(rows=1,cols=2,shared_yaxes=False,
                      subplot_titles=['Compresion por fuste','Traccion por fuste'])
    for i,(nombre,r) in enumerate(casos):
        L,C,T=puntos_fuste(r)
        for col,serie in [(1,C),(2,T)]:
            fig.add_trace(go.Scatter(x=L,y=serie,mode='lines+markers',name=nombre,
                          legendgroup=nombre,showlegend=(col==1),marker=dict(size=4),
                          line=dict(color=COLORES[i%len(COLORES)],width=2.5),
                          hovertemplate='L=%{x:.2f} m<br>R=%{y:.1f} kN<extra>%{fullData.name}</extra>'),row=1,col=col)
    l5=5/cos(radians(angulo))
    if any(puntos_fuste(r)[0][-1]>=l5 for _,r in casos):
        for col in (1,2):
            fig.add_vline(x=l5,line=dict(color=NARANJA,dash='dash',width=1),row=1,col=col)
    _estilo(fig,'Resistencia de calculo por fuste frente a longitud',480)
    fig.update_xaxes(title_text='Longitud axial (m)',rangemode='tozero')
    fig.update_yaxes(title_text='Resistencia (kN)',rangemode='tozero')
    return fig

def contribucion(r):
    etiquetas=[f"{t['z_inicio']:.2f}–{t['z_fin']:.2f}" for t in r['tramos']]
    fig=go.Figure()
    for k,n,c in [('compresion','Compresion',AZUL),('traccion','Traccion',VERDE)]:
        fig.add_bar(x=etiquetas,y=[t[k] for t in r['tramos']],name=n,marker_color=c,
                    hovertemplate='%{x} m: %{y:.2f} kN<extra>%{fullData.name}</extra>')
    _estilo(fig,'Contribucion resistente de cada tramo',420)
    fig.update_layout(barmode='group')
    fig.update_xaxes(title_text='Intervalo vertical (m)',type='category')
    fig.update_yaxes(title_text='Resistencia de calculo (kN)')
    return fig

def seccion_transversal(D, dp, de, t, re, relleno):
    """Seccion unica a escala: acero original, merma radial exterior y acero residual."""
    s=seccion(de,t,re)
    original=s['a_nominal_mm2']/100
    residual=s['a_residual_mm2']/100
    perdida=original-residual
    pct=100*perdida/original
    fig=go.Figure()
    def circulo(diam,fill,line,dash='solid',width=1.2):
        rad=diam/2
        fig.add_shape(type='circle',x0=-rad,x1=rad,y0=-rad,y1=rad,
                      fillcolor=fill,line=dict(color=line,width=width,dash=dash))
    circulo(dp,'rgba(0,0,0,0)',NARANJA,'dash')
    circulo(D,'#dcd9d1','#948a7b')
    if re>0:
        circulo(de,'#e58c47','#b45309',width=.8)
    circulo(s['de_residual_mm'],'#475569','#334155',width=.8)
    circulo(s['di_mm'],'#dcd9d1' if relleno else '#ffffff','#334155')
    leyenda=[('Perforación',NARANJA),('Nominal / lechada','#b8b1a5'),('Acero residual','#475569')]
    if re>0: leyenda.append(('Acero perdido por corrosión','#e58c47'))
    for n,c in leyenda:
        fig.add_trace(go.Scatter(x=[None],y=[None],mode='markers',marker=dict(color=c,size=10),name=n))
    titulo=(f'Sección tubular Ø {de:g} × {t:g} mm · D={D:g} mm · perforación={dp:g} mm'
            f'<br><sup>Merma de área: {perdida:.2f} cm² ({pct:.2f} %) · pérdida radial: {re:.2f} mm · espesor residual: {t-re:.2f} mm</sup>')
    _estilo(fig,titulo,520)
    fig.update_layout(margin=dict(l=58,r=28,t=92,b=85),legend=dict(orientation='h',y=-.20,x=.5,xanchor='center'))
    lim=max(dp,D,de)*.6
    fig.update_xaxes(range=[-lim,lim],title_text='mm',constrain='domain')
    fig.update_yaxes(range=[-lim,lim],title_text='mm',scaleanchor='x',scaleratio=1)
    return fig

def _envolvente(L, valores, tope):
    """Inserta el cruce exacto para evitar interpolacion diagonal en el tope."""
    x,y=[L[0]],[min(valores[0],tope)]
    for a,b,u,v in zip(L,L[1:],valores,valores[1:]):
        if u<tope<v:
            x.append(a+(b-a)*(tope-u)/(v-u)); y.append(tope)
        x.append(b); y.append(min(v,tope))
    return x,y

def comparacion_parcial(r, se, acciones):
    L,C,T=puntos_fuste(r)
    fig=make_subplots(rows=1,cols=2,subplot_titles=['Compresion','Traccion'])
    for col,vals,lim,ed in [(1,C,se['nc_kN'],acciones[0]),(2,T,se['nt_kN'],acciones[1])]:
        x,y=_envolvente(L,vals,lim)
        for xx,yy,n,c,dash in [(L,vals,'Fuste',AZUL,'solid'),([L[0],L[-1]],[lim,lim],'Seccion fija',NARANJA,'dash'),
                               (x,y,'Envolvente parcial',VERDE,'solid')]:
            fig.add_trace(go.Scatter(x=xx,y=yy,mode='lines',name=n,legendgroup=n,showlegend=(col==1),
                          line=dict(color=c,width=3 if n=='Envolvente parcial' else 2,dash=dash)),row=1,col=col)
        if ed>0:
            fig.add_trace(go.Scatter(x=[L[0],L[-1]],y=[ed,ed],mode='lines',name='Accion de calculo',
                          legendgroup='accion',showlegend=(col==1),line=dict(color='#dc2626',dash='dot')),row=1,col=col)
    _estilo(fig,'Comparacion parcial: fuste y seccion fija',480)
    fig.update_xaxes(title_text='Longitud axial (m)',rangemode='tozero')
    fig.update_yaxes(title_text='Resistencia (kN)',rangemode='tozero')
    return fig
