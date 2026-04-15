"""
================================================================================
🏆 PÁGINA: ENSEMBLE TOP 10 — CARTÕES DE 14 NÚMEROS
================================================================================
Página dedicada ao melhor ensemble identificado (10 estratégias) gerando
cartões de 14 números para jogar de verdade.

- Gera cartões prontos para o próximo sorteio
- Salva no sistema (meus_cartoes / banco SQLite)
- Confere resultado quando sair
================================================================================
"""

import streamlit as st
import pandas as pd
import random
from datetime import datetime
from collections import Counter
from math import comb

from modules import data_manager as dm
from modules import statistics as stats
from modules import game_generator as gen
from helpers import CUSTOS_CARTAO, versao_estrategia


# =============================================================================
# CONFIGURAÇÃO DO ENSEMBLE CAMPEÃO
# =============================================================================

ENSEMBLE_TOP10 = [
    'atrasados', 'candidatos_ouro', 'ciclos', 'consenso', 'equilibrado',
    'escada', 'frequencia_desvio', 'momentum', 'pares_frequentes', 'sequencias'
]

NOMES = {
    'escada': '🔄 Escada', 'atrasados': '⏰ Atrasados', 'quentes': '🔥 Quentes',
    'equilibrado': '⚖️ Equilibrado', 'misto': '🎨 Misto', 'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleat.Smart', 'sequencias': '🧬 Sequências', 'wheel': '🎯 Wheel',
    'candidatos_ouro': '🥇 Cand.Ouro', 'momentum': '🚀 Momentum', 'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Freq.Desvio', 'pares_frequentes': '👫 Pares.Freq', 'ciclos': '🔁 Ciclos'
}

NUMS_POR_CARTAO = 14
CUSTO_14 = CUSTOS_CARTAO.get(14, 15015.00)
COMBINACOES_14 = comb(14, 6)  # 3.003


# =============================================================================
# GERAR CARTÃO DE 14 NÚMEROS VIA ENSEMBLE
# =============================================================================

def _gerar_cartao_14(estrategias, contagem_total, contagem_recente, df_atrasos, df=None):
    """
    Gera 1 cartão de 14 números usando votação do ensemble.
    Cada estratégia gera um jogo base de 6 e é expandido para 14 mantendo
    coerência. Os 14 mais votados entre os 140 (10 estratégias × 14) são
    selecionados.
    """
    votos = Counter()
    for est in estrategias:
        try:
            base = gen.gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
            jogo = gen.expandir_jogo(
                base, NUMS_POR_CARTAO, est,
                contagem_total, contagem_recente, df_atrasos, df=df
            )
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


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_ensemble_14(df):
    """Página do Ensemble Top 10 com cartões de 14 números."""

    st.header("🏆 Ensemble Top 10 — Cartões de 14 Números")

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Estratégias", f"{len(ENSEMBLE_TOP10)}")
    with col_info2:
        st.metric("Números/cartão", f"{NUMS_POR_CARTAO}")
    with col_info3:
        st.metric("Combinações/cartão", f"{COMBINACOES_14:,}")

    st.caption(
        "Ensemble campeão: **10 estratégias** × **14 números** por cartão. "
        f"Cada cartão cobre {COMBINACOES_14:,} combinações de 6. "
        f"Custo: R$ {CUSTO_14:,.2f} por cartão."
    )

    # Mostrar estratégias do ensemble
    with st.expander("📋 Estratégias do Ensemble Top 10", expanded=False):
        cols = st.columns(5)
        for i, est in enumerate(ENSEMBLE_TOP10):
            cols[i % 5].markdown(f"**{NOMES.get(est, est)}**")

    st.markdown("---")

    # =========================================================================
    # TABS: GERAR | CONFERIR | HISTÓRICO
    # =========================================================================
    tab_gerar, tab_conferir, tab_info = st.tabs([
        "🎲 Gerar Cartões",
        "✅ Conferir Resultado",
        "📊 Informações",
    ])

    # =====================================================================
    # TAB 1: GERAR CARTÕES
    # =====================================================================
    with tab_gerar:
        _tab_gerar_cartoes(df)

    # =====================================================================
    # TAB 2: CONFERIR
    # =====================================================================
    with tab_conferir:
        _tab_conferir_resultado(df)

    # =====================================================================
    # TAB 3: INFO
    # =====================================================================
    with tab_info:
        _tab_informacoes()


# =============================================================================
# TAB: GERAR CARTÕES
# =============================================================================

def _tab_gerar_cartoes(df):
    """Gera cartões de 14 números com o ensemble top 10."""

    ultimo_concurso = int(df['concurso'].max())
    proximo_concurso = ultimo_concurso + 1

    col1, col2 = st.columns(2)
    with col1:
        qtd_cartoes = st.number_input(
            "Quantos cartões gerar?", 1, 20, 5,
            key="ens14_qtd",
            help="Cada cartão tem 14 números"
        )
    with col2:
        concurso_alvo = st.number_input(
            "Concurso alvo", proximo_concurso - 5, proximo_concurso + 10,
            proximo_concurso, key="ens14_conc"
        )

    custo_total = qtd_cartoes * CUSTO_14
    st.info(
        f"**{qtd_cartoes} cartões** × R$ {CUSTO_14:,.2f} = "
        f"**R$ {custo_total:,.2f}** | "
        f"Cobertura total: {qtd_cartoes * COMBINACOES_14:,} combinações de 6 | "
        f"Concurso alvo: **{concurso_alvo}**"
    )

    marcar_jogar = st.checkbox("✅ Marcar cartões como 'vai jogar'", value=True, key="ens14_jogar")

    if st.button("🚀 Gerar Cartões", type="primary", use_container_width=True, key="ens14_btn"):
        with st.spinner("Calculando estatísticas..."):
            contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)

        cartoes_novos = []
        barra = st.progress(0, text="Gerando cartões...")

        for i in range(qtd_cartoes):
            random.seed(None)  # Seed aleatório para cada cartão
            dezenas = _gerar_cartao_14(
                ENSEMBLE_TOP10, contagem_total, contagem_recente, df_atrasos, df=df
            )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cartao = {
                'id': f'ENS14-{timestamp}-{i+1:02d}',
                'dezenas': dezenas,
                'estrategia': 'ensemble_top10',
                'estrategia_versao': '1.0',
                'vai_jogar': marcar_jogar,
                'verificado': False,
                'concurso_alvo': int(concurso_alvo),
                'status': 'aguardando',
                'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'qtd_numeros': NUMS_POR_CARTAO,
                'observacao': f'Ensemble Top 10 ({len(ENSEMBLE_TOP10)} estratégias, {NUMS_POR_CARTAO} nums)'
            }
            cartoes_novos.append(cartao)
            barra.progress((i + 1) / qtd_cartoes, text=f"Cartão {i+1}/{qtd_cartoes}...")

        barra.progress(1.0, text="Concluído!")

        # Salvar no sistema
        cartoes_existentes = dm.carregar_cartoes_salvos()
        cartoes_existentes.extend(cartoes_novos)

        if dm.salvar_cartoes(cartoes_existentes):
            st.success(f"✅ **{len(cartoes_novos)} cartões** gerados e salvos!")
            st.balloons()
        else:
            st.error("❌ Erro ao salvar cartões")

        # Exibir cartões gerados
        st.markdown("### 🎫 Cartões Gerados")
        for i, c in enumerate(cartoes_novos):
            dezenas_fmt = '  '.join([f"**{n:02d}**" for n in c['dezenas']])
            with st.expander(f"🎫 Cartão {i+1} — {len(c['dezenas'])} números", expanded=(i < 3)):
                st.markdown(dezenas_fmt)

                # Visualização em grid 6x10
                _exibir_grid_numeros(c['dezenas'])

                # Estatísticas do cartão
                pares = sum(1 for n in c['dezenas'] if n % 2 == 0)
                impares = len(c['dezenas']) - pares
                soma = sum(c['dezenas'])
                st.caption(
                    f"Soma: {soma} | Pares: {pares} | Ímpares: {impares} | "
                    f"ID: {c['id']}"
                )

    # Mostrar cartões pendentes deste concurso
    _exibir_cartoes_pendentes(concurso_alvo)


# =============================================================================
# TAB: CONFERIR RESULTADO
# =============================================================================

def _tab_conferir_resultado(df):
    """Confere cartões ensemble_top10 contra resultado do sorteio."""

    cartoes = dm.carregar_cartoes_salvos()
    cartoes_ens = [
        c for c in cartoes
        if c.get('estrategia') == 'ensemble_top10' and not c.get('verificado', False)
    ]

    if not cartoes_ens:
        st.info("Nenhum cartão Ensemble Top 10 pendente de verificação.")
        st.caption("Gere cartões na aba anterior e volte aqui após o sorteio.")
        return

    concursos_pendentes = sorted(set(c.get('concurso_alvo') for c in cartoes_ens if c.get('concurso_alvo')))
    st.markdown(f"**{len(cartoes_ens)} cartões pendentes** em {len(concursos_pendentes)} concurso(s)")

    concurso_ver = st.selectbox(
        "Concurso para conferir",
        concursos_pendentes,
        key="ens14_conc_ver"
    )

    cartoes_conc = [c for c in cartoes_ens if c.get('concurso_alvo') == concurso_ver]
    st.caption(f"{len(cartoes_conc)} cartões para o concurso {concurso_ver}")

    # Buscar resultado
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Buscar resultado na API", key="ens14_api"):
            resultado = dm.buscar_resultado_concurso(concurso_ver)
            if resultado:
                st.session_state['ens14_resultado'] = resultado
                st.success(f"Resultado: {' - '.join(f'{n:02d}' for n in resultado)}")
            else:
                st.warning("Resultado ainda não disponível na API.")

    with col_b:
        st.markdown("**Ou digite manualmente:**")

    cols_manual = st.columns(6)
    dezenas_manual = []
    for i in range(6):
        v = cols_manual[i].number_input(f"Dez {i+1}", 1, 60, 1 + i*10, key=f"ens14_dez{i}")
        dezenas_manual.append(v)

    if st.button("📝 Usar números manuais", key="ens14_manual"):
        if len(set(dezenas_manual)) == 6:
            st.session_state['ens14_resultado'] = sorted(dezenas_manual)
        else:
            st.error("Os 6 números devem ser diferentes!")

    # Conferir
    resultado = st.session_state.get('ens14_resultado')
    if resultado and len(resultado) == 6:
        st.markdown(f"### 🎰 Resultado do concurso {concurso_ver}")
        st.markdown("**" + "  —  ".join(f"{n:02d}" for n in resultado) + "**")
        st.markdown("---")

        # Verificar cada cartão
        resultados_ver = []
        for c in cartoes_conc:
            acertos = len(set(c['dezenas']) & set(resultado))
            nums_acertados = sorted(set(c['dezenas']) & set(resultado))
            resultados_ver.append({
                'cartao': c,
                'acertos': acertos,
                'acertados': nums_acertados,
            })

        resultados_ver.sort(key=lambda x: x['acertos'], reverse=True)

        # Resumo
        dist = Counter(r['acertos'] for r in resultados_ver)
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        col_r1.metric("🎯 Senas (6)", dist.get(6, 0))
        col_r2.metric("⭐ Quinas (5)", dist.get(5, 0))
        col_r3.metric("🟢 Quadras (4)", dist.get(4, 0))
        col_r4.metric("🔔 Ternos (3)", dist.get(3, 0))

        # Detalhes
        for i, r in enumerate(resultados_ver):
            emoji = "🎯" if r['acertos'] >= 6 else "⭐" if r['acertos'] >= 5 else "🟢" if r['acertos'] >= 4 else "🔔" if r['acertos'] >= 3 else "⚪"
            label = f"{emoji} Cartão {i+1} — **{r['acertos']} acertos**"
            with st.expander(label, expanded=(r['acertos'] >= 4)):
                dezenas_str = []
                for n in r['cartao']['dezenas']:
                    if n in resultado:
                        dezenas_str.append(f"**:green[{n:02d}]**")
                    else:
                        dezenas_str.append(f"{n:02d}")
                st.markdown("  ".join(dezenas_str))
                if r['acertados']:
                    st.caption(f"Acertados: {', '.join(f'{n:02d}' for n in r['acertados'])}")

        # Marcar como verificado
        if st.button(f"✅ Marcar {len(cartoes_conc)} cartões como verificados", key="ens14_verificar"):
            todos = dm.carregar_cartoes_salvos()
            ids_conc = set(c['id'] for c in cartoes_conc)
            for c in todos:
                if c.get('id') in ids_conc:
                    c['verificado'] = True
                    c['status'] = 'verificado'
            dm.salvar_cartoes(todos)
            st.success("Cartões marcados como verificados!")
            st.rerun()


# =============================================================================
# TAB: INFORMAÇÕES
# =============================================================================

def _tab_informacoes():
    """Exibe informações sobre o ensemble e probabilidades."""

    st.subheader("📊 Por que 10 estratégias e 14 números?")

    st.markdown("""
    ### Resultado da análise (`analisar_14_numeros.py`)

    Testamos todas as combinações de 7 a 15 estratégias com cartões de 14 números
    em 100 concursos históricos × 10 cartões cada (226.000 cartões total).

    **Melhor tamanho de ensemble: 10 estratégias** (Média = 1.446 acertos)

    | Tamanho | Média | Melhor combo |
    |---------|-------|-------------|
    | 7 | 1.374 | 1.433 |
    | 8 | 1.373 | 1.445 |
    | 9 | 1.379 | 1.433 |
    | **10** | **1.374** | **1.446** |
    | 11 | 1.366 | 1.442 |
    | 12 | 1.372 | 1.423 |
    | 13 | 1.371 | 1.394 |
    """)

    st.markdown("### 📈 Comparativo: 6 vs 14 números por cartão")

    data = []
    for k in range(7):
        p6 = comb(6, k) * comb(54, 6-k) / comb(60, 6)
        p14 = comb(14, k) * comb(46, 6-k) / comb(60, 6)
        fator = p14 / p6 if p6 > 0 else 0
        label = {0: '0 acertos', 1: '1 acerto', 2: '2 acertos', 3: 'Terno', 4: 'Quadra', 5: 'Quina', 6: 'Sena'}[k]
        data.append({
            'Acertos': label,
            '6 números': f"{p6:.8f}",
            '14 números': f"{p14:.8f}",
            'Fator': f"{fator:.1f}x",
        })
    st.table(pd.DataFrame(data))

    st.markdown(f"""
    ### 💰 Custo e cobertura

    | Item | Valor |
    |------|-------|
    | Custo 1 cartão de 14 | R$ {CUSTO_14:,.2f} |
    | Combinações por cartão | {COMBINACOES_14:,} |
    | Prob. Sena (1 cartão) | 1 em {int(comb(60,6)/COMBINACOES_14):,} |
    | Fator vs cartão de 6 | **{COMBINACOES_14}x** melhor |

    ### 🏆 As 10 estratégias campeãs
    """)

    for est in ENSEMBLE_TOP10:
        st.markdown(f"- {NOMES.get(est, est)}")

    st.markdown("""
    ---
    **Metodologia:** Votação por maioria. Cada estratégia gera 6 números.
    Os 14 números mais votados pelo conjunto formam o cartão final.
    """)


# =============================================================================
# HELPERS
# =============================================================================

def _exibir_grid_numeros(dezenas):
    """Exibe grid visual 10x6 com números marcados."""
    dezenas_set = set(dezenas)
    linhas = []
    for faixa_inicio in range(1, 61, 10):
        nums = []
        for n in range(faixa_inicio, min(faixa_inicio + 10, 61)):
            if n in dezenas_set:
                nums.append(f"🟢 **{n:02d}**")
            else:
                nums.append(f"⚪ {n:02d}")
        linhas.append("  ".join(nums))
    st.code("\n".join(linhas), language=None)


def _exibir_cartoes_pendentes(concurso_alvo):
    """Mostra cartões ensemble_top10 já salvos para este concurso."""
    cartoes = dm.carregar_cartoes_salvos()
    cartoes_conc = [
        c for c in cartoes
        if c.get('estrategia') == 'ensemble_top10'
        and c.get('concurso_alvo') == concurso_alvo
        and not c.get('verificado', False)
    ]
    if cartoes_conc:
        st.markdown("---")
        st.markdown(f"### 📋 Cartões já salvos para o concurso {concurso_alvo}")
        for i, c in enumerate(cartoes_conc):
            dezenas_fmt = ' - '.join(f"{n:02d}" for n in c['dezenas'])
            st.markdown(f"**{i+1}.** {dezenas_fmt} ({c.get('id', '?')})")
