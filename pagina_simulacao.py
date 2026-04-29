"""
================================================================================
🎯 PÁGINA: SIMULAÇÃO E CONFERÊNCIA UNIFICADA
================================================================================
Hub central para:
- Simular jogos em TODAS as estratégias de uma vez
- Inserir jogos manuais
- Conferir resultados assim que sair o concurso
- Ranking de melhores estratégias
================================================================================
"""

import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime
from modules import data_manager as dm
from modules import statistics as stats
from modules import game_generator as gen
from helpers import CUSTOS_CARTAO, versao_estrategia


# =============================================================================
# CONSTANTES
# =============================================================================

TODAS_ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart', 'sequencias', 'wheel',
    'ensemble', 'candidatos_ouro', 'momentum', 'vizinhanca', 'frequencia_desvio',
    'pares_frequentes', 'ciclos'
]

NOMES_ESTRATEGIAS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Números Atrasados',
    'quentes': '🔥 Números Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Inteligente',
    'sequencias': '🧬 Sequências (Clusters+Vizinhança)',
    'wheel': '🎯 Wheel (Cobertura)',
    'ensemble': '🧠 Ensemble',
    'candidatos_ouro': '🥇 Candidatos Ouro',
    'momentum': '🚀 Momentum',
    'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Frequência Desvio',
    'pares_frequentes': '👫 Pares Frequentes',
    'ciclos': '🔁 Ciclos',
    'automl': '🤖 AutoML',
    'Manual': '✍️ Manual'
}


def _nome_estrategia(key) -> str:
    return NOMES_ESTRATEGIAS.get(key, str(key))


def _eh_ensemble(cartao) -> bool:
    estrategia = str(cartao.get('estrategia', '')).strip().lower()
    return estrategia == 'ensemble' or estrategia.startswith('ensemble_')


def _calcular_custo(qtd):
    return CUSTOS_CARTAO.get(qtd, 0.0)


def _calcular_combinacoes(qtd):
    from math import comb
    return comb(qtd, 6) if qtd >= 6 else 0


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_conferencia(df):
    """Página de Conferência Semanal — histórico + conferir novo concurso + ranking"""

    st.title("📋 Conferência Semanal")
    st.markdown("### Histórico de conferências e acertos dos seus jogos")

    # Histórico sempre visível no topo
    todos_cartoes = dm.carregar_cartoes_salvos()
    _mostrar_historico_testados(todos_cartoes)

    st.markdown("---")

    tab_conferir, tab_ranking = st.tabs([
        "✅ Conferir Novo Concurso",
        "🏆 Ranking de Estratégias",
    ])

    with tab_conferir:
        _aba_conferir(df)

    with tab_ranking:
        _aba_ranking(df)


def pagina_simulacao(df):
    """Página de Simulação — gerar jogos para testar metodologias"""

    st.title("🎲 Simulação de Jogos")
    st.info(
        "Use esta página para **testar metodologias** gerando jogos e conferindo contra concursos passados. "
        "Para conferir seus jogos semanais, use **📋 Conferência Semanal**."
    )

    _aba_simular(df)


# =============================================================================
# ABA 1: SIMULAR JOGOS
# =============================================================================

def _aba_simular(df):
    """Aba para gerar jogos de forma manual ou automática"""

    st.markdown("---")
    modo = st.radio(
        "Escolha o modo de simulação",
        ["🤖 Automático (todas as estratégias)", "✍️ Manual (escolher números)"],
        horizontal=True
    )

    st.markdown("---")

    # ---- CONFIGURAÇÕES COMUNS ----
    st.subheader("⚙️ Configuração do Concurso")
    col1, col2, col3 = st.columns(3)

    with col1:
        proximo = int(df['concurso'].max()) + 1 if 'concurso' in df.columns else 2956
        concurso_alvo = st.number_input(
            "🎯 Concurso Alvo",
            min_value=1, max_value=9999,
            value=proximo, step=1,
            help="Concurso para o qual os jogos serão gerados"
        )

    with col2:
        qtd_numeros = st.select_slider(
            "🔢 Números por cartão",
            options=list(range(6, 21)),
            value=10,
            help="Mais números = mais combinações = mais chance de acertar (e mais caro)"
        )

    with col3:
        custo = _calcular_custo(qtd_numeros)
        combinacoes = _calcular_combinacoes(qtd_numeros)
        st.metric("💰 Custo por cartão", f"R$ {custo:.2f}")
        st.caption(f"🎯 {combinacoes:,} combinações por cartão")

    # Tabela de probabilidades para ajudar na escolha
    with st.expander("📊 Ver tabela de chances por quantidade de números", expanded=(qtd_numeros > 6)):
        dados_prob = []
        for n in range(6, 21):
            c = _calcular_combinacoes(n)
            custo_n = _calcular_custo(n)
            # Cada combinação de 6 dentro do cartão é um "jogo"
            fator = c  # comparado a 1 jogo de 6 números
            dados_prob.append({
                'Números': n,
                'Combinações de 6': f"{c:,}",
                'Custo': f"R$ {custo_n:,.2f}",
                'Chance Sena (1 cartão)': f"1 em {50_063_860 // c:,}",
                'Vezes mais chance': f"{fator}x" if n > 6 else "1x (base)"
            })
        df_prob = pd.DataFrame(dados_prob)
        st.dataframe(df_prob, width="stretch", hide_index=True)

        if qtd_numeros > 6:
            fator_atual = _calcular_combinacoes(qtd_numeros)
            st.success(
                f"✅ Com **{qtd_numeros} números**, cada cartão equivale a **{fator_atual} jogos de 6**, "
                f"ou seja, **{fator_atual}x mais chance** de acertar!"
            )

    st.markdown("---")

    if modo.startswith("🤖"):
        _simular_automatico(df, concurso_alvo, qtd_numeros)
    else:
        _simular_manual(df, concurso_alvo, qtd_numeros)


def _simular_automatico(df, concurso_alvo, qtd_numeros):
    """Simulação automática em todas as estratégias"""
    
    st.subheader("🤖 Simulação Automática - Todas as Estratégias")

    col1, col2 = st.columns(2)

    with col1:
        qtd_cartoes_por_estrategia = st.number_input(
            "📋 Cartões por estratégia",
            min_value=1, max_value=20, value=5, step=1,
            help="Quantos cartões gerar para CADA estratégia"
        )

    with col2:
        estrategias_selecionadas = st.multiselect(
            "📊 Estratégias a usar",
            options=TODAS_ESTRATEGIAS,
            default=TODAS_ESTRATEGIAS,
            format_func=_nome_estrategia
        )

    qtd_cartoes_ensemble = qtd_cartoes_por_estrategia
    if 'ensemble' in estrategias_selecionadas:
        qtd_cartoes_ensemble = st.number_input(
            "🧠 Cartões Ensemble (votação)",
            min_value=1, max_value=50, value=20, step=5,
            help="Ensemble usa só as estratégias mais fortes do ranking recente/backtesting — gerar mais cartões aumenta cobertura"
        )

    # Calcular total considerando ensemble separado
    _outras = [e for e in estrategias_selecionadas if e != 'ensemble']
    total_cartoes = qtd_cartoes_por_estrategia * len(_outras)
    if 'ensemble' in estrategias_selecionadas:
        total_cartoes += qtd_cartoes_ensemble
    custo_total = total_cartoes * _calcular_custo(qtd_numeros)
    combinacoes_total = total_cartoes * _calcular_combinacoes(qtd_numeros)

    _ensemble_info = f" (Ensemble: {qtd_cartoes_ensemble})" if 'ensemble' in estrategias_selecionadas and qtd_cartoes_ensemble != qtd_cartoes_por_estrategia else ""
    st.info(f"""
    📊 **Resumo da simulação:**
    - **{len(estrategias_selecionadas)}** estratégias → **{total_cartoes} cartões** no total{_ensemble_info}
    - Cada cartão com **{qtd_numeros} números** ({_calcular_combinacoes(qtd_numeros)} combinações de 6 por cartão)
    - **Total de combinações cobertas: {combinacoes_total:,}** jogos de 6
    - Custo total estimado: **R$ {custo_total:,.2f}**
    - Concurso alvo: **{concurso_alvo}**
    """)

    marcar_jogar = st.checkbox(
        "🎯 Marcar todos para jogar",
        value=True,
        help="Se marcado, os cartões entram automaticamente na conferência"
    )

    st.markdown("---")

    if st.button("🚀 GERAR SIMULAÇÃO COMPLETA", type="primary", width="stretch"):
        with st.spinner("Gerando cartões para todas as estratégias..."):
            contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)

            todos_novos = []
            progresso = st.progress(0)
            status = st.empty()

            for idx_est, estrategia in enumerate(estrategias_selecionadas):
                status.text(f"Gerando cartões: {_nome_estrategia(estrategia)}...")
                qtd_est = qtd_cartoes_ensemble if estrategia == 'ensemble' else qtd_cartoes_por_estrategia
                for i in range(qtd_est):
                    # Gerar jogo base (6 números)
                    dezenas_base = gen.gerar_jogo(
                        estrategia=estrategia,
                        contagem_total=contagem_total,
                        contagem_recente=contagem_recente,
                        df_atrasos=df_atrasos,
                        df=df
                    )

                    # Expandir se necessário
                    if qtd_numeros > 6:
                        dezenas = gen.expandir_jogo(
                            dezenas_base, qtd_numeros, estrategia,
                            contagem_total, contagem_recente, df_atrasos, df=df
                        )
                    else:
                        dezenas = dezenas_base

                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    cartao = {
                        'id': f'{estrategia.upper()}-{timestamp}-{i+1:02d}',
                        'dezenas': sorted(dezenas),
                        'estrategia': estrategia,
                        'estrategia_versao': versao_estrategia(estrategia),
                        'vai_jogar': marcar_jogar,
                        'verificado': False,
                        'concurso_alvo': int(concurso_alvo),
                        'status': 'aguardando',
                        'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'qtd_numeros': qtd_numeros
                    }
                    todos_novos.append(cartao)

                progresso.progress((idx_est + 1) / len(estrategias_selecionadas))

            status.empty()
            progresso.empty()

            # Salvar
            cartoes_existentes = dm.carregar_cartoes_salvos()
            cartoes_existentes.extend(todos_novos)

            if dm.salvar_cartoes(cartoes_existentes):
                st.success(f"✅ **{len(todos_novos)} cartões** gerados e salvos com sucesso!")
                st.balloons()

                # Preview por estratégia
                _mostrar_preview_por_estrategia(todos_novos)
            else:
                st.error("❌ Erro ao salvar cartões")


def _simular_manual(df, concurso_alvo, qtd_numeros):
    """Simulação manual - escolher números"""
    
    st.subheader("✍️ Inserir Números Manualmente")
    
    # Mostrar sugestões
    with st.expander("💡 Ver sugestões das análises", expanded=False):
        contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)
        _, _, _, _, _, inversoes = stats.calcular_escada_temporal(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🔄 Escada (inversões):**")
            if inversoes:
                nums = [inv['numero'] for inv in inversoes[:10]]
                st.code(" - ".join([f"{n:02d}" for n in sorted(nums)]))
            else:
                st.caption("Sem inversões detectadas")
        with col2:
            st.markdown("**⏰ Mais atrasados:**")
            atrasados = df_atrasos.nlargest(10, 'jogos_sem_sair')['numero'].tolist()
            st.code(" - ".join([f"{n:02d}" for n in sorted(atrasados)]))
        with col3:
            st.markdown("**🔥 Mais quentes:**")
            quentes = contagem_recente.nlargest(10).index.tolist()
            st.code(" - ".join([f"{n:02d}" for n in sorted(quentes)]))

    st.markdown("---")

    # Inicializar seleção
    if 'nums_manual_sim' not in st.session_state:
        st.session_state['nums_manual_sim'] = []

    numeros_selecionados = st.session_state['nums_manual_sim']

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎲 Sugestão aleatória", type="secondary"):
            st.session_state['nums_manual_sim'] = sorted(random.sample(range(1, 61), qtd_numeros))
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Limpar seleção"):
            st.session_state['nums_manual_sim'] = []
            st.rerun()

    # Grid de números
    st.markdown(f"##### Selecione **{qtd_numeros}** números:")
    for linha in range(6):
        cols = st.columns(10)
        for i, col in enumerate(cols):
            numero = linha * 10 + i + 1
            with col:
                is_sel = numero in numeros_selecionados
                label = f"✓{numero:02d}" if is_sel else f"{numero:02d}"
                tipo = "primary" if is_sel else "secondary"

                if st.button(label, key=f"sim_num_{numero}", type=tipo, width="stretch"):
                    if numero in numeros_selecionados:
                        numeros_selecionados.remove(numero)
                    elif len(numeros_selecionados) < qtd_numeros:
                        numeros_selecionados.append(numero)
                    else:
                        st.toast(f"⚠️ Máximo de {qtd_numeros} números!")
                    st.session_state['nums_manual_sim'] = sorted(numeros_selecionados)
                    st.rerun()

    # Status
    faltam = qtd_numeros - len(numeros_selecionados)
    if numeros_selecionados:
        nums_str = " - ".join([f"**{n:02d}**" for n in sorted(numeros_selecionados)])
        st.markdown(f"📊 Selecionados: {nums_str}")
    
    if faltam > 0:
        st.warning(f"Faltam **{faltam}** número(s)")
    elif faltam == 0:
        st.success("✅ Seleção completa!")

    st.markdown("---")

    # Salvar cartão manual
    if st.button("💾 Salvar Cartão Manual", type="primary", width="stretch",
                 disabled=(len(numeros_selecionados) != qtd_numeros)):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        cartao = {
            'id': f'MANUAL-{timestamp}',
            'dezenas': sorted(numeros_selecionados),
            'estrategia': 'Manual',
            'estrategia_versao': '-',
            'vai_jogar': True,
            'verificado': False,
            'concurso_alvo': int(concurso_alvo),
            'status': 'aguardando',
            'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'qtd_numeros': qtd_numeros
        }

        cartoes_existentes = dm.carregar_cartoes_salvos()
        cartoes_existentes.append(cartao)

        if dm.salvar_cartoes(cartoes_existentes):
            st.success("✅ Cartão manual salvo!")
            st.session_state['nums_manual_sim'] = []
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Erro ao salvar")


# =============================================================================
# ABA 2: CONFERIR RESULTADOS
# =============================================================================

def _mostrar_historico_testados(todos_cartoes):
    """Mostra histórico de todos os concursos já verificados"""
    verificados = [c for c in todos_cartoes if c.get('verificado', False) and c.get('acertos') is not None]
    pendentes = [c for c in todos_cartoes if not c.get('verificado', False) and c.get('concurso_alvo')]

    concursos_verif = sorted(set(c.get('concurso_alvo') for c in verificados if c.get('concurso_alvo')), reverse=True)
    concursos_pend = sorted(set(c.get('concurso_alvo') for c in pendentes if c.get('concurso_alvo')), reverse=True)

    total_concursos = len(concursos_verif) + len(concursos_pend)

    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Concursos testados", len(concursos_verif))
    col_t2.metric("Concursos pendentes", len(concursos_pend))
    col_t3.metric("Total de jogos salvos", len(todos_cartoes))

    if not concursos_verif and not concursos_pend:
        st.info("📭 Nenhum jogo salvo ainda. Use a aba **Simular Jogos** para gerar jogos.")
        return

    # Tabela resumo de todos os concursos (verificados + pendentes)
    st.markdown("#### 📋 Histórico por Concurso")

    linhas = []

    for conc in sorted(set(concursos_verif + concursos_pend), reverse=True):
        jogos_conc = [c for c in todos_cartoes if c.get('concurso_alvo') == conc]
        verif_conc = [c for c in jogos_conc if c.get('verificado', False)]
        pend_conc = [c for c in jogos_conc if not c.get('verificado', False)]

        if verif_conc:
            # Calcular stats dos verificados
            acertos_todos = [c.get('acertos', 0) for c in verif_conc]
            melhor = max(acertos_todos)
            media = sum(acertos_todos) / len(acertos_todos)
            ternas = sum(1 for a in acertos_todos if a == 3)
            quadras = sum(1 for a in acertos_todos if a == 4)
            quinas = sum(1 for a in acertos_todos if a == 5)
            senas = sum(1 for a in acertos_todos if a == 6)

            # Estratégia com melhor média neste concurso
            por_est = {}
            for c in verif_conc:
                est = c.get('estrategia', 'N/A')
                por_est.setdefault(est, []).append(c.get('acertos', 0))
            melhor_est = max(por_est, key=lambda e: max(por_est[e]))

            tem_ensemble = any(_eh_ensemble(c) for c in jogos_conc)

            # Dezenas sorteadas (do primeiro verificado)
            resultado = verif_conc[0].get('resultado_concurso', [])
            dezenas_str = " ".join(f"{n:02d}" for n in sorted(resultado)) if resultado else "—"

            premios = []
            if senas: premios.append(f"🏆{senas}S")
            if quinas: premios.append(f"🥈{quinas}Q5")
            if quadras: premios.append(f"🥉{quadras}Q4")
            if ternas: premios.append(f"👍{ternas}T")
            premios_str = " ".join(premios) if premios else "—"

            status_icon = "✅" if tem_ensemble else "✅⚠️"
            status_txt = f"{len(verif_conc)} verificados"
            if pend_conc:
                status_txt += f" + {len(pend_conc)} pendentes"
            if tem_ensemble:
                status_txt += " (🧠 ensemble incluído)"
            else:
                status_txt += " (sem ensemble)"
        else:
            melhor = "—"
            media = 0.0
            melhor_est = "—"
            dezenas_str = "Aguardando sorteio"
            premios_str = "—"
            tem_ensemble = any(_eh_ensemble(c) for c in pend_conc)
            status_icon = "⏳"
            status_txt = f"{len(pend_conc)} pendentes"
            if tem_ensemble:
                status_txt += " (🧠 ensemble incluído)"

        linhas.append({
            "": status_icon,
            "Concurso": conc,
            "Sorteio": dezenas_str,
            "Jogos": len(jogos_conc),
            "Verificados": len(verif_conc),
            "Melhor Acerto": melhor,
            "Média": f"{media:.1f}" if verif_conc else "—",
            "Prêmios": premios_str,
            "Melhor Estratégia": _nome_estrategia(melhor_est) if melhor_est != "—" else "—",
            "Status": status_txt,
        })

    if linhas:
        df_hist = pd.DataFrame(linhas)
        st.dataframe(df_hist, hide_index=True, use_container_width=True)

    # Expandir detalhes por concurso verificado
    if concursos_verif:
        with st.expander(f"🔍 Ver detalhes por estratégia ({len(concursos_verif)} concurso(s) verificado(s))", expanded=False):
            for conc in concursos_verif:
                verif_conc = [c for c in verificados if c.get('concurso_alvo') == conc]
                resultado = verif_conc[0].get('resultado_concurso', [])
                dezenas_str = " - ".join(f"{n:02d}" for n in sorted(resultado)) if resultado else "não registrado"

                st.markdown(f"**Concurso {conc}** — Sorteio: `{dezenas_str}`")

                por_est = {}
                for c in verif_conc:
                    est = c.get('estrategia', 'N/A')
                    por_est.setdefault(est, []).append(c.get('acertos', 0))

                linhas_est = []
                for est, ac_list in sorted(por_est.items(), key=lambda x: max(x[1]), reverse=True):
                    melhor_est = max(ac_list)
                    media_est = sum(ac_list) / len(ac_list)
                    t = sum(1 for a in ac_list if a == 3)
                    q4 = sum(1 for a in ac_list if a == 4)
                    q5 = sum(1 for a in ac_list if a == 5)
                    s = sum(1 for a in ac_list if a == 6)
                    emoji = "🟢" if melhor_est >= 3 else "🟡" if melhor_est >= 2 else "🔴"
                    linhas_est.append({
                        "": emoji,
                        "Estratégia": _nome_estrategia(est),
                        "Jogos": len(ac_list),
                        "Melhor": melhor_est,
                        "Média": f"{media_est:.1f}",
                        "Ternas": t,
                        "Quadras": q4,
                        "Quinas": q5,
                        "Senas": s,
                    })
                st.dataframe(pd.DataFrame(linhas_est), hide_index=True, use_container_width=True)
                st.markdown("---")


def _aba_conferir(df):
    """Aba de conferência de resultados"""

    st.subheader("🔍 Selecionar Concurso")

    todos_cartoes = dm.carregar_cartoes_salvos()

    # Todos os concursos com cartões salvos (verificados + pendentes)
    todos_concursos = sorted(set(
        c.get('concurso_alvo') for c in todos_cartoes if c.get('concurso_alvo')
    ), reverse=True)

    if not todos_concursos:
        st.info("📭 Nenhum jogo salvo ainda.")
        return

    def _label_concurso(conc):
        jogos = [c for c in todos_cartoes if c.get('concurso_alvo') == conc]
        verif = sum(1 for c in jogos if c.get('verificado', False))
        pend = len(jogos) - verif
        if pend == 0:
            return f"✅ Concurso {conc}  ({verif} verificados)"
        elif verif == 0:
            return f"⏳ Concurso {conc}  ({pend} pendentes)"
        return f"⚡ Concurso {conc}  ({verif} verificados · {pend} pendentes)"

    col1, col2 = st.columns([3, 1])
    with col1:
        concurso_conferir = st.selectbox(
            "Concurso",
            options=todos_concursos,
            format_func=_label_concurso,
            label_visibility="collapsed",
        )
    with col2:
        conferir_btn = st.button("🔍 VER / CONFERIR", type="primary", width="stretch")

    if conferir_btn:
        dm.limpar_cache_resultados()

    if conferir_btn or st.session_state.get('ultimo_conferido') == concurso_conferir:
        st.session_state['ultimo_conferido'] = concurso_conferir
        _executar_conferencia(df, todos_cartoes, concurso_conferir)


def _executar_conferencia(df, todos_cartoes, concurso):
    """Executa a conferência de um concurso"""
    
    # Buscar jogos deste concurso
    jogos_concurso = [c for c in todos_cartoes if c.get('concurso_alvo') == concurso]
    
    if not jogos_concurso:
        st.warning(f"Nenhum jogo encontrado para o concurso {concurso}")
        return

    st.markdown("---")
    st.markdown(f"### 📋 Concurso {concurso} — {len(jogos_concurso)} jogo(s)")

    # Buscar resultado
    resultado_dezenas = _buscar_resultado(df, concurso)

    if not resultado_dezenas:
        st.warning(f"⏳ **Concurso {concurso} ainda não foi sorteado** ou resultado indisponível.")
        _mostrar_status_oficial_concurso(concurso)

        resultado_manual = _entrada_resultado_manual(concurso)
        if not resultado_manual:
            st.markdown("Os jogos estão aguardando o sorteio:")
            _mostrar_jogos_aguardando(jogos_concurso)
            return

        resultado_dezenas = resultado_manual
        st.info("Resultado digitado manualmente.")

    if not resultado_dezenas:
        # Mostrar jogos aguardando
        _mostrar_jogos_aguardando(jogos_concurso)
        return

    # TEM RESULTADO! Conferir
    st.success("✅ Resultado disponível!")
    nums_str = " - ".join([f"**{n:02d}**" for n in sorted(resultado_dezenas)])
    st.markdown(f"#### 🎲 Números sorteados: {nums_str}")
    st.markdown("---")

    # Calcular acertos para cada jogo
    resultados = []
    for jogo in jogos_concurso:
        acertos = len(set(jogo['dezenas']) & set(resultado_dezenas))
        jogo['acertos'] = acertos
        jogo['verificado'] = True
        jogo['resultado_concurso'] = resultado_dezenas
        jogo['data_verificacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resultados.append({
            'cartao': jogo,
            'acertos': acertos,
            'estrategia': jogo.get('estrategia', 'N/A'),
            'dezenas': jogo['dezenas'],
            'acertados': sorted(set(jogo['dezenas']) & set(resultado_dezenas))
        })

    # Salvar cartões atualizados
    dm.salvar_cartoes(todos_cartoes)

    # Métricas gerais
    total_quadras = sum(1 for r in resultados if r['acertos'] == 4)
    total_quinas = sum(1 for r in resultados if r['acertos'] == 5)
    total_senas = sum(1 for r in resultados if r['acertos'] == 6)
    max_acertos = max(r['acertos'] for r in resultados)

    cols = st.columns(5)
    cols[0].metric("🎲 Total Jogos", len(resultados))
    cols[1].metric("🏅 Melhor Acerto", f"{max_acertos} números")
    cols[2].metric("🥉 Quadras", total_quadras)
    cols[3].metric("🥈 Quinas", total_quinas)
    if total_senas > 0:
        cols[4].success(f"🎉 **{total_senas} SENA(S)!**")
    else:
        cols[4].metric("🏆 Senas", total_senas)

    st.markdown("---")

    # Ranking por estratégia neste concurso
    st.subheader("📊 Performance por Estratégia neste Concurso")
    _mostrar_ranking_concurso(resultados)

    st.markdown("---")

    # Detalhamento dos jogos
    st.subheader("📋 Detalhamento dos Jogos")
    resultados.sort(key=lambda x: x['acertos'], reverse=True)

    # Agrupar por estratégia — ensemble sempre primeiro
    por_estrategia = {}
    for r in resultados:
        est = r['estrategia']
        por_estrategia.setdefault(est, []).append(r)

    for estrategia, jogos_est in sorted(por_estrategia.items(), key=lambda x: -max(j['acertos'] for j in x[1])):
        total_est = len(jogos_est)
        melhor_est = max(j['acertos'] for j in jogos_est)
        media_est = sum(j['acertos'] for j in jogos_est) / total_est
        ver = jogos_est[0]['cartao'].get('estrategia_versao', versao_estrategia(estrategia))

        with st.expander(
            f"{_nome_estrategia(estrategia)} v{ver} — {total_est} jogos | Melhor: {melhor_est} | Média: {media_est:.1f}",
            expanded=(melhor_est >= 4)
        ):
            for i, r in enumerate(sorted(jogos_est, key=lambda x: x['acertos'], reverse=True), 1):
                col1, col2, col3 = st.columns([5, 2, 1])
                
                with col1:
                    nums = " - ".join([f"{n:02d}" for n in r['dezenas']])
                    st.code(f"#{i:02d}  {nums}")
                    if r['acertados']:
                        acertados_str = " ".join([f"✅ {n:02d}" for n in r['acertados']])
                        st.caption(acertados_str)
                
                with col2:
                    ac = r['acertos']
                    if ac == 6:
                        st.success(f"🎉 **{ac} acertos - SENA!**")
                    elif ac == 5:
                        st.warning(f"⭐ **{ac} acertos - QUINA!**")
                    elif ac == 4:
                        st.info(f"🏅 **{ac} acertos - QUADRA!**")
                    elif ac > 0:
                        st.caption(f"{ac} acertos")
                    else:
                        st.caption("0 acertos")

                with col3:
                    if r['cartao'].get('vai_jogar'):
                        st.caption("🎯 Jogado")

    # Arquivar automaticamente no histórico
    st.markdown("---")
    stats_concurso = _calcular_stats_por_estrategia(resultados)
    
    col_save, col_report = st.columns(2)
    with col_save:
        if st.button("💾 Arquivar no Histórico", type="primary", width="stretch"):
            sucesso = dm.salvar_historico_analise(
                concurso,
                datetime.now().strftime("%Y-%m-%d"),
                stats_concurso,
                resultado_dezenas
            )
            if sucesso:
                st.success(f"✅ Concurso {concurso} arquivado!")
            else:
                st.error("❌ Erro ao arquivar")

    with col_report:
        # Gerar relatório texto
        relatorio = _gerar_relatorio_texto(concurso, resultado_dezenas, resultados, stats_concurso)
        st.download_button(
            "📄 Baixar Relatório",
            relatorio,
            file_name=f"relatorio_concurso_{concurso}.txt",
            mime="text/plain",
            width="stretch"
        )


# =============================================================================
# ABA 3: RANKING DE ESTRATÉGIAS
# =============================================================================

def _aba_ranking(df):
    """Ranking simples: qual estratégia acerta mais dezenas"""

    st.subheader("🏆 Qual estratégia acerta mais?")
    st.caption("Ordenado por mais acertos — use para escolher o bolão")

    todos_cartoes = dm.carregar_cartoes_salvos()
    cartoes_verificados = [c for c in todos_cartoes if c.get('verificado', False) and c.get('acertos') is not None]

    if not cartoes_verificados:
        st.info("📭 Nenhum resultado conferido ainda.")
        return

    # Consolidar por estratégia
    ranking = {}
    for c in cartoes_verificados:
        est = c.get('estrategia', 'N/A')
        if est not in ranking:
            ranking[est] = {'jogos': 0, 'total_acertos': 0, 'ternos': 0,
                            'quadras': 0, 'quinas': 0, 'senas': 0,
                            'melhor': 0, 'concursos': set()}
        r = ranking[est]
        ac = c.get('acertos', 0)
        r['jogos'] += 1
        r['total_acertos'] += ac
        r['melhor'] = max(r['melhor'], ac)
        if ac >= 3: r['ternos'] += 1
        if ac >= 4: r['quadras'] += 1
        if ac >= 5: r['quinas'] += 1
        if ac >= 6: r['senas'] += 1
        if c.get('concurso_alvo'):
            r['concursos'].add(c['concurso_alvo'])

    linhas = []
    for est, d in ranking.items():
        media = d['total_acertos'] / d['jogos'] if d['jogos'] else 0
        linhas.append({
            'Estratégia': _nome_estrategia(est),
            'Concursos': len(d['concursos']),
            'Jogos': d['jogos'],
            'Melhor': d['melhor'],
            'Média': round(media, 2),
            'Ternos': d['ternos'],
            'Quadras': d['quadras'],
            'Quinas': d['quinas'],
            'Senas': d['senas'],
        })

    # Ordenar: senas > quinas > quadras > média
    linhas.sort(key=lambda x: (x['Senas'], x['Quinas'], x['Quadras'], x['Média']), reverse=True)

    # Destaque top 3
    medalhas = ["🥇", "🥈", "🥉"]
    for i, item in enumerate(linhas[:3]):
        med = medalhas[i]
        cols = st.columns([1, 4, 2, 2, 2, 2])
        cols[0].markdown(f"### {med}")
        cols[1].markdown(f"**{item['Estratégia']}**  \n{item['Jogos']} jogos · {item['Concursos']} concurso(s)")
        cols[2].metric("Melhor", f"{item['Melhor']} dezenas")
        cols[3].metric("Média", f"{item['Média']:.2f}")
        cols[4].metric("Quadras", item['Quadras'])
        cols[5].metric("Quinas/Senas", f"{item['Quinas']} / {item['Senas']}")
    st.markdown("---")

    # Tabela completa
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                   contagem_total, contagem_recente, df_atrasos, df):
    """Wrapper legado — delega para gen.expandir_jogo centralizado."""
    return gen.expandir_jogo(
        dezenas_base, qtd_numeros, estrategia,
        contagem_total, contagem_recente, df_atrasos, df=df
    )


def _buscar_resultado(df, concurso):
    """Busca resultado de um concurso"""
    max_concurso_df = int(df['concurso'].max()) if 'concurso' in df.columns else 0

    if concurso <= max_concurso_df:
        # Buscar do dataframe
        linha = df[df['concurso'] == concurso]
        if not linha.empty:
            row = linha.iloc[0]
            dezenas = []
            if 'dez1' in df.columns:
                for i in range(1, 7):
                    try:
                        dezenas.append(int(row.get(f'dez{i}')))
                    except (ValueError, TypeError):
                        pass
            if len(dezenas) == 6:
                return sorted(dezenas)

    # Tentar API
    return dm.buscar_resultado_concurso(concurso)


def _mostrar_status_oficial_concurso(concurso):
    """Mostra o status publicado pela Caixa para orientar concursos adiados."""
    resumo = dm.buscar_ultimo_resultado_oficial()
    if not resumo:
        st.caption("Não foi possível consultar o status oficial agora.")
        return

    ultimo = resumo.get('numero')
    data_ultimo = resumo.get('data') or "data não informada"
    proximo = resumo.get('numero_proximo')
    data_proximo = resumo.get('data_proximo') or "data não informada"

    if ultimo and concurso > ultimo:
        if proximo == concurso:
            st.info(
                f"Caixa: último sorteado {ultimo} em {data_ultimo}. "
                f"Próximo concurso {proximo}: {data_proximo}."
            )
        else:
            st.info(
                f"Caixa: último sorteado {ultimo} em {data_ultimo}. "
                f"Próximo informado: {proximo or 'não informado'}."
            )
    elif ultimo == concurso:
        st.info("A Caixa já lista este concurso como último; a busca por número pode estar atrasada.")


def _parse_dezenas_manual(texto):
    nums = [int(n) for n in re.findall(r"\d{1,2}", texto or "")]
    if len(nums) != 6:
        return None
    if len(set(nums)) != 6:
        return None
    if any(n < 1 or n > 60 for n in nums):
        return None
    return sorted(nums)


def _entrada_resultado_manual(concurso):
    """Permite conferir quando a API ainda não atualizou."""
    with st.expander("✏️ Conferir manualmente", expanded=True):
        texto = st.text_input(
            "Dezenas sorteadas",
            placeholder="Ex.: 15 18 28 31 52 58",
            key=f"manual_resultado_conferencia_{concurso}",
        )
        if st.button("✅ Conferir com dezenas digitadas", type="primary", key=f"btn_manual_conf_{concurso}"):
            dezenas = _parse_dezenas_manual(texto)
            if not dezenas:
                st.error("Informe 6 dezenas únicas entre 1 e 60.")
                return None
            return dezenas
    return None


def _mostrar_jogos_aguardando(jogos):
    """Mostra jogos aguardando sorteio"""
    por_estrategia = {}
    for jogo in jogos:
        est = jogo.get('estrategia', 'Outros')
        por_estrategia.setdefault(est, []).append(jogo)

    for estrategia, jogos_est in por_estrategia.items():
        with st.expander(f"{_nome_estrategia(estrategia)} ({len(jogos_est)} jogos)", expanded=True):
            for i, jogo in enumerate(jogos_est, 1):
                col1, col2 = st.columns([6, 1])
                with col1:
                    nums = " - ".join([f"{n:02d}" for n in jogo['dezenas']])
                    st.code(f"#{i:02d}  {nums}")
                with col2:
                    if jogo.get('vai_jogar'):
                        st.caption("🎯 Jogar")


def _mostrar_preview_por_estrategia(novos_cartoes):
    """Mostra preview de cartões agrupados por estratégia"""
    por_estrategia = {}
    for c in novos_cartoes:
        est = c.get('estrategia', 'N/A')
        por_estrategia.setdefault(est, []).append(c)

    for estrategia, cartoes in por_estrategia.items():
        with st.expander(f"{_nome_estrategia(estrategia)} — {len(cartoes)} cartões", expanded=False):
            for i, c in enumerate(cartoes, 1):
                nums = " - ".join([f"{n:02d}" for n in c['dezenas']])
                st.code(f"#{i:02d}  {nums}")


def _mostrar_ranking_concurso(resultados):
    """Ranking simples de estratégias para este concurso"""
    por_estrategia = {}
    for r in resultados:
        est = r['estrategia']
        por_estrategia.setdefault(est, []).append(r['acertos'])

    ranking = []
    for est, acertos_list in por_estrategia.items():
        media = sum(acertos_list) / len(acertos_list)
        melhor = max(acertos_list)
        ranking.append({
            'Estratégia': _nome_estrategia(est),
            'Jogos': len(acertos_list),
            'Melhor': melhor,
            'Média': round(media, 2),
            'Ternos': sum(1 for a in acertos_list if a >= 3),
            'Quadras': sum(1 for a in acertos_list if a >= 4),
            'Quinas': sum(1 for a in acertos_list if a >= 5),
            'Senas': sum(1 for a in acertos_list if a >= 6),
        })

    ranking.sort(key=lambda x: (x['Senas'], x['Quinas'], x['Quadras'], x['Média']), reverse=True)

    if ranking:
        top = ranking[0]
        st.success(f"🥇 **{top['Estratégia']}** — melhor acerto: {top['Melhor']} dezenas | média: {top['Média']:.2f}")

    st.dataframe(pd.DataFrame(ranking), hide_index=True, use_container_width=True)


def _calcular_stats_por_estrategia(resultados):
    """Calcula estatísticas por estratégia para arquivamento"""
    stats_est = {}
    for r in resultados:
        est = r['estrategia']
        if est not in stats_est:
            stats_est[est] = {
                'total_jogos': 0, 'total_acertos': 0,
                'senas': 0, 'quinas': 0, 'quadras': 0,
                'melhor_acerto': 0, 'media_acertos': 0
            }
        s = stats_est[est]
        s['total_jogos'] += 1
        s['total_acertos'] += r['acertos']
        s['melhor_acerto'] = max(s['melhor_acerto'], r['acertos'])
        if r['acertos'] == 6:
            s['senas'] += 1
        elif r['acertos'] == 5:
            s['quinas'] += 1
        elif r['acertos'] == 4:
            s['quadras'] += 1

    for est in stats_est:
        total = stats_est[est]['total_jogos']
        stats_est[est]['media_acertos'] = round(
            stats_est[est]['total_acertos'] / total, 2) if total > 0 else 0

    return stats_est


def _gerar_relatorio_texto(concurso, dezenas, resultados, stats_concurso):
    """Gera relatório em texto para download"""
    texto = f"""
{'='*65}
   RELATÓRIO DE CONFERÊNCIA - MEGA SENA ANALYZER
   Concurso: {concurso}
   Data da conferência: {datetime.now().strftime('%d/%m/%Y %H:%M')}
{'='*65}

NÚMEROS SORTEADOS:
{' - '.join([f'{n:02d}' for n in sorted(dezenas)])}

{'='*65}
RESUMO GERAL:
{'='*65}
Total de jogos verificados: {len(resultados)}
Quadras: {sum(1 for r in resultados if r['acertos'] == 4)}
Quinas: {sum(1 for r in resultados if r['acertos'] == 5)}
Senas: {sum(1 for r in resultados if r['acertos'] == 6)}

{'='*65}
RANKING DE ESTRATÉGIAS NESTE CONCURSO:
{'='*65}
"""
    for est, dados in sorted(stats_concurso.items(), 
                              key=lambda x: x[1]['media_acertos'], reverse=True):
        texto += f"""
Estratégia: {_nome_estrategia(est)}
  Jogos: {dados['total_jogos']}
  Média de acertos: {dados['media_acertos']:.2f}
  Melhor acerto: {dados['melhor_acerto']}
  Senas: {dados['senas']} | Quinas: {dados['quinas']} | Quadras: {dados['quadras']}
"""

    texto += f"""
{'='*65}
DETALHAMENTO DOS JOGOS:
{'='*65}
"""
    for i, r in enumerate(sorted(resultados, key=lambda x: x['acertos'], reverse=True), 1):
        texto += f"""
#{i:02d} | {_nome_estrategia(r['estrategia'])} | {r['acertos']} acertos
Números: {' - '.join([f'{n:02d}' for n in r['dezenas']])}
Acertou: {' - '.join([f'{n:02d}' for n in r['acertados']]) if r['acertados'] else 'Nenhum'}
{'-'*50}
"""

    return texto
