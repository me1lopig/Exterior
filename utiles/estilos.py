CSS_APP = """
<style>
    :root {
        --geo-ink: #12304A;
        --geo-muted: #6F7F91;
        --geo-accent: #E45454;
        --geo-blue: #2164AF;
        --geo-line: #D9DEE6;
        --geo-input: #F0F3F7;
        --geo-success: #E3F5EA;
    }
    .stApp { background: #FFFFFF; color: var(--geo-ink); }
    .block-container { max-width: 1320px; padding-top: 2.1rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--geo-ink); letter-spacing: 0 !important; }
    h1 { font-size: 2.1rem !important; font-weight: 760 !important; margin-bottom: .25rem !important; }
    h2 { font-size: 1.35rem !important; margin-top: 1.2rem !important; }
    h3 { font-size: 1.05rem !important; }
    [data-testid="stCaptionContainer"] { color: var(--geo-muted); }
    [data-baseweb="tab-list"] { gap: 1.15rem; border-bottom: 1px solid var(--geo-line); }
    [data-baseweb="tab"] { padding-left: 0; padding-right: 0; color: var(--geo-ink); }
    [aria-selected="true"][data-baseweb="tab"] { color: var(--geo-accent) !important; }
    [data-baseweb="tab-highlight"] { background: var(--geo-accent) !important; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
    .stTextArea textarea, [data-testid="stDataEditor"] { background: var(--geo-input); }
    .stButton > button[kind="primary"] { background: var(--geo-accent); border-color: var(--geo-accent); }
    .stButton > button, .stDownloadButton > button { border-radius: 4px; min-height: 2.55rem; }
    [data-testid="stMetric"] { border-left: 3px solid var(--geo-blue); padding-left: .85rem; }
    [data-testid="stSidebar"] { border-right: 1px solid var(--geo-line); background: #FBFCFD; }
    [data-testid="stAlert"] { border-radius: 4px; }
    .geo-kicker { color: #D7A9A9; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; }
    .geo-subtitle { color: var(--geo-muted); font-size: 1rem; margin-bottom: 1rem; }
    .geo-rule { border: none; border-top: 1px solid var(--geo-line); margin: 1.1rem 0; }
</style>
"""

