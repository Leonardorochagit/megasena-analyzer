"""
================================================================================
🔬 PÁGINA: SIMULADOR VISUAL DE COMBINAÇÕES DE ESTRATÉGIAS (14 NÚMEROS)
================================================================================
Testa diferentes combinações de estratégias no ensemble com
cartões de 14 números (C(14,6)=3.003 combinações por cartão).
Progresso visual em tempo real, rankings e gráficos.
================================================================================
"""

import streamlit as st
import pandas as pd
import random
import time
import json
import os
from collections import Counter
from modules import statistics as stats
from modules import game_generator as gen


# =============================================================================
# ESTRATÉGIAS DISPONÍVEIS
# =============================================================================

ESTRATEGIAS_DISPONIVEIS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Números Atrasados',
    'quentes': '🔥 Números Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Inteligente',
    'sequencias': '🧬 Sequências',
    'wheel': '🎯 Wheel',
    'candidatos_ouro': '🥇 Candidatos Ouro',
    'momentum': '🚀 Momentum',
    'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Frequência Desvio',
    'pares_frequentes': '👫 Pares Frequentes',
    'ciclos': '🔁 Ciclos',
}

NOMES_CURTOS = {
    'escada': 'Escada', 'atrasados': 'Atras.', 'quentes': 'Quent.',
    'equilibrado': 'Equil.', 'misto': 'Misto', 'consenso': 'Consen.',
    'aleatorio_smart': 'Aleat.', 'sequencias': 'Sequ.', 'wheel': 'Wheel',
    'candidatos_ouro': 'C.Ouro', 'momentum': 'Moment.', 'vizinhanca': 'Vizin.',
    'frequencia_desvio': 'F.Desv.', 'pares_frequentes': 'Pares', 'ciclos': 'Ciclos'
}

ARQUIVO_RESULTADO = "sim_combinacoes_resultado.json"

NUMS_POR_CARTAO = 14  # Cartão de 14 números — C(14,6)=3.003 combinações


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _gerar_ensemble_14(estrategias_lista, contagem_total, contagem_recente, df_atrasos, df=None):
    """Gera um cartão de 14 números usando ensemble de estratégias.
    Pega os 14 números mais votados pelo conjunto de estratégias.
    """
    votos = Counter()
    for est in estrategias_lista:
        try:
            jogo = gen.gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
            for n in jogo:
                votos[n] += 1
        except Exception:
            pass

    if not votos:
        return sorted(random.sample(range(1, 61), NUMS_POR_CARTAO))

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    if len(candidatos) >= NUMS_POR_CARTAO:
        return sorted(candidatos[:NUMS_POR_CARTAO])
    else:
        extras = [n for n in range(1, 61) if n not in candidatos]
        random.shuffle(extras)
        todos = candidatos + extras[:NUMS_POR_CARTAO - len(candidatos)]
        return sorted(todos[:NUMS_POR_CARTAO])


def _preparar_concursos(df, n_concursos):
    """Pré-calcula dados de concursos de teste (evita repetir)."""
    ultimo = df['concurso'].max()
    concursos = list(range(ultimo - n_concursos + 1, ultimo + 1))
    dados = []
    for conc in concursos:
        mask = df['concurso'] == conc
        if not mask.any():
            continue
        row = df[mask].iloc[0]
        resultado_real = sorted([int(row[f'dez{i}']) for i in range(1, 7)])
        df_treino = df[df['concurso'] < conc].copy().reset_index(drop=True)
        if len(df_treino) < 100:
            continue
        contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df_treino)
        dados.append({
            'concurso': conc,
            'resultado': resultado_real,
            'contagem_total': contagem_total,
            'contagem_recente': contagem_recente,
            'df_atrasos': df_atrasos,
            'df_treino': df_treino,
        })
    return dados


def _avaliar_combo(combo, dados_concursos, n_jogos):
    """Avalia uma combinação de estratégias com cartões de 14 números."""
    acertos_total = []
    melhores = []
    dist = Counter()

    for dc in dados_concursos:
        melhor = 0
        random.seed(dc['concurso'])
        for _ in range(n_jogos):
            try:
                jogo14 = _gerar_ensemble_14(
                    list(combo),
                    dc['contagem_total'], dc['contagem_recente'],
                    dc['df_atrasos'], df=dc['df_treino']
                )
                ac = len(set(jogo14) & set(dc['resultado']))
                acertos_total.append(ac)
                dist[ac] += 1
                if ac > melhor:
                    melhor = ac
            except Exception:
                pass
        melhores.append(melhor)

    media = sum(acertos_total) / len(acertos_total) if acertos_total else 0
    maximo = max(melhores) if melhores else 0
    melhor_med = sum(melhores) / len(melhores) if melhores else 0
    senas = sum(v for k, v in dist.items() if k == 6)
    quinas = sum(v for k, v in dist.items() if k == 5)
    quadras = sum(v for k, v in dist.items() if k == 4)
    ternos = sum(v for k, v in dist.items() if k == 3)

    return {
        'combo': list(combo),
        'media': media,
        'max': maximo,
        'melhor_med': melhor_med,
        'melhores': melhores,
        'dist': dict(dist),
        'total_jogos': len(acertos_total),
        'senas': senas,
        'quinas': quinas,
        'quadras': quadras,
        'ternos': ternos,
    }


def _combo_label(combo):
    """Label curta para uma combinação."""
    nomes = [NOMES_CURTOS.get(e, e) for e in combo]
    if len(nomes) <= 5:
        return ' + '.join(nomes)
    return ' + '.join(nomes[:4]) + f' +{len(nomes)-4}'


def _resultados_para_df(resultados):
    """Converte lista de resultados em DataFrame para exibição."""
    linhas = []
    for i, r in enumerate(resultados):
        medalha = '🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else f'{i+1}º'
        nomes = [ESTRATEGIAS_DISPONIVEIS.get(e, e) for e in r['combo']]
        linhas.append({
            ' ': medalha,
            'Tam': len(r['combo']),
            'Média': round(r['media'], 3),
            'MAX': r['max'],
            '🎯6': r.get('senas', 0),
            '⭐5': r.get('quinas', 0),
            '🟢4': r.get('quadras', 0),
            '🔵3': r.get('ternos', 0),
            'Combinação': ', '.join(nomes),
        })
    return pd.DataFrame(linhas)


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_simulador_combinacoes(df):
    """Página visual do simulador de combinações."""

    st.header("🔬 Simulador de Combinações (14 Números)")
    st.caption(
        "Cartões de **14 números** — C(14,6) = 3.003 combinações por cartão. "
        "Melhor tamanho de ensemble: **10 estratégias**."
    )

    # Inicializar session state
    if 'sim_ranking' not in st.session_state:
        st.session_state['sim_ranking'] = []
    if 'sim_dados_concursos' not in st.session_state:
        st.session_state['sim_dados_concursos'] = None
    if 'sim_cfg' not in st.session_state:
        st.session_state['sim_cfg'] = {'n_concursos': 0, 'n_jogos': 0}
    # Limpar ranking antigo (6 nums) se existir
    if st.session_state.get('sim_mode') != '14nums':
        st.session_state['sim_ranking'] = []
        st.session_state['sim_mode'] = '14nums'

    # =========================================================================
    # SIDEBAR: CONFIGURAÇÃO
    # =========================================================================
    with st.sidebar:
        st.markdown("### ⚙️ Config Simulador")
        n_concursos = st.number_input(
            "Concursos de teste", 5, 500, 15, key="sim_n_conc",
            help="Concursos recentes para testar"
        )
        n_jogos = st.number_input(
            "Cartões por concurso", 5, 200, 40, key="sim_n_jogos",
            help="Cartões ensemble gerados por concurso"
        )

        # Preparar concursos (cache no session_state)
        cfg_atual = {'n_concursos': n_concursos, 'n_jogos': n_jogos}
        if (st.session_state['sim_dados_concursos'] is None or
                st.session_state['sim_cfg']['n_concursos'] != n_concursos):
            if st.button("📊 Preparar concursos", use_container_width=True):
                with st.spinner(f"Calculando estatísticas de {n_concursos} concursos..."):
                    st.session_state['sim_dados_concursos'] = _preparar_concursos(df, n_concursos)
                    st.session_state['sim_cfg'] = cfg_atual
                st.success(f"{len(st.session_state['sim_dados_concursos'])} concursos prontos")
                st.rerun()
        else:
            n_prep = len(st.session_state['sim_dados_concursos'])
            st.success(f"{n_prep} concursos prontos")

        st.markdown("---")
        st.markdown(f"**Ranking:** {len(st.session_state['sim_ranking'])} combos")
        if st.session_state['sim_ranking']:
            if st.button("🗑️ Limpar ranking", use_container_width=True):
                st.session_state['sim_ranking'] = []
                st.rerun()

    # =========================================================================
    # LAYOUT PRINCIPAL: 2 COLUNAS
    # =========================================================================
    col_esq, col_dir = st.columns([1, 2])

    # =========================================================================
    # COLUNA ESQUERDA: MONTAR E TESTAR COMBO
    # =========================================================================
    with col_esq:
        st.subheader("🎯 Testar Combinação")

        todas_keys = list(ESTRATEGIAS_DISPONIVEIS.keys())
        dados_ok = st.session_state['sim_dados_concursos'] is not None

        if not dados_ok:
            st.warning("Clique em **Preparar concursos** na barra lateral primeiro.")

        # Tamanho da combinação
        tam_combo = st.slider("Tamanho (nº de estratégias)", 3, 15, 10, key="sim_tam")

        # Gerar combo aleatória do tamanho escolhido
        if st.button(f"🎲 Gerar aleatória ({tam_combo} est.)", use_container_width=True):
            import random as _rnd
            st.session_state['sim_selecao'] = sorted(
                _rnd.sample(todas_keys, tam_combo),
                key=lambda x: todas_keys.index(x)
            )
            st.rerun()

        # Seleção manual
        default_sel = st.session_state.get('sim_selecao', todas_keys[:tam_combo])
        default_sel = [e for e in default_sel if e in ESTRATEGIAS_DISPONIVEIS]

        selecionadas = st.multiselect(
            "Estratégias",
            options=todas_keys,
            format_func=lambda x: ESTRATEGIAS_DISPONIVEIS[x],
            default=default_sel,
            key="sim_combo_select"
        )

        if len(selecionadas) >= 3:
            st.caption(
                f"{len(selecionadas)} estratégias | "
                f"{n_concursos} conc × {n_jogos} cartões de 14 números = "
                f"{n_concursos * n_jogos:,} cartões"
            )

            # Verificar se já testou
            combo_tuple = tuple(sorted(selecionadas))
            ja_testou = any(
                tuple(sorted(r['combo'])) == combo_tuple
                for r in st.session_state['sim_ranking']
            )
            if ja_testou:
                st.info("Essa combinação já foi testada.")

            if st.button(
                "🚀 Testar esta combinação",
                type="primary",
                use_container_width=True,
                disabled=(not dados_ok or ja_testou)
            ):
                _executar_teste_combo(
                    selecionadas,
                    st.session_state['sim_dados_concursos'],
                    n_jogos, n_concursos
                )
        else:
            st.warning("Selecione pelo menos 3 estratégias.")

        # =================================================================
        # VARREDURA AUTOMÁTICA POR TAMANHO
        # =================================================================
        st.markdown("---")
        st.markdown("**🔄 Varredura automática**")
        st.caption("Testa várias combos aleatórias de cada tamanho")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tam_de = st.number_input("De (tam)", 3, 15, 7, key="varr_de")
        with col_t2:
            tam_ate = st.number_input("Até (tam)", 3, 15, 10, key="varr_ate")

        n_por_tam = st.number_input(
            "Combos por tamanho", 1, 50, 5, key="varr_n",
            help="Quantas combinações aleatórias testar por tamanho"
        )

        total_varr = n_por_tam * (int(tam_ate) - int(tam_de) + 1)
        st.caption(f"Total: {total_varr} combinações")

        if st.button(
            f"🔄 Varrer {tam_de} a {tam_ate} ({total_varr} combos)",
            use_container_width=True,
            disabled=not dados_ok
        ):
            _executar_varredura(
                todas_keys,
                int(tam_de), int(tam_ate), int(n_por_tam),
                st.session_state['sim_dados_concursos'],
                n_jogos, n_concursos
            )

    # =========================================================================
    # COLUNA DIREITA: RANKING ACUMULADO
    # =========================================================================
    with col_dir:
        _exibir_ranking(df, n_concursos)

    # =========================================================================
    # ABAIXO: DETALHES E GRÁFICOS
    # =========================================================================
    if st.session_state['sim_ranking']:
        st.markdown("---")
        _exibir_graficos_e_detalhes(df, n_concursos)


# =============================================================================
# EXECUÇÃO DE 1 COMBO COM PROGRESSO
# =============================================================================

def _executar_teste_combo(estrategias, dados_concursos, n_jogos, n_concursos):
    """Testa uma única combinação com progresso visual."""
    combo = list(estrategias)
    nomes = [ESTRATEGIAS_DISPONIVEIS.get(e, e) for e in combo]
    total_conc = len(dados_concursos)

    st.info(f"Testando: {', '.join(nomes)}")
    barra = st.progress(0, text="Iniciando teste...")

    acertos_total = []
    melhores = []
    dist = Counter()
    t_inicio = time.time()

    for idx_c, dc in enumerate(dados_concursos):
        melhor = 0
        random.seed(dc['concurso'])
        for _ in range(n_jogos):
            try:
                jogo14 = _gerar_ensemble_14(
                    combo,
                    dc['contagem_total'], dc['contagem_recente'],
                    dc['df_atrasos'], df=dc['df_treino']
                )
                ac = len(set(jogo14) & set(dc['resultado']))
                acertos_total.append(ac)
                dist[ac] += 1
                if ac > melhor:
                    melhor = ac
            except Exception:
                pass
        melhores.append(melhor)

        # Progresso
        pct = (idx_c + 1) / total_conc
        elapsed = time.time() - t_inicio
        rate = (idx_c + 1) / elapsed if elapsed > 0 else 0
        eta = (total_conc - idx_c - 1) / rate if rate > 0 else 0
        barra.progress(pct, text=f"Concurso {idx_c+1}/{total_conc} | {rate:.1f} conc/s | ETA: {int(eta)}s")

    barra.progress(1.0, text="Concluido!")
    dt = time.time() - t_inicio

    media = sum(acertos_total) / len(acertos_total) if acertos_total else 0
    maximo = max(melhores) if melhores else 0
    melhor_med = sum(melhores) / len(melhores) if melhores else 0
    senas = sum(v for k, v in dist.items() if k == 6)
    quinas = sum(v for k, v in dist.items() if k == 5)
    quadras = sum(v for k, v in dist.items() if k == 4)
    ternos = sum(v for k, v in dist.items() if k == 3)

    resultado = {
        'combo': combo,
        'media': media,
        'max': maximo,
        'melhor_med': melhor_med,
        'melhores': melhores,
        'dist': dict(dist),
        'total_jogos': len(acertos_total),
        'senas': senas,
        'quinas': quinas,
        'quadras': quadras,
        'ternos': ternos,
        'tempo': round(dt, 1),
        'n_concursos': n_concursos,
        'n_jogos': n_jogos,
    }

    # Adicionar ao ranking
    st.session_state['sim_ranking'].append(resultado)
    st.session_state['sim_ranking'].sort(
        key=lambda r: (r['media'], r['max'], r['melhor_med']), reverse=True
    )

    # Salvar no JSON
    _salvar_resultado_incremental(resultado)

    # Mostrar resultado desta combo
    pos = next(i for i, r in enumerate(st.session_state['sim_ranking'])
               if r['combo'] == combo) + 1
    st.success(
        f"Resultado (14 nums): Média **{media:.3f}** | MAX **{maximo}** | "
        f"🎯Senas: **{senas}** | ⭐Quinas: **{quinas}** | "
        f"🟢Quadras: **{quadras}** | "
        f"Posição: **#{pos}** de {len(st.session_state['sim_ranking'])} | "
        f"Tempo: {dt:.1f}s"
    )
    st.rerun()


# =============================================================================
# VARREDURA AUTOMÁTICA POR TAMANHO
# =============================================================================

def _executar_varredura(todas_keys, tam_de, tam_ate, n_por_tam, dados_concursos, n_jogos, n_concursos):
    """Varre automaticamente combos aleatórias de cada tamanho."""
    total_conc = len(dados_concursos)
    total_combos = n_por_tam * (tam_ate - tam_de + 1)
    combo_idx = 0
    t_inicio = time.time()

    # Coletar combos já testadas para evitar repetição
    ja_testadas = set(
        tuple(sorted(r['combo'])) for r in st.session_state['sim_ranking']
    )

    st.subheader(f"🔄 Varredura: tamanhos {tam_de} a {tam_ate}, {n_por_tam} combos cada")
    barra_global = st.progress(0, text="Iniciando varredura...")

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    m_testadas = col_s1.empty()
    m_vel = col_s2.empty()
    m_eta = col_s3.empty()
    m_melhor = col_s4.empty()

    tabela_live = st.empty()
    melhor_media = 0

    for tam in range(tam_de, tam_ate + 1):
        # Gerar N combos únicas deste tamanho
        combos_geradas = set()
        tentativas = 0
        while len(combos_geradas) < n_por_tam and tentativas < n_por_tam * 20:
            combo = tuple(sorted(random.sample(todas_keys, tam)))
            if combo not in ja_testadas and combo not in combos_geradas:
                combos_geradas.add(combo)
            tentativas += 1

        for combo in combos_geradas:
            combo_idx += 1
            nomes = [NOMES_CURTOS.get(e, e) for e in combo]
            barra_global.progress(
                combo_idx / total_combos,
                text=f"[{combo_idx}/{total_combos}] Tam {tam}: {' + '.join(nomes[:5])}..."
            )

            # Avaliar
            acertos_total = []
            melhores_conc = []
            dist = Counter()
            t_combo = time.time()

            for dc in dados_concursos:
                melhor = 0
                random.seed(dc['concurso'])
                for _ in range(n_jogos):
                    try:
                        jogo14 = _gerar_ensemble_14(
                            list(combo),
                            dc['contagem_total'], dc['contagem_recente'],
                            dc['df_atrasos'], df=dc['df_treino']
                        )
                        ac = len(set(jogo14) & set(dc['resultado']))
                        acertos_total.append(ac)
                        dist[ac] += 1
                        if ac > melhor:
                            melhor = ac
                    except Exception:
                        pass
                melhores_conc.append(melhor)

            dt_combo = time.time() - t_combo
            media = sum(acertos_total) / len(acertos_total) if acertos_total else 0
            maximo = max(melhores_conc) if melhores_conc else 0
            melhor_med = sum(melhores_conc) / len(melhores_conc) if melhores_conc else 0
            senas = sum(v for k, v in dist.items() if k == 6)
            quinas = sum(v for k, v in dist.items() if k == 5)
            quadras = sum(v for k, v in dist.items() if k == 4)
            ternos = sum(v for k, v in dist.items() if k == 3)

            resultado = {
                'combo': list(combo),
                'media': media,
                'max': maximo,
                'melhor_med': melhor_med,
                'melhores': melhores_conc,
                'dist': dict(dist),
                'total_jogos': len(acertos_total),
                'senas': senas,
                'quinas': quinas,
                'quadras': quadras,
                'ternos': ternos,
                'tempo': round(dt_combo, 1),
                'n_concursos': n_concursos,
                'n_jogos': n_jogos,
            }

            st.session_state['sim_ranking'].append(resultado)
            ja_testadas.add(tuple(sorted(combo)))
            _salvar_resultado_incremental(resultado)

            if media > melhor_media:
                melhor_media = media

            # Atualizar métricas
            elapsed = time.time() - t_inicio
            rate = combo_idx / elapsed if elapsed > 0 else 0
            restante = (total_combos - combo_idx) / rate if rate > 0 else 0

            m_testadas.metric("Testadas", f"{combo_idx}/{total_combos}")
            m_vel.metric("Velocidade", f"{rate:.2f}/s")
            min_r = int(restante // 60)
            sec_r = int(restante % 60)
            m_eta.metric("ETA", f"{min_r}m {sec_r}s" if min_r > 0 else f"{sec_r}s")
            m_melhor.metric("Melhor média", f"{melhor_media:.3f}")

            # Ranking ao vivo (top 10)
            ranking_temp = sorted(
                st.session_state['sim_ranking'],
                key=lambda r: (r['media'], r['max']), reverse=True
            )
            tabela_live.dataframe(
                _resultados_para_df(ranking_temp[:10]),
                use_container_width=True, hide_index=True
            )

    # Finalizar
    barra_global.progress(1.0, text="Varredura concluída!")
    st.session_state['sim_ranking'].sort(
        key=lambda r: (r['media'], r['max'], r['melhor_med']), reverse=True
    )

    elapsed_total = time.time() - t_inicio
    st.success(
        f"Varredura completa: {combo_idx} combos em "
        f"{int(elapsed_total//60)}m {int(elapsed_total%60)}s"
    )
    st.rerun()


# =============================================================================
# EXIBIR RANKING ACUMULADO
# =============================================================================

def _exibir_ranking(df, n_concursos):
    """Exibe ranking acumulado de todas as combos testadas."""
    ranking = st.session_state['sim_ranking']

    st.subheader(f"🏆 Ranking ({len(ranking)} combos)")

    if not ranking:
        st.info("Nenhuma combinação testada ainda. Monte uma combo e clique em Testar.")
        return

    # Tabela de ranking
    df_rank = _resultados_para_df(ranking)
    st.dataframe(df_rank, use_container_width=True, hide_index=True,
                 height=min(400, 40 + 35 * len(ranking)))

    # Pódio compacto (top 3)
    if len(ranking) >= 2:
        st.markdown("---")
        medalhas = ['🥇', '🥈', '🥉']
        n_podio = min(3, len(ranking))
        cols = st.columns(n_podio)
        for i in range(n_podio):
            r = ranking[i]
            with cols[i]:
                st.markdown(f"**{medalhas[i]}** ({len(r['combo'])} est.)")
                st.metric("Média", f"{r['media']:.3f}")
                st.metric("MAX", r['max'])
                nomes = [NOMES_CURTOS.get(e, e) for e in r['combo']]
                st.caption(' + '.join(nomes))


# =============================================================================
# GRÁFICOS E DETALHES (ABAIXO DO LAYOUT PRINCIPAL)
# =============================================================================

def _exibir_graficos_e_detalhes(df, n_concursos):
    """Exibe gráficos comparativos e detalhes expandíveis."""
    ranking = st.session_state['sim_ranking']

    tab_graf, tab_det, tab_freq = st.tabs([
        "📈 Gráficos",
        "🔍 Detalhes",
        "📊 Frequência"
    ])

    # --- GRÁFICOS ---
    with tab_graf:
        chart_data = []
        for r in ranking:
            chart_data.append({
                'Combinação': _combo_label(r['combo']),
                'Média': r['media'],
                'MAX': r['max'],
                'Quinas': r.get('quinas', 0),
                'Quadras': r.get('quadras', 0),
            })
        df_chart = pd.DataFrame(chart_data)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("**Média de acertos (14 números)**")
            st.bar_chart(df_chart.set_index('Combinação')['Média'], color='#4CAF50')
        with col_g2:
            st.markdown("**MAX acertos**")
            st.bar_chart(df_chart.set_index('Combinação')['MAX'], color='#FF5722')

        if any(r.get('quinas', 0) > 0 for r in ranking):
            st.markdown("**⭐ Quinas (5 acertos)**")
            st.bar_chart(df_chart.set_index('Combinação')['Quinas'], color='#FF9800')

        if any(r.get('quadras', 0) > 0 for r in ranking):
            st.markdown("**🟢 Quadras (4 acertos)**")
            st.bar_chart(df_chart.set_index('Combinação')['Quadras'], color='#2196F3')

    # --- DETALHES ---
    with tab_det:
        medalhas = ['🥇', '🥈', '🥉']
        for i, r in enumerate(ranking):
            nomes = [ESTRATEGIAS_DISPONIVEIS.get(e, e) for e in r['combo']]
            tag = medalhas[i] if i < 3 else f"{i+1}º"
            with st.expander(
                f"{tag} Média {r['media']:.3f} | MAX {r['max']} | "
                f"{len(r['combo'])} est. ({r.get('tempo', '?')}s)",
                expanded=(i == 0)
            ):
                st.markdown(f"**Estratégias:** {', '.join(nomes)}")

                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                col_d1.metric("Média", f"{r['media']:.3f}")
                col_d2.metric("🎯 Senas", r.get('senas', 0))
                col_d3.metric("⭐ Quinas", r.get('quinas', 0))
                col_d4.metric("🟢 Quadras", r.get('quadras', 0))

                # Distribuição
                dist = r['dist']
                if dist:
                    st.markdown("**Distribuição:**")
                    max_ac = max(dist.keys())
                    dcols = st.columns(min(7, max_ac + 1))
                    for ac in range(max_ac, -1, -1):
                        if ac in dist and (max_ac - ac) < len(dcols):
                            dcols[max_ac - ac].metric(f"{ac} ac", f"{dist[ac]}x")

                # Melhor por concurso (gráfico)
                if r['melhores']:
                    st.markdown("**Melhor por concurso:**")
                    ultimo = df['concurso'].max()
                    nc = r.get('n_concursos', n_concursos)
                    concs = list(range(ultimo - nc + 1, ultimo + 1))
                    conc_df = pd.DataFrame({
                        'Concurso': concs[:len(r['melhores'])],
                        'Melhor': r['melhores']
                    })
                    st.bar_chart(conc_df.set_index('Concurso')['Melhor'])

    # --- FREQUÊNCIA ---
    with tab_freq:
        st.subheader("Estratégias mais presentes no ranking")
        freq = Counter()
        for r in ranking:
            for e in r['combo']:
                freq[e] += 1

        if freq:
            freq_data = []
            for est, cnt in freq.most_common():
                freq_data.append({
                    'Estratégia': ESTRATEGIAS_DISPONIVEIS.get(est, est),
                    'Aparições': cnt
                })
            df_freq = pd.DataFrame(freq_data)
            st.bar_chart(df_freq.set_index('Estratégia')['Aparições'], color='#9C27B0')


# =============================================================================
# SALVAR INCREMENTAL
# =============================================================================

def _salvar_resultado_incremental(resultado):
    """Salva resultado de uma combo no histórico JSON."""
    entrada = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'combo': resultado['combo'],
        'nums_por_cartao': NUMS_POR_CARTAO,
        'config': {
            'n_concursos': resultado.get('n_concursos', 0),
            'n_jogos': resultado.get('n_jogos', 0),
        },
        'media': round(resultado['media'], 4),
        'max': resultado['max'],
        'melhor_med': round(resultado['melhor_med'], 2),
        'senas': resultado.get('senas', 0),
        'quinas': resultado.get('quinas', 0),
        'quadras': resultado.get('quadras', 0),
        'ternos': resultado.get('ternos', 0),
        'tempo': resultado.get('tempo', 0),
    }

    historico = []
    if os.path.exists(ARQUIVO_RESULTADO):
        try:
            with open(ARQUIVO_RESULTADO, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if isinstance(conteudo, list):
                    historico = conteudo
                else:
                    historico = [conteudo]
        except Exception:
            pass

    historico.append(entrada)
    historico = historico[-100:]  # manter últimos 100

    with open(ARQUIVO_RESULTADO, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
