"""
================================================================================
ENSEMBLE ADAPTATIVO — COMPOSICAO POR DESEMPENHO RECENTE
================================================================================
Pagina do ensemble como estrategia: mostra quais estrategias estao DENTRO
(porque acertaram terno+ recentemente) e quais foram cortadas (streak sem
terno+). Gera cartoes por votacao das estrategias DENTRO.
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
# CONFIGURAÇÃO
# =============================================================================

NOMES = {
    'escada': '🔄 Escada', 'atrasados': '⏰ Atrasados', 'quentes': '🔥 Quentes',
    'equilibrado': '⚖️ Equilibrado', 'misto': '🎨 Misto', 'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleat.Smart', 'sequencias': '🧬 Sequências', 'wheel': '🎯 Wheel',
    'candidatos_ouro': '🥇 Cand.Ouro', 'momentum': '🚀 Momentum', 'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Freq.Desvio', 'pares_frequentes': '👫 Pares.Freq', 'ciclos': '🔁 Ciclos',
    'atraso_recente': '🕰️ Atraso Recente',
}

ESTRATEGIAS_ENSEMBLE_CARTAO_SALVO = ('ensemble', 'ensemble_top10')


# =============================================================================
# GERAÇÃO
# =============================================================================

def _gerar_cartao_ensemble(estrategias, qtd_numeros, contagem_total, contagem_recente, df_atrasos, df=None):
    """Gera 1 cartão via votação entre as estratégias informadas."""
    votos = Counter()
    for est in estrategias:
        try:
            base = gen.gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
            if qtd_numeros > 6:
                jogo = gen.expandir_jogo(
                    base, qtd_numeros, est,
                    contagem_total, contagem_recente, df_atrasos, df=df
                )
            else:
                jogo = base
            for n in jogo:
                votos[n] += 1
        except Exception:
            pass

    if not votos:
        return sorted(random.sample(range(1, 61), qtd_numeros))

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    if len(candidatos) >= qtd_numeros:
        return sorted(candidatos[:qtd_numeros])
    extras = [n for n in range(1, 61) if n not in candidatos]
    random.shuffle(extras)
    todos = candidatos + extras[:qtd_numeros - len(candidatos)]
    return sorted(todos[:qtd_numeros])


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_ensemble_14(df):
    """Página do Ensemble Adaptativo."""

    st.header("🏆 Ensemble Adaptativo")
    st.caption(
        "Estratégias entram e saem automaticamente pelo desempenho recente. "
        "Sai do ensemble quem ficar N concursos seguidos sem marcar terno ou mais."
    )

    max_streak = st.session_state.get('ens_max_streak', 2)
    composicao = gen.composicao_ensemble_atual(max_streak=max_streak)
    dentro = [c['estrategia'] for c in composicao if c['status'] == 'dentro']
    fora = [c for c in composicao if c['status'] == 'fora']

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Estratégias DENTRO", len(dentro))
    with col2:
        st.metric("❌ Estratégias FORA", len(fora))
    with col3:
        st.metric("Concursos avaliados", max((c['total_concursos_avaliados'] for c in composicao), default=0))

    _exibir_grid_composicao(composicao, max_streak)

    st.markdown("---")

    tab_gerar, tab_conferir = st.tabs([
        "🎲 Gerar Cartões",
        "✅ Conferir Resultado",
    ])

    with tab_gerar:
        _tab_gerar_cartoes(df, dentro, composicao)

    with tab_conferir:
        _tab_conferir_resultado(df)


# =============================================================================
# GRID DE COMPOSIÇÃO
# =============================================================================

def _exibir_grid_composicao(composicao, max_streak_atual):
    """Grid com status de cada estratégia + controle do max_streak."""

    st.subheader("📋 Composição atual do ensemble")

    col_cfg, col_info = st.columns([1, 2])
    with col_cfg:
        novo = st.slider(
            "Jogos sem terno+ para SAIR",
            min_value=1, max_value=5,
            value=max_streak_atual,
            key="slider_max_streak",
            help="Se a estratégia ficar este número de concursos consecutivos sem marcar 3+ acertos em nenhum cartão, ela sai do ensemble."
        )
        if novo != max_streak_atual:
            st.session_state['ens_max_streak'] = novo
            st.rerun()

    with col_info:
        dentro = [c['estrategia'] for c in composicao if c['status'] == 'dentro']
        if dentro:
            nomes_in = ' · '.join(NOMES.get(e, e) for e in dentro)
            st.success(f"**{len(dentro)} dentro:** {nomes_in}")
        else:
            st.warning("Nenhuma estratégia atende ao critério. Será usado o fallback clássico.")

    if not composicao:
        st.info("Sem histórico de conferências ainda. Execute o Piloto Automático para gerar dados.")
        return

    linhas = []
    for c in composicao:
        est = c['estrategia']
        status = c['status']
        if status == 'dentro':
            icon = '✅'
        elif status == 'fora':
            icon = '❌'
        else:
            icon = '⚪'
        ultimo = c['ultimo_terno_concurso'] or '—'
        linhas.append({
            '': icon,
            'Estratégia': NOMES.get(est, est),
            'Streak sem terno+': c['streak_sem_terno'],
            'Último terno+ (concurso)': ultimo,
            'Concursos com terno+': c['concursos_com_terno'],
            'Total avaliado': c['total_concursos_avaliados'],
            'Status': status.upper(),
        })

    df_grid = pd.DataFrame(linhas)
    st.dataframe(df_grid, use_container_width=True, hide_index=True)


# =============================================================================
# TAB: GERAR CARTÕES
# =============================================================================

def _tab_gerar_cartoes(df, dentro, composicao):
    """Gera cartões via votação das estratégias DENTRO."""

    if not dentro:
        st.warning(
            "Nenhuma estratégia está dentro do ensemble no critério atual. "
            "Aumente o slider ou aguarde novos resultados."
        )
        return

    ultimo_concurso = int(df['concurso'].max())
    proximo_concurso = ultimo_concurso + 1

    col1, col2, col3 = st.columns(3)
    with col1:
        qtd_numeros = st.select_slider(
            "Números por cartão",
            options=list(range(6, 21)),
            value=st.session_state.get('ens_qtd_nums', 14),
            key="ens_qtd_nums_input",
            help="6 = cartão simples. 14 = cartão estendido (custa mais, cobre mais)."
        )
        st.session_state['ens_qtd_nums'] = qtd_numeros
    with col2:
        qtd_cartoes = st.number_input(
            "Quantos cartões gerar?", 1, 50, 5,
            key="ens_qtd_cartoes",
        )
    with col3:
        concurso_alvo = st.number_input(
            "Concurso alvo", proximo_concurso - 5, proximo_concurso + 10,
            proximo_concurso, key="ens_conc_alvo"
        )

    custo_unit = CUSTOS_CARTAO.get(qtd_numeros, 0)
    custo_total = qtd_cartoes * custo_unit
    combos = comb(qtd_numeros, 6)
    st.info(
        f"**{qtd_cartoes} cartões** × {qtd_numeros} números × R$ {custo_unit:,.2f} = "
        f"**R$ {custo_total:,.2f}** | {qtd_cartoes * combos:,} combinações de 6 | "
        f"Concurso alvo: **{concurso_alvo}**"
    )

    marcar_jogar = st.checkbox("✅ Marcar cartões como 'vai jogar'", value=True, key="ens_jogar")

    if st.button("🚀 Gerar Cartões", type="primary", use_container_width=True, key="ens_gerar_btn"):
        with st.spinner("Calculando estatísticas..."):
            contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)

        cartoes_novos = []
        barra = st.progress(0, text="Gerando cartões...")

        versao_ens = versao_estrategia('ensemble')
        obs = f"Ensemble adaptativo ({len(dentro)} estratégias DENTRO, {qtd_numeros} nums)"

        for i in range(qtd_cartoes):
            random.seed(None)
            dezenas = _gerar_cartao_ensemble(
                dentro, qtd_numeros, contagem_total, contagem_recente, df_atrasos, df=df
            )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cartao = {
                'id': f'ENS-{timestamp}-{i+1:02d}',
                'dezenas': dezenas,
                'estrategia': 'ensemble',
                'estrategia_versao': versao_ens,
                'vai_jogar': marcar_jogar,
                'verificado': False,
                'concurso_alvo': int(concurso_alvo),
                'status': 'aguardando',
                'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'qtd_numeros': qtd_numeros,
                'observacao': obs,
                'ensemble_composicao': list(dentro),
            }
            cartoes_novos.append(cartao)
            barra.progress((i + 1) / qtd_cartoes, text=f"Cartão {i+1}/{qtd_cartoes}...")

        barra.progress(1.0, text="Concluído!")

        cartoes_existentes = dm.carregar_cartoes_salvos()
        cartoes_existentes.extend(cartoes_novos)
        if dm.salvar_cartoes(cartoes_existentes):
            st.success(f"✅ **{len(cartoes_novos)} cartões** gerados e salvos!")
            st.balloons()
        else:
            st.error("❌ Erro ao salvar cartões")

        st.markdown("### 🎫 Cartões Gerados")
        for i, c in enumerate(cartoes_novos):
            dezenas_fmt = '  '.join([f"**{n:02d}**" for n in c['dezenas']])
            with st.expander(f"🎫 Cartão {i+1} — {len(c['dezenas'])} números", expanded=(i < 3)):
                st.markdown(dezenas_fmt)
                _exibir_grid_numeros(c['dezenas'])
                pares = sum(1 for n in c['dezenas'] if n % 2 == 0)
                impares = len(c['dezenas']) - pares
                soma = sum(c['dezenas'])
                st.caption(
                    f"Soma: {soma} | Pares: {pares} | Ímpares: {impares} | ID: {c['id']}"
                )

    _exibir_cartoes_pendentes(concurso_alvo)


# =============================================================================
# TAB: CONFERIR RESULTADO
# =============================================================================

def _tab_conferir_resultado(df):
    """Confere cartões ensemble contra resultado do sorteio."""

    cartoes = dm.carregar_cartoes_salvos()
    cartoes_ens = [
        c for c in cartoes
        if c.get('estrategia') in ESTRATEGIAS_ENSEMBLE_CARTAO_SALVO
        and not c.get('verificado', False)
    ]

    if not cartoes_ens:
        st.info("Nenhum cartão Ensemble pendente de verificação.")
        st.caption("Gere cartões na aba anterior e volte aqui após o sorteio.")
        return

    concursos_pendentes = sorted(set(c.get('concurso_alvo') for c in cartoes_ens if c.get('concurso_alvo')))
    st.markdown(f"**{len(cartoes_ens)} cartões pendentes** em {len(concursos_pendentes)} concurso(s)")

    concurso_ver = st.selectbox(
        "Concurso para conferir",
        concursos_pendentes,
        key="ens_conc_ver"
    )

    cartoes_conc = [c for c in cartoes_ens if c.get('concurso_alvo') == concurso_ver]
    st.caption(f"{len(cartoes_conc)} cartões para o concurso {concurso_ver}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Buscar resultado na API", key="ens_api"):
            resultado = dm.buscar_resultado_concurso(concurso_ver)
            if resultado:
                st.session_state['ens_resultado'] = resultado
                st.success(f"Resultado: {' - '.join(f'{n:02d}' for n in resultado)}")
            else:
                st.warning("Resultado ainda não disponível na API.")

    with col_b:
        st.markdown("**Ou digite manualmente:**")

    cols_manual = st.columns(6)
    dezenas_manual = []
    for i in range(6):
        v = cols_manual[i].number_input(f"Dez {i+1}", 1, 60, 1 + i*10, key=f"ens_dez{i}")
        dezenas_manual.append(v)

    if st.button("📝 Usar números manuais", key="ens_manual"):
        if len(set(dezenas_manual)) == 6:
            st.session_state['ens_resultado'] = sorted(dezenas_manual)
        else:
            st.error("Os 6 números devem ser diferentes!")

    resultado = st.session_state.get('ens_resultado')
    if resultado and len(resultado) == 6:
        st.markdown(f"### 🎰 Resultado do concurso {concurso_ver}")
        st.markdown("**" + "  —  ".join(f"{n:02d}" for n in resultado) + "**")
        st.markdown("---")

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

        dist = Counter(r['acertos'] for r in resultados_ver)
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        col_r1.metric("🎯 Senas (6)", dist.get(6, 0))
        col_r2.metric("⭐ Quinas (5)", dist.get(5, 0))
        col_r3.metric("🟢 Quadras (4)", dist.get(4, 0))
        col_r4.metric("🔔 Ternos (3)", dist.get(3, 0))

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

        if st.button(f"✅ Marcar {len(cartoes_conc)} cartões como verificados", key="ens_verificar"):
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
# HELPERS
# =============================================================================

def _exibir_grid_numeros(dezenas):
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
    cartoes = dm.carregar_cartoes_salvos()
    cartoes_conc = [
        c for c in cartoes
        if c.get('estrategia') in ESTRATEGIAS_ENSEMBLE_CARTAO_SALVO
        and c.get('concurso_alvo') == concurso_alvo
        and not c.get('verificado', False)
    ]
    if cartoes_conc:
        st.markdown("---")
        st.markdown(f"### 📋 Cartões já salvos para o concurso {concurso_alvo}")
        for i, c in enumerate(cartoes_conc):
            dezenas_fmt = ' - '.join(f"{n:02d}" for n in c['dezenas'])
            st.markdown(f"**{i+1}.** {dezenas_fmt} ({c.get('id', '?')})")
