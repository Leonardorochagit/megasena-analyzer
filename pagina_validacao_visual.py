"""
================================================================================
📊 PÁGINA: VISUALIZAÇÃO DE RESULTADOS DA VALIDAÇÃO WALK-FORWARD
================================================================================
Lê o arquivo data/backtesting_resultado.json (gerado pelo scripts/backtesting.py)
e exibe os resultados de forma clara: quantos ternos, quadras, quinas e senas
cada estratégia acertou.
================================================================================
"""

import json
import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ARQUIVO_RESULTADO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'backtesting_resultado.json'
)

NOMES_ESTRATEGIAS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Atrasados',
    'quentes': '🔥 Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Smart',
    'sequencias': '🧬 Sequências',
    'ensemble': '🧠 Ensemble',
    'candidatos_ouro': '🥇 Candidatos Ouro',
    'momentum': '🚀 Momentum',
    'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Freq. Desvio',
    'pares_frequentes': '👫 Pares Frequentes',
    'ciclos': '🔁 Ciclos',
    'ensemble_v2': '🧠✨ Ensemble V2',
}


def _carregar_resultado():
    """Carrega o JSON de backtesting salvo."""
    if not os.path.exists(ARQUIVO_RESULTADO):
        return None
    with open(ARQUIVO_RESULTADO, 'r', encoding='utf-8') as f:
        return json.load(f)


def pagina_validacao_visual(df=None):
    """Página de visualização dos resultados de validação walk-forward."""

    st.title("🏆 Resultados da Validação Walk-Forward")

    dados = _carregar_resultado()
    if dados is None:
        st.warning(
            "Nenhum resultado de validação encontrado. "
            "Execute primeiro: `python scripts/backtesting.py --concurso-inicial 2500 --cartoes 10 --numeros 14 --seed 42`"
        )
        return

    params = dados['parametros']
    benchmark = dados['benchmark_aleatorio']
    ranking = dados['ranking']

    # ── PARÂMETROS DA EXECUÇÃO ────────────────────────────────────────────────
    st.markdown(
        f"**Execução:** {dados['data_execucao']}  \n"
        f"**Concursos:** {params['concurso_inicial']} → {params['concurso_final']} "
        f"({params['concursos_validos']} válidos)  \n"
        f"**Cartões por estratégia:** {params['cartoes_por_estrategia']} "
        f"| **Números por cartão:** {params['qtd_numeros']} "
        f"| **Seed:** {params['seed']}  \n"
        f"**Total de jogos por estratégia:** {params['concursos_validos'] * params['cartoes_por_estrategia']:,}"
    )

    st.markdown("---")

    # ── TABELA PRINCIPAL: PREMIAÇÕES ABSOLUTAS ────────────────────────────────
    st.subheader("🎯 Premiações por Estratégia (números absolutos)")
    st.caption(
        f"Total de {params['concursos_validos'] * params['cartoes_por_estrategia']:,} jogos "
        f"por estratégia com {params['qtd_numeros']} números cada."
    )

    linhas = []
    for r in ranking:
        nome = NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia'])
        linhas.append({
            'Pos': 0,  # preenchido abaixo
            'Estratégia': nome,
            'Senas (6)': r['senas'],
            'Quinas (5)': r['quinas'],
            'Quadras (4)': r['quadras'],
            'Ternos (3)': r['ternos'],
            'Média Acertos': round(r['media_por_cartao'], 3),
            'Δ vs Aleatório': f"{r['delta_vs_aleatorio']:+.3f}",
        })

    df_tab = pd.DataFrame(linhas)
    # Ordenar por senas desc, depois quinas, depois quadras
    df_tab = df_tab.sort_values(
        ['Senas (6)', 'Quinas (5)', 'Quadras (4)', 'Ternos (3)'],
        ascending=False
    ).reset_index(drop=True)
    df_tab['Pos'] = range(1, len(df_tab) + 1)

    st.dataframe(
        df_tab,
        hide_index=True,
        use_container_width=True,
        column_config={
            'Pos': st.column_config.NumberColumn('🏅', width='small'),
            'Senas (6)': st.column_config.NumberColumn('🎉 Senas', help='6 acertos'),
            'Quinas (5)': st.column_config.NumberColumn('⭐ Quinas', help='5 acertos'),
            'Quadras (4)': st.column_config.NumberColumn('🟢 Quadras', help='4 acertos'),
            'Ternos (3)': st.column_config.NumberColumn('🔵 Ternos', help='3 acertos'),
        }
    )

    # ── MÉTRICAS DE DESTAQUE ──────────────────────────────────────────────────
    total_quinas = sum(r['quinas'] for r in ranking)
    total_senas = sum(r['senas'] for r in ranking)
    total_quadras = sum(r['quadras'] for r in ranking)
    melhor_quina = max(ranking, key=lambda r: r['quinas'])
    melhor_sena = max(ranking, key=lambda r: r['senas'])

    st.markdown("---")
    st.subheader("📊 Destaques")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎉 Total Senas", total_senas)
    c2.metric("⭐ Total Quinas", total_quinas)
    c3.metric("🟢 Total Quadras", total_quadras)
    c4.metric(
        "📈 Benchmark Aleatório",
        f"{benchmark['media_esperada']:.3f}",
        help="Média esperada de acertos por jogo aleatório com mesmos parâmetros"
    )

    c5, c6 = st.columns(2)
    c5.metric(
        "🏆 Mais Quinas",
        f"{NOMES_ESTRATEGIAS.get(melhor_quina['estrategia'], melhor_quina['estrategia'])}",
        f"{melhor_quina['quinas']} quinas"
    )
    c6.metric(
        "🏆 Mais Senas",
        f"{NOMES_ESTRATEGIAS.get(melhor_sena['estrategia'], melhor_sena['estrategia'])}",
        f"{melhor_sena['senas']} senas"
    )

    # ── GRÁFICO DE BARRAS: QUINAS E QUADRAS ──────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Quinas e Quadras por Estratégia")

    nomes = [NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia']) for r in ranking]
    quinas = [r['quinas'] for r in ranking]
    quadras = [r['quadras'] for r in ranking]
    senas = [r['senas'] for r in ranking]

    # Ordenar por quinas desc
    ordem = np.argsort(quinas)[::-1]
    nomes_ord = [nomes[i] for i in ordem]
    quinas_ord = [quinas[i] for i in ordem]
    quadras_ord = [quadras[i] for i in ordem]
    senas_ord = [senas[i] for i in ordem]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(nomes_ord))
    w = 0.3

    bars_q = ax.bar(x - w, quadras_ord, w, label='Quadras (4)', color='#2196F3', edgecolor='white')
    bars_5 = ax.bar(x, quinas_ord, w, label='Quinas (5)', color='#FF9800', edgecolor='white')
    bars_6 = ax.bar(x + w, senas_ord, w, label='Senas (6)', color='#4CAF50', edgecolor='white')

    # Rótulos nas barras de quinas
    for bar, val in zip(bars_5, quinas_ord):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    str(val), ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Rótulos nas barras de senas
    for bar, val in zip(bars_6, senas_ord):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    str(val), ha='center', va='bottom', fontsize=9, fontweight='bold',
                    color='#2E7D32')

    ax.set_xticks(x)
    ax.set_xticklabels(nomes_ord, rotation=35, ha='right', fontsize=8)
    ax.set_ylabel('Quantidade')
    ax.set_title(
        f'Premiações — {params["concursos_validos"]} concursos × '
        f'{params["cartoes_por_estrategia"]} cartões × {params["qtd_numeros"]} números',
        fontsize=11
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # ── GRÁFICO HORIZONTAL: MÉDIA DE ACERTOS + IC 95% ────────────────────────
    st.markdown("---")
    st.subheader("📈 Média de Acertos por Jogo (IC 95%)")

    medias = [r['media_por_cartao'] for r in ranking]
    ic_inf = [r['ic95_inf'] for r in ranking]
    ic_sup = [r['ic95_sup'] for r in ranking]

    ordem_media = np.argsort(medias)[::-1]
    nomes_m = [nomes[i] for i in ordem_media]
    medias_m = [medias[i] for i in ordem_media]
    err_lo = [medias[i] - ic_inf[i] for i in ordem_media]
    err_hi = [ic_sup[i] - medias[i] for i in ordem_media]

    fig2, ax2 = plt.subplots(figsize=(10, max(5, len(nomes_m) * 0.45)))
    y_pos = range(len(nomes_m))

    colors = ['#4CAF50' if m > benchmark['media_esperada'] else '#F44336' for m in medias_m]

    ax2.barh(y_pos, medias_m, xerr=[err_lo, err_hi],
             align='center', color=colors, ecolor='#555',
             capsize=4, alpha=0.85, height=0.7)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(nomes_m, fontsize=9)
    ax2.axvline(x=benchmark['media_esperada'], color='red', linestyle='--',
                alpha=0.7, label=f'Aleatório ({benchmark["media_esperada"]:.3f})')
    ax2.set_xlabel('Média de acertos por jogo')
    ax2.set_title('Média de acertos — Verde = acima do aleatório, Vermelho = abaixo')
    ax2.legend(fontsize=8)
    ax2.invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

    # ── TABELA DETALHADA COM TAXAS ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Tabela Detalhada")

    det = []
    for r in ranking:
        nome = NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia'])
        jogos = r['jogos']
        det.append({
            'Estratégia': nome,
            'Jogos': jogos,
            'Ternos': r['ternos'],
            'Quadras': r['quadras'],
            'Quinas': r['quinas'],
            'Senas': r['senas'],
            '% Quadra+': f"{r['taxa_jogo_quadra_ou_mais']*100:.2f}%",
            '% Quina+': f"{r['taxa_jogo_quina_ou_mais']*100:.2f}%",
            'Média': round(r['media_por_cartao'], 3),
            'p-value': f"{r['p_media_vs_aleatorio']:.4f}" if r['p_media_vs_aleatorio'] > 0.0001 else f"{r['p_media_vs_aleatorio']:.2e}",
        })

    df_det = pd.DataFrame(det)
    st.dataframe(df_det, hide_index=True, use_container_width=True)

    # ── CONCLUSÃO ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 Interpretação Rápida")

    # Top 3 por quinas
    top3_quina = sorted(ranking, key=lambda r: r['quinas'], reverse=True)[:3]
    # Top 3 por quadras
    top3_quadra = sorted(ranking, key=lambda r: r['quadras'], reverse=True)[:3]
    # Significativamente piores (p < 0.05 e delta negativo)
    piores = [r for r in ranking if r['p_media_vs_aleatorio'] < 0.05 and r['delta_vs_aleatorio'] < 0]

    st.markdown("**🏅 Top 3 em Quinas:**")
    for i, r in enumerate(top3_quina):
        nome = NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia'])
        st.markdown(f"  {i+1}. {nome} — **{r['quinas']} quinas** em {r['jogos']} jogos")

    st.markdown("**🏅 Top 3 em Quadras:**")
    for i, r in enumerate(top3_quadra):
        nome = NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia'])
        st.markdown(f"  {i+1}. {nome} — **{r['quadras']} quadras** em {r['jogos']} jogos")

    if piores:
        st.markdown("**⚠️ Estratégias significativamente piores que aleatório (p < 0.05):**")
        for r in piores:
            nome = NOMES_ESTRATEGIAS.get(r['estrategia'], r['estrategia'])
            st.markdown(f"  - {nome} (Δ = {r['delta_vs_aleatorio']:+.3f}, p = {r['p_media_vs_aleatorio']:.4f})")

    total_senas_txt = f"**{total_senas} sena(s)** no total" if total_senas > 0 else "**Nenhuma sena** no total"
    st.info(
        f"Em {params['concursos_validos']} concursos com {params['cartoes_por_estrategia']} "
        f"cartões de {params['qtd_numeros']} números por estratégia: "
        f"{total_senas_txt}, **{total_quinas} quinas** e **{total_quadras} quadras** somando todas as estratégias."
    )
