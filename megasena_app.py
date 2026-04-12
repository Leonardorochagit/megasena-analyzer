"""
================================================================================
🎰 MEGA SENA ANALYZER - VERSÃO MODULAR SIMPLIFICADA
================================================================================
Versão focada em análise escada e verificação de resultados
Executa sem necessidade de senha

Execute com: streamlit run app_modular.py
================================================================================
"""

import warnings
import streamlit as st

# Importar módulos
from modules import data_manager as dm
from modules import statistics as stats
from modules import auth

# Importar páginas separadas
from pagina_escada_temporal import pagina_escada_temporal
from pagina_verificar_resultados import pagina_verificar_resultados
from pagina_analise_estrategia import pagina_analise_estrategia
from pagina_relatorio_geral import pagina_relatorio_geral
from pagina_automl import pagina_automl
from pagina_simulacao import pagina_simulacao
from pagina_analise_sequencias import pagina_analise_sequencias
from pagina_piloto_automatico import pagina_piloto_automatico
from pagina_backtesting import pagina_backtesting
from pagina_admin_banco import pagina_admin_banco

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="🎰 Mega Sena Analyzer",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }

    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    """Função principal da aplicação"""

    # Inicializar sessão (sem necessidade de login)
    auth.inicializar_sessao()

    # Mostrar interface principal
    exibir_interface_principal()


def exibir_interface_principal():
    """Exibe a interface principal"""

    # Carregar dados
    df = dm.carregar_dados()

    # Carregar cartões salvos
    cartoes_salvos = dm.carregar_cartoes_salvos()
    total_cartoes = len(cartoes_salvos)

    # =========================================================================
    # SIDEBAR
    # =========================================================================
    st.sidebar.title("🎰 Mega Sena Analyzer")
    st.sidebar.caption("Versão Modular 3.0")
    st.sidebar.markdown("---")

    # Menu de navegação reorganizado
    st.sidebar.markdown("### 🎯 Principal")
    menu = st.sidebar.radio(
        "Navegação",
        [
            "🤖 Piloto Automático",
            "🎯 Simulação & Conferência",
            "🔄 Análise Escada",
            "🧬 Análise de Sequências",
            "📊 Backtesting Estatístico",
            "🗄️ Admin Banco de Dados",
            "⏰ Números Atrasados",
            "🔥 Números Quentes",
            "⏳ Atraso Recente",
            "⚖️ Equilibrado",
            "🎨 Misto",
            "🤝 Consenso",
            "🎲 Aleatório Inteligente",
            "🤖 AutoML (PyCaret)",
            "📊 Relatório Geral",
            "🎯 Verificar Resultados"
        ]
    )

    st.sidebar.markdown("---")

    # Info do sistema
    with st.sidebar.expander("ℹ️ Sobre o Sistema"):
        st.markdown("""
        **Mega Sena Analyzer v3.4**

        **🤖 Piloto Automático** (NOVO!)
        - Roda sozinho: confere e gera automaticamente
        - Dashboard em tempo real
        
        **🎯 Simulação & Conferência**
        - Gere jogos de TODAS as estratégias
        - Escolha de 6 a 20 números por cartão
        - Conferência automática de resultados
        - Ranking de melhores estratégias

        **Estratégias disponíveis:**
        - 🔄 Escada Temporal
        - ⏰ Números Atrasados
        - 🔥 Números Quentes
        - ⏳ Atraso Recente
        - ⚖️ Equilibrado
        - 🎨 Misto
        - 🤝 Consenso
        - 🎲 Aleatório Inteligente
        - 🤖 AutoML (Machine Learning)

        **Fluxo recomendado:**
        1. Vá em **Simulação & Conferência**
        2. Escolha qtd de números (6-20)
        3. Gere simulação automática
        4. Quando sair o resultado, confira
        5. Veja qual estratégia foi melhor!
        """)

    st.sidebar.metric("💾 Cartões Salvos", total_cartoes)

    # Mostrar concursos pendentes
    concursos_pendentes = set(
        c.get('concurso_alvo') for c in cartoes_salvos
        if c.get('concurso_alvo') and not c.get('verificado', False) and c.get('vai_jogar', False)
    )
    if concursos_pendentes:
        st.sidebar.warning(f"⏳ {len(concursos_pendentes)} concurso(s) pendente(s)")

    # =========================================================================
    # RENDERIZAR PÁGINA SELECIONADA
    # =========================================================================

    # Verificar se há navegação via session state
    if 'navegar_para' in st.session_state:
        if st.session_state['navegar_para'] == 'verificar_resultados':
            menu = "🎯 Verificar Resultados"
        del st.session_state['navegar_para']

    if menu == "🤖 Piloto Automático":
        pagina_piloto_automatico(df)

    elif menu == "🎯 Simulação & Conferência":
        pagina_simulacao(df)

    elif menu == "🔄 Análise Escada":
        pagina_escada_temporal(df)

    elif menu == "🧬 Análise de Sequências":
        pagina_analise_sequencias(df)

    elif menu == "📊 Backtesting Estatístico":
        pagina_backtesting(df)

    elif menu == "🗄️ Admin Banco de Dados":
        pagina_admin_banco()

    elif menu == "⏰ Números Atrasados":
        pagina_analise_estrategia(df, "Números Atrasados", "atrasados")

    elif menu == "🔥 Números Quentes":
        pagina_analise_estrategia(df, "Números Quentes", "quentes")

    elif menu == "⏳ Atraso Recente":
        pagina_analise_estrategia(df, "Atraso Recente", "atraso_recente")

    elif menu == "⚖️ Equilibrado":
        pagina_analise_estrategia(df, "Análise Equilibrada", "equilibrado")

    elif menu == "🎨 Misto":
        pagina_analise_estrategia(df, "Estratégia Mista", "misto")

    elif menu == "🤝 Consenso":
        pagina_analise_estrategia(df, "Consenso de Estratégias", "consenso")

    elif menu == "🎲 Aleatório Inteligente":
        pagina_analise_estrategia(
            df, "Aleatório Inteligente", "aleatorio_smart")

    elif menu == "🤖 AutoML (PyCaret)":
        pagina_automl(df)

    elif menu == "📊 Relatório Geral":
        pagina_relatorio_geral(df)

    elif menu == "🎯 Verificar Resultados":
        pagina_verificar_resultados(df)


# =============================================================================
# EXECUTAR APLICAÇÃO
# =============================================================================

if __name__ == "__main__":
    main()
