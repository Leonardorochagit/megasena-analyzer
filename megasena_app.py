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

    # Menu de navegação por grupos com session_state
    GRUPOS = {
        "\U0001f3e0 SISTEMA": [
            "\U0001f916 Piloto Automático",
            "\U0001f3af Simulação & Conferência",
            "\u2705 Verificar Resultados",
        ],
        "\U0001f4ca ANÁLISE": [
            "\U0001f4ca Backtesting Estatístico",
            "\U0001f3c6 Resultados Validação",
            "\U0001f504 Análise Escada",
            "\U0001f9ec Análise de Sequências",
            "\U0001f4ca Relatório Geral",
        ],
        "\U0001f3b2 ESTRATÉGIAS": [
            "01. \U0001f9e0 Ensemble",
            "02. \U0001f4ca Frequência Desvio",
            "03. \U0001f46b Pares Frequentes",
            "04. \U0001f91d Consenso",
            "05. \U0001f501 Ciclos",
            "06. \U0001f9ec Sequências Clusters",
            "07. \U0001f525 Números Quentes",
            "08. \U0001f4cd Vizinhança",
            "09. \U0001f947 Candidatos Ouro",
            "10. \U0001f3b2 Aleatório Inteligente",
            "11. \u2696\ufe0f Equilibrado",
            "12. \U0001f3a8 Misto",
            "13. \U0001f680 Momentum",
            "14. \u23f0 Números Atrasados",
            "15. \u23f3 Atraso Recente",
            "16. \U0001f504 Escada Temporal",
            "17. \U0001f3af Wheel Cobertura",
        ],
        "\u2699\ufe0f ADMIN": [
            "\U0001f916 AutoML PyCaret",
            "\U0001f5c4\ufe0f Admin Banco de Dados",
        ],
    }

    if "menu_ativo" not in st.session_state:
        st.session_state["menu_ativo"] = "\U0001f916 Piloto Automático"

    # Construir lista flat: todos os itens de todos os grupos
    TODOS_ITENS = []
    for itens in GRUPOS.values():
        TODOS_ITENS.extend(itens)

    menu_ativo = st.session_state["menu_ativo"]

    for titulo, itens in GRUPOS.items():
        st.sidebar.markdown(f"**{titulo}**")
        # Se o item ativo está nesse grupo, seleciona ele; senão nenhum
        idx = None
        if menu_ativo in itens:
            idx = itens.index(menu_ativo)
        radio_key = f"radio_grupo_{titulo}"
        escolha = st.sidebar.radio(
            titulo, itens, index=idx,
            key=radio_key,
            label_visibility="collapsed"
        )
        # Se o user clicou em algo neste grupo (e não é o que já estava ativo)
        if escolha is not None and escolha != menu_ativo and escolha in itens:
            st.session_state["menu_ativo"] = escolha
            # Limpar o estado dos radios dos outros grupos para evitar
            # que o Streamlit restaure a selecao antiga e sobreescreva a navegacao
            for outro_titulo in GRUPOS:
                if outro_titulo != titulo:
                    outro_key = f"radio_grupo_{outro_titulo}"
                    if outro_key in st.session_state:
                        del st.session_state[outro_key]
            st.rerun()
        st.sidebar.markdown("---")

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

    elif menu == "🎯 Simulação & Conferência":
        pagina_simulacao(df)

    elif menu == "✅ Verificar Resultados":
        pagina_verificar_resultados(df)

    elif menu == "📊 Backtesting Estatístico":
        pagina_backtesting(df)

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
