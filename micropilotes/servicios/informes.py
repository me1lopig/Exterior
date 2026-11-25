"""Exportaciones desde un único resultado, sin recalcular ni redondear el motor."""
from io import BytesIO
from xml.sax.saxutils import escape
import math
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import ScatterChart, Series, Reference
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from matplotlib.figure import Figure

from resultados.parametricos import matriz_fuste, matriz_unitaria, matriz_parcial, aprovechamiento, longitudes

LIMITACIONES=[
    'Predimensionamiento axial de micropilote aislado. No equivale a comprobación global ELU/ELS.',
    'Punta +15 % solo hipótesis máxima no verificada; no interviene en envolventes.',
    'Fuste sin peso propio favorable ni rozamiento negativo. Cavidades y tramos con camisa perdida deben desactivarse.',
    'Capacidades de acero parciales con coacción y corrosión constantes; verificar materiales, empalmes y ejecución.',
    'Carga comercial CS550/CSTM80 informativa, no resistencia de cálculo.',
    'Fuente: Guía DGC, octubre de 2005, apartados 3.3, 3.4, 3.6 y tablas aplicables. Revisar normativa del proyecto.'
]
def plano(d):
    return [{'Parámetro':k,'Valor':str(v) if isinstance(v,(dict,list)) else v} for k,v in d.items()]

def tablas(s):
    e=s['entrada']; b=pd.DataFrame(s['barrido'])
    a=pd.DataFrame(s.get('armaduras',[]))
    d=[]
    for diam,r in s['detalle_Lmax'].items():
        d.extend([dict(D_mm=float(diam),**t) for t in r['tramos']])
    conf={k:v for k,v in e.items() if k not in ('estratos','armaduras','adherencias_MPa')}
    ge=pd.DataFrame(e['estratos'])
    cc=['D_mm','L_m','z_m','Rc_fuste_kN','punta_max_hipotetica_kN','Rc_max_hipotetica_kN']
    tt=['D_mm','L_m','z_m','Rt_fuste_kN']
    co=[{'Parámetro':'Fr','Valor':e['Fr'],'Referencia':'Tabla 3.2'},
        {'Parámetro':'eta','Valor':.6 if e['alternancia'] else .75,'Referencia':'3.4.2.3'},
        {'Parámetro':'gamma acero','Valor':1.1,'Referencia':'3.6'},
        {'Parámetro':'fyd,c máximo MPa','Valor':400,'Referencia':'3.6.1'}]
    ar=e.get('armaduras',{})
    if ar: co.extend(plano({k:ar.get(k) for k in ('union','ejecucion','CR','corrosion_mm','vida','coaccion')}))
    warnings=list(LIMITACIONES)
    if not e.get('control_presiones'): warnings.append('Control numérico de presiones no realizado.')
    if ar.get('error_entrada'): warnings.append(str(ar['error_entrada']))
    base={'Proyecto':pd.DataFrame(plano(conf)),'Geotecnia':ge,'Coeficientes':pd.DataFrame(co),
            'Armaduras':pd.DataFrame(ar.get('tubos',[])),
            'Compresion':b.reindex(columns=cc),'Traccion':b.reindex(columns=tt),
            'Comparativas':a,'Detalle_Lmax':pd.DataFrame(d),
            'Advertencias':pd.DataFrame({'Advertencia':warnings})}
    # Mantener hojas previas y añadir matrices desde los mismos resultados.
    for m,n in [('c','C'),('t','T')]:
        base['Matriz_Fuste_'+n]=matriz_fuste(b,m).reset_index()
        if s.get('unitarios'):
            base['Unitarios_'+n]=matriz_unitaria(pd.DataFrame(s['unitarios']),m)
        if s.get('armaduras'):
            p=matriz_parcial(b,s['armaduras'],m)
            base['Envolventes_'+n]=p.reset_index()
            ed=e.get('Nc_Ed_kN' if m=='c' else 'Nt_Ed_kN')
            if ed is not None:
                base['Aprovechamiento_'+n]=aprovechamiento(p,ed).reset_index()
                base['Longitudes_'+n]=longitudes(b,s['armaduras'],m,ed)
    if s.get('sensibilidad'): base['Sensibilidad']=pd.DataFrame(s['sensibilidad'])
    if e.get('adherencias_MPa'): base['Adherencias_MPa']=pd.DataFrame(e['adherencias_MPa'])
    if s.get('inyecciones_no_evaluadas'):
        base['Inyecciones_pendientes']=pd.DataFrame([{'procedimiento':n,'motivo':v} for n,v in s['inyecciones_no_evaluadas'].items()])
    for n,r in s.get('resultados_inyeccion',{}).items():
        b2=pd.DataFrame(r['barrido']);u=pd.DataFrame(r['unitarios']);ar2=r['armaduras']
        base[n+'_Fuste']=b2
        base[n+'_Unitarios']=u
        base[n+'_Estratos']=pd.DataFrame(r['estratos'])
        if ar2: base[n+'_Armaduras']=pd.DataFrame(ar2)
        for m,suf in [('c','C'),('t','T')]:
            if ar2:
                mat=matriz_parcial(b2,ar2,m)
                base[n+'_Env_'+suf]=mat.reset_index()
                ed=e.get('Nc_Ed_kN' if m=='c' else 'Nt_Ed_kN')
                if ed is not None:
                    base[n+'_Aprov_'+suf]=aprovechamiento(mat,ed).reset_index()
                    base[n+'_Long_'+suf]=longitudes(b2,ar2,m,ed)
    return base

def valor(v):
    if v is None: return None
    if isinstance(v,(list,dict)): return str(v)
    if pd.isna(v): return None
    return v.item() if hasattr(v,'item') else v

def texto(v):
    v=valor(v)
    if v is None:return '—'
    if isinstance(v,float):return f'{v:.2f}'
    return str(v)

def excel(s):
    wb=Workbook(); wb.remove(wb.active)
    conjunto=tablas(s)
    for nombre,df in conjunto.items():
        ws=wb.create_sheet(nombre)
        if len(df.columns)==0:
            ws.append(['Sin datos']);continue
        ws.append(list(df.columns))
        for row in df.itertuples(index=False,name=None):
            ws.append([valor(v) for v in row])
            for c in ws[ws.max_row]:
                if isinstance(c.value,str):c.data_type='s'
                elif isinstance(c.value,(int,float)) and not isinstance(c.value,bool):c.number_format='0.00'
        for c in ws[1]:
            c.fill=PatternFill('solid',fgColor='183B56');c.font=Font(color='FFFFFF',bold=True);c.alignment=Alignment(wrap_text=True)
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for i,col in enumerate(df.columns,1):
            sample=[len(str(col))]+[len(texto(v)) for v in df[col].head(150)]
            ws.column_dimensions[get_column_letter(i)].width=min(65,max(14,max(sample)+2))
    ws=wb.create_sheet('Graficas')
    for pos,modo,col in [('A1','Compresion','Rc_fuste_kN'),('A19','Traccion','Rt_fuste_kN')]:
        df=conjunto[modo]; src=wb[modo]; chart=ScatterChart()
        chart.title='Fuste · '+modo;chart.x_axis.title='Longitud axial (m)';chart.y_axis.title='Resistencia (kN)'
        chart.width=23;chart.height=10;chart.scatterStyle='line'
        for diam,group in df.groupby('D_mm',sort=False):
            idx=group.index.tolist()
            if idx!=list(range(idx[0],idx[-1]+1)): continue
            x=Reference(src,min_col=2,min_row=idx[0]+2,max_row=idx[-1]+2)
            y=Reference(src,min_col=list(df.columns).index(col)+1,min_row=idx[0]+2,max_row=idx[-1]+2)
            chart.series.append(Series(y,x,title=f'D {diam:g} mm'))
        ws.add_chart(chart,pos)
    out=BytesIO();wb.save(out);return out.getvalue()

def figura(s,modo):
    b=pd.DataFrame(s['barrido']);f=Figure(figsize=(8.3,4.1),dpi=140);ax=f.subplots()
    campo='Rc_fuste_kN' if modo=='Compresión' else 'Rt_fuste_kN'
    for diam,g in b.groupby('D_mm'):
        line,=ax.plot(g.L_m,g[campo],label=f'Ø {diam:g} mm',linewidth=2)
        if modo=='Compresión' and s['entrada']['punta_hipotetica']:
            ax.plot(g.L_m,g.Rc_max_hipotetica_kN,linestyle=':',color=line.get_color(),linewidth=1.3)
    ax.set(xlabel='Longitud axial (m)',ylabel='Resistencia por fuste (kN)',title=modo+' · curvas resistentes')
    ax.grid(alpha=.25);ax.legend(fontsize=8,ncol=2);f.tight_layout()
    out=BytesIO();f.savefig(out,format='png');out.seek(0);return out

def perfil(s):
    f=Figure(figsize=(8.3,4.6),dpi=140);a,b=f.subplots(1,2,sharey=True)
    e=s['entrada'];r=next(iter(s['detalle_Lmax'].values()));z=r['profundidad']
    for i,t in enumerate(e['estratos']):
        zi,zf=t['inicio_m'],t['fin_m']
        a.axhspan(zi,zf,color=['#dfd2b9','#bca58d','#e8d8a3','#ccd3d6'][i%4],ec='#aaa',lw=.5)
        a.text(.95,(zi+zf)/2,str(t['nombre']),ha='right',va='center',fontsize=8)
    a.plot([.25,.25],[0,z],color='#334155',lw=5)
    a.set(xlim=(0,1),xticks=[],ylabel='Profundidad vertical (m)',title='Estratigrafía (esquema)')
    for campo,color,label in [('r_lim','#2563eb','Límite'),('r_calculo','#0d9488','Admisible')]:
        xs=[];ys=[]
        for t in r['tramos']:xs.extend([t[campo]]*2);ys.extend([t['z_inicio'],t['z_fin']])
        b.plot(xs,ys,color=color,label=label,lw=2)
    for ax in (a,b):
        ax.axhline(z,color='#2563eb',ls=':')
        if e['estratos'][-1]['fin_m']>=5:ax.axhline(5,color='#b45309',ls='--')
    b.set(xlabel='Adherencia (kPa)',title='Adherencias aplicadas')
    b.legend(fontsize=8);a.set_ylim(e['estratos'][-1]['fin_m'],0);f.tight_layout()
    out=BytesIO();f.savefig(out,format='png');out.seek(0);return out

def figura_unitaria(s,modo):
    df=pd.DataFrame(s['unitarios']);campo='qc_kN_m' if modo=='Compresión' else 'qt_kN_m'
    f=Figure(figsize=(8.3,4.1),dpi=170);ax=f.subplots()
    for d,g in df.groupby('D_mm'):
        x=[];y=[]
        for t in g.itertuples():
            x.extend([getattr(t,campo)]*2);y.extend([t.z_inicio_m,t.z_fin_m])
        ax.plot(x,y,lw=2,label=f'Ø {d:g} mm')
    ax.set(xlabel='Resistencia unitaria (kN/ml)',ylabel='Profundidad vertical (m)',title=modo+' · fuste por metro axial')
    ax.invert_yaxis();ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2);f.tight_layout()
    out=BytesIO();f.savefig(out,format='png');out.seek(0);return out

def figura_inyecciones(s,modo,diam):
    campo='Rc_fuste_kN' if modo=='Compresión' else 'Rt_fuste_kN'
    f=Figure(figsize=(8.3,4.1),dpi=160);ax=f.subplots()
    colores={'IU':'#64748b','IR':'#2563eb','IRS':'#0d9488','Mixto':'#7c3aed'}
    for n,r in s['resultados_inyeccion'].items():
        b=pd.DataFrame(r['barrido']);g=b[b.D_mm.sub(diam).abs()<1e-7]
        ax.plot(g.L_m,g[campo],label=n,color=colores[n],lw=2,linestyle={'IU':':','IR':'--','IRS':'-','Mixto':'-.'}[n])
    ax.set(title=f'{modo} · Ø {diam:g} mm · comparación de inyección',xlabel='Longitud axial (m)',ylabel='Resistencia por fuste (kN)')
    ax.grid(alpha=.2);ax.legend(fontsize=8);f.tight_layout()
    out=BytesIO();f.savefig(out,format='png');out.seek(0);return out

def figuras_documento(s):
    out=[('Perfil geotécnico',perfil(s)),('Compresión',figura(s,'Compresión')),('Tracción',figura(s,'Tracción'))]
    if s.get('unitarios'):
        out.extend([(m+' · resistencia unitaria',figura_unitaria(s,m)) for m in ('Compresión','Tracción')])
    if s.get('resultados_inyeccion'):
        for d in sorted({float(x['D_mm']) for x in s['barrido']}):
            for m in ('Compresión','Tracción'):
                out.append((f'{m} · inyecciones · Ø {d:g} mm',figura_inyecciones(s,m,d)))
    return out

def resumen(s):
    b=pd.DataFrame(s['barrido']);a=pd.DataFrame(s.get('armaduras',[]))
    ge=pd.DataFrame(s['entrada']['estratos'])
    out=[('Modelo geotécnico',ge.reindex(columns=['nombre','espesor_m','inyeccion','adlim_kPa','fr','activo'])),
         ('Capacidades a longitud máxima',b.groupby('D_mm',as_index=False).tail(1).reindex(columns=['D_mm','L_m','Rc_fuste_kN','Rt_fuste_kN'])),
         ('Armaduras y envolventes parciales',a.reindex(columns=['alternativa','limite_c_kN','limite_t_kN','Rc_parcial_Lmax_kN','Rt_parcial_Lmax_kN','estado']))]
    if s.get('unitarios'):
        u=pd.DataFrame(s['unitarios'])
        # Formato largo evita tablas demasiado anchas en Word/PDF.
        out.append(('Resistencia unitaria por tramo (kN/ml)',u[['unidad','z_inicio_m','z_fin_m','inyeccion_efectiva','D_mm','qc_kN_m','qt_kN_m']]))
    if s['entrada'].get('adherencias_MPa'):
        out.append(('Adherencias límite de entrada (MPa)',pd.DataFrame(s['entrada']['adherencias_MPa'])))
    if s.get('resultados_inyeccion'):
        bb=[];uu=[]
        for n,r in s['resultados_inyeccion'].items():
            g=pd.DataFrame(r['barrido']).groupby('D_mm',as_index=False).tail(1).copy()
            g.insert(0,'procedimiento',n);bb.append(g)
            u=pd.DataFrame(r['unitarios']);u.insert(0,'procedimiento',n);uu.append(u)
        out.append(('Comparación por procedimiento a longitud máxima',pd.concat(bb,ignore_index=True)[['procedimiento','D_mm','L_m','Rc_fuste_kN','Rt_fuste_kN']]))
        out.append(('Resistencias unitarias por procedimiento (kN/ml)',pd.concat(uu,ignore_index=True)[['procedimiento','z_inicio_m','z_fin_m','inyeccion_efectiva','D_mm','qc_kN_m','qt_kN_m']]))
    if s.get('inyecciones_no_evaluadas'):
        out.append(('Procedimientos no evaluados',pd.DataFrame([{'procedimiento':n,'motivo':v} for n,v in s['inyecciones_no_evaluadas'].items()])))
    return out

def introduccion(s):
    e=s['entrada']
    return [f"Proyecto: {e['proyecto']} | Autor: {e.get('autor','')} | Revisión: {e.get('revision','')}",
        f"Versión: {s['version']} | Longitudes {e['L_min_m']:.2f}–{e['L_max_m']:.2f} m | Paso {e['paso_m']:.2f} m | Inclinación {e['angulo_grados']:.2f}° | Fr {e['Fr']}",
        'Procedimiento principal: '+str(e.get('procedimiento_principal','Según modelo geotécnico'))+'. Las comparaciones emplean las mismas hipótesis estructurales.',
        'Compresión: sumatorio de pi D Li rf,lim / Fr. Tracción por fuste: eta por la resistencia de compresión. IU en los primeros 5 m verticales.',
        'Acero: área residual geométrica; fyd,c = min(fy/1,10; 400 MPa); Nc,acero = Aa fyd,c R/(1,20 Fe); Nt,acero = Aa fy/(1,10 x 1,10). Aa incluye el factor de unión correspondiente.',
        'El Excel y CSV contienen el barrido completo. Esta memoria recoge las capacidades a longitud máxima y las figuras del intervalo.']

def word(s):
    doc=Document();style=doc.styles['Normal'];style.font.name='Calibri';style.font.size=Pt(10)
    doc.sections[0].header.paragraphs[0].text='GEO_APP  |  MICROPILOTES'
    doc.add_heading('Memoria de predimensionamiento axial',0)
    for v in introduccion(s):doc.add_paragraph(v)
    for title,df in resumen(s):
        doc.add_heading(title,level=1)
        if df.empty:doc.add_paragraph('Sin datos.');continue
        t=doc.add_table(rows=1,cols=len(df.columns));t.style='Light Shading Accent 1'
        for c,v in zip(t.rows[0].cells,df.columns):c.text=str(v)
        for row in df.itertuples(index=False,name=None):
            for c,v in zip(t.add_row().cells,row):c.text=texto(v)
    for title,buf in figuras_documento(s):
        doc.add_page_break();doc.add_heading(title,1);doc.add_picture(buf,width=Inches(6.2))
    doc.add_heading('Limitaciones y referencias',1)
    for v in tablas(s)['Advertencias']['Advertencia']:doc.add_paragraph(v)
    out=BytesIO();doc.save(out);return out.getvalue()

def pdf(s):
    out=BytesIO();size=landscape(A4);doc=SimpleDocTemplate(out,pagesize=size,rightMargin=36,leftMargin=36,topMargin=40,bottomMargin=36)
    styles=getSampleStyleSheet()
    def p(x,sty='BodyText'):return Paragraph(escape(str(x)),styles[sty])
    story=[p('GEO_APP | Micropilotes','Title'),p('Memoria de predimensionamiento axial','Heading1')]
    for v in introduccion(s):story.extend([p(v),Spacer(1,5)])
    for title,df in resumen(s):
        story.extend([Spacer(1,10),p(title,'Heading2')])
        if df.empty:story.append(p('Sin datos.'));continue
        rows=[[p(v) for v in df.columns]]+[[p(texto(v)) for v in row] for row in df.itertuples(index=False,name=None)]
        t=LongTable(rows,repeatRows=1,colWidths=[(size[0]-72)/len(df.columns)]*len(df.columns))
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE8F0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F6F8')]),('GRID',(0,0),(-1,-1),.25,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.append(t)
    for title,buf in figuras_documento(s):
        story.extend([PageBreak(),p(title,'Heading1'),Image(buf,width=670,height=370 if title=='Perfil geotécnico' else 331)])
    story.append(p('Limitaciones y referencias','Heading1'))
    for v in tablas(s)['Advertencias']['Advertencia']:story.append(p(v))
    def pie(c,d):
        c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#334155'));c.drawString(36,20,'Geo_App | Predimensionamiento axial');c.drawRightString(size[0]-36,20,f'Página {d.page}')
    doc.build(story,onFirstPage=pie,onLaterPages=pie);return out.getvalue()
