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
    'pares_frequentes', 'ciclos', 'ensemble_v2'
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
    'ensemble_v2': '🧠✨ Ensemble V2',
    'automl': '🤖 AutoML',
    'Manual': '✍️ Manual'
}


def _nome_estrategia(key) -> str:
    return NOMES_ESTRATEGIAS.get(key, str(key))


def _calcular_custo(qtd):
    return CUSTOS_CARTAO.get(qtd, 0.0)


def _calcular_combinacoes(qtd):
    from math import comb
    return comb(qtd, 6) if qtd >= 6 else 0


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_simulacao(df):
    """Página central de Simulação e Conferência"""
    
    st.title("🎯 Simulação & Conferência")
    st.markdown("### Gere jogos, confira resultados e descubra qual estratégia funciona melhor")

    tab_simular, tab_conferir, tab_ranking = st.tabs([
        "🎲 Simular Jogos",
        "✅ Conferir Resultados",
        "🏆 Ranking de Estratégias"
    ])

    with tab_simular:
        _aba_simular(df)

    with tab_conferir:
        _aba_conferir(df)

    with tab_ranking:
        _aba_ranking(df)


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

    total_cartoes = qtd_cartoes_por_estrategia * len(estrategias_selecionadas)
    custo_total = total_cartoes * _calcular_custo(qtd_numeros)
    combinacoes_total = total_cartoes * _calcular_combinacoes(qtd_numeros)

    st.info(f"""
    📊 **Resumo da simulação:**
    - **{len(estrategias_selecionadas)}** estratégias × **{qtd_cartoes_por_estrategia}** cartões = **{total_cartoes} cartões** no total
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
                
                for i in range(qtd_cartoes_por_estrategia):
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

def _aba_conferir(df):
    """Aba de conferência de resultados"""
    
    st.subheader("✅ Conferir Resultados do Concurso")

    # Carregar cartões
    todos_cartoes = dm.carregar_cartoes_salvos()
    
    # Listar concursos com jogos pendentes
    concursos_pendentes = sorted(set(
        c.get('concurso_alvo') for c in todos_cartoes
        if c.get('concurso_alvo') and not c.get('verificado', False)
    ))

    if not concursos_pendentes:
        st.info("📭 Nenhum concurso pendente de conferência. Gere jogos na aba 'Simular Jogos'.")
        
        # Mostrar opção de conferir qualquer concurso
        st.markdown("---")
        st.markdown("#### 🔍 Conferir concurso específico")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if concursos_pendentes:
            concurso_conferir = st.selectbox(
                "🎯 Concurso para conferir",
                options=concursos_pendentes,
                format_func=lambda x: f"Concurso {x} ({sum(1 for c in todos_cartoes if c.get('concurso_alvo') == x and not c.get('verificado', False))} jogos pendentes)"
            )
        else:
            ultimo = int(df['concurso'].max()) if 'concurso' in df.columns else 2955
            concurso_conferir = st.number_input(
                "Número do concurso", min_value=1, max_value=9999,
                value=ultimo, step=1
            )

    with col2:
        st.markdown("##### ")
        conferir_btn = st.button("🔍 CONFERIR", type="primary", width="stretch")

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
        st.markdown("Os jogos estão aguardando o sorteio:")
        
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

    # Agrupar por estratégia
    por_estrategia = {}
    for r in resultados:
        est = r['estrategia']
        por_estrategia.setdefault(est, []).append(r)

    for estrategia, jogos_est in por_estrategia.items():
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
    """Aba com ranking consolidado de todas as estratégias"""
    
    st.subheader("🏆 Ranking Geral de Estratégias")
    st.caption("Baseado em todos os concursos verificados")

    # Fonte 1: Cartões verificados salvos
    todos_cartoes = dm.carregar_cartoes_salvos()
    cartoes_verificados = [c for c in todos_cartoes if c.get('verificado', False) and c.get('acertos') is not None]

    # Fonte 2: Histórico arquivado
    historico = dm.carregar_historico_analises()

    if not cartoes_verificados and not historico:
        st.info("📭 Nenhum dado de performance ainda. Gere jogos, confira resultados e os dados aparecerão aqui!")
        return

    # ---- RANKING DOS CARTÕES VERIFICADOS ----
    if cartoes_verificados:
        st.markdown("### 📊 Ranking dos Cartões Verificados")

        import statistics as st_mod

        ranking = {}
        acertos_por_est = {}
        for c in cartoes_verificados:
            est = c.get('estrategia', 'N/A')
            if est not in ranking:
                ranking[est] = {
                    'jogos': 0, 'total_acertos': 0,
                    'senas': 0, 'quinas': 0, 'quadras': 0,
                    'melhor_acerto': 0, 'concursos': set()
                }
                acertos_por_est[est] = []
            r = ranking[est]
            r['jogos'] += 1
            acertos = c.get('acertos', 0)
            r['total_acertos'] += acertos
            acertos_por_est[est].append(acertos)
            r['melhor_acerto'] = max(r['melhor_acerto'], acertos)
            if acertos == 6:
                r['senas'] += 1
            elif acertos == 5:
                r['quinas'] += 1
            elif acertos == 4:
                r['quadras'] += 1
            if c.get('concurso_alvo'):
                r['concursos'].add(c['concurso_alvo'])

        # Calcular score, média e IC95%
        ranking_lista = []
        for est, dados in ranking.items():
            n = dados['jogos']
            media = dados['total_acertos'] / n if n > 0 else 0
            desvio = st_mod.stdev(acertos_por_est[est]) if n > 1 else 0
            ic95 = 1.96 * desvio / (n ** 0.5) if n > 1 else 0
            score = dados['senas'] * 1000 + dados['quinas'] * 100 + dados['quadras'] * 10 + media
            ranking_lista.append({
                'Estratégia': _nome_estrategia(est),
                'est_key': est,
                'Jogos': n,
                'Média Acertos': round(media, 2),
                'IC95% Inf': round(media - ic95, 3),
                'IC95% Sup': round(media + ic95, 3),
                'Desvio': round(desvio, 3),
                'Senas': dados['senas'],
                'Quinas': dados['quinas'],
                'Quadras': dados['quadras'],
                'Melhor': dados['melhor_acerto'],
                'Concursos': len(dados['concursos']),
                'Score': round(score, 2)
            })

        ranking_lista.sort(key=lambda x: x['Média Acertos'], reverse=True)

        # Destaque top 3 com IC95%
        for i, item in enumerate(ranking_lista[:3]):
            medalha = ["🥇", "🥈", "🥉"][i]
            cols = st.columns([1, 3, 2, 2, 2])
            cols[0].markdown(f"### {medalha}")
            cols[1].markdown(f"**{item['Estratégia']}**\n\n{item['Jogos']} jogos em {item['Concursos']} concurso(s)")
            cols[2].metric("Média", f"{item['Média Acertos']:.2f}")
            cols[3].metric("IC 95%", f"[{item['IC95% Inf']:.2f}, {item['IC95% Sup']:.2f}]")
            cols[4].markdown(f"🏆 {item['Senas']}S | 🥈 {item['Quinas']}Q | 🥉 {item['Quadras']}Q")
            st.markdown("---")

        # Tabela completa com IC95%
        df_ranking = pd.DataFrame([
            {k: v for k, v in r.items() if k != 'est_key'}
            for r in ranking_lista
        ])
        st.dataframe(df_ranking, width="stretch", hide_index=True)

        # Análise de significância
        if len(ranking_lista) >= 2:
            st.markdown("### 📐 Análise de Significância Estatística")
            melhor = ranking_lista[0]
            significancia = []
            for r in ranking_lista[1:]:
                sobrepoe = melhor['IC95% Inf'] < r['IC95% Sup'] and r['IC95% Inf'] < melhor['IC95% Sup']
                significancia.append({
                    'Comparação': f"{melhor['Estratégia']} vs {r['Estratégia']}",
                    'Diferença': round(melhor['Média Acertos'] - r['Média Acertos'], 3),
                    'Resultado': "Indistinguível" if sobrepoe else "Significativamente melhor",
                })
            df_sig = pd.DataFrame(significancia)
            st.dataframe(df_sig, width="stretch", hide_index=True)

            n_indist = sum(1 for s in significancia if s['Resultado'] == "Indistinguível")
            if n_indist == len(significancia):
                st.warning("Todas as estratégias estão dentro da margem de erro. Mais concursos necessários para conclusão.")
            else:
                n_melhores = len(significancia) - n_indist
                st.success(f"A estratégia **{melhor['Estratégia']}** é significativamente melhor que {n_melhores} outra(s).")

        # Gráfico com barras de erro
        st.markdown("### 📈 Comparativo Visual (com intervalo de confiança)")
        df_grafico = pd.DataFrame({
            'Estratégia': [r['Estratégia'] for r in ranking_lista],
            'Média de Acertos': [r['Média Acertos'] for r in ranking_lista]
        })
        st.bar_chart(df_grafico.set_index('Estratégia'))

    # ---- RANKING DO HISTÓRICO ARQUIVADO ----
    if historico:
        st.markdown("---")
        st.markdown("### 📚 Ranking do Histórico Arquivado")
        st.caption("Dados consolidados de todos os concursos arquivados")

        ranking_hist = {}
        for item in historico:
            estatisticas = item.get('estatisticas', {})
            for est, dados in estatisticas.items():
                if est not in ranking_hist:
                    ranking_hist[est] = {
                        'jogos': 0, 'senas': 0, 'quinas': 0,
                        'quadras': 0, 'melhor_acerto': 0, 'concursos': 0
                    }
                rh = ranking_hist[est]
                rh['jogos'] += dados.get('total_jogos', 0)
                rh['senas'] += dados.get('senas', 0)
                rh['quinas'] += dados.get('quinas', 0)
                rh['quadras'] += dados.get('quadras', 0)
                rh['melhor_acerto'] = max(rh['melhor_acerto'], dados.get('melhor_acerto', 0))
                rh['concursos'] += 1

        if ranking_hist:
            ranking_hist_lista = []
            for est, dados in ranking_hist.items():
                ranking_hist_lista.append({
                    'Estratégia': _nome_estrategia(est),
                    'Jogos': dados['jogos'],
                    'Senas': dados['senas'],
                    'Quinas': dados['quinas'],
                    'Quadras': dados['quadras'],
                    'Melhor Acerto': dados['melhor_acerto'],
                    'Concursos Verificados': dados['concursos']
                })

            ranking_hist_lista.sort(
                key=lambda x: (x['Senas'], x['Quinas'], x['Quadras'], x['Melhor Acerto']),
                reverse=True
            )

            df_hist = pd.DataFrame(ranking_hist_lista)
            st.dataframe(df_hist, width="stretch", hide_index=True)

    # ---- PERFORMANCE POR CONCURSO ----
    if cartoes_verificados:
        st.markdown("---")
        st.markdown("### 🗓️ Performance por Concurso")

        concursos_verificados = sorted(set(
            c.get('concurso_alvo') for c in cartoes_verificados if c.get('concurso_alvo')
        ), reverse=True)

        for concurso in concursos_verificados[:10]:  # Últimos 10
            jogos_c = [c for c in cartoes_verificados if c.get('concurso_alvo') == concurso]
            melhor = max(c.get('acertos', 0) for c in jogos_c)
            media = sum(c.get('acertos', 0) for c in jogos_c) / len(jogos_c)

            with st.expander(f"Concurso {concurso} — {len(jogos_c)} jogos | Melhor: {melhor} | Média: {media:.1f}"):
                # Agrupar por estratégia
                por_est = {}
                for c in jogos_c:
                    est = c.get('estrategia', 'N/A')
                    por_est.setdefault(est, []).append(c.get('acertos', 0))

                for est, acertos_list in sorted(por_est.items(), key=lambda x: max(x[1]), reverse=True):
                    media_est = sum(acertos_list) / len(acertos_list)
                    max_est = max(acertos_list)
                    st.markdown(
                        f"**{_nome_estrategia(est)}**: {len(acertos_list)} jogos | "
                        f"Média: {media_est:.1f} | Melhor: {max_est}"
                    )


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
    """Mostra ranking de estratégias para um concurso específico"""
    por_estrategia = {}
    for r in resultados:
        est = r['estrategia']
        por_estrategia.setdefault(est, []).append(r['acertos'])

    ranking = []
    for est, acertos_list in por_estrategia.items():
        media = sum(acertos_list) / len(acertos_list)
        melhor = max(acertos_list)
        quadras = sum(1 for a in acertos_list if a == 4)
        quinas = sum(1 for a in acertos_list if a == 5)
        senas = sum(1 for a in acertos_list if a == 6)
        score = senas * 1000 + quinas * 100 + quadras * 10 + media
        ranking.append({
            'Estratégia': _nome_estrategia(est),
            'Jogos': len(acertos_list),
            'Média': round(media, 2),
            'Melhor': melhor,
            'Quadras': quadras,
            'Quinas': quinas,
            'Senas': senas,
            'Score': round(score, 2)
        })

    ranking.sort(key=lambda x: x['Score'], reverse=True)

    if ranking:
        # Destacar vencedor
        top = ranking[0]
        st.success(f"🥇 **Melhor estratégia: {top['Estratégia']}** — Média: {top['Média']:.2f} acertos | Melhor jogo: {top['Melhor']} acertos")

    df_ranking = pd.DataFrame(ranking)
    st.dataframe(df_ranking, width="stretch", hide_index=True)


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
