"""Esquema proporcional en planta de la zapata rectangular."""
import plotly.graph_objects as go


def figura_esquema_cimentacion(b_m: float, l_m: float) -> go.Figure:
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=l_m, y1=b_m,
                  line=dict(color="#2164AF", width=3), fillcolor="rgba(33,100,175,.12)")
    fig.add_annotation(x=l_m / 2, y=b_m / 2, text="Presión neta uniforme q",
                       showarrow=False, font=dict(size=13, color="#12304A"))
    fig.add_annotation(x=l_m / 2, y=b_m * 1.12, text=f"L = {l_m:.2f} m",
                       showarrow=False, font=dict(size=12))
    fig.add_annotation(x=-l_m * .10, y=b_m / 2, text=f"B = {b_m:.2f} m",
                       textangle=-90, showarrow=False, font=dict(size=12))
    fig.update_xaxes(visible=False, range=[-l_m * .2, l_m * 1.12], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[-b_m * .2, b_m * 1.28])
    fig.update_layout(height=290, margin=dict(l=12, r=12, t=8, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def figura_perfil_estratos(estratos, df_m: float, nivel_freatico_m: float) -> go.Figure:
    """Sección esquemática, sin interpolar ni inferir geometría geológica."""
    fig = go.Figure()
    colores = ["#DDE9F5", "#E4F0E9", "#F5EBDD", "#EDE8F5", "#E7EEF0"]
    limite = max(float(df_m) + 1, float(nivel_freatico_m) + 1)
    for i, (_, capa) in enumerate(estratos.iterrows()):
        try:
            z0, z1 = float(capa["z_sup_m"]), float(capa["z_inf_m"])
            if not (0 <= z0 < z1):
                continue
            limite = max(limite, z1)
            fig.add_shape(type="rect", x0=0, x1=1, y0=z0, y1=z1,
                          line=dict(color="#8C9BAA", width=1), fillcolor=colores[i % len(colores)])
            fig.add_annotation(x=.5, y=(z0+z1)/2, text=str(capa["Estrato"]),
                               showarrow=False, font=dict(color="#12304A", size=12))
        except (ValueError, TypeError, KeyError):
            continue
    fig.add_hline(y=df_m, line_color="#2164AF", line_width=3,
                  annotation_text="Base de apoyo", annotation_position="top right")
    fig.add_hline(y=nivel_freatico_m, line_color="#0D9488", line_dash="dash",
                  annotation_text="Nivel freático", annotation_position="bottom right")
    fig.update_xaxes(visible=False, range=[-.15, 1.45])
    fig.update_yaxes(title="Profundidad desde superficie (m)", autorange="reversed", range=[limite, 0])
    fig.update_layout(height=320, margin=dict(l=12, r=12, t=15, b=12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig
