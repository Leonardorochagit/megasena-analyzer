"""
Página: Validação do Ensemble Novo — Backtest em Tempo Real
Roda o ensemble (10 estratégias × 14 via expandir_jogo → votação → top 14)
contra todos os concursos disponíveis, com pause/continue e métricas ao vivo.
"""

import random
import time
from collections import Counter

import pandas as pd
import streamlit as st

from modules import statistics as stats
from modules import game_generator as gen


ENSEMBLE_TOP10 = [
    'atrasados', 'candidatos_ouro', 'ciclos', 'consenso', 'equilibrado',
    'escada', 'frequencia_desvio', 'momentum', 'pares_frequentes', 'sequencias'
]

NUMS_POR_CARTAO = 14
LOTE = 10
MIN_TREINO = 100


def _gerar_cartao(ct, cr, da, df_treino):
    votos = Counter()
    for est in ENSEMBLE_TOP10:
        try:
            base = gen.gerar_jogo(est, ct, cr, da, df=df_treino)
            exp = gen.expandir_jogo(base, NUMS_POR_CARTAO, est, ct, cr, da, df=df_treino)
            for n in exp:
                votos[int(n)] += 1
        except Exception:
            pass
    if not votos:
        return sorted(random.sample(range(1, 61), NUMS_POR_CARTAO))
    ordenados = sorted(
        votos.keys(),
        key=lambda n: (votos[n], cr.get(n, 0)),
        reverse=True
    )
    if len(ordenados) < NUMS_POR_CARTAO:
        extras = [n for n in range(1, 61) if n not in ordenados]
        random.shuffle(extras)
        ordenados.extend(extras[:NUMS_POR_CARTAO - len(ordenados)])
    return sorted(ordenados[:NUMS_POR_CARTAO])


def _processar_lote(df, concursos, idx, n_cartoes, resultados):
    fim = min(idx + LOTE, len(concursos))
    detalhes = resultados.get('detalhes', [])

    for i in range(idx, fim):
        conc = concursos[i]
        mask = df['concurso'] == conc
        if not mask.any():
            continue
        row = df[mask].iloc[0]
        real = sorted([int(row[f'dez{j}']) for j in range(1, 7)])

        df_treino = df[df['concurso'] < conc].reset_index(drop=True)
        if len(df_treino) < MIN_TREINO:
            continue

        ct, cr, da = stats.calcular_estatisticas(df_treino)

        melhor = 0
        for c in range(n_cartoes):
            random.seed(conc * 1000 + c)
            cartao = _gerar_cartao(ct, cr, da, df_treino)
            ac = len(set(cartao) & set(real))
            resultados['acertos'].append(ac)
            resultados['dist'][ac] = resultados['dist'].get(ac, 0) + 1
            if ac > melhor:
                melhor = ac

        resultados['melhor_por_conc'].append(melhor)
        detalhes.append({'concurso': int(conc), 'melhor': melhor, 'resultado': real})

    resultados['detalhes'] = detalhes
    return fim, resultados


def _init_resultados():
    return {
        'acertos': [],
        'dist': {},
        'melhor_por_conc': [],
        'detalhes': [],
    }


def pagina_validacao_ensemble(df):
    st.header("Validacao Ensemble — Backtest Tempo Real")

    ultimo = int(df['concurso'].max())
    primeiro_valido = int(df['concurso'].min()) + MIN_TREINO
    max_conc = ultimo - primeiro_valido + 1

    st.caption(
        f"Ensemble: {len(ENSEMBLE_TOP10)} estrategias x {NUMS_POR_CARTAO} numeros | "
        f"Concursos disponiveis: {primeiro_valido} a {ultimo} ({max_conc})"
    )

    # --- Config ---
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        n_cartoes = st.number_input("Cartoes por concurso", 1, 20, 5, key="ve_cfg_cartoes")
    with col_cfg2:
        n_concursos = st.number_input("Concursos a testar", 100, max_conc, min(max_conc, 2895), key="ve_cfg_conc")

    # --- Controles ---
    col1, col2, col3 = st.columns(3)

    with col1:
        btn_iniciar = st.button(
            "Continuar" if st.session_state.get('ve_pausado') else "Iniciar",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get('ve_rodando', False) and not st.session_state.get('ve_pausado', False),
        )
    with col2:
        btn_pausar = st.button(
            "Pausar",
            use_container_width=True,
            disabled=not st.session_state.get('ve_rodando', False) or st.session_state.get('ve_pausado', False),
        )
    with col3:
        btn_reset = st.button("Reset", use_container_width=True)

    # --- Handlers ---
    if btn_reset:
        for k in list(st.session_state.keys()):
            if k.startswith('ve_') and k not in ('ve_cfg_cartoes', 've_cfg_conc'):
                del st.session_state[k]
        st.rerun()

    if btn_pausar:
        st.session_state['ve_pausado'] = True
        st.session_state['ve_tempo_total'] = st.session_state.get('ve_tempo_total', 0) + (
            time.time() - st.session_state.get('ve_tempo_lote', time.time())
        )
        st.rerun()

    if btn_iniciar:
        if not st.session_state.get('ve_rodando'):
            concursos = list(range(ultimo - n_concursos + 1, ultimo + 1))
            st.session_state['ve_rodando'] = True
            st.session_state['ve_pausado'] = False
            st.session_state['ve_idx'] = 0
            st.session_state['ve_resultados'] = _init_resultados()
            st.session_state['ve_concursos'] = concursos
            st.session_state['ve_n_cartoes'] = n_cartoes
            st.session_state['ve_tempo_total'] = 0
            st.session_state['ve_tempo_lote'] = time.time()
        else:
            st.session_state['ve_pausado'] = False
            st.session_state['ve_tempo_lote'] = time.time()
        st.rerun()

    # --- Estado atual ---
    rodando = st.session_state.get('ve_rodando', False)
    pausado = st.session_state.get('ve_pausado', False)
    idx = st.session_state.get('ve_idx', 0)
    resultados = st.session_state.get('ve_resultados', _init_resultados())
    concursos = st.session_state.get('ve_concursos', [])
    total = len(concursos)

    # --- Barra de progresso ---
    if total > 0:
        pct = idx / total
        tempo_total = st.session_state.get('ve_tempo_total', 0)
        if rodando and not pausado:
            tempo_total += time.time() - st.session_state.get('ve_tempo_lote', time.time())

        if idx > 0 and tempo_total > 0:
            vel = idx / tempo_total
            eta = (total - idx) / vel
            eta_str = f"{int(eta // 60)}m{int(eta % 60):02d}s"
        else:
            eta_str = "--"

        status_label = "PAUSADO" if pausado else ("RODANDO" if rodando else ("CONCLUIDO" if idx >= total else "PRONTO"))
        st.progress(pct, text=f"{status_label} | {idx}/{total} ({pct*100:.1f}%) | Tempo: {tempo_total:.0f}s | ETA: {eta_str}")

    # --- Metricas ---
    if resultados['acertos']:
        media = sum(resultados['acertos']) / len(resultados['acertos'])
        melhor_med = sum(resultados['melhor_por_conc']) / len(resultados['melhor_por_conc']) if resultados['melhor_por_conc'] else 0
        maximo = max(resultados['melhor_por_conc']) if resultados['melhor_por_conc'] else 0
        dist = resultados['dist']
        t3 = sum(v for k, v in dist.items() if k >= 3)
        t4 = sum(v for k, v in dist.items() if k >= 4)
        t5 = sum(v for k, v in dist.items() if k >= 5)
        t6 = dist.get(6, 0)

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Media", f"{media:.3f}")
        c2.metric("Melhor/conc", f"{melhor_med:.2f}")
        c3.metric("MAX", f"{maximo}")
        c4.metric("Ternos 3+", f"{t3}")
        c5.metric("Quadras 4+", f"{t4}")
        c6.metric("Quinas 5+", f"{t5}")
        c7.metric("Senas 6", f"{t6}")

        # Distribuicao
        st.markdown("**Distribuicao de acertos:**")
        dist_cols = st.columns(max(len(dist), 1))
        for i, k in enumerate(sorted(dist.keys())):
            label = f"{k} ac" if k < 6 else "SENA"
            dist_cols[i % len(dist_cols)].metric(label, dist[k])

        # Grafico: media movel do melhor por concurso
        if len(resultados['melhor_por_conc']) > 20:
            janela = 50
            melhor_list = resultados['melhor_por_conc']
            media_movel = []
            for i in range(len(melhor_list)):
                inicio = max(0, i - janela + 1)
                media_movel.append(sum(melhor_list[inicio:i+1]) / (i - inicio + 1))
            chart_df = pd.DataFrame({
                'Melhor acerto (media movel 50)': media_movel,
            })
            st.line_chart(chart_df, height=250)

        # Ultimos concursos
        if resultados.get('detalhes'):
            ultimos = resultados['detalhes'][-20:][::-1]
            with st.expander(f"Ultimos {len(ultimos)} concursos processados", expanded=False):
                for d in ultimos:
                    emoji = {0: '', 1: '', 2: '', 3: '🔔', 4: '🟢', 5: '⭐', 6: '🎯'}.get(d['melhor'], '')
                    st.text(f"Conc {d['concurso']}: melhor={d['melhor']} ac {emoji}  resultado={d['resultado']}")

    elif rodando:
        st.info("Iniciando processamento...")

    # --- Motor: processar proximo lote ---
    if rodando and not pausado and idx < total:
        st.session_state['ve_tempo_lote'] = st.session_state.get('ve_tempo_lote', time.time())

        novo_idx, novos_resultados = _processar_lote(
            df, concursos, idx,
            st.session_state.get('ve_n_cartoes', 5),
            resultados,
        )

        st.session_state['ve_idx'] = novo_idx
        st.session_state['ve_resultados'] = novos_resultados

        if novo_idx >= total:
            st.session_state['ve_rodando'] = False
            st.session_state['ve_pausado'] = False
            st.session_state['ve_tempo_total'] = st.session_state.get('ve_tempo_total', 0) + (
                time.time() - st.session_state.get('ve_tempo_lote', time.time())
            )
            st.balloons()
            st.rerun()
        else:
            st.session_state['ve_tempo_total'] = st.session_state.get('ve_tempo_total', 0) + (
                time.time() - st.session_state.get('ve_tempo_lote', time.time())
            )
            st.session_state['ve_tempo_lote'] = time.time()
            st.rerun()
