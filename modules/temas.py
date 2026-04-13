import json
import os
import streamlit as st

TEMAS = {
    "Claro": {
        "label": "Claro",
        "icon": "☀️",
        "--bg": "#ffffff",
        "--bg2": "#f0f2f6",
        "--sidebar-bg": "#f8f9fa",
        "--text": "#262730",
        "--text-muted": "#6c757d",
        "--primary": "#667eea",
        "--primary-dark": "#764ba2",
        "--border": "#dee2e6",
        "--card-border": "#1f77b4",
        "--metric-bg": "#f0f2f6",
        "--btn-radius": "10px",
        "--header-gradient": "linear-gradient(90deg, #667eea 0%, #764ba2 100%)",
    },
    "Escuro": {
        "label": "Escuro",
        "icon": "🌙",
        "--bg": "#0e1117",
        "--bg2": "#1a1d27",
        "--sidebar-bg": "#151820",
        "--text": "#fafafa",
        "--text-muted": "#9ba3af",
        "--primary": "#818cf8",
        "--primary-dark": "#a78bfa",
        "--border": "#2d3748",
        "--card-border": "#818cf8",
        "--metric-bg": "#1a1d27",
        "--btn-radius": "10px",
        "--header-gradient": "linear-gradient(90deg, #818cf8 0%, #a78bfa 100%)",
    },
    "Verde Mega": {
        "label": "Verde Mega",
        "icon": "🍀",
        "--bg": "#0d1f0f",
        "--bg2": "#132916",
        "--sidebar-bg": "#0a1a0c",
        "--text": "#e8f5e9",
        "--text-muted": "#81c784",
        "--primary": "#4caf50",
        "--primary-dark": "#2e7d32",
        "--border": "#1b5e20",
        "--card-border": "#4caf50",
        "--metric-bg": "#132916",
        "--btn-radius": "10px",
        "--header-gradient": "linear-gradient(90deg, #4caf50 0%, #2e7d32 100%)",
    },
    "Alto Contraste": {
        "label": "Alto Contraste",
        "icon": "⬛",
        "--bg": "#000000",
        "--bg2": "#111111",
        "--sidebar-bg": "#080808",
        "--text": "#ffffff",
        "--text-muted": "#cccccc",
        "--primary": "#ffff00",
        "--primary-dark": "#ffd700",
        "--border": "#444444",
        "--card-border": "#ffff00",
        "--metric-bg": "#111111",
        "--btn-radius": "10px",
        "--header-gradient": "linear-gradient(90deg, #ffff00 0%, #ffd700 100%)",
    },
}

TEMA_PADRAO = "Alto Contraste"
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "piloto_config.json")


def _carregar_tema_disco():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        tema = cfg.get("tema", TEMA_PADRAO)
        return tema if tema in TEMAS else TEMA_PADRAO
    except Exception:
        return TEMA_PADRAO


def _salvar_tema_disco(nome):
    try:
        cfg = {}
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["tema"] = nome
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def inicializar_tema():
    if "tema_ativo" not in st.session_state:
        st.session_state["tema_ativo"] = _carregar_tema_disco()


def renderizar_seletor_tema():
    inicializar_tema()
    nomes = list(TEMAS.keys())
    labels = [f"{TEMAS[n]['icon']} {TEMAS[n]['label']}" for n in nomes]
    idx_atual = nomes.index(st.session_state["tema_ativo"])

    escolha_label = st.sidebar.selectbox(
        "🎨 Tema",
        labels,
        index=idx_atual,
        key="select_tema",
    )
    nome_escolhido = nomes[labels.index(escolha_label)]
    if nome_escolhido != st.session_state["tema_ativo"]:
        st.session_state["tema_ativo"] = nome_escolhido
        _salvar_tema_disco(nome_escolhido)
        st.rerun()


def aplicar_tema():
    inicializar_tema()
    tema = TEMAS[st.session_state["tema_ativo"]]
    vars_css = "\n".join(f"        {k}: {v};" for k, v in tema.items() if k.startswith("--"))
    css = f"""
<style>
    :root {{
{vars_css}
    }}

    /* Fundo principal */
    .stApp {{
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: var(--text) !important;
    }}

    /* Inputs, selects, textareas */
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"] div,
    .stTextArea textarea {{
        background-color: var(--bg2) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }}

    /* Dataframes / tabelas */
    .stDataFrame,
    .stDataFrame table {{
        background-color: var(--bg2) !important;
        color: var(--text) !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background-color: var(--bg2) !important;
        color: var(--text) !important;
    }}
    .streamlit-expanderContent {{
        background-color: var(--bg2) !important;
    }}

    /* Metric cards */
    .metric-card {{
        background-color: var(--metric-bg) !important;
        border-left: 4px solid var(--card-border) !important;
        color: var(--text) !important;
    }}

    /* Botoes */
    .stButton > button {{
        border-radius: var(--btn-radius) !important;
        font-weight: bold !important;
        background-color: var(--bg2) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }}
    .stButton > button:hover {{
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }}

    /* Header principal */
    .main-header {{
        font-size: 2.5rem;
        text-align: center;
        padding: 1rem;
        background: var(--header-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: var(--bg2) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: var(--text) !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        border-bottom-color: var(--primary) !important;
        color: var(--primary) !important;
    }}

    /* Dividers */
    hr {{
        border-color: var(--border) !important;
    }}

    /* Metricas nativas do Streamlit */
    [data-testid="metric-container"] {{
        background-color: var(--bg2) !important;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        border-left: 4px solid var(--card-border);
    }}
    [data-testid="metric-container"] label,
    [data-testid="metric-container"] div {{
        color: var(--text) !important;
    }}

    /* Menu lateral — separadores: sem bullet, com linha separadora */
    section[data-testid="stSidebar"] .stRadio label:nth-child(1),
    section[data-testid="stSidebar"] .stRadio label:nth-child(5),
    section[data-testid="stSidebar"] .stRadio label:nth-child(11),
    section[data-testid="stSidebar"] .stRadio label:nth-child(29) {{
        margin-top: 14px !important;
        padding: 2px 4px 4px 4px !important;
        pointer-events: none !important;
        cursor: default !important;
        opacity: 0.6 !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.07em !important;
        background: none !important;
        border-radius: 0 !important;
        border: none !important;
        border-bottom: 1px solid var(--border) !important;
        margin-bottom: 4px !important;
    }}
    section[data-testid="stSidebar"] .stRadio label:nth-child(1) input,
    section[data-testid="stSidebar"] .stRadio label:nth-child(5) input,
    section[data-testid="stSidebar"] .stRadio label:nth-child(11) input,
    section[data-testid="stSidebar"] .stRadio label:nth-child(29) input {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] .stRadio label:nth-child(1) {{
        margin-top: 0 !important;
    }}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
