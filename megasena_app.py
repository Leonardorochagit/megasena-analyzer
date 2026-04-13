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
from pagina_validacao_visual import pagina_validacao_visual
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

    # Menu de navegação por grupos
    MENU_OPCOES = [
        "━━━ 🏠 SISTEMA ━━━",
        "01. 🤖 Piloto Automático",
        "02. 🎯 Simulação & Conferência",
        "03. ✅ Verificar Resultados",
        "━━━ 📊 ANÁLISE ━━━",
        "04. 📊 Backtesting Estatístico",
        "05. 🏆 Resultados Validação",
        "06. 🔄 Análise Escada",
        "07. 🧬 Análise de Sequências",
        "08. 📊 Relatório Geral",
        "━━━ 🎲 ESTRATÉGIAS ━━━",
        "09. 🧠 Ensemble",
        "10. 📊 Frequência Desvio",
        "11. 👫 Pares Frequentes",
        "12. 🤝 Consenso",
        "13. 🔁 Ciclos",
        "14. 🧬 Sequências Clusters",
        "15. 🔥 Números Quentes",
        "16. 📍 Vizinhança",
        "17. 🥇 Candidatos Ouro",
        "18. 🎲 Aleatório Inteligente",
        "19. ⚖️ Equilibrado",
        "20. 🎨 Misto",
        "21. 🚀 Momentum",
        "22. ⏰ Números Atrasados",
        "23. ⏳ Atraso Recente",
        "24. 🔄 Escada Temporal",
        "25. 🎯 Wheel Cobertura",
        "━━━ ⚙️ ADMIN ━━━",
        "26. 🤖 AutoML PyCaret",
        "27. 🗄️ Admin Banco de Dados",
    ]
    SEPARADORES = [o for o in MENU_OPCOES if o.startswith("━━━")]
    menu = st.sidebar.selectbox(
        "Navegação",
        MENU_OPCOES,
        index=1,
        key="menu_nav"
    )
    if menu in SEPARADORES:
        menu = "01. 🤖 Piloto Automático"

    st.sidebar.markdown("---")

    # Info do sistema
    with st.sidebar.expander("ℹ️ Sobre o Sistema"):
        st.markdown("""
        **Mega Sena Analyzer v3.5**

        ---
        ### 🧭 Páginas principais

        **🤖 Piloto Automático**
        Roda automaticamente: confere o último resultado, gera cartões para o
        próximo concurso e salva tudo. Ideal para usar no dia a dia sem
        precisar entrar em cada página.

        **🎯 Simulação & Conferência**
        Gere jogos com qualquer estratégia, escolha de 6 a 20 números por
        cartão e confira os resultados assim que saírem.

        **📊 Backtesting Estatístico**
        Testa as estratégias nos últimos N concursos com dados históricos reais
        (sem data leakage) e compara as distribuições de acertos.

        **🏆 Resultados Validação**
        Visualiza o resultado do backtesting salvo: contagem absoluta de
        ternos, quadras, quinas e senas por estratégia, com gráficos e ranking.

        ---
        ### 🎲 Estratégias disponíveis

        **🔄 Escada Temporal**
        Usa as inversões reais da escada temporal — números que "subiram" na
        fila de espera e estão na vez de sair.

        **⏰ Números Atrasados**
        Top-20 números que aparecem com menos frequência no histórico total.
        Aposta na reversão à média no longo prazo.

        **🔥 Números Quentes**
        Top-20 mais frequentes nos últimos 50 sorteios. Segue o momentum
        recente da frequência.

        **⏳ Atraso Recente**
        Números que não saem há mais concursos do que o normal nos últimos
        100 sorteios — combinação de atraso + janela recente.

        **⚖️ Equilibrado**
        Força exatamente 3 números pares e 3 ímpares. Aproveita a tendência
        estatística de equilíbrio par/ímpar da Mega-Sena.

        **🎨 Misto**
        Combina 2 atrasados + 2 quentes + 2 de atraso recente, com filtros
        básicos de soma e paridade.

        **🤝 Consenso**
        Interseção de 3 pools (atrasados, quentes, atraso recente) — só
        entra número que aparece em pelo menos 2 dos 3 critérios.

        **🎲 Aleatório Inteligente**
        Sorteio aleatório puro com rejeição: só aceita jogos cuja soma fique
        entre 140–210 e com 2–4 números pares. Serve como baseline.

        **🧬 Sequências (Clusters)**
        Agrupa números por co-ocorrência com KMeans (4 clusters) e expande
        com vizinhança N±1. Captura padrões de agrupamento histórico.

        **🧠 Ensemble**
        Votação de 7 estratégias base (escada, atrasados, quentes, atraso
        recente, equilibrado, misto, consenso). Os top-20 mais votados formam
        o pool. Foi a estratégia com **mais quinas** no backtesting (15 quinas
        em 4.960 jogos).

        **🎯 Wheel (Cobertura)**
        Gera múltiplos cartões com cobertura sistemática tipo "wheel" —
        garante que qualquer subconjunto de N números seja coberto.

        **🥇 Candidatos Ouro**
        Combina números frios (abaixo da frequência esperada) com os muito
        atrasados, usando score = déficit de frequência + atraso/10.

        **🚀 Momentum**
        Calcula a razão freq(últimos 20) / freq(últimos 100). Números com
        ratio > 1,2 estão "acelerando" e entram no pool.

        **📍 Vizinhança**
        Usa os números ±2 de cada dezena do último sorteio como candidatos.
        Explora a tendência de repetição de faixas numéricas.

        **📊 Frequência Desvio**
        Filtra os números cuja frequência histórica está mais de 1 desvio
        padrão acima da média. Seleciona os genuinamente super-frequentes.

        **👫 Pares Frequentes**
        Identifica os 30 pares de números que mais co-ocorrem nos últimos
        200 sorteios e extrai os números únicos desses pares como pool.

        **🔁 Ciclos**
        Calcula o intervalo médio de aparição de cada número e seleciona
        aqueles cujo gap atual está próximo do ciclo médio — "na hora de sair".

        **🧠✨ Ensemble V2**
        Versão melhorada do ensemble: votação de 7 estratégias fortes
        (sem escada nem atrasados, que performaram mal no backtesting).

        ---
        ### 📈 Resultados do backtesting (2500→2995)
        496 concursos · 10 cartões · 14 números por estratégia

        | Destaque | Estratégia |
        |---|---|
        | Mais quinas (15) | 🧠 Ensemble |
        | Mais senas (1 cada) | 📍 Vizinhança, 🥇 Candidatos Ouro, ⏰ Atrasados |
        | Mais quadras (123) | 🧬 Sequências |
        | Melhor média | 🔁 Ciclos (+0.019 vs aleatório) |

        ⚠️ Nenhuma estratégia é estatisticamente superior ao aleatório (p>0,05).
        Lembre: loteria é aleatória — use como diversão responsável.
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
            menu = "03. ✅ Verificar Resultados"
        del st.session_state['navegar_para']

    if menu == "01. 🤖 Piloto Automático":
        pagina_piloto_automatico(df)

    elif menu == "02. 🎯 Simulação & Conferência":
        pagina_simulacao(df)

    elif menu == "03. ✅ Verificar Resultados":
        pagina_verificar_resultados(df)

    elif menu == "04. 📊 Backtesting Estatístico":
        pagina_backtesting(df)

    elif menu == "05. 🏆 Resultados Validação":
        pagina_validacao_visual(df)

    elif menu == "06. 🔄 Análise Escada":
        pagina_escada_temporal(df)

    elif menu == "07. 🧬 Análise de Sequências":
        pagina_analise_sequencias(df)

    elif menu == "08. 📊 Relatório Geral":
        pagina_relatorio_geral(df)

    elif menu == "09. 🧠 Ensemble":
        pagina_analise_estrategia(df, "Ensemble", "ensemble")

    elif menu == "10. 📊 Frequência Desvio":
        pagina_analise_estrategia(df, "Frequência Desvio", "frequencia_desvio")

    elif menu == "11. 👫 Pares Frequentes":
        pagina_analise_estrategia(df, "Pares Frequentes", "pares_frequentes")

    elif menu == "12. 🤝 Consenso":
        pagina_analise_estrategia(df, "Consenso de Estratégias", "consenso")

    elif menu == "13. 🔁 Ciclos":
        pagina_analise_estrategia(df, "Ciclos", "ciclos")

    elif menu == "14. 🧬 Sequências Clusters":
        pagina_analise_estrategia(df, "Sequências (Clusters)", "sequencias")

    elif menu == "15. 🔥 Números Quentes":
        pagina_analise_estrategia(df, "Números Quentes", "quentes")

    elif menu == "16. 📍 Vizinhança":
        pagina_analise_estrategia(df, "Vizinhança", "vizinhanca")

    elif menu == "17. 🥇 Candidatos Ouro":
        pagina_analise_estrategia(df, "Candidatos Ouro", "candidatos_ouro")

    elif menu == "18. 🎲 Aleatório Inteligente":
        pagina_analise_estrategia(df, "Aleatório Inteligente", "aleatorio_smart")

    elif menu == "19. ⚖️ Equilibrado":
        pagina_analise_estrategia(df, "Análise Equilibrada", "equilibrado")

    elif menu == "20. 🎨 Misto":
        pagina_analise_estrategia(df, "Estratégia Mista", "misto")

    elif menu == "21. 🚀 Momentum":
        pagina_analise_estrategia(df, "Momentum", "momentum")

    elif menu == "22. ⏰ Números Atrasados":
        pagina_analise_estrategia(df, "Números Atrasados", "atrasados")

    elif menu == "23. ⏳ Atraso Recente":
        pagina_analise_estrategia(df, "Atraso Recente", "atraso_recente")

    elif menu == "24. 🔄 Escada Temporal":
        pagina_escada_temporal(df)

    elif menu == "25. 🎯 Wheel Cobertura":
        pagina_analise_estrategia(df, "Wheel (Cobertura)", "wheel")

    elif menu == "26. 🤖 AutoML PyCaret":
        pagina_automl(df)

    elif menu == "27. 🗄️ Admin Banco de Dados":
        pagina_admin_banco()


# =============================================================================
# EXECUTAR APLICAÇÃO
# =============================================================================

if __name__ == "__main__":
    main()
