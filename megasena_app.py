"""
================================================================================
🎰 MEGA SENA ANALYZER - VERSÃO MODULAR SIMPLIFICADA
================================================================================
Versão focada em análise escada e verificação de resultados
Executa sem necessidade de senha

Execute com: streamlit run megasena_app.py
================================================================================
"""

import warnings
import streamlit as st

# Importar módulos
from modules import data_manager as dm
from modules import statistics as stats
from modules import auth
from modules.temas import aplicar_tema, renderizar_seletor_tema

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
from pagina_simulador_combinacoes import pagina_simulador_combinacoes
from pagina_ensemble_14 import pagina_ensemble_14
from pagina_validacao_ensemble import pagina_validacao_ensemble

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

aplicar_tema()


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
    st.sidebar.caption("Versão 3.7.0")
    st.sidebar.markdown("---")

    with st.sidebar.expander("🎨 Tema"):
        renderizar_seletor_tema()

    st.sidebar.markdown("---")

    # Menu de navegação — lista plana com um único radio (evita race condition entre grupos)
    MENU_ITENS = [
        "🏠 SISTEMA",
        "🤖 Piloto Automático",
        "🏆 Ensemble Top 10 (14 nums)",
        "🎯 Simulação & Conferência",
        "✅ Verificar Resultados",
        "📊 ANÁLISE",
        "🔬 Simulador Combinações",
        "📊 Backtesting Estatístico",
        "🧪 Validacao Ensemble",
        "🏆 Resultados Validação",
        "🔄 Análise Escada",
        "🧬 Análise de Sequências",
        "📊 Relatório Geral",
        "🎲 ESTRATÉGIAS",
        "01. 🧠 Ensemble",
        "02. 📊 Frequência Desvio",
        "03. 👫 Pares Frequentes",
        "04. 🤝 Consenso",
        "05. 🔁 Ciclos",
        "06. 🧬 Sequências Clusters",
        "07. 🔥 Números Quentes",
        "08. 📍 Vizinhança",
        "09. 🥇 Candidatos Ouro",
        "10. 🎲 Aleatório Inteligente",
        "11. ⚖️ Equilibrado",
        "12. 🎨 Misto",
        "13. 🚀 Momentum",
        "14. ⏰ Números Atrasados",
        "15. ⏳ Atraso Recente",
        "16. 🔄 Escada Temporal",
        "17. 🎯 Wheel Cobertura",
        "⚙️ ADMIN",
        "🤖 AutoML PyCaret",
        "🗄️ Admin Banco de Dados",
    ]

    SEPARADORES = {"🏠 SISTEMA", "📊 ANÁLISE", "🎲 ESTRATÉGIAS", "⚙️ ADMIN"}

    if "menu_ativo" not in st.session_state:
        st.session_state["menu_ativo"] = "🤖 Piloto Automático"

    # Garantir que o valor atual nao e um separador
    if st.session_state["menu_ativo"] in SEPARADORES:
        st.session_state["menu_ativo"] = "🤖 Piloto Automático"

    idx_atual = MENU_ITENS.index(st.session_state["menu_ativo"]) if st.session_state["menu_ativo"] in MENU_ITENS else 0

    escolha = st.sidebar.radio(
        "Navegação",
        MENU_ITENS,
        index=idx_atual,
        key="radio_menu_principal",
        label_visibility="collapsed",
    )

    if escolha in SEPARADORES:
        st.session_state["menu_ativo"] = st.session_state.get("menu_ativo", "🤖 Piloto Automático")
        st.rerun()
    elif escolha != st.session_state["menu_ativo"]:
        st.session_state["menu_ativo"] = escolha
        st.rerun()

    menu = st.session_state["menu_ativo"]

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
            st.session_state["menu_ativo"] = "✅ Verificar Resultados"
            menu = "✅ Verificar Resultados"
        del st.session_state['navegar_para']

    if menu == "🤖 Piloto Automático":
        pagina_piloto_automatico(df)

    elif menu == "🏆 Ensemble Top 10 (14 nums)":
        pagina_ensemble_14(df)

    elif menu == "🎯 Simulação & Conferência":
        pagina_simulacao(df)

    elif menu == "✅ Verificar Resultados":
        pagina_verificar_resultados(df)

    elif menu == "🔬 Simulador Combinações":
        pagina_simulador_combinacoes(df)

    elif menu == "📊 Backtesting Estatístico":
        pagina_backtesting(df)

    elif menu == "🧪 Validacao Ensemble":
        pagina_validacao_ensemble(df)

    elif menu == "🏆 Resultados Validação":
        pagina_validacao_visual(df)

    elif menu == "🔄 Análise Escada":
        pagina_escada_temporal(df)

    elif menu == "🧬 Análise de Sequências":
        pagina_analise_sequencias(df)

    elif menu == "📊 Relatório Geral":
        pagina_relatorio_geral(df)

    elif menu == "01. 🧠 Ensemble":
        pagina_analise_estrategia(df, "Ensemble", "ensemble")

    elif menu == "02. 📊 Frequência Desvio":
        pagina_analise_estrategia(df, "Frequência Desvio", "frequencia_desvio")

    elif menu == "03. 👫 Pares Frequentes":
        pagina_analise_estrategia(df, "Pares Frequentes", "pares_frequentes")

    elif menu == "04. 🤝 Consenso":
        pagina_analise_estrategia(df, "Consenso de Estratégias", "consenso")

    elif menu == "05. 🔁 Ciclos":
        pagina_analise_estrategia(df, "Ciclos", "ciclos")

    elif menu == "06. 🧬 Sequências Clusters":
        pagina_analise_estrategia(df, "Sequências (Clusters)", "sequencias")

    elif menu == "07. 🔥 Números Quentes":
        pagina_analise_estrategia(df, "Números Quentes", "quentes")

    elif menu == "08. 📍 Vizinhança":
        pagina_analise_estrategia(df, "Vizinhança", "vizinhanca")

    elif menu == "09. 🥇 Candidatos Ouro":
        pagina_analise_estrategia(df, "Candidatos Ouro", "candidatos_ouro")

    elif menu == "10. 🎲 Aleatório Inteligente":
        pagina_analise_estrategia(df, "Aleatório Inteligente", "aleatorio_smart")

    elif menu == "11. ⚖️ Equilibrado":
        pagina_analise_estrategia(df, "Análise Equilibrada", "equilibrado")

    elif menu == "12. 🎨 Misto":
        pagina_analise_estrategia(df, "Estratégia Mista", "misto")

    elif menu == "13. 🚀 Momentum":
        pagina_analise_estrategia(df, "Momentum", "momentum")

    elif menu == "14. ⏰ Números Atrasados":
        pagina_analise_estrategia(df, "Números Atrasados", "atrasados")

    elif menu == "15. ⏳ Atraso Recente":
        pagina_analise_estrategia(df, "Atraso Recente", "atraso_recente")

    elif menu == "16. 🔄 Escada Temporal":
        pagina_escada_temporal(df)

    elif menu == "17. 🎯 Wheel Cobertura":
        pagina_analise_estrategia(df, "Wheel (Cobertura)", "wheel")

    elif menu == "🤖 AutoML PyCaret":
        pagina_automl(df)

    elif menu == "🗄️ Admin Banco de Dados":
        pagina_admin_banco()


# =============================================================================
# EXECUTAR APLICAÇÃO
# =============================================================================

if __name__ == "__main__":
    main()
