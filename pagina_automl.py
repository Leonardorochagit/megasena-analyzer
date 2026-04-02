"""
================================================================================
🤖 PÁGINA: AUTOML COM PYCARET
================================================================================
Interface de Machine Learning para gerar cartões otimizados
Objetivo: maximizar chances de acertar pelo menos a QUADRA (4 números)
"""

import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime
from collections import Counter
from modules import data_manager as dm
from modules import statistics as stats

# PyCaret será importado sob demanda (lazy) para não travar o carregamento
PYCARET_DISPONIVEL = None  # None = ainda não verificado
setup_clf = None
compare_models = None
pull = None
create_model = None
predict_model = None

def _carregar_pycaret():
    """Carrega PyCaret sob demanda"""
    global PYCARET_DISPONIVEL, setup_clf, compare_models, pull, create_model, predict_model
    if PYCARET_DISPONIVEL is not None:
        return PYCARET_DISPONIVEL
    try:
        from pycaret.classification import (
            setup as _setup, compare_models as _compare,
            pull as _pull, create_model as _create, predict_model as _predict
        )
        setup_clf = _setup
        compare_models = _compare
        pull = _pull
        create_model = _create
        predict_model = _predict
        PYCARET_DISPONIVEL = True
    except (ImportError, RuntimeError):
        PYCARET_DISPONIVEL = False
    return PYCARET_DISPONIVEL


def calcular_probabilidades_todos_numeros(df, n_concursos=300, progress_callback=None):
    """
    Treina modelos para TODOS os 60 números e retorna probabilidades.
    Usa Random Forest para cada número.
    """
    import io
    import sys
    import logging

    logging.getLogger('pycaret').setLevel(logging.ERROR)
    logging.getLogger('lightgbm').setLevel(logging.ERROR)
    logging.getLogger('sklearn').setLevel(logging.ERROR)

    probabilidades = {}
    modelos_info = {}

    for numero in range(1, 61):
        if progress_callback:
            progress_callback(numero)

        dados = stats.preparar_dados_pycaret(df, numero, n_concursos)

        if dados is not None and len(dados) > 50:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            try:
                clf_setup = setup_clf(
                    data=dados,
                    target='saiu',
                    session_id=42 + numero,
                    verbose=False,
                    html=False,
                    log_experiment=False,
                    system_log=False,
                    n_jobs=1
                )

                # Criar modelo rápido
                modelo = create_model('rf', verbose=False, fold=3)

                # Prever probabilidade para próximo sorteio
                ultimo_dado = dados.tail(1).drop('saiu', axis=1)
                previsao = predict_model(modelo, data=ultimo_dado, verbose=False)

                # Extrair probabilidade
                if 'prediction_score' in previsao.columns:
                    prob = float(previsao['prediction_score'].values[0])
                elif 'Score' in previsao.columns:
                    prob = float(previsao['Score'].values[0])
                elif 'prediction_score_1' in previsao.columns:
                    prob = float(previsao['prediction_score_1'].values[0])
                else:
                    prob = 0.5

                # Se previu que NÃO sai (label=0), a prob de sair é 1-prob
                pred_label = None
                if 'prediction_label' in previsao.columns:
                    pred_label = int(previsao['prediction_label'].values[0])
                elif 'Label' in previsao.columns:
                    pred_label = int(previsao['Label'].values[0])

                if pred_label == 0:
                    prob = 1 - prob

                probabilidades[numero] = round(prob, 4)
                modelos_info[numero] = {
                    'prob': prob,
                    'dados_treino': len(dados),
                }

            except Exception:
                probabilidades[numero] = 0.1
                modelos_info[numero] = {'prob': 0.1, 'dados_treino': 0}
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        else:
            probabilidades[numero] = 0.1
            modelos_info[numero] = {'prob': 0.1, 'dados_treino': 0}

    return probabilidades, modelos_info


def gerar_cartoes_otimizados(probabilidades, contagem_total, contagem_recente,
                              df_atrasos, qtd_cartoes, qtd_numeros, concurso_alvo):
    """
    Gera cartões otimizados para maximizar chance de acertar quadra.

    Estratégia:
    - Usa ranking de probabilidades do ML como base
    - Diversifica os cartões para cobrir mais combinações
    - Valida equilíbrio par/ímpar e distribuição
    """
    # Ranking por probabilidade ML
    ranking_ml = sorted(probabilidades.items(), key=lambda x: x[1], reverse=True)

    # Top números por diferentes critérios
    top_ml = [n for n, _ in ranking_ml[:25]]
    top_quentes = contagem_recente.nlargest(20).index.tolist()
    top_atrasados = df_atrasos.nlargest(15, 'jogos_sem_sair')['numero'].tolist()
    top_frequentes = contagem_total.nlargest(20).index.tolist()

    # Score combinado: ML + frequência recente + atraso
    scores = {}
    for num in range(1, 61):
        score = 0
        # Peso principal: probabilidade ML (0-100 pontos)
        score += probabilidades.get(num, 0) * 100

        # Peso secundário: frequência recente (0-20 pontos)
        if num in top_quentes[:10]:
            score += 20 - top_quentes.index(num) * 2
        elif num in top_quentes:
            score += 5

        # Peso terciário: atraso (números com atraso moderado, 0-15 pontos)
        if num in top_atrasados[:10]:
            pos = top_atrasados.index(num)
            score += 15 - pos * 1.5

        scores[num] = round(score, 2)

    # Ranking final
    ranking_final = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    cartoes_gerados = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    numeros_usados_global = Counter()

    for i in range(qtd_cartoes):
        tentativas = 0
        melhor_jogo = None
        melhor_score_jogo = 0

        while tentativas < 200:
            tentativas += 1

            if i == 0:
                # Primeiro cartão: top números do ranking
                pool = [n for n, _ in ranking_final[:qtd_numeros + 10]]
            elif i < qtd_cartoes // 3:
                # Primeira terça parte: foco em ML + quentes
                pool = list(set(top_ml[:20] + top_quentes[:15]))
            elif i < 2 * qtd_cartoes // 3:
                # Segunda terça parte: foco em ML + atrasados
                pool = list(set(top_ml[:20] + top_atrasados[:15]))
            else:
                # Última terça parte: diversificado
                menos_usados = [n for n in range(1, 61)]
                menos_usados.sort(key=lambda n: (numeros_usados_global[n], -scores.get(n, 0)))
                pool = menos_usados[:30]

            if len(pool) < qtd_numeros:
                pool = [n for n, _ in ranking_final[:30]]

            jogo = sorted(random.sample(pool, qtd_numeros))

            # Validações de equilíbrio
            pares = sum(1 for n in jogo if n % 2 == 0)
            soma = sum(jogo)
            dezenas_baixas = sum(1 for n in jogo if n <= 30)

            equilibrio_ok = True
            if qtd_numeros == 6:
                equilibrio_ok = (2 <= pares <= 4 and 120 <= soma <= 240 and 2 <= dezenas_baixas <= 4)
            elif qtd_numeros >= 7:
                equilibrio_ok = (2 <= pares <= qtd_numeros - 2 and
                                100 <= soma <= 300 and
                                2 <= dezenas_baixas <= qtd_numeros - 2)

            if not equilibrio_ok:
                continue

            # Score do jogo = soma das probabilidades
            score_jogo = sum(probabilidades.get(n, 0) for n in jogo)

            # Penalizar sobreposição excessiva com cartões anteriores
            if cartoes_gerados:
                for cartao_ant in cartoes_gerados:
                    overlap = len(set(jogo) & set(cartao_ant['dezenas']))
                    if overlap > qtd_numeros - 2:
                        score_jogo *= 0.5

            if score_jogo > melhor_score_jogo:
                melhor_score_jogo = score_jogo
                melhor_jogo = jogo

        if melhor_jogo is None:
            pool = [n for n, _ in ranking_final[:30]]
            melhor_jogo = sorted(random.sample(pool, qtd_numeros))

        for n in melhor_jogo:
            numeros_usados_global[n] += 1

        prob_media = np.mean([probabilidades.get(n, 0) for n in melhor_jogo])

        cartao = {
            'id': f'AUTOML-{timestamp}-{i+1:02d}',
            'dezenas': melhor_jogo,
            'estrategia': 'automl',
            'vai_jogar': False,
            'verificado': False,
            'concurso_alvo': concurso_alvo,
            'status': 'gerado',
            'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'qtd_numeros': qtd_numeros,
            'score_ml': round(melhor_score_jogo, 2),
            'prob_media_ml': round(prob_media, 4)
        }
        cartoes_gerados.append(cartao)

    return cartoes_gerados, scores


def pagina_automl(df):
    """
    Página dedicada ao AutoML com PyCaret
    Foco: gerar cartões otimizados para acertar pelo menos a QUADRA
    """

    st.title("🤖 AutoML com PyCaret")
    st.markdown("### Machine Learning para Gerar Cartões Otimizados")

    if not _carregar_pycaret():
        st.error("❌ **PyCaret não está instalado!**")
        st.code("pip install pycaret", language="bash")
        st.info("""
        📌 **O que é PyCaret?**

        PyCaret é uma biblioteca de AutoML que automaticamente:
        - Testa múltiplos algoritmos de ML
        - Compara performance de cada modelo
        - Seleciona o melhor automaticamente
        - Gera previsões otimizadas
        """)
        return

    # Abas principais
    tab_gerar, tab_ranking, tab_historico = st.tabs([
        "🎲 Gerar Cartões",
        "📊 Ranking de Números",
        "📋 Histórico"
    ])

    # ==========================================================================
    # TAB 1: GERAR CARTÕES
    # ==========================================================================
    with tab_gerar:
        st.markdown("## 🎲 Gerar Cartões Otimizados por ML")

        st.info("""
        🎯 **Como funciona:**
        1. O sistema treina um modelo de ML para **cada um dos 60 números**
        2. Calcula a **probabilidade** de cada número sair no próximo sorteio
        3. Gera cartões **otimizados** combinando os números mais prováveis
        4. Diversifica os cartões para **maximizar cobertura** e chance de acertar a **quadra** (4+ acertos)

        ⏱️ O treinamento leva ~3-5 minutos (60 modelos são criados).
        """)

        st.markdown("---")

        st.markdown("### ⚙️ Configuração")

        col1, col2, col3 = st.columns(3)

        with col1:
            qtd_cartoes = st.number_input(
                "📋 Quantidade de Cartões",
                min_value=1,
                max_value=50,
                value=10,
                step=1,
                help="Mais cartões = maior cobertura de combinações"
            )

        with col2:
            qtd_numeros = st.selectbox(
                "🎯 Números por Cartão",
                options=[6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                index=0,
                help="Mais números = maior chance de quadra, mas mais caro"
            )

        with col3:
            concurso_alvo = st.number_input(
                "🏁 Concurso Alvo",
                min_value=1,
                max_value=9999,
                value=len(df) + 1,
                step=1
            )

        col4, col5 = st.columns(2)

        with col4:
            n_concursos = st.slider(
                "📊 Concursos para Treino",
                min_value=100,
                max_value=500,
                value=300,
                step=50,
                help="Mais concursos = modelos mais precisos, mas mais lento"
            )

        with col5:
            preco_aposta = {6: 5.00, 7: 35.00, 8: 140.00, 9: 420.00, 10: 1050.00,
                           11: 2310.00, 12: 4620.00, 13: 8580.00, 14: 15015.00, 15: 25025.00}
            custo_unitario = preco_aposta.get(qtd_numeros, 5.00)
            custo_total = custo_unitario * qtd_cartoes
            st.metric("💰 Custo Estimado", f"R$ {custo_total:,.2f}",
                      delta=f"R$ {custo_unitario:.2f}/cartão")

        # Explicação da vantagem de mais números
        if qtd_numeros >= 7:
            from math import comb
            st.success(f"""
            📈 Com **{qtd_numeros} números** por cartão, você tem **{comb(qtd_numeros, 4)} combinações**
            de quadra possíveis (vs {comb(6, 4)} com 6 números = **{comb(qtd_numeros, 4)/comb(6,4):.1f}x mais chances**).
            """)

        st.markdown("---")

        # Botão principal
        if st.button("🚀 TREINAR ML E GERAR CARTÕES", type="primary", width="stretch"):
            with st.spinner("🔄 Treinando modelos para todos os 60 números..."):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def atualizar_progresso(numero):
                        progress_bar.progress(numero / 60)
                        status_text.text(f"⚙️ Treinando modelo para número {numero}/60...")

                    # ETAPA 1: Treinar modelos para todos os números
                    probabilidades, modelos_info = calcular_probabilidades_todos_numeros(
                        df, n_concursos, progress_callback=atualizar_progresso
                    )

                    progress_bar.progress(100)
                    status_text.text("✅ Modelos treinados! Gerando cartões otimizados...")

                    # Salvar probabilidades no session_state
                    st.session_state['automl_probabilidades'] = probabilidades
                    st.session_state['automl_modelos_info'] = modelos_info
                    st.session_state['automl_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # ETAPA 2: Calcular estatísticas tradicionais
                    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)

                    # ETAPA 3: Gerar cartões otimizados
                    cartoes_gerados, scores = gerar_cartoes_otimizados(
                        probabilidades, contagem_total, contagem_recente,
                        df_atrasos, qtd_cartoes, qtd_numeros, concurso_alvo
                    )

                    st.session_state['automl_scores'] = scores
                    st.session_state['automl_ultimo_cartoes'] = cartoes_gerados

                    # Salvar cartões
                    cartoes_existentes = dm.carregar_cartoes_salvos()
                    cartoes_existentes.extend(cartoes_gerados)

                    if dm.salvar_cartoes(cartoes_existentes):
                        status_text.empty()
                        progress_bar.empty()

                        st.success(f"✅ **{qtd_cartoes} cartões gerados e salvos com sucesso!**")
                        st.balloons()

                        # Resumo dos resultados
                        st.markdown("---")
                        st.markdown("### 📊 Resumo da Geração")

                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)

                        with col_r1:
                            st.metric("🎲 Cartões Gerados", qtd_cartoes)
                        with col_r2:
                            st.metric("🔢 Números/Cartão", qtd_numeros)
                        with col_r3:
                            todos_nums = set()
                            for c in cartoes_gerados:
                                todos_nums.update(c['dezenas'])
                            st.metric("🎯 Números Únicos", len(todos_nums))
                        with col_r4:
                            cobertura = len(todos_nums) / 60 * 100
                            st.metric("📈 Cobertura", f"{cobertura:.0f}%")

                        # Top 10 números mais prováveis
                        st.markdown("### 🏆 Top 10 Números Mais Prováveis (ML)")
                        top10 = sorted(probabilidades.items(), key=lambda x: x[1], reverse=True)[:10]
                        cols = st.columns(10)
                        for idx, (num, prob) in enumerate(top10):
                            with cols[idx]:
                                st.metric(f"#{idx+1}", f"{num:02d}", f"{prob:.1%}")

                        # Mostrar cartões
                        st.markdown("### 🎲 Cartões Gerados")
                        for i, cartao in enumerate(cartoes_gerados, 1):
                            col_n, col_d, col_s = st.columns([0.5, 4, 1.5])
                            with col_n:
                                st.write(f"**#{i}**")
                            with col_d:
                                nums_str = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
                                st.code(nums_str)
                            with col_s:
                                st.caption(f"Score ML: {cartao.get('score_ml', 0):.1f}")
                    else:
                        st.error("❌ Erro ao salvar cartões")

                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
                    import traceback
                    with st.expander("🔍 Detalhes do Erro"):
                        st.code(traceback.format_exc())

        # Se já tem cartões gerados, mostrar
        elif 'automl_ultimo_cartoes' in st.session_state:
            cartoes_gerados = st.session_state['automl_ultimo_cartoes']
            probabilidades = st.session_state.get('automl_probabilidades', {})

            st.success(f"✅ Última geração: {len(cartoes_gerados)} cartões em {st.session_state.get('automl_timestamp', 'N/A')}")

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("🎲 Cartões", len(cartoes_gerados))
            with col_r2:
                todos_nums = set()
                for c in cartoes_gerados:
                    todos_nums.update(c['dezenas'])
                st.metric("🎯 Números Únicos", len(todos_nums))
            with col_r3:
                st.metric("📈 Cobertura", f"{len(todos_nums)/60*100:.0f}%")

            st.markdown("### 🎲 Cartões Gerados")
            for i, cartao in enumerate(cartoes_gerados, 1):
                col_n, col_d, col_s = st.columns([0.5, 4, 1.5])
                with col_n:
                    st.write(f"**#{i}**")
                with col_d:
                    nums_str = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
                    st.code(nums_str)
                with col_s:
                    st.caption(f"Score: {cartao.get('score_ml', 0):.1f}")

    # ==========================================================================
    # TAB 2: RANKING DE NÚMEROS
    # ==========================================================================
    with tab_ranking:
        st.markdown("## 📊 Ranking de Probabilidades por ML")

        if 'automl_probabilidades' not in st.session_state:
            st.warning("⚠️ **Treine os modelos primeiro!**")
            st.info("👈 Vá para a aba 'Gerar Cartões' e clique em 'Treinar ML e Gerar Cartões'.")
            return

        probabilidades = st.session_state['automl_probabilidades']
        timestamp = st.session_state.get('automl_timestamp', 'N/A')

        st.caption(f"📅 Treinamento em: {timestamp}")

        # Criar DataFrame do ranking
        ranking_data = []
        for num in range(1, 61):
            prob = probabilidades.get(num, 0)
            ranking_data.append({
                'Número': f"{num:02d}",
                'Probabilidade': prob,
                'Prob %': f"{prob:.1%}",
                'Classificação': '🔥 Alto' if prob >= 0.15 else ('⚡ Médio' if prob >= 0.10 else '❄️ Baixo')
            })

        df_ranking = pd.DataFrame(ranking_data)
        df_ranking = df_ranking.sort_values('Probabilidade', ascending=False).reset_index(drop=True)
        df_ranking.index = df_ranking.index + 1
        df_ranking.index.name = 'Rank'

        # Métricas rápidas
        col1, col2, col3 = st.columns(3)
        with col1:
            altos = len([r for r in ranking_data if r['Probabilidade'] >= 0.15])
            st.metric("🔥 Prob. Alta (≥15%)", altos)
        with col2:
            medios = len([r for r in ranking_data if 0.10 <= r['Probabilidade'] < 0.15])
            st.metric("⚡ Prob. Média (10-15%)", medios)
        with col3:
            baixos = len([r for r in ranking_data if r['Probabilidade'] < 0.10])
            st.metric("❄️ Prob. Baixa (<10%)", baixos)

        # Tabela
        st.dataframe(df_ranking[['Número', 'Prob %', 'Classificação']],
                     width="stretch", height=500)

        # Gráfico
        import plotly.express as px

        df_plot = df_ranking.head(30).copy()
        df_plot['Probabilidade_pct'] = df_plot['Probabilidade'] * 100

        fig = px.bar(
            df_plot,
            x='Número',
            y='Probabilidade_pct',
            color='Probabilidade_pct',
            color_continuous_scale='RdYlGn',
            title='Top 30 Números - Probabilidade de Sair (ML)',
            labels={'Probabilidade_pct': 'Probabilidade (%)', 'Número': 'Número'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch")

    # ==========================================================================
    # TAB 3: HISTÓRICO
    # ==========================================================================
    with tab_historico:
        st.markdown("## 📋 Histórico de Cartões AutoML")

        todos_cartoes = dm.carregar_cartoes_salvos()
        cartoes_automl = [c for c in todos_cartoes if c.get('estrategia') == 'automl']

        if cartoes_automl:
            st.metric("📋 Total de Cartões AutoML", len(cartoes_automl))

            # Agrupar por concurso alvo
            por_concurso = {}
            for cartao in cartoes_automl:
                conc = cartao.get('concurso_alvo', 'N/A')
                if conc not in por_concurso:
                    por_concurso[conc] = []
                por_concurso[conc].append(cartao)

            st.markdown("### 📋 Cartões por Concurso Alvo")

            for concurso, cartoes in sorted(por_concurso.items(), key=lambda x: x[0] if x[0] is not None else 0, reverse=True):
                with st.expander(f"🏁 Concurso {concurso} - {len(cartoes)} cartões"):
                    for i, cartao in enumerate(cartoes, 1):
                        col1, col2, col3 = st.columns([0.5, 4, 1.5])
                        with col1:
                            st.write(f"**#{i}**")
                        with col2:
                            nums = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
                            st.code(nums)
                        with col3:
                            st.caption(f"📅 {cartao.get('data_criacao', 'N/A')[:10]}")
                            if 'score_ml' in cartao:
                                st.caption(f"🎯 Score: {cartao['score_ml']}")

            # Botão para limpar histórico AutoML
            st.markdown("---")
            if st.button("🗑️ Limpar Cartões AutoML", type="secondary"):
                cartoes_sem_automl = [c for c in todos_cartoes if c.get('estrategia') != 'automl']
                if dm.salvar_cartoes(cartoes_sem_automl):
                    st.success("✅ Cartões AutoML removidos!")
                    st.rerun()
        else:
            st.info("📭 Nenhum cartão AutoML gerado ainda.")
            st.markdown("👉 Vá para a aba **'Gerar Cartões'** para criar seus cartões com ML!")
