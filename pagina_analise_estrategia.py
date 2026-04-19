"""
================================================================================
📊 PÁGINA: ANÁLISE DE ESTRATÉGIA GENÉRICA
================================================================================
Página reutilizável para qualquer estratégia de análise
"""

import streamlit as st
from datetime import datetime
from pagina_escada_temporal import (
    _descricao_estrategia,
    _descricao_detalhada_estrategia,
    _calcular_custo,
    _calcular_combinacoes
)
from modules import data_manager as dm
from modules import statistics as stats
from modules import game_generator as gen


def pagina_analise_estrategia(df, estrategia_nome, estrategia_key):
    """
    Página genérica de análise para qualquer estratégia

    Args:
        df: DataFrame com dados históricos
        estrategia_nome: Nome exibido da estratégia (ex: "Números Atrasados")
        estrategia_key: Chave da estratégia (ex: "atrasados")
    """

    st.title(f"📊 {estrategia_nome}")
    st.markdown(f"### {_descricao_estrategia(estrategia_key)}")

    # Janela configurável
    janela_recente = st.slider(
        "Janela recente (jogos)",
        min_value=20,
        max_value=200,
        value=50,
        step=10,
        help="Quantidade de concursos recentes usados para definir números quentes/atrasados"
    )

    # Calcular estatísticas com janela escolhida
    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(
        df, ultimos=janela_recente)

    # Mostrar informações da estratégia
    col1, col2, col3 = st.columns(3)

    with col1:
        if estrategia_key == 'atrasados':
            mais_atrasado = df_atrasos['atraso'].idxmax()
            st.metric("Mais Atrasado", f"Nº {mais_atrasado:02d}",
                      f"{df_atrasos.loc[mais_atrasado, 'atraso']} jogos")
        elif estrategia_key == 'quentes':
            mais_quente = contagem_recente.idxmax()
            st.metric("Mais Quente", f"Nº {mais_quente:02d}",
                      f"{contagem_recente[mais_quente]} saídas")
        else:
            st.metric("Total de Concursos", len(df))

    with col2:
        st.metric("Janela Recente", f"{janela_recente} jogos")

    with col3:
        cartoes_estrategia = [c for c in dm.carregar_cartoes_salvos()
                              if c.get('estrategia') == estrategia_key]
        st.metric("Cartões Salvos", len(cartoes_estrategia))

    # Abas
    st.markdown("---")

    tab_info, tab_manual, tab_auto, tab_verificar = st.tabs([
        "💡 Informações",
        "✍️ Geração Manual",
        "🤖 Geração Automática",
        "🎯 Verificar Resultados"
    ])

    # TAB: INFORMAÇÕES
    with tab_info:
        st.markdown(_descricao_detalhada_estrategia(estrategia_key))

        # Mostrar top números baseado na estratégia
        st.markdown("### 🎯 Top 15 Números Sugeridos")

        if estrategia_key == 'atrasados':
            top_nums = df_atrasos.nlargest(15, 'atraso')
            for idx, row in top_nums.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"### Nº {idx:02d}")
                with col2:
                    st.metric("Atraso", f"{row['atraso']} jogos")
                st.markdown("---")

        elif estrategia_key == 'quentes':
            top_nums = contagem_recente.nlargest(15)
            for idx, num in enumerate(top_nums.index, 1):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"### Nº {num:02d}")
                with col2:
                    st.metric("Saídas Recentes", f"{top_nums[num]} vezes")
                st.markdown("---")

        else:
            st.info("Use a geração automática para criar jogos com esta estratégia.")

    # TAB: GERAÇÃO MANUAL
    with tab_manual:
        st.markdown("#### ✍️ Criar Cartão Manualmente")
        st.info("Use a aba 'Análise Escada' para geração manual visual com botões.")

    # TAB: GERAÇÃO AUTOMÁTICA
    with tab_auto:
        st.markdown(f"#### 🤖 Geração Automática - {estrategia_nome}")

        col1, col2, col3 = st.columns(3)

        with col1:
            qtd_numeros = st.select_slider(
                "🔢 Números por cartão",
                options=list(range(6, 21)),
                value=10
            )

        with col2:
            qtd_cartoes = st.number_input(
                "📋 Quantidade de cartões",
                min_value=1,
                max_value=50,
                value=10,
                step=1
            )

        with col3:
            st.metric("💰 Custo/cartão",
                      f"R$ {_calcular_custo(qtd_numeros):.2f}")
            st.caption(f"🎯 {_calcular_combinacoes(qtd_numeros):,} combinações")

        # Concurso e flag de jogo
        col_conf1, col_conf2 = st.columns(2)
        with col_conf1:
            concurso_alvo_auto = st.number_input(
                "Concurso alvo",
                min_value=1,
                max_value=9999,
                value=len(df) + 1,
                step=1,
                help="Concurso para o qual estes cartões serão conferidos"
            )
        with col_conf2:
            marcar_jogar_auto = st.checkbox(
                "Marcar para jogar",
                value=True,
                help="Se marcado, os cartões já entram na conferência do concurso escolhido"
            )

        st.markdown("---")

        st.info(f"""
        ℹ️ **Resumo:**
        - {qtd_cartoes} cartões de {qtd_numeros} números cada
        - Estratégia: **{estrategia_nome.upper()}**
        - Custo total: **R$ {qtd_cartoes * _calcular_custo(qtd_numeros):.2f}**
        """)

        if st.button(f"🎲 Gerar {qtd_cartoes} Cartões", type="primary", width="stretch"):
            with st.spinner(f"Gerando cartões com estratégia {estrategia_nome}..."):
                import random

                novos_cartoes = []
                for i in range(qtd_cartoes):
                    # Gerar jogo base
                    if estrategia_key == 'automl':
                        # AutoML precisa do DataFrame completo
                        dezenas_base = gen.gerar_jogo_automl(
                            df=df,
                            contagem_total=contagem_total,
                            contagem_recente=contagem_recente,
                            df_atrasos=df_atrasos
                        )
                    else:
                        dezenas_base = gen.gerar_jogo(
                            estrategia=estrategia_key,
                            contagem_total=contagem_total,
                            contagem_recente=contagem_recente,
                            df_atrasos=df_atrasos
                        )

                    # Expandir se necessário
                    if qtd_numeros > 6:
                        if estrategia_key == 'atrasados':
                            candidatos = df_atrasos.nlargest(
                                30, 'atraso').index.tolist()
                        elif estrategia_key == 'quentes':
                            candidatos = contagem_recente.nlargest(
                                30).index.tolist()
                        else:
                            candidatos = list(range(1, 61))

                        candidatos = [
                            n for n in candidatos if n not in dezenas_base]
                        random.shuffle(candidatos)
                        numeros_extras = candidatos[:qtd_numeros - 6]
                        dezenas = sorted(dezenas_base + numeros_extras)
                    else:
                        dezenas = dezenas_base

                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    cartao = {
                        'id': f'{estrategia_key.upper()}-{timestamp}-{i+1:02d}',
                        'dezenas': sorted(dezenas),
                        'estrategia': estrategia_key,
                        'vai_jogar': marcar_jogar_auto,
                        'verificado': False,
                        'concurso_alvo': int(concurso_alvo_auto),
                        'status': 'não_marcado',
                        'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'qtd_numeros': qtd_numeros
                    }
                    novos_cartoes.append(cartao)

                # Salvar
                cartoes_existentes = dm.carregar_cartoes_salvos()
                cartoes_existentes.extend(novos_cartoes)

                if dm.salvar_cartoes(cartoes_existentes):
                    st.success(f"✅ {qtd_cartoes} cartões gerados e salvos!")
                    st.balloons()

                    with st.expander("👀 Visualizar cartões gerados", expanded=True):
                        for i, cartao in enumerate(novos_cartoes, 1):
                            cols = st.columns([1, 6])
                            with cols[0]:
                                st.write(f"**#{i}**")
                            with cols[1]:
                                nums = " - ".join(
                                    [f"{n:02d}" for n in cartao['dezenas']])
                                st.code(nums)
                else:
                    st.error("❌ Erro ao salvar cartões")

    # TAB: VERIFICAR RESULTADOS
    with tab_verificar:
        st.markdown(f"#### 🎯 Verificar Resultados - {estrategia_nome}")

        # Carregar cartões desta estratégia
        todos_cartoes_verif = dm.carregar_cartoes_salvos()
        cartoes_esta_estrategia = [
            c for c in todos_cartoes_verif
            if c.get('estrategia') == estrategia_key
        ]

        if not cartoes_esta_estrategia:
            st.info(f"📭 Nenhum cartão salvo para **{estrategia_nome}**. Gere cartões nas abas acima!")
        else:
            # Listar concursos pendentes desta estratégia
            concursos_est = sorted(set(
                c.get('concurso_alvo') for c in cartoes_esta_estrategia
                if c.get('concurso_alvo')
            ), reverse=True)

            col_v1, col_v2 = st.columns([3, 1])
            with col_v1:
                concurso_ver = st.selectbox(
                    "🎯 Concurso para conferir",
                    options=concursos_est,
                    format_func=lambda x: f"Concurso {x} ({sum(1 for c in cartoes_esta_estrategia if c.get('concurso_alvo') == x)} jogos)",
                    key=f"concurso_ver_{estrategia_key}"
                )
            with col_v2:
                st.markdown("##### ")
                btn_ver = st.button("🔍 Conferir", type="primary", key=f"btn_ver_{estrategia_key}")

            if btn_ver and concurso_ver:
                jogos_ver = [c for c in cartoes_esta_estrategia if c.get('concurso_alvo') == concurso_ver]

                # Buscar resultado
                max_c = int(df['concurso'].max()) if 'concurso' in df.columns else 0
                resultado_ver = None
                if concurso_ver <= max_c:
                    linha_ver = df[df['concurso'] == concurso_ver]
                    if not linha_ver.empty:
                        row_ver = linha_ver.iloc[0]
                        dezenas_ver = []
                        if 'dez1' in df.columns:
                            for ii in range(1, 7):
                                try:
                                    dezenas_ver.append(int(row_ver.get(f'dez{ii}')))
                                except:
                                    pass
                        if len(dezenas_ver) == 6:
                            resultado_ver = sorted(dezenas_ver)

                if not resultado_ver:
                    resultado_ver = dm.buscar_resultado_concurso(concurso_ver)

                if not resultado_ver:
                    st.warning(f"⏳ Concurso {concurso_ver} ainda não sorteado.")
                    for idx_j, jogo_j in enumerate(jogos_ver, 1):
                        nums_j = " - ".join([f"{n:02d}" for n in jogo_j['dezenas']])
                        st.code(f"#{idx_j:02d}  {nums_j}")
                else:
                    st.success(f"✅ Resultado: {' - '.join([f'**{n:02d}**' for n in sorted(resultado_ver)])}")
                    st.markdown("---")

                    for idx_j, jogo_j in enumerate(jogos_ver, 1):
                        acertos_j = len(set(jogo_j['dezenas']) & set(resultado_ver))
                        acertados_j = sorted(set(jogo_j['dezenas']) & set(resultado_ver))

                        col_j1, col_j2 = st.columns([5, 2])
                        with col_j1:
                            nums_j = " - ".join([f"{n:02d}" for n in jogo_j['dezenas']])
                            st.code(f"#{idx_j:02d}  {nums_j}")
                            if acertados_j:
                                st.caption(" ".join([f"✅ {n:02d}" for n in acertados_j]))
                        with col_j2:
                            if acertos_j >= 4:
                                st.warning(f"⭐ **{acertos_j} acertos!**")
                            elif acertos_j > 0:
                                st.info(f"{acertos_j} acertos")
                            else:
                                st.caption("0 acertos")

        st.markdown("---")
        st.info("💡 Para conferir **TODAS** as estratégias juntas, use '📋 Conferência Semanal' no menu lateral.")
