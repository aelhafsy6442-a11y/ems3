"""Thème glassmorphism sombre pour l'application Streamlit.

Usage dans app.py :  from theme import apply_theme, brand
Les couleurs et le template Plotly sont aussi définis ici pour rester cohérents.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

TEAL, VIOLET, CYAN, RED = "#3dffb0", "#b9a2ff", "#3fd5ff", "#ff6b7a"
INK, MUTED = "#ffffff", "#c3cfe2"
GRID = "rgba(255,255,255,0.06)"

# --- Template Plotly : fonds transparents pour laisser voir la carte en verre ---
pio.templates["ems_glass"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        title=dict(font=dict(color=INK, size=14)),
        colorway=[TEAL, VIOLET, CYAN, "#f5b94a", RED, "#6c7a89"],
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, title=dict(font=dict(color=MUTED))),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, title=dict(font=dict(color=MUTED))),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK)),
        hoverlabel=dict(bgcolor="#0d1424", bordercolor="rgba(255,255,255,0.15)", font=dict(color=INK)),
        colorscale=dict(sequential=[[0, "#0d1424"], [1, TEAL]],
                        diverging=[[0, VIOLET], [0.5, "#0d1424"], [1, TEAL]]),
    )
)
pio.templates.default = "ems_glass"

GLASS = """
background: linear-gradient(145deg, rgba(255,255,255,.075), rgba(255,255,255,.022));
border: 1px solid rgba(255,255,255,.10);
border-radius: 18px;
backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
box-shadow: 0 10px 34px rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.09);
"""

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}

/* Fond : nuit + halos teal / violet */
.stApp {{
  background:
    radial-gradient(900px 520px at 8% -8%, rgba(61,255,176,.16), transparent 60%),
    radial-gradient(900px 620px at 100% 105%, rgba(167,139,250,.18), transparent 60%),
    #070b14;
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.2rem; max-width: 1400px; }}

/* Titres */
h1, h2, h3 {{ color: {INK}; letter-spacing: -.01em; }}
h2 {{ font-weight: 700; font-size: 1.9rem; padding-bottom: .4rem; }}
h3 {{ font-weight: 600; font-size: 1.05rem; color: {INK}; margin-top: 1.4rem; }}
p, label, .stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* Sidebar : panneau de verre + navigation en pastilles */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.015));
  backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
  border-right: 1px solid rgba(255,255,255,.08);
}}
.ems-brand {{ display:flex; align-items:center; gap:.7rem; margin: .2rem 0 1.2rem; }}
.ems-logo {{ width:38px; height:38px; border-radius:11px; display:grid; place-items:center; font-size:1.2rem;
  background: linear-gradient(135deg, {TEAL}, {CYAN}); color:#04110c; box-shadow: 0 0 22px rgba(61,255,176,.45); }}
.ems-brand b {{ display:block; color:{INK}; font-size:1rem; line-height:1.15; }}
.ems-brand span {{ color:{MUTED}; font-size:.74rem; }}

[data-testid="stSidebar"] [role="radiogroup"] {{ gap: .3rem; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label {{
  width:100%; padding:.62rem .85rem; border-radius:12px; border:1px solid transparent;
  transition: background .15s, border-color .15s;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{ display:none !important; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{ background: rgba(255,255,255,.05); }}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
  background: linear-gradient(90deg, rgba(61,255,176,.20), rgba(61,255,176,.04));
  border-color: rgba(61,255,176,.28); box-shadow: inset 3px 0 0 {TEAL};
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{ color:{INK}; font-weight:600; }}

/* Cartes de verre : KPI, graphiques, tableaux, panneaux repliables */
[data-testid="stMetric"], [data-testid="stPlotlyChart"], [data-testid="stExpander"],
[data-testid="stDataFrame"], [data-testid="stImage"], [data-testid="stAlert"],
[data-testid="stForm"] {{ {GLASS} }}
[data-testid="stForm"] {{ padding: 1.4rem 1.4rem 1rem; }}
[data-testid="stMetric"] {{ padding: 1rem 1.15rem; }}
[data-testid="stPlotlyChart"] {{ padding: .7rem .6rem .3rem; }}
[data-testid="stDataFrame"] {{ padding: .35rem; overflow: hidden; }}
[data-testid="stImage"] {{ padding: .6rem; }}
[data-testid="stImage"] img {{ border-radius: 12px; }}
[data-testid="stExpander"] details {{ border: none; }}
[data-testid="stAlert"] {{ padding: .55rem .8rem; }}

[data-testid="stMetricLabel"] p {{ color:{MUTED}; font-size:.82rem; font-weight:500; }}
[data-testid="stMetricValue"] {{ color:{INK}; font-size:1.85rem; font-weight:650; letter-spacing:-.02em; }}
[data-testid="stMetricDelta"] {{ font-weight:600; }}


/* Alertes lisibles : verre sombre + texte blanc */
[data-testid="stAlert"] {{ border: 1px solid rgba(61,255,176,.55); background: rgba(61,255,176,.10);
  box-shadow: 0 0 24px rgba(61,255,176,.15), inset 0 1px 0 rgba(255,255,255,.10); }}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {{ border-color: rgba(255,107,122,.65);
  background: rgba(255,107,122,.12); box-shadow: 0 0 24px rgba(255,107,122,.15); }}
[data-testid="stAlert"] > div, [data-testid="stAlertContainer"] {{ background: transparent !important; color:#fff !important; }}
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] svg {{ color:#fff !important; fill:#3dffb0; }}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) svg {{ fill:#ff6b7a; }}
[data-testid="stAlert"] p {{ font-size:.95rem; font-weight:500; }}

/* Bouton principal vert */
button[kind="primary"], button[kind="primaryFormSubmit"] {{
  background: linear-gradient(135deg, #3dffb0, #1fd68f); color:#04110c; font-weight:700; border:none; border-radius:12px;
  box-shadow: 0 0 22px rgba(61,255,176,.35); }}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {{ filter: brightness(1.08); color:#04110c; }}
button[kind="secondary"] {{ border-radius:12px; border:1px solid rgba(255,255,255,.2); color:#fff; background: rgba(255,255,255,.06); }}


/* Marque tout en haut à gauche de la sidebar */
[data-testid="stSidebarHeader"] {{ height: 2.4rem; min-height: 0; padding: .4rem .8rem; }}
[data-testid="stSidebarUserContent"] {{ padding-top: 0 !important; }}
.ems-brand {{ margin-top: -1.2rem; }}

/* Titres toujours blancs (même pendant le rechargement) */
[data-testid="stHeading"], [data-testid="stHeading"] *, .stMain h1, .stMain h2, .stMain h3 {{ color:#ffffff !important; opacity:1 !important; }}
.stMain [data-testid="stWidgetLabel"] p, .stMain label p {{ color:#ffffff !important; }}

/* Accent vert partout, même si config.toml n'est pas chargé */
[data-baseweb="tag"] {{ background: rgba(61,255,176,.18) !important; border:1px solid rgba(61,255,176,.5); }}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {{ color:#ffffff !important; fill:#ffffff !important; }}
[data-baseweb="select"] > div {{ color:#ffffff; }}
.stMain [data-testid="stRadio"] label > div:first-child {{ background: transparent !important; border:2px solid rgba(255,255,255,.55) !important; }}
.stMain [data-testid="stRadio"] label:has(input:checked) > div:first-child {{ background:#3dffb0 !important; border-color:#3dffb0 !important; box-shadow:0 0 10px rgba(61,255,176,.7); }}
.stMain [data-testid="stRadio"] label:has(input:checked) > div:first-child > div {{ background:#04110c !important; }}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div {{ background-color: rgba(61,255,176,.6) !important; }}
a, a:visited {{ color:#3dffb0 !important; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color:#c3cfe2 !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.12) !important; }}

/* Onglets */
[data-baseweb="tab-list"] {{ gap:.4rem; border-bottom: 1px solid rgba(255,255,255,.08); }}
[data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; color:{MUTED}; padding: .55rem 1rem; }}
[data-baseweb="tab"][aria-selected="true"] {{ color:{TEAL}; background: rgba(61,255,176,.08); }}
[data-baseweb="tab-highlight"] {{ background-color:{TEAL}; height:2px; }}

/* Champs de saisie */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"],
[data-testid="stDateInput"] > div > div {{
  background: rgba(255,255,255,.045) !important; border-color: rgba(255,255,255,.10) !important;
  border-radius: 12px !important;
}}
[data-baseweb="tag"] {{ background: rgba(61,255,176,.16) !important; border-radius: 8px; }}
[data-testid="stSlider"] [role="slider"] {{ background:{TEAL}; box-shadow: 0 0 12px rgba(61,255,176,.7); }}

/* Radios horizontaux de la zone principale */
.stMain label[data-baseweb="radio"] p {{ color:{INK}; }}

::-webkit-scrollbar {{ width:10px; height:10px; }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,.12); border-radius:10px; }}
</style>
"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def brand():
    st.sidebar.markdown(
        '<div class="ems-brand"><div class="ems-logo">⚡</div>'
        '<div><b>Energy Management</b><span>Analyse énergétique de l&rsquo;aciérie</span></div></div>',
        unsafe_allow_html=True,
    )
