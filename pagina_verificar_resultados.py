"""
================================================================================
🎯 PÁGINA: VERIFICAR RESULTADOS E COMPARAR ESTRATÉGIAS
================================================================================
Verificação de acertos e análise de performance das estratégias
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules import data_manager as dm
from modules import ui_components as ui


def pagina_verificar_resultados(df):
    """
    Página de verificação de resultados e análise de estratégias

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
    """
    st.title("🎯 Verificar Resultados")
    st.markdown("### Gerencie seus cartões e verifique acertos")

    # Carregar cartões salvos
    cartoes = dm.carregar_cartoes_salvos()

    if not cartoes:
        st.warning("📭 Nenhum cartão salvo ainda!")
        st.info("💡 Vá para 'Análise Escada Temporal' para gerar cartões")
        return

    # =========================================================================
    # TABS PRINCIPAIS
    # =========================================================================
    tab_gerenciar, tab_verificar, tab_estatisticas = st.tabs([
        "📋 Gerenciar Cartões",
        "✅ Verificar Acertos",
        "📊 Estatísticas por Estratégia"
    ])

    # -------------------------------------------------------------------------
    # TAB: GERENCIAR CARTÕES
    # -------------------------------------------------------------------------
    with tab_gerenciar:
        st.subheader("📋 Seus Cartões")
        st.caption(f"Total de {len(cartoes)} cartões salvos")

        # Listar concursos disponíveis
        concursos_disponiveis = sorted(set(
            c.get('concurso_alvo') for c in cartoes if c.get('concurso_alvo')
        ), reverse=True)

        if not concursos_disponiveis:
            st.warning("📭 Nenhum cartão com concurso definido.")
            return

        # Resumo por concurso
        resumo_concursos = {}
        for conc in concursos_disponiveis:
            cart_conc = [c for c in cartoes if c.get('concurso_alvo') == conc]
            pendentes = sum(1 for c in cart_conc if not c.get('verificado'))
            verificados = sum(1 for c in cart_conc if c.get('verificado'))
            resumo_concursos[conc] = {
                'total': len(cart_conc),
                'pendentes': pendentes,
                'verificados': verificados
            }

        # Seleção do concurso
        concurso_sel = st.selectbox(
            "🎯 Selecione o concurso",
            options=concursos_disponiveis,
            format_func=lambda x: (
                f"Concurso {x}  —  "
                f"{resumo_concursos[x]['total']} cartões ("
                f"⏳ {resumo_concursos[x]['pendentes']} pendentes, "
                f"✅ {resumo_concursos[x]['verificados']} verificados)"
            ),
            key="sel_concurso_gerenciar"
        )

        # Métricas do concurso selecionado
        r = resumo_concursos[concurso_sel]
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Total", r['total'])
        mc2.metric("⏳ Pendentes", r['pendentes'])
        mc3.metric("✅ Verificados", r['verificados'])

        st.markdown("---")

        # Filtros adicionais (dentro do concurso)
        cartoes_concurso = [c for c in cartoes if c.get('concurso_alvo') == concurso_sel]

        col1, col2, col3 = st.columns(3)

        with col1:
            estrategias_conc = list(set(c.get('estrategia', 'N/A') for c in cartoes_concurso))
            filtro_estrategia = st.multiselect(
                "Filtrar por estratégia",
                options=estrategias_conc,
                default=None,
                key="filtro_est_ger"
            )

        with col2:
            filtro_status = st.selectbox(
                "Filtrar por status",
                options=['Todos', 'Pendentes', 'Verificados'],
                index=0,
                key="filtro_status_ger"
            )

        with col3:
            ordenar_por = st.selectbox(
                "Ordenar por",
                options=['Mais recente', 'Mais antigo',
                         'Estratégia', 'Acertos (desc)'],
                index=0,
                key="ordenar_ger"
            )

        # Aplicar filtros ao concurso selecionado
        cartoes_filtrados = _filtrar_cartoes(
            cartoes_concurso, filtro_estrategia, filtro_status)
        cartoes_ordenados = _ordenar_cartoes(cartoes_filtrados, ordenar_por)

        st.markdown("---")

        # Mostrar cartões
        if not cartoes_ordenados:
            st.info("Nenhum cartão encontrado com os filtros selecionados")
        else:
            st.caption(f"Exibindo {len(cartoes_ordenados)} cartão(ões) do concurso {concurso_sel}")
            for idx, cartao in enumerate(cartoes_ordenados):
                _exibir_cartao(cartao, idx, df)

        # Ações em lote
        st.markdown("---")
        st.subheader("⚡ Ações em Lote")

        col1, col2, col3 = st.columns(3)

        with col1:
            with st.expander("🗑️ Limpar Todos os Cartões", expanded=False):
                st.warning(
                    "⚠️ **ATENÇÃO:** Esta ação irá remover TODOS os cartões salvos e não pode ser desfeita!")
                if st.button("🗑️ Confirmar Exclusão Total", key="confirm_delete_all", type="primary"):
                    dm.salvar_cartoes([])
                    st.success("✅ Todos os cartões foram removidos!")
                    st.rerun()

        with col2:
            if st.button(f"❌ Remover verificados do concurso {concurso_sel}", key="btn_rem_verif_conc"):
                cartoes_restantes = [
                    c for c in cartoes
                    if not (c.get('concurso_alvo') == concurso_sel and c.get('verificado', False))
                ]
                removidos = len(cartoes) - len(cartoes_restantes)
                if dm.salvar_cartoes(cartoes_restantes):
                    st.success(f"✅ {removidos} cartões verificados do concurso {concurso_sel} removidos!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao remover cartões")

        with col3:
            if st.button("❌ Remover todos verificados", key="btn_rem_verif_todos"):
                cartoes_nao_verificados = [
                    c for c in cartoes if not c.get('verificado', False)]
                removidos = len(cartoes) - len(cartoes_nao_verificados)
                if dm.salvar_cartoes(cartoes_nao_verificados):
                    st.success(f"✅ {removidos} cartões verificados removidos!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao remover cartões")

    # -------------------------------------------------------------------------
    # TAB: VERIFICAR ACERTOS
    # -------------------------------------------------------------------------
    with tab_verificar:
        st.subheader("✅ Verificar Acertos dos Cartões")

        # Identificar concursos
        concursos_pendentes = sorted(set(
            c.get('concurso_alvo') for c in cartoes
            if not c.get('verificado', False) and c.get('concurso_alvo')
        ))
        concursos_verificados_list = sorted(set(
            c.get('concurso_alvo') for c in cartoes
            if c.get('verificado', False) and c.get('concurso_alvo')
        ))

        # ---- SELEÇÃO DO CONCURSO ----
        opcoes = []
        labels = {}
        for c in concursos_pendentes:
            qtd = sum(1 for x in cartoes if x.get('concurso_alvo') == c and not x.get('verificado'))
            opcoes.append(c)
            labels[c] = f"Concurso {c}  —  ⏳ {qtd} cartão(ões) pendente(s)"
        for c in concursos_verificados_list:
            if c not in labels:
                qtd = sum(1 for x in cartoes if x.get('concurso_alvo') == c and x.get('verificado'))
                opcoes.append(c)
                labels[c] = f"Concurso {c}  —  ✅ {qtd} já verificado(s)"

        if not opcoes:
            st.warning("📭 Nenhum cartão com concurso definido.")
            st.info("💡 Vá para 'Análise Escada Temporal' para gerar cartões.")
            return

        concurso_verificar = st.selectbox(
            "🎯 Selecione o concurso",
            options=opcoes,
            format_func=lambda x: labels.get(x, f"Concurso {x}"),
            key="sel_concurso_verif"
        )

        # Limpar resultado em cache se concurso mudou
        if st.session_state.get('concurso_temp') != concurso_verificar:
            st.session_state.pop('resultado_temp', None)
            st.session_state.pop('concurso_temp', None)

        # Resumo rápido do concurso selecionado
        qtd_pend = sum(1 for c in cartoes if c.get('concurso_alvo') == concurso_verificar and not c.get('verificado'))
        qtd_verif = sum(1 for c in cartoes if c.get('concurso_alvo') == concurso_verificar and c.get('verificado'))

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric("Pendentes", qtd_pend)
        with col_res2:
            st.metric("Já verificados", qtd_verif)

        st.markdown("---")

        # ---- INFORMAR RESULTADO ----
        st.markdown("#### 📝 Resultado do Sorteio")

        tab_api, tab_manual = st.tabs(["🔍 Buscar automático", "✏️ Digitar manual"])

        with tab_api:
            if st.button("🔍 Buscar resultado da API", type="primary", key="btn_api"):
                with st.spinner(f"Buscando concurso {concurso_verificar}..."):
                    dm.limpar_cache_resultados()
                    resultado = dm.buscar_resultado_concurso(concurso_verificar)
                    if resultado:
                        st.session_state['resultado_temp'] = resultado
                        st.session_state['concurso_temp'] = concurso_verificar
                    else:
                        resumo = dm.buscar_ultimo_resultado_oficial()
                        if resumo:
                            st.info(
                                f"Caixa: último sorteado {resumo.get('numero')} em "
                                f"{resumo.get('data') or 'data não informada'}. "
                                f"Próximo: {resumo.get('numero_proximo') or 'não informado'} "
                                f"em {resumo.get('data_proximo') or 'data não informada'}."
                            )
                        st.error("❌ Não encontrado. Tente digitar manualmente.")

        with tab_manual:
            st.caption("Informe as 6 dezenas sorteadas:")
            cols = st.columns(6)
            dezenas_manual = []
            for i, col in enumerate(cols):
                with col:
                    dezenas_manual.append(st.number_input(f"{i+1}ª", min_value=1, max_value=60, value=(i+1)*5, key=f"dez_{i}"))

            tem_duplicata = len(set(dezenas_manual)) < 6
            if tem_duplicata:
                st.warning("⚠️ Dezenas repetidas!")

            if st.button("✅ Confirmar", type="primary", key="btn_manual", disabled=tem_duplicata):
                st.session_state['resultado_temp'] = sorted(dezenas_manual)
                st.session_state['concurso_temp'] = concurso_verificar
                st.rerun()

        # ---- EXIBIR RESULTADO E VERIFICAR ----
        if 'resultado_temp' in st.session_state and st.session_state.get('concurso_temp') == concurso_verificar:
            resultado = st.session_state['resultado_temp']
            concurso = concurso_verificar

            st.markdown("---")
            st.success(f"🎯 **Resultado Concurso {concurso}:**  {' - '.join(f'{n:02d}' for n in resultado)}")

            # Separar cartões — todos do concurso (sem filtro vai_jogar)
            cartoes_pendentes = [
                c for c in cartoes
                if c.get('concurso_alvo') == concurso
                and not c.get('verificado', False)
            ]
            cartoes_ja_verificados = [
                c for c in cartoes
                if c.get('concurso_alvo') == concurso
                and c.get('verificado', False)
            ]

            # ---- CARTÕES JÁ VERIFICADOS ----
            if cartoes_ja_verificados:
                with st.expander(f"✅ {len(cartoes_ja_verificados)} cartão(ões) já conferidos", expanded=False):
                    # Agrupar já verificados por estratégia
                    ja_verif_por_est = {}
                    for cartao in cartoes_ja_verificados:
                        est = cartao.get('estrategia', 'N/A')
                        ja_verif_por_est.setdefault(est, []).append(cartao)

                    for est, carts in ja_verif_por_est.items():
                        st.markdown(f"**🎲 {est}** ({len(carts)} cartões)")
                        for cartao in carts:
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.code(" - ".join(f"{n:02d}" for n in cartao.get('dezenas', [])))
                            with c2:
                                ac = cartao.get('acertos', 0)
                                st.markdown(f"**{ac} acertos**" if ac < 4 else f"🎉 **{ac} acertos**")

            # ---- VERIFICAR PENDENTES ----
            if cartoes_pendentes:
                st.markdown(f"### 📋 {len(cartoes_pendentes)} cartão(ões) para verificar")

                if st.button(f"⚡ Verificar {len(cartoes_pendentes)} cartão(ões) agora", type="primary", key="btn_verificar"):
                    resultados_verificacao = []

                    for cartao in cartoes_pendentes:
                        acertos = dm.verificar_acertos(cartao['dezenas'], resultado)
                        resultados_verificacao.append({'cartao': cartao, 'acertos': acertos})

                        cartao['verificado'] = True
                        cartao['resultado_concurso'] = resultado
                        cartao['acertos'] = acertos
                        cartao['data_verificacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    dm.salvar_cartoes(cartoes)
                    _exibir_resultados_verificacao(resultados_verificacao)

                    # Arquivar
                    todos_verif = cartoes_ja_verificados + [r['cartao'] for r in resultados_verificacao]
                    stats_concurso = _calcular_stats_para_historico(todos_verif)

                    st.markdown("---")
                    if st.button("📂 Arquivar no Histórico", key="btn_arquivar_hist"):
                        sucesso = dm.salvar_historico_analise(
                            concurso, datetime.now().strftime("%Y-%m-%d"), stats_concurso, resultado
                        )
                        if sucesso:
                            st.success(f"✅ Concurso {concurso} arquivado!")
                        else:
                            st.error("❌ Erro ao arquivar.")

                    st.balloons()

            elif qtd_pend == 0 and qtd_verif > 0:
                st.success(f"✅ Todos os cartões do concurso {concurso} já foram verificados!")
            else:
                st.info(f"💡 Nenhum cartão para o concurso {concurso}")

    # -------------------------------------------------------------------------
    # TAB: ESTATÍSTICAS POR ESTRATÉGIA
    # -------------------------------------------------------------------------
    with tab_estatisticas:
        st.subheader("📊 Análise Real de Performance das Estratégias")
        st.caption(
            "Qual estratégia acerta mais? Qual é mais consistente? Qual usar no seu bolão?")

        # Filtrar apenas cartões verificados
        cartoes_verificados = [
            c for c in cartoes if c.get('verificado', False)]

        if not cartoes_verificados:
            st.warning("📭 Nenhum cartão verificado ainda!")
            st.info("💡 Marque cartões para jogar e verifique os resultados")
            return

        # Sub-abas para organizar melhor
        sub_ranking, sub_evolucao, sub_recomendacao = st.tabs([
            "🏆 Ranking & Consistência",
            "📈 Evolução por Concurso",
            "🎯 Recomendação para Bolão"
        ])

        # Calcular estatísticas completas
        stats_estrategias = _calcular_stats_estrategias_v2(cartoes_verificados)

        with sub_ranking:
            _exibir_ranking_consistencia(stats_estrategias)

        with sub_evolucao:
            _exibir_evolucao_concursos(cartoes_verificados)

        with sub_recomendacao:
            _exibir_recomendacao_bolao(cartoes_verificados)


def _filtrar_cartoes(cartoes, filtro_estrategia, filtro_status):
    """Filtra cartões"""
    resultado = cartoes.copy()

    # Filtro de estratégia
    if filtro_estrategia:
        resultado = [c for c in resultado if c.get(
            'estrategia', 'N/A') in filtro_estrategia]

    # Filtro de status
    if filtro_status != 'Todos':
        if filtro_status == 'Pendentes':
            resultado = [c for c in resultado if not c.get('verificado', False)]
        elif filtro_status == 'Verificados':
            resultado = [c for c in resultado if c.get('verificado', False)]

    return resultado


def _ordenar_cartoes(cartoes, ordenar_por):
    """Ordena cartões"""
    if ordenar_por == 'Mais recente':
        return sorted(cartoes, key=lambda x: x.get('data_criacao', ''), reverse=True)
    elif ordenar_por == 'Mais antigo':
        return sorted(cartoes, key=lambda x: x.get('data_criacao', ''))
    elif ordenar_por == 'Estratégia':
        return sorted(cartoes, key=lambda x: x.get('estrategia', ''))
    elif ordenar_por == 'Acertos (desc)':
        return sorted(cartoes, key=lambda x: x.get('acertos', -1), reverse=True)
    return cartoes


def _exibir_cartao(cartao, idx, df):
    """Exibe um cartão"""
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col1:
            st.markdown(f"**{cartao.get('id', 'N/A')}**")
            nums = " - ".join([f"{n:02d}" for n in cartao.get('dezenas', [])])
            st.code(nums)

        with col2:
            st.caption("Estratégia")
            st.write(cartao.get('estrategia', 'N/A'))

        with col3:
            if cartao.get('verificado', False):
                st.success(f"✅ {cartao.get('acertos', 0)} acertos")
            else:
                st.info(f"⏳ Pendente")

        with col4:
            if st.button("🗑️", key=f"del_{idx}", help="Remover cartão"):
                cartoes = dm.carregar_cartoes_salvos()
                cartoes = [c for c in cartoes if c.get(
                    'id') != cartao.get('id')]
                dm.salvar_cartoes(cartoes)
                st.rerun()

        st.markdown("---")


def _exibir_resultados_verificacao(resultados):
    """Exibe resultados da verificação"""
    # Agrupar por estratégia
    por_estrategia = {}
    for res in resultados:
        est = res['cartao'].get('estrategia', 'N/A')
        por_estrategia.setdefault(est, []).append(res)

    for estrategia, res_list in por_estrategia.items():
        st.markdown(f"#### 🎲 Estratégia: **{estrategia}**")
        for res in res_list:
            cartao = res['cartao']
            acertos = res['acertos']

            # Determinar prêmio
            premio = _calcular_premio(acertos)

            col1, col2, col3 = st.columns([3, 1, 2])

            with col1:
                nums = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
                st.code(nums)

            with col2:
                if acertos >= 4:
                    st.success(f"🎉 {acertos} acertos")
                else:
                    st.info(f"{acertos} acertos")

            with col3:
                st.write(premio)

            st.markdown("---")


def _calcular_premio(acertos):
    """Retorna descrição do prêmio"""
    premios = {
        6: "🏆 SENA!",
        5: "🥈 QUINA",
        4: "🥉 QUADRA",
        3: "👍 Boa tentativa",
        2: "💪 Continue tentando",
        1: "🎯 Próximo jogo!",
        0: "🔄 Tente outra estratégia"
    }
    return premios.get(acertos, "")


def _calcular_stats_para_historico(cartoes_verificados):
    """Calcula stats simplificadas para salvar no histórico (compatibilidade)"""
    stats = {}
    for cartao in cartoes_verificados:
        estrategia = cartao.get('estrategia', 'N/A')
        acertos = cartao.get('acertos', 0)
        qtd_nums = len(cartao.get('dezenas', []))
        if estrategia not in stats:
            stats[estrategia] = {
                'total_jogos': 0, 'total_acertos': 0,
                'senas': 0, 'quinas': 0, 'quadras': 0,
                'ternas': 0, 'duques': 0,
                'melhor_acerto': 0, 'media_acertos': 0,
                'qtd_nums_usadas': []
            }
        s = stats[estrategia]
        s['total_jogos'] += 1
        s['total_acertos'] += acertos
        s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
        if qtd_nums not in s['qtd_nums_usadas']:
            s['qtd_nums_usadas'].append(qtd_nums)
        if acertos == 6: s['senas'] += 1
        elif acertos == 5: s['quinas'] += 1
        elif acertos == 4: s['quadras'] += 1
        elif acertos == 3: s['ternas'] += 1
        elif acertos == 2: s['duques'] += 1
    for est in stats:
        t = stats[est]['total_jogos']
        stats[est]['media_acertos'] = stats[est]['total_acertos'] / t if t > 0 else 0
    return stats


# =============================================================================
# NOVO SISTEMA DE ANÁLISE DE ESTRATÉGIAS V2
# =============================================================================

def _calcular_stats_estrategias_v2(cartoes_verificados):
    """
    Calcula estatísticas detalhadas por estratégia com foco em:
    - Contagens absolutas (não percentuais)
    - Consistência (quantas vezes acertou 3+ em concursos diferentes)
    - Detalhamento por quantidade de números jogados
    - Evolução temporal por concurso
    """
    from collections import defaultdict
    import statistics as py_stats

    stats = {}

    for cartao in cartoes_verificados:
        estrategia = cartao.get('estrategia', 'N/A')
        acertos = cartao.get('acertos', 0)
        qtd_nums = len(cartao.get('dezenas', []))
        concurso = cartao.get('concurso_alvo', 0)

        if estrategia not in stats:
            stats[estrategia] = {
                'total_jogos': 0,
                'total_acertos_soma': 0,
                'senas': 0,
                'quinas': 0,
                'quadras': 0,
                'ternas': 0,
                'melhor_acerto': 0,
                'acertos_list': [],
                'dist_acertos': defaultdict(int),
                'por_concurso': defaultdict(list),
                'por_qtd_nums': defaultdict(list),
                'qtd_nums_usadas': set(),
                'concursos_set': set()
            }

        s = stats[estrategia]
        s['total_jogos'] += 1
        s['total_acertos_soma'] += acertos
        s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
        s['acertos_list'].append(acertos)
        s['dist_acertos'][acertos] += 1
        s['por_concurso'][concurso].append(acertos)
        s['por_qtd_nums'][qtd_nums].append(acertos)
        s['qtd_nums_usadas'].add(qtd_nums)
        s['concursos_set'].add(concurso)

        if acertos == 6: s['senas'] += 1
        elif acertos == 5: s['quinas'] += 1
        elif acertos == 4: s['quadras'] += 1
        elif acertos == 3: s['ternas'] += 1

    # Calcular métricas avançadas de consistência
    for estrategia in stats:
        s = stats[estrategia]
        total = s['total_jogos']

        # Média de acertos
        s['media_acertos'] = s['total_acertos_soma'] / total if total > 0 else 0

        # Contagem absoluta de 3+ acertos
        s['qtd_3_mais'] = sum(1 for a in s['acertos_list'] if a >= 3)
        s['qtd_2_mais'] = sum(1 for a in s['acertos_list'] if a >= 2)

        # === CONSISTÊNCIA ===
        # Em quantos CONCURSOS DIFERENTES teve pelo menos 1 jogo com 3+ acertos?
        concursos_com_3_mais = 0
        concursos_com_2_mais = 0
        total_concursos = len(s['por_concurso'])
        melhores_por_concurso = []

        for conc, acertos_list in s['por_concurso'].items():
            melhor_conc = max(acertos_list)
            melhores_por_concurso.append(melhor_conc)
            if melhor_conc >= 3:
                concursos_com_3_mais += 1
            if melhor_conc >= 2:
                concursos_com_2_mais += 1

        s['total_concursos'] = total_concursos
        s['concursos_com_3_mais'] = concursos_com_3_mais
        s['concursos_com_2_mais'] = concursos_com_2_mais

        # Consistência = desvio padrão dos melhores acertos por concurso
        # Menor desvio = mais consistente
        if len(melhores_por_concurso) > 1:
            s['desvio_padrao'] = py_stats.stdev(melhores_por_concurso)
        else:
            s['desvio_padrao'] = 0

        s['melhores_por_concurso'] = melhores_por_concurso

        # Sequência de concursos consecutivos com 3+ (streak)
        s['streak_3_mais'] = _calcular_streak(s['por_concurso'], 3)
        s['streak_2_mais'] = _calcular_streak(s['por_concurso'], 2)

        # Score de consistência: prioriza quem acerta regularmente
        # Fórmula: (concursos com 3+) * 100 + (concursos com 2+) * 10 + ternas * 5 + quadras * 50
        s['score_consistencia'] = (
            concursos_com_3_mais * 100 +
            concursos_com_2_mais * 10 +
            s['ternas'] * 5 +
            s['quadras'] * 50 +
            s['quinas'] * 500 +
            s['senas'] * 5000
        )
        s['score_por_concurso'] = s['score_consistencia'] / total_concursos if total_concursos > 0 else 0

    return stats


def _calcular_streak(por_concurso, min_acertos):
    """Calcula a maior sequência consecutiva de concursos com acertos >= min_acertos"""
    concursos_ordenados = sorted(por_concurso.keys())
    melhor_streak = 0
    streak_atual = 0
    for conc in concursos_ordenados:
        melhor_do_concurso = max(por_concurso[conc])
        if melhor_do_concurso >= min_acertos:
            streak_atual += 1
            melhor_streak = max(melhor_streak, streak_atual)
        else:
            streak_atual = 0
    return melhor_streak


def _exibir_ranking_consistencia(stats):
    """Exibe ranking focado em consistência e dados absolutos"""
    st.markdown("### 🏆 Ranking de Estratégias — Foco em Consistência")
    st.caption(
        "Ordenado por quem acerta mais REGULARMENTE, não por sorte pontual. "
        "Uma estratégia que acerta 3 em vários concursos é melhor que uma que acertou 5 uma única vez."
    )

    # Ordenar por score de consistencia por concurso
    ranking = sorted(
        stats.items(),
        key=lambda x: (x[1]['score_por_concurso'], x[1]['concursos_com_3_mais'], x[1]['media_acertos']),
        reverse=True
    )

    for pos, (estrategia, d) in enumerate(ranking, 1):
        medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"#{pos}"

        # Montar resumo de qtd de números usados
        qtds = sorted(d['qtd_nums_usadas'])
        qtd_str = ", ".join(str(q) for q in qtds)

        with st.container():
            st.markdown(
                f"{medalha} **{estrategia.upper()}** — "
                f"{d['total_jogos']} jogos em {d['total_concursos']} concurso(s) | "
                f"Jogou com **{qtd_str} números**"
            )

            # Linha 1: Métricas principais em números absolutos
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Melhor Acerto", f"{d['melhor_acerto']} de 6")
            c2.metric("Ternas (3 ac)", d['ternas'])
            c3.metric("Quadras (4 ac)", d['quadras'])
            c4.metric("Quinas (5 ac)", d['quinas'])
            c5.metric("Senas (6 ac)", d['senas'])

            # Linha 2: Consistência
            c1b, c2b, c3b, c4b = st.columns(4)
            c1b.metric(
                "Concursos com 3+ acertos",
                f"{d['concursos_com_3_mais']}/{d['total_concursos']}",
                help="Em quantos concursos diferentes esta estratégia acertou pelo menos 3 números em algum jogo"
            )
            c2b.metric(
                "Concursos com 2+ acertos",
                f"{d['concursos_com_2_mais']}/{d['total_concursos']}",
                help="Em quantos concursos diferentes esta estratégia acertou pelo menos 2 números"
            )
            c3b.metric(
                "Sequência 3+ (streak)",
                f"{d['streak_3_mais']} concurso(s)",
                help="Máxima sequência consecutiva de concursos com pelo menos 3 acertos"
            )
            c4b.metric(
                "Média acertos/jogo",
                f"{d['media_acertos']:.1f}",
                help="Média de dezenas acertadas por jogo"
            )

            # Distribuição visual de acertos
            dist = d['dist_acertos']
            partes = []
            for k in sorted(dist.keys()):
                v = dist[k]
                if v > 0:
                    partes.append(f"**{k}ac:** {v}")
            st.caption(f"Distribuição: {' | '.join(partes)}")

            # Histórico por concurso (melhor acerto em cada)
            concursos_ord = sorted(d['por_concurso'].keys())
            historico_parts = []
            for conc in concursos_ord:
                ac_list = d['por_concurso'][conc]
                melhor = max(ac_list)
                jogos_conc = len(ac_list)
                emoji = "🟢" if melhor >= 3 else "🟡" if melhor >= 2 else "🔴"
                historico_parts.append(f"{emoji} C{conc}: {melhor}ac ({jogos_conc}j)")
            st.caption(f"Por concurso: {' | '.join(historico_parts)}")

            # Prêmios
            premios_parts = []
            if d['senas'] > 0: premios_parts.append(f"🏆 {d['senas']} Sena")
            if d['quinas'] > 0: premios_parts.append(f"🥈 {d['quinas']} Quina")
            if d['quadras'] > 0: premios_parts.append(f"🥉 {d['quadras']} Quadra")
            if d['ternas'] > 0: premios_parts.append(f"👍 {d['ternas']} Terna")
            if premios_parts:
                st.write(" | ".join(premios_parts))

            st.markdown("---")

    # Tabela comparativa rápida
    st.markdown("### 📋 Tabela Comparativa Rápida")
    tabela_data = []
    for est, d in ranking:
        qtds = sorted(d['qtd_nums_usadas'])
        tabela_data.append({
            'Estratégia': est.upper(),
            'Jogos': d['total_jogos'],
            'Concursos': d['total_concursos'],
            'Nº Números': "/".join(str(q) for q in qtds),
            'Ternas': d['ternas'],
            'Quadras': d['quadras'],
            'Quinas': d['quinas'],
            'Melhor': d['melhor_acerto'],
            'Conc. c/ 3+': f"{d['concursos_com_3_mais']}/{d['total_concursos']}",
            'Streak 3+': d['streak_3_mais'],
            'Média': f"{d['media_acertos']:.1f}"
        })
    df_tab = pd.DataFrame(tabela_data)
    st.dataframe(df_tab, hide_index=True, use_container_width=True)


def _exibir_evolucao_concursos(cartoes_verificados):
    """Mostra evolução do melhor acerto de cada estratégia ao longo dos concursos"""
    from collections import defaultdict

    st.markdown("### 📈 Evolução por Concurso")
    st.caption(
        "Como cada estratégia se comportou ao longo do tempo. "
        "Veja se ela mantém acertos consistentes ou se é aleatória."
    )

    # Agrupar por estratégia e concurso
    dados = defaultdict(lambda: defaultdict(list))
    for c in cartoes_verificados:
        est = c.get('estrategia', 'N/A')
        conc = c.get('concurso_alvo', 0)
        acertos = c.get('acertos', 0)
        dados[est][conc].append(acertos)

    # Construir DataFrame para gráfico
    concursos_todos = sorted(set(
        c.get('concurso_alvo', 0) for c in cartoes_verificados
    ))

    # Gráfico: Melhor acerto por concurso por estratégia
    grafico_data = {}
    for est, por_conc in dados.items():
        melhores = []
        for conc in concursos_todos:
            if conc in por_conc:
                melhores.append(max(por_conc[conc]))
            else:
                melhores.append(None)
        grafico_data[est.upper()] = melhores

    df_grafico = pd.DataFrame(grafico_data, index=[f"C{c}" for c in concursos_todos])
    st.markdown("#### Melhor acerto por concurso")
    st.line_chart(df_grafico)

    # Detalhamento por estratégia
    st.markdown("---")
    st.markdown("#### 🔍 Detalhamento por Estratégia e Concurso")

    estrategia_selecionada = st.selectbox(
        "Selecione a estratégia para detalhar",
        options=sorted(dados.keys()),
        key="sel_est_evolucao"
    )

    if estrategia_selecionada:
        por_conc = dados[estrategia_selecionada]
        for conc in sorted(por_conc.keys()):
            ac_list = por_conc[conc]
            melhor = max(ac_list)
            total_jogos = len(ac_list)

            # Distribuição no concurso
            dist_conc = defaultdict(int)
            for a in ac_list:
                dist_conc[a] += 1

            emoji = "🟢" if melhor >= 3 else "🟡" if melhor >= 2 else "🔴"

            col1, col2, col3 = st.columns([2, 3, 3])
            with col1:
                st.markdown(f"{emoji} **Concurso {conc}**")
            with col2:
                st.markdown(f"**{total_jogos}** jogos | Melhor: **{melhor} acertos**")
            with col3:
                dist_str = " | ".join(f"{k}ac: {v}" for k, v in sorted(dist_conc.items()))
                st.caption(dist_str)


def _exibir_recomendacao_bolao(cartoes_verificados):
    """
    Recomendação de qual estratégia usar para um bolão com X números.
    Analisa performance normalizada pela quantidade de números.
    """
    from collections import defaultdict
    import statistics as py_stats

    st.markdown("### 🎯 Recomendação para Bolão")
    st.caption(
        "Você está testando com 10-20 números para avaliar estratégias. "
        "Aqui mostramos qual estratégia tem melhor desempenho para cada tamanho de jogo, "
        "ajudando na sua decisão de qual usar no bolão real."
    )

    # Agrupar por qtd_nums e estratégia
    dados = defaultdict(lambda: defaultdict(list))
    for c in cartoes_verificados:
        est = c.get('estrategia', 'N/A')
        qtd = len(c.get('dezenas', []))
        acertos = c.get('acertos', 0)
        dados[qtd][est].append(acertos)

    qtd_disponiveis = sorted(dados.keys())

    if not qtd_disponiveis:
        st.warning("Sem dados suficientes.")
        return

    # Seletor de quantidade de números para análise
    st.markdown("#### Selecione o tamanho do jogo para análise")

    col1, col2 = st.columns([2, 3])
    with col1:
        qtd_bolao = st.selectbox(
            "🔢 Quantos números no bolão?",
            options=qtd_disponiveis,
            format_func=lambda x: f"{x} números",
            index=0,
            key="sel_qtd_bolao"
        )

    with col2:
        st.info(
            f"Analisando dados de jogos com **{qtd_bolao} números**. "
            f"Estratégias disponíveis: **{len(dados[qtd_bolao])}**"
        )

    # Ranking para o tamanho selecionado
    st.markdown(f"#### 🏆 Ranking para jogos de {qtd_bolao} números")

    ranking_bolao = []
    for est, acertos_list in dados[qtd_bolao].items():
        total = len(acertos_list)
        media = sum(acertos_list) / total
        ternas = sum(1 for a in acertos_list if a == 3)
        quadras = sum(1 for a in acertos_list if a == 4)
        quinas = sum(1 for a in acertos_list if a == 5)
        senas = sum(1 for a in acertos_list if a == 6)
        qtd_3_mais = sum(1 for a in acertos_list if a >= 3)
        qtd_2_mais = sum(1 for a in acertos_list if a >= 2)
        melhor = max(acertos_list)

        # Desvio padrão (menor = mais consistente)
        desvio = py_stats.stdev(acertos_list) if total > 1 else 0

        # Score: prioriza consistência de acertos altos
        score = qtd_3_mais * 100 + qtd_2_mais * 10 + ternas * 5 + quadras * 50 + quinas * 500 + senas * 5000
        score_norm = score / total if total > 0 else 0

        ranking_bolao.append({
            'estrategia': est,
            'total': total,
            'media': media,
            'ternas': ternas,
            'quadras': quadras,
            'quinas': quinas,
            'senas': senas,
            'qtd_3_mais': qtd_3_mais,
            'qtd_2_mais': qtd_2_mais,
            'melhor': melhor,
            'desvio': desvio,
            'score': score,
            'score_norm': score_norm,
            'acertos_list': acertos_list
        })

    # Ordenar por score normalizado
    ranking_bolao.sort(key=lambda x: (x['score_norm'], x['qtd_3_mais'], x['media']), reverse=True)

    if not ranking_bolao:
        st.warning(f"Nenhum dado para jogos de {qtd_bolao} números.")
        return

    # Destaque: Melhor estratégia recomendada
    melhor_est = ranking_bolao[0]
    st.success(
        f"✅ **RECOMENDAÇÃO:** Para um bolão de **{qtd_bolao} números**, "
        f"use a estratégia **{melhor_est['estrategia'].upper()}** — "
        f"acertou 3+ em **{melhor_est['qtd_3_mais']}** de **{melhor_est['total']}** jogos, "
        f"média de **{melhor_est['media']:.1f}** acertos/jogo"
    )

    for pos, d in enumerate(ranking_bolao, 1):
        medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"#{pos}"

        with st.container():
            st.markdown(
                f"{medalha} **{d['estrategia'].upper()}** — {d['total']} jogos de {qtd_bolao} números"
            )

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Melhor Acerto", f"{d['melhor']}/6")
            c2.metric("Ternas (3ac)", d['ternas'])
            c3.metric("Vezes com 3+", f"{d['qtd_3_mais']}/{d['total']}")
            c4.metric("Vezes com 2+", f"{d['qtd_2_mais']}/{d['total']}")
            c5.metric("Média acertos", f"{d['media']:.1f}")

            # Distribuição
            from collections import Counter
            dist = Counter(d['acertos_list'])
            partes = " | ".join(f"**{k}ac:** {v}" for k, v in sorted(dist.items()))
            st.caption(f"Distribuição: {partes}")

            st.markdown("---")

    # Tabela comparativa
    st.markdown("#### 📋 Tabela Comparativa")
    tab_data = []
    for d in ranking_bolao:
        tab_data.append({
            'Estratégia': d['estrategia'].upper(),
            'Jogos': d['total'],
            'Ternas': d['ternas'],
            'Quadras': d['quadras'],
            'Quinas': d['quinas'],
            'Melhor': d['melhor'],
            'c/ 3+': d['qtd_3_mais'],
            'c/ 2+': d['qtd_2_mais'],
            'Média': f"{d['media']:.1f}",
            'Desvio': f"{d['desvio']:.2f}"
        })
    st.dataframe(pd.DataFrame(tab_data), hide_index=True, use_container_width=True)

    # Comparação entre tamanhos de jogo
    if len(qtd_disponiveis) > 1:
        st.markdown("---")
        st.markdown("#### 📊 Comparação entre tamanhos de jogo")
        st.caption(
            "Veja como a performance muda quando joga com mais ou menos números. "
            "Isso ajuda a calibrar expectativas ao reduzir de 20 para 10 números."
        )

        comparacao = []
        for qtd in qtd_disponiveis:
            for est, ac_list in dados[qtd].items():
                total = len(ac_list)
                media = sum(ac_list) / total
                qtd_3 = sum(1 for a in ac_list if a >= 3)
                melhor = max(ac_list)
                comparacao.append({
                    'Nº Números': qtd,
                    'Estratégia': est.upper(),
                    'Jogos': total,
                    'Média': f"{media:.1f}",
                    'c/ 3+ acertos': qtd_3,
                    'Melhor': melhor
                })
        df_comp = pd.DataFrame(comparacao)
        df_comp = df_comp.sort_values(['Nº Números', 'c/ 3+ acertos'], ascending=[True, False])
        st.dataframe(df_comp, hide_index=True, use_container_width=True)

