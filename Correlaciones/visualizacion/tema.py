"""Tema visual de la aplicacion."""


CSS = """
<style>
:root {
  --ink: #10263f;
  --muted: #66758a;
  --line: #dfe4ea;
  --panel: #f4f6f8;
  --accent: #e45155;
  --ok: #16835a;
}
.stApp { background: #ffffff; color: var(--ink); }
[data-testid="stSidebar"] { background: #f7f8fa; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--ink); letter-spacing: 0; }
h1, h2, h3 { color: var(--ink); letter-spacing: 0 !important; }
h1 { font-size: 2rem !important; font-weight: 760 !important; margin-bottom: .2rem !important; }
h2 { font-size: 1.3rem !important; margin-top: 1.1rem !important; }
h3 { font-size: 1rem !important; }
p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
.stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); }
.stButton > button { border-radius: 4px; min-height: 2.5rem; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border: 1px solid var(--line); border-radius: 4px; }
[data-baseweb="tab-list"] { gap: 1.15rem; border-bottom: 1px solid var(--line); }
[data-baseweb="tab"] { padding-left: 0; padding-right: 0; }
[aria-selected="true"] { color: var(--accent) !important; }
.geo-kicker { color: var(--accent); text-transform: uppercase; font-size: .72rem; font-weight: 700; }
.geo-lead { max-width: 760px; margin-top: 0; }
.geo-rule { border-top: 1px solid var(--line); margin: 1rem 0; }
.geo-status { padding: .75rem .9rem; border-left: 3px solid var(--ok); background: #edf8f3; color: #146343; }
.geo-warning { padding: .75rem .9rem; border-left: 3px solid #c98910; background: #fff7e7; color: #76520b; }
.geo-method { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .78rem; color: #36516f; }
div[data-testid="stMetric"] { background: transparent; border-bottom: 1px solid var(--line); padding: .25rem 0 .65rem; }
</style>
"""

