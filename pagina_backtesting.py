"""
================================================================================
📊 PÁGINA: BACKTESTING ESTATÍSTICO DE ESTRATÉGIAS
================================================================================
Roda cada estratégia nos últimos N concursos históricos e compara a distribuição
de acertos com intervalo de confiança de 95%.

Se duas estratégias tiverem distribuições sobrepostas → estatisticamente iguais
→ a estratégia não tem edge sobre a outra.
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import random
import warnings
from collections import defaultdict
from scipy import stats as scipy_stats
from modules import data_manager as dm
from modules import statistics as stats_mod
from modules import game_generator as gen

warnings.filterwarnings("ignore")


NOMES_ESTRATEGIAS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Números Atrasados',
    'quentes': '🔥 Números Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Inteligente (baseline)',
    'sequencias': '🧬 Sequências (Clusters)',
    'ensemble': '🧠 Ensemble',
    'wheel': '🎯 Wheel',
    'candidatos_ouro': '🥇 Candidatos Ouro',
    'momentum': '🚀 Momentum',
    'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Frequência Desvio',
    'pares_frequentes': '👫 Pares Frequentes',
    'ciclos': '🔁 Ciclos',
}


def _rodar_backtesting(df: pd.DataFrame, estrategias: list, n_concursos: int,
                        cartoes_por_sorteio: int, progress_cb=None) -> dict:
    """
    Para cada concurso nos últimos n_concursos, gera cartoes_por_sorteio jogos
    de 6 números com cada estratégia usando os dados ANTERIORES ao sorteio
    (sem data leakage), e conta acertos.

    Retorna dict: estrategia -> lista de acertos por cartão (todos os concursos)
    """
    df = df.sort_values('concurso').reset_index(drop=True)
    total = len(df)

    if n_concursos >= total - 50:
        n_concursos = total - 50

    resultados = defaultdict(list)

    for idx in range(total - n_concursos, total):
        if progress_cb:
            progress_cb(idx - (total - n_concursos), n_concursos)

        df_hist = df.iloc[:idx]
        sorteio_real = set(int(df.iloc[idx][f'dez{i}']) for i in range(1, 7))

        if len(df_hist) < 30:
            continue

        contagem_total, contagem_recente, df_atrasos = stats_mod.calcular_estatisticas(df_hist)

        for est in estrategias:
            for _ in range(cartoes_por_sorteio):
                try:
                    jogo = gen.gerar_jogo(
                        est, contagem_total, contagem_recente, df_atrasos, df=df_hist
                    )
                    acertos = len(set(jogo) & sorteio_real)
                    resultados[est].append(acertos)
                except Exception:
                    resultados[est].append(0)

    return dict(resultados)


def _calcular_stats(acertos: list) -> dict:
    """Calcula media, IC95% e distribuicao de acertos para uma lista."""
    arr = np.array(acertos, dtype=float)
    n = len(arr)
    if n == 0:
        return {}

    media = arr.mean()
    std = arr.std(ddof=1) if n > 1 else 0.0
    margem = 1.96 * std / np.sqrt(n) if n > 1 else 0.0

    dist = {}
    for k in range(7):
        dist[k] = int((arr == k).sum())

    return {
        'media': round(media, 4),
        'std': round(std, 4),
        'ic_inf': round(media - margem, 4),
        'ic_sup': round(media + margem, 4),
        'n': n,
        'dist': dist,
        'quadras_pct': round((arr >= 4).mean() * 100, 2),
        'quinas_pct': round((arr >= 5).mean() * 100, 2),
        'senas_pct': round((arr == 6).mean() * 100, 4),
    }


def _teste_mann_whitney(acertos_a: list, acertos_b: list):
    """Teste de Mann-Whitney U para comparar duas distribuicoes."""
    if len(acertos_a) < 2 or len(acertos_b) < 2:
        return 1.0
    _, p = scipy_stats.mannwhitneyu(acertos_a, acertos_b, alternative='two-sided')
    return float(p)


def pagina_backtesting(df: pd.DataFrame):
    """Página de Backtesting Estatístico de Estratégias."""

    st.title("📊 Backtesting Estatístico de Estratégias")
    st.markdown(
        "Roda cada estratégia nos últimos **N concursos históricos** usando apenas "
        "dados anteriores a cada sorteio (**sem data leakage**). "
        "Compara a distribuição de acertos com **intervalo de confiança de 95%** e "
        "teste estatístico de Mann-Whitney."
    )

    if df is None or df.empty:
        st.warning("Nenhum dado disponível.")
        return

    df = df.sort_values('concurso').reset_index(drop=True)
    total_concursos = len(df)

    st.markdown("---")

    # ── CONFIGURAÇÃO ─────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        n_concursos = st.slider(
            "📅 Concursos para testar",
            min_value=50, max_value=min(500, total_concursos - 50),
            value=min(200, total_concursos - 50), step=25,
            help="Quantos sorteios recentes usar como janela de teste"
        )

    with col2:
        cartoes_por_sorteio = st.slider(
            "🎲 Cartões por sorteio",
            min_value=1, max_value=10, value=3,
            help="Quantos cartões gerar por estratégia em cada sorteio"
        )

    with col3:
        estrategias_sel = st.multiselect(
            "📊 Estratégias",
            options=list(NOMES_ESTRATEGIAS.keys()),
            default=['escada', 'atrasados', 'quentes', 'aleatorio_smart', 'misto', 'ensemble'],
            format_func=lambda k: NOMES_ESTRATEGIAS.get(k, k)
        )

    total_jogos = n_concursos * cartoes_por_sorteio * len(estrategias_sel)
    st.info(
        f"**{n_concursos}** concursos × **{cartoes_por_sorteio}** cartões × "
        f"**{len(estrategias_sel)}** estratégias = **{total_jogos:,}** jogos simulados. "
        f"Tempo estimado: ~{total_jogos // 500 + 1} segundos."
    )

    if not estrategias_sel:
        st.warning("Selecione pelo menos uma estratégia.")
        return

    st.markdown("---")

    if st.button("🚀 Executar Backtesting", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status = st.empty()

        def progress_cb(atual, total):
            pct = atual / total if total > 0 else 0
            progress_bar.progress(min(pct, 1.0))
            status.text(f"Processando concurso {atual}/{total}…")

        with st.spinner("Rodando backtesting…"):
            resultados_raw = _rodar_backtesting(
                df, estrategias_sel, n_concursos, cartoes_por_sorteio, progress_cb
            )

        progress_bar.empty()
        status.empty()

        st.session_state['bt_resultados'] = resultados_raw
        st.session_state['bt_n_concursos'] = n_concursos
        st.session_state['bt_cartoes'] = cartoes_por_sorteio
        st.success(f"✅ Backtesting concluído — {total_jogos:,} jogos simulados!")

    if 'bt_resultados' not in st.session_state:
        return

    resultados_raw = st.session_state['bt_resultados']
    n_concursos_usado = st.session_state['bt_n_concursos']

    # ── CALCULAR ESTATÍSTICAS ─────────────────────────────────────────────────
    stats_resultados = {}
    for est, acertos in resultados_raw.items():
        stats_resultados[est] = _calcular_stats(acertos)

    # ── TABELA RESUMO ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Resumo Comparativo")

    linhas = []
    for est, s in stats_resultados.items():
        if not s:
            continue
        linhas.append({
            'Estratégia': NOMES_ESTRATEGIAS.get(est, est),
            'Média Acertos': s['media'],
            'IC 95% Inf': s['ic_inf'],
            'IC 95% Sup': s['ic_sup'],
            '% Quadras (4+)': s['quadras_pct'],
            '% Quinas (5+)': s['quinas_pct'],
            'N Jogos': s['n'],
        })

    df_resumo = pd.DataFrame(linhas).sort_values('Média Acertos', ascending=False).reset_index(drop=True)
    st.dataframe(df_resumo, hide_index=True, use_container_width=True)

    # ── GRÁFICO DE IC ─────────────────────────────────────────────────────────
    st.subheader("📈 Intervalo de Confiança 95% — Média de Acertos")
    st.caption(
        "Se os intervalos de duas estratégias se sobrepõem, elas são **estatisticamente equivalentes** "
        "nessa janela de teste."
    )

    nomes = [NOMES_ESTRATEGIAS.get(e, e) for e in stats_resultados]
    medias = [s['media'] for s in stats_resultados.values()]
    ic_inf = [s['ic_inf'] for s in stats_resultados.values()]
    ic_sup = [s['ic_sup'] for s in stats_resultados.values()]
    erros_inf = [m - i for m, i in zip(medias, ic_inf)]
    erros_sup = [s - m for m, s in zip(medias, ic_sup)]

    ordem = np.argsort(medias)[::-1]
    nomes_ord = [nomes[i] for i in ordem]
    medias_ord = [medias[i] for i in ordem]
    err_inf_ord = [erros_inf[i] for i in ordem]
    err_sup_ord = [erros_sup[i] for i in ordem]

    fig, ax = plt.subplots(figsize=(10, max(4, len(nomes_ord) * 0.6)))
    y_pos = range(len(nomes_ord))
    ax.barh(y_pos, medias_ord, xerr=[err_inf_ord, err_sup_ord],
            align='center', color='steelblue', ecolor='black',
            capsize=5, alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nomes_ord, fontsize=9)
    ax.set_xlabel("Média de acertos por jogo de 6")
    ax.set_title(f"Backtesting: {n_concursos_usado} concursos — IC 95%")
    ax.axvline(x=6 * 6 / 60, color='red', linestyle='--', alpha=0.6,
               label='Esperado aleatório (0.6)')
    ax.legend(fontsize=8)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # ── DISTRIBUIÇÃO DE ACERTOS ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Distribuição de Acertos por Estratégia")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        est_ref = st.selectbox(
            "Estratégia de referência",
            options=list(stats_resultados.keys()),
            format_func=lambda k: NOMES_ESTRATEGIAS.get(k, k),
            index=0
        )
    with col_sel2:
        est_comp = st.selectbox(
            "Comparar com",
            options=[e for e in stats_resultados if e != est_ref],
            format_func=lambda k: NOMES_ESTRATEGIAS.get(k, k),
            index=0
        )

    s_ref = stats_resultados[est_ref]
    s_comp = stats_resultados[est_comp]

    p_mw = _teste_mann_whitney(
        resultados_raw.get(est_ref, []),
        resultados_raw.get(est_comp, [])
    )

    if p_mw < 0.05:
        st.error(
            f"**Diferença estatisticamente significativa** entre "
            f"*{NOMES_ESTRATEGIAS.get(est_ref, est_ref)}* e "
            f"*{NOMES_ESTRATEGIAS.get(est_comp, est_comp)}* "
            f"(Mann-Whitney p = {p_mw:.4f}). Uma estratégia tem edge real sobre a outra."
        )
    else:
        st.success(
            f"**Sem diferença significativa** entre "
            f"*{NOMES_ESTRATEGIAS.get(est_ref, est_ref)}* e "
            f"*{NOMES_ESTRATEGIAS.get(est_comp, est_comp)}* "
            f"(Mann-Whitney p = {p_mw:.4f}). As distribuições são estatisticamente equivalentes."
        )

    fig2, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=False)
    for ax_i, (est_k, s_k) in enumerate([(est_ref, s_ref), (est_comp, s_comp)]):
        dist = s_k['dist']
        ks = sorted(dist.keys())
        vs = [dist[k] for k in ks]
        axes[ax_i].bar(ks, vs, color='steelblue', edgecolor='white')
        axes[ax_i].set_title(
            f"{NOMES_ESTRATEGIAS.get(est_k, est_k)}\n"
            f"Média: {s_k['media']:.3f} | IC95%: [{s_k['ic_inf']:.3f}, {s_k['ic_sup']:.3f}]",
            fontsize=9
        )
        axes[ax_i].set_xlabel("Acertos")
        axes[ax_i].set_ylabel("Frequência")
        axes[ax_i].set_xticks(ks)

    plt.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

    # ── QUADRAS E QUINAS ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Taxa de Quadras e Quinas por Estratégia")

    df_premia = pd.DataFrame([
        {
            'Estratégia': NOMES_ESTRATEGIAS.get(e, e),
            '% Quadras (4+ acertos)': s['quadras_pct'],
            '% Quinas (5+ acertos)': s['quinas_pct'],
            '% Senas (6 acertos)': s['senas_pct'],
        }
        for e, s in stats_resultados.items() if s
    ]).sort_values('% Quadras (4+ acertos)', ascending=False).reset_index(drop=True)

    st.dataframe(df_premia, hide_index=True, use_container_width=True)

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    x = np.arange(len(df_premia))
    w = 0.35
    ax3.bar(x - w/2, df_premia['% Quadras (4+ acertos)'], w, label='Quadras (4+)', color='steelblue')
    ax3.bar(x + w/2, df_premia['% Quinas (5+ acertos)'], w, label='Quinas (5+)', color='coral')
    ax3.set_xticks(x)
    ax3.set_xticklabels(df_premia['Estratégia'], rotation=30, ha='right', fontsize=8)
    ax3.set_ylabel('%')
    ax3.set_title('Taxa de premiação por estratégia (backtesting)')
    ax3.legend()
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close(fig3)

    # ── DOWNLOAD ──────────────────────────────────────────────────────────────
    st.markdown("---")
    dados_export = []
    for est, acertos in resultados_raw.items():
        s = stats_resultados.get(est, {})
        if s:
            for ac in acertos:
                dados_export.append({'estrategia': est, 'acertos': ac})

    df_export = pd.DataFrame(dados_export)
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Baixar dados brutos do backtesting (CSV)",
        data=csv,
        file_name=f"backtesting_{n_concursos_usado}_concursos.csv",
        mime="text/csv"
    )
