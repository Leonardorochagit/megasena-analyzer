"""
================================================================================
📊 PÁGINA: ANÁLISE ESCADA TEMPORAL + GERADOR DE CARTÕES
================================================================================
Interface focada em visualização e geração de jogos
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules import data_manager as dm
from modules import statistics as stats
from modules import visualizations as viz
from modules import game_generator as gen
from helpers import converter_dezenas_para_int


def pagina_escada_temporal(df):
    """
    Página da Análise Escada Temporal com geração de cartões

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
    """
    st.title("🔄 Análise Escada Temporal")
    st.markdown("### Inversões de Tendência - Números Esquentando e Esfriando")

    # =========================================================================
    # CONFIGURAÇÕES E ATUALIZAÇÃO
    # =========================================================================
    col_config, col_atualizar = st.columns([3, 1])

    with col_config:
        with st.expander("⚙️ Configurações da Análise", expanded=False):
            janela_recente = st.slider(
                "Janela de jogos recentes",
                min_value=20,
                max_value=200,
                value=50,
                step=10,
                help="Quantidade de jogos recentes para comparar com o histórico total"
            )

    with col_atualizar:
        st.markdown("###")  # Espaçamento
        if st.button("🔄 Atualizar Dados", help="Limpa cache e recarrega dados da API"):
            dm.limpar_cache()
            st.success("✅ Dados atualizados!")
            st.rerun()
    with st.spinner("🔄 Calculando análise escada temporal..."):
        freq_total, freq_recente, freq_total_norm, freq_recente_norm, variacao, inversoes = \
            stats.calcular_escada_temporal(df, janela_recente=janela_recente)

    # =========================================================================
    # GRÁFICO DE FREQUÊNCIA TOTAL
    # =========================================================================
    st.markdown("---")
    st.subheader("📊 Frequência Total dos Números")
    st.caption(f"Baseado em {len(df)} concursos históricos")

    # Gráfico principal
    fig = viz.criar_grafico_frequencia(freq_total)
    st.plotly_chart(fig, width='stretch')

    # Estatísticas rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Média de Saídas", f"{freq_total.mean():.1f}")
    with col2:
        mais_frequente = freq_total.idxmax()
        st.metric("Mais Frequente",
                  f"Nº {mais_frequente:02d}", f"{freq_total[mais_frequente]} vezes")
    with col3:
        menos_frequente = freq_total.idxmin()
        st.metric("Menos Frequente",
                  f"Nº {menos_frequente:02d}", f"{freq_total[menos_frequente]} vezes")
    with col4:
        st.metric("Inversões Detectadas", len(inversoes))

    # =========================================================================
    # ABAS PRINCIPAIS
    # =========================================================================
    st.markdown("---")

    tab_sugestoes, tab_manual, tab_auto, tab_verificar = st.tabs([
        "💡 Sugestões de Números",
        "✍️ Geração Manual",
        "🤖 Geração Automática",
        "🎯 Verificar Resultados"
    ])

    # -------------------------------------------------------------------------
    # TAB: SUGESTÕES DE NÚMEROS
    # -------------------------------------------------------------------------
    with tab_sugestoes:
        st.subheader("💡 Números Sugeridos - Análise Escada")
        st.caption("Números com inversão de tendência detectada")

        if not inversoes:
            st.info(
                "Nenhuma inversão detectada com a janela atual. Tente ajustar a configuração.")
        else:
            # Explicação
            st.markdown("""
            ### 📊 Como interpretar:
            
            Estes números estavam **"frios"** (saíam pouco) no histórico total, 
            mas agora estão **"quentes"** (saindo muito) nos últimos jogos.
            
            **Variação positiva** = Número está esquentando 🔥
            """)

            st.markdown("---")

            # Mostrar top 15 inversões com detalhes
            st.markdown("### 🎯 Top 15 Candidatos")

            for i, inv in enumerate(inversoes[:15], 1):
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 2, 2, 3])

                    with col1:
                        if i <= 3:
                            medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                            st.markdown(f"### {medalha}")
                        else:
                            st.markdown(f"### #{i}")

                    with col2:
                        st.markdown(f"### Nº {inv['numero']:02d}")

                    with col3:
                        cor = "🔥" if inv['variacao'] > 1.0 else "📈"
                        st.metric(
                            "Variação", f"{inv['variacao']:+.2f}%", delta=cor)

                    with col4:
                        # Explicação detalhada
                        freq_t = inv['freq_total']
                        freq_r = inv['freq_recente']

                        if inv['variacao'] > 1.5:
                            status = "🔥 Esquentando FORTE!"
                        elif inv['variacao'] > 0.8:
                            status = "📈 Tendência positiva clara"
                        else:
                            status = "💡 Inversão detectada"

                        st.markdown(f"""
                        **{status}**  
                        Total: {freq_t} saídas | Recente: {freq_r} saídas
                        """)

                    st.markdown("---")

            # Resumo final
            st.success(f"""
            ✅ **{len(inversoes)} números** identificados com inversão de tendência!
            
            💡 **Dica:** Use a estratégia "Escada" na geração automática para priorizar estes números.
            """)

    # -------------------------------------------------------------------------
    # TAB: GERAÇÃO MANUAL
    # -------------------------------------------------------------------------
    with tab_manual:
        st.markdown("#### Crie seu cartão manualmente")

        # Linha para quantidade de números
        col_qtd, col_info = st.columns([1, 2])

        with col_qtd:
            qtd_numeros_manual = st.select_slider(
                "🔢 Quantidade de números",
                options=list(range(6, 21)),
                value=10,
                help="Escolha quantos números terá seu cartão (6 a 20)"
            )

        with col_info:
            st.info(f"""
            **{qtd_numeros_manual} números selecionados**
            
            💰 Custo aproximado: R$ {_calcular_custo(qtd_numeros_manual):.2f}
            🎯 Combinações: {_calcular_combinacoes(qtd_numeros_manual):,}
            """)

        st.markdown("---")

        # Botão para usar sugestões automáticas com variação
        col_btn_sugestao, col_btn_limpar, col_info_variacao = st.columns([
                                                                         1, 1, 1])

        with col_btn_sugestao:
            if st.button("✨ Gerar Sugestão Variada", help="Gera combinações diferentes a cada clique", type="primary"):
                import random

                # Contador de sugestões para variar
                if 'contador_sugestoes' not in st.session_state:
                    st.session_state['contador_sugestoes'] = 0
                st.session_state['contador_sugestoes'] += 1

                contador = st.session_state['contador_sugestoes']

                if inversoes:
                    # Criar pool de candidatos baseado na iteração
                    if contador % 3 == 1:
                        # Primeira sugestão: Top inversões
                        candidatos = [inv['numero']
                                      for inv in inversoes[:min(20, len(inversoes))]]
                        st.session_state['ultima_sugestao'] = "Top Inversões"
                    elif contador % 3 == 2:
                        # Segunda sugestão: Mix inversões + quentes
                        top_inv = [inv['numero']
                                   for inv in inversoes[:min(10, len(inversoes))]]
                        # Pegar números mais frequentes recentemente
                        quentes = [n for n in freq_recente.nlargest(
                            15).index.tolist() if n not in top_inv]
                        candidatos = top_inv + quentes
                        st.session_state['ultima_sugestao'] = "Mix Inversões + Quentes"
                    else:
                        # Terceira sugestão: Variação mais ampla
                        meio_inv = [inv['numero']
                                    for inv in inversoes[5:min(25, len(inversoes))]]
                        outros = [n for n in range(1, 61) if n not in meio_inv]
                        random.shuffle(outros)
                        candidatos = meio_inv + outros[:10]
                        st.session_state['ultima_sugestao'] = "Variação Ampla"

                    # Selecionar quantidade necessária de forma aleatória
                    random.shuffle(candidatos)
                    numeros_sugeridos = sorted(candidatos[:qtd_numeros_manual])
                    st.session_state['numeros_selecionados_manual'] = numeros_sugeridos
                    st.rerun()
                else:
                    st.warning(
                        "⚠️ Nenhuma inversão detectada. Use a geração automática.")

        with col_btn_limpar:
            if st.button("🗑️ Limpar Seleção"):
                if 'numeros_selecionados_manual' in st.session_state:
                    del st.session_state['numeros_selecionados_manual']
                if 'contador_sugestoes' in st.session_state:
                    st.session_state['contador_sugestoes'] = 0
                st.rerun()

        with col_info_variacao:
            if 'ultima_sugestao' in st.session_state:
                st.info(f"🎲 {st.session_state['ultima_sugestao']}")

        st.markdown("---")

        # Inicializar seleção do session state se existir
        if 'numeros_selecionados_manual' not in st.session_state:
            st.session_state['numeros_selecionados_manual'] = []

        numeros_selecionados = st.session_state['numeros_selecionados_manual']

        # Criar grid visual de números
        st.markdown("##### 🎯 Clique nos números para selecionar/desselecionar:")

        # Criar 6 linhas com 10 números cada
        for linha in range(6):
            cols = st.columns(10)
            for i, col in enumerate(cols):
                numero = linha * 10 + i + 1
                with col:
                    # Verificar se é número sugerido
                    is_sugerido = any(
                        inv['numero'] == numero for inv in inversoes[:15]) if inversoes else False
                    is_selecionado = numero in numeros_selecionados

                    # Definir estilo do botão
                    if is_selecionado:
                        tipo = "primary"
                        label = f"✓ {numero:02d}"
                    elif is_sugerido:
                        tipo = "secondary"
                        label = f"⭐ {numero:02d}"
                    else:
                        label = f"{numero:02d}"
                        tipo = "secondary"

                    # Botão do número
                    if st.button(label, key=f"num_{numero}", type=tipo, width="stretch"):
                        if numero in numeros_selecionados:
                            numeros_selecionados.remove(numero)
                        else:
                            if len(numeros_selecionados) < qtd_numeros_manual:
                                numeros_selecionados.append(numero)
                            else:
                                st.warning(
                                    f"⚠️ Você já selecionou {qtd_numeros_manual} números!")
                        st.session_state['numeros_selecionados_manual'] = sorted(
                            numeros_selecionados)
                        st.rerun()

        # Legenda
        st.caption(
            "⭐ = Números sugeridos pela análise | ✓ = Números selecionados")

        st.markdown("---")

        # Mostrar seleção atual
        col_sel, col_status = st.columns([2, 1])

        with col_sel:
            st.markdown("##### 📊 Números Selecionados:")
            if numeros_selecionados:
                # Mostrar números selecionados em grade organizada
                nums_formatados = " - ".join(
                    [f"**{n:02d}**" for n in sorted(numeros_selecionados)])
                st.markdown(nums_formatados)
            else:
                st.info(
                    f"Clique nos números acima para selecionar {qtd_numeros_manual} dezenas")

        with col_status:
            # Validar e mostrar status
            if numeros_selecionados:
                if len(numeros_selecionados) < qtd_numeros_manual:
                    st.warning(
                        f"⚠️ Faltam **{qtd_numeros_manual - len(numeros_selecionados)}**")
                elif len(numeros_selecionados) > qtd_numeros_manual:
                    st.error(
                        f"❌ **{len(numeros_selecionados) - qtd_numeros_manual}** a mais")
                else:
                    st.success(f"✅ **Completo!**")

            st.metric("Selecionados",
                      f"{len(numeros_selecionados)}/{qtd_numeros_manual}")

        st.markdown("---")

        # Configurações do cartão
        col_conf1, col_conf2 = st.columns(2)
        with col_conf1:
            concurso_alvo_manual = st.number_input(
                "Concurso alvo",
                min_value=1,
                max_value=9999,
                value=len(df) + 1,
                step=1,
                help="Concurso que você pretende jogar"
            )
        with col_conf2:
            marcar_jogar_manual = st.checkbox(
                "Marcar para jogar",
                value=True,
                help="Se marcado, o cartão já entra na conferência do concurso escolhido"
            )

        # Botão para salvar cartão manual
        if st.button("💾 Salvar Cartão Manual", type="primary", width="stretch"):
            if len(numeros_selecionados) == qtd_numeros_manual:
                # Criar cartão
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                cartao = {
                    'id': f'MANUAL-{timestamp}',
                    'dezenas': sorted(numeros_selecionados),
                    'estrategia': 'Manual',
                    'vai_jogar': marcar_jogar_manual,
                    'verificado': False,
                    'concurso_alvo': int(concurso_alvo_manual),
                    'status': 'não_marcado',
                    'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'qtd_numeros': qtd_numeros_manual
                }

                # Carregar cartões existentes e adicionar novo
                cartoes_existentes = dm.carregar_cartoes_salvos()

                # Verificar se já existe cartão idêntico (proteção contra duplicatas)
                cartao_duplicado = any(
                    c.get('dezenas') == cartao['dezenas'] and
                    c.get('estrategia') == 'Manual' and
                    c.get('qtd_numeros') == qtd_numeros_manual
                    for c in cartoes_existentes
                )

                if cartao_duplicado:
                    st.warning(
                        "⚠️ Você já tem um cartão manual idêntico a este! Selecione números diferentes.")
                else:
                    cartoes_existentes.append(cartao)

                    # Salvar
                    if dm.salvar_cartoes(cartoes_existentes):
                        st.success(
                            f"✅ 1 cartão manual salvo com {qtd_numeros_manual} números!")
                        st.balloons()
                        # Limpar seleção para permitir criar outro cartão
                        st.session_state['numeros_selecionados_manual'] = []
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar cartão")
            else:
                st.error(
                    f"❌ Selecione exatamente {qtd_numeros_manual} números!")

        st.markdown("---")

        # Mostrar cartões manuais salvos
        cartoes_salvos = dm.carregar_cartoes_salvos()
        cartoes_manuais = [c for c in cartoes_salvos if c.get(
            'estrategia') == 'Manual']

        if cartoes_manuais:
            st.subheader(f"📋 Cartões Manuais Salvos ({len(cartoes_manuais)})")
            st.caption("Cada linha é UM cartão criado manualmente")

            with st.expander("👀 Visualizar e configurar cartões manuais", expanded=True):
                for i, cartao in enumerate(cartoes_manuais, 1):
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns(
                            [1, 3, 2, 1, 1])

                        with col1:
                            st.markdown(f"**#{i}**")
                            qtd = cartao.get(
                                'qtd_numeros', len(cartao['dezenas']))
                            st.caption(f"{qtd} nums")

                        with col2:
                            nums = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
                            st.code(nums)

                        with col3:
                            # Seletor de concurso alvo
                            concurso_atual = cartao.get('concurso_alvo', None)
                            novo_concurso = st.number_input(
                                "Concurso alvo",
                                min_value=1,
                                max_value=9999,
                                value=concurso_atual if concurso_atual else len(
                                    df) + 1,
                                step=1,
                                key=f"concurso_manual_{cartao['id']}"
                            )

                            # Atualizar se mudou
                            if novo_concurso != concurso_atual:
                                cartao['concurso_alvo'] = novo_concurso
                                if dm.salvar_cartoes(cartoes_salvos):
                                    st.success("✅")

                        with col4:
                            # Marcar se vai jogar
                            vai_jogar = st.checkbox(
                                "Vai jogar?",
                                value=cartao.get('vai_jogar', False),
                                key=f"vai_jogar_manual_{cartao['id']}"
                            )

                            if vai_jogar != cartao.get('vai_jogar', False):
                                cartao['vai_jogar'] = vai_jogar
                                if dm.salvar_cartoes(cartoes_salvos):
                                    st.success("✅")

                        with col5:
                            # Botão para deletar este cartão
                            if st.button("🗑️", key=f"del_manual_{cartao['id']}", help="Remover este cartão"):
                                cartoes_salvos.remove(cartao)
                                if dm.salvar_cartoes(cartoes_salvos):
                                    st.success("✅ Removido!")
                                    st.rerun()

                        st.markdown("---")

                # Botão para limpar todos os cartões manuais
                if st.button("🗑️ Limpar Todos os Cartões Manuais", type="secondary"):
                    cartoes_restantes = [
                        c for c in cartoes_salvos if c.get('estrategia') != 'Manual']
                    if dm.salvar_cartoes(cartoes_restantes):
                        st.success(
                            "✅ Todos os cartões manuais foram removidos!")
                        st.rerun()

    # -------------------------------------------------------------------------
    # TAB: GERAÇÃO AUTOMÁTICA
    # -------------------------------------------------------------------------
    with tab_auto:
        st.markdown(
            "#### Gere cartões automaticamente usando estratégias estatísticas")

        # Primeira linha: estratégia
        estrategia = st.selectbox(
            "📊 Estratégia",
            options=['escada', 'atrasados', 'quentes',
                     'equilibrado', 'misto', 'consenso', 'aleatorio_smart'],
            format_func=lambda x: {
                'escada': '🔄 Escada Temporal',
                'atrasados': '⏰ Números Atrasados',
                'quentes': '🔥 Números Quentes',
                'equilibrado': '⚖️ Equilibrado',
                'misto': '🎨 Misto',
                'consenso': '🤝 Consenso',
                'aleatorio_smart': '🎲 Aleatório Inteligente'
            }[x],
            index=0
        )

        # Informações sobre a estratégia selecionada
        st.info(f"""
        **{estrategia.upper()}**: {_descricao_estrategia(estrategia)}
        """)

        st.markdown("---")

        # Segunda linha: configurações de geração
        col1, col2, col3 = st.columns(3)

        with col1:
            qtd_numeros = st.select_slider(
                "🔢 Números por cartão",
                options=list(range(6, 21)),
                value=10,
                help="Quantidade de números em cada cartão (6 a 20)"
            )

        with col2:
            qtd_cartoes = st.number_input(
                "📋 Quantidade de cartões",
                min_value=1,
                max_value=50,
                value=10,
                step=1,
                help="Quantos cartões serão gerados automaticamente"
            )

        with col3:
            st.metric(
                "💰 Custo/cartão",
                f"R$ {_calcular_custo(qtd_numeros):.2f}",
                help="Custo aproximado por cartão"
            )
            st.caption(f"🎯 {_calcular_combinacoes(qtd_numeros):,} combinações")

        st.markdown("---")

        # Resumo da geração
        st.info(f"""
        ℹ️ **Como funciona:**
        - Clique em "Gerar e Salvar Cartões" 
        - Os cartões serão **automaticamente salvos**
        - Você poderá visualizá-los e configurá-los na aba "Verificar Resultados"
        """)

        st.markdown(f"""
        ### 📊 Resumo da Geração
        - **{qtd_cartoes} cartões** serão gerados e salvos
        - Cada cartão terá **{qtd_numeros} números**
        - Estratégia: **{estrategia.upper()}**
        - Custo total aproximado: **R$ {qtd_cartoes * _calcular_custo(qtd_numeros):.2f}**
        """)

        # Botão para gerar cartões
        col_btn1, col_btn2 = st.columns(2)

        # Configuração de concurso e flag
        col_conf1, col_conf2 = st.columns(2)
        with col_conf1:
            concurso_alvo_auto = st.number_input(
                "Concurso alvo",
                min_value=1,
                max_value=9999,
                value=len(df) + 1,
                step=1,
                help="Concurso que você pretende jogar com estes cartões"
            )
        with col_conf2:
            marcar_jogar_auto = st.checkbox(
                "Marcar para jogar",
                value=True,
                help="Se marcado, os cartões já entram na conferência do concurso escolhido"
            )

        # Use first column for the main generation button
        with col_btn1:
            if st.button("🎲 Gerar e Salvar Cartões", type="primary", width="stretch"):
                with st.spinner(f"Gerando {qtd_cartoes} cartões com estratégia {estrategia}..."):
                    # Calcular estatísticas necessárias
                    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(
                        df)

                    # Gerar cartões
                    novos_cartoes = []
                    for i in range(qtd_cartoes):
                        # Gerar jogo base com 6 números
                        dezenas_base = gen.gerar_jogo(
                            estrategia=estrategia,
                            contagem_total=contagem_total,
                            contagem_recente=contagem_recente,
                            df_atrasos=df_atrasos,
                            df=df
                        )

                        # Se precisar de mais números, adicionar baseado na estratégia
                        if qtd_numeros > 6:
                            # Obter candidatos baseado na estratégia
                            pool_size = max(40, qtd_numeros + 10)
                            if estrategia == 'atrasados':
                                candidatos = contagem_total.sort_values().head(pool_size).index.tolist()
                            elif estrategia == 'quentes':
                                candidatos = contagem_recente.head(
                                    pool_size).index.tolist()
                            elif estrategia == 'escada':
                                _, _, _, _, _, inversoes = stats.calcular_escada_temporal(
                                    df)
                                candidatos = [inv['numero'] for inv in inversoes[:pool_size]] if inversoes else list(
                                    range(1, 61))
                            else:
                                candidatos = list(range(1, 61))

                            # Remover números já selecionados
                            candidatos = [
                                n for n in candidatos if n not in dezenas_base]

                            # Adicionar números extras
                            import random
                            numeros_extras = random.sample(
                                candidatos, min(qtd_numeros - 6, len(candidatos)))
                            dezenas = sorted(dezenas_base + numeros_extras)
                        else:
                            dezenas = dezenas_base

                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        cartao = {
                            'id': f'{estrategia.upper()}-{timestamp}-{i+1:02d}',
                            'dezenas': sorted(dezenas),
                            'estrategia': estrategia,
                            'vai_jogar': marcar_jogar_auto,
                            'verificado': False,
                            'concurso_alvo': int(concurso_alvo_auto),
                            'status': 'não_marcado',
                            'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'qtd_numeros': qtd_numeros
                        }
                        novos_cartoes.append(cartao)

                    # Carregar existentes e adicionar novos
                    cartoes_existentes = dm.carregar_cartoes_salvos()
                    cartoes_existentes.extend(novos_cartoes)

                    # Salvar todos
                    if dm.salvar_cartoes(cartoes_existentes):
                        st.success(
                            f"✅ {qtd_cartoes} cartões gerados e salvos com sucesso!")
                        st.balloons()

                        # Mostrar preview dos cartões gerados
                        with st.expander("👀 Visualizar todos os cartões gerados", expanded=True):
                            # Mostrar TODOS os cartões
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

        with col_btn2:
            # Botão para ver cartões salvos
            total_salvos = len(dm.carregar_cartoes_salvos())
            if st.button(f"📂 Ver Cartões Salvos ({total_salvos})"):
                st.session_state['navegar_para'] = 'verificar_resultados'
                st.rerun()

    # -------------------------------------------------------------------------
    # TAB: VERIFICAR RESULTADOS
    # -------------------------------------------------------------------------
    with tab_verificar:
        st.markdown("#### 🎯 Verificação de Resultados - Estratégia Escada")

        # Buscar último concurso automaticamente
        ultimo_concurso = len(df)

        col1, col2 = st.columns([2, 1])

        with col1:
            concurso_verificar = st.number_input(
                "Número do concurso para verificar",
                min_value=1,
                max_value=9999,
                value=ultimo_concurso,
                step=1,
                help="Digite o número do concurso ou deixe o último"
            )

        with col2:
            if st.button("🔍 Buscar Resultado", type="primary", width="stretch"):
                st.session_state['atualizar_resultado'] = True
                st.rerun()

        # Buscar resultado automaticamente ao abrir
        if 'resultado_verificado' not in st.session_state or st.session_state.get('atualizar_resultado', False):
            with st.spinner(f"Buscando resultado do concurso {concurso_verificar}..."):
                max_concurso_df = int(df['concurso'].max()) if 'concurso' in df.columns else len(df)

                if concurso_verificar > max_concurso_df:
                    dezenas_api = dm.buscar_resultado_concurso(concurso_verificar)
                    if dezenas_api:
                        resultado = {
                            'dezenas': dezenas_api,
                            'data': 'N/A'
                        }
                    else:
                        st.warning(f"⚠️ Resultado do concurso {concurso_verificar} ainda não disponível.")
                        st.session_state['resultado_verificado'] = None
                        st.session_state['concurso_verificado'] = concurso_verificar
                        if 'atualizar_resultado' in st.session_state:
                            del st.session_state['atualizar_resultado']
                        st.stop()
                else:
                    # Buscar diretamente do dataframe
                    data_val = df.iloc[concurso_verificar -
                                       1]['data'] if 'data' in df.columns else 'N/A'
                    if hasattr(data_val, 'strftime'):
                        data_formatada = data_val.strftime("%d/%m/%Y")
                    else:
                        data_formatada = str(data_val)

                    dezenas_raw = df.iloc[concurso_verificar - 1]['dezenas']
                    dezenas_int = converter_dezenas_para_int(dezenas_raw)

                    resultado = {
                        'dezenas': dezenas_int,
                        'data': data_formatada
                    }

                st.session_state['resultado_verificado'] = resultado
                st.session_state['concurso_verificado'] = concurso_verificar
                if 'atualizar_resultado' in st.session_state:
                    del st.session_state['atualizar_resultado']

        resultado = st.session_state.get('resultado_verificado')

        if resultado and isinstance(resultado, dict) and resultado.get('dezenas'):
            st.success(
                f"✅ Resultado do concurso {concurso_verificar} encontrado!")

            # Mostrar resultado
            col_res1, col_res2 = st.columns([2, 1])

            with col_res1:
                st.markdown("##### 🎲 Números Sorteados:")
                # resultado['dezenas'] já são inteiros após converter_dezenas_para_int
                nums_resultado = " - ".join(
                    [f"**{n:02d}**" for n in sorted(resultado['dezenas'])])
                st.markdown(nums_resultado)

            with col_res2:
                data_sorteio = resultado.get('data', 'N/A')
                st.info(f"📅 Data: {data_sorteio}")

            st.markdown("---")

            # Carregar cartões da estratégia Escada, filtrando pelo concurso alvo selecionado
            todos_cartoes = dm.carregar_cartoes_salvos()
            cartoes_escada = [
                c for c in todos_cartoes
                if c.get('estrategia') in ['escada', 'Manual']
            ]
            cartoes_filtrados = [
                c for c in cartoes_escada
                if c.get('concurso_alvo') == concurso_verificar
            ]

            if not cartoes_filtrados:
                st.info(f"Nenhum cartão marcado para o concurso {concurso_verificar}.")
                return

            if cartoes_filtrados:
                st.subheader(f"📊 Verificação de {len(cartoes_filtrados)} Cartões")

                # Calcular acertos para cada cartão
                # resultado['dezenas'] já é lista de inteiros após converter_dezenas_para_int
                dezenas_resultado_int = resultado['dezenas']
                resultados_cartoes = []
                for cartao in cartoes_filtrados:
                    dezenas_cartao = cartao['dezenas']
                    acertos = len(set(dezenas_cartao) &
                                  set(dezenas_resultado_int))

                    resultados_cartoes.append({
                        'id': cartao['id'],
                        'estrategia': cartao.get('estrategia', 'N/A'),
                        'dezenas': dezenas_cartao,
                        'qtd_numeros': len(dezenas_cartao),
                        'acertos': acertos,
                        'vai_jogar': cartao.get('vai_jogar', False)
                    })

                # Ordenar por acertos (maior para menor)
                resultados_cartoes.sort(
                    key=lambda x: x['acertos'], reverse=True)

                # Métricas gerais
                st.markdown("### 📈 Resumo Geral")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total de Cartões", len(resultados_cartoes))

                with col2:
                    quadras = sum(
                        1 for r in resultados_cartoes if r['acertos'] >= 4)
                    st.metric("Quadras ou +", quadras)

                with col3:
                    quinas = sum(
                        1 for r in resultados_cartoes if r['acertos'] >= 5)
                    st.metric("Quinas ou +", quinas)

                with col4:
                    senas = sum(
                        1 for r in resultados_cartoes if r['acertos'] == 6)
                    if senas > 0:
                        st.metric("🎉 SENAS 🎉", senas)
                    else:
                        st.metric("Senas", senas)

                st.markdown("---")

                # Melhor técnica
                if resultados_cartoes:
                    melhor = resultados_cartoes[0]
                    if melhor['acertos'] >= 4:
                        st.success(f"""
                        🏆 **MELHOR RESULTADO!**
                        - Estratégia: **{melhor['estrategia'].upper()}**
                        - Acertos: **{melhor['acertos']} números**
                        - ID: {melhor['id']}
                        """)

                        nums_melhor = " - ".join(
                            [f"{n:02d}" for n in melhor['dezenas']])
                        st.code(nums_melhor)
                        st.markdown("---")

                # Relatório detalhado por cartão
                st.markdown("### 📋 Relatório Detalhado")

                for i, res in enumerate(resultados_cartoes, 1):
                    with st.expander(
                        f"{'🏆' if res['acertos'] >= 4 else '📄'} Cartão #{i} - {res['estrategia'].upper()} - {res['acertos']} acertos",
                        expanded=(res['acertos'] >= 4)
                    ):
                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            st.markdown("**Números do Cartão:**")
                            nums = " - ".join([f"{n:02d}" for n in res['dezenas']])
                            st.code(nums)

                        with col2:
                            st.metric("Acertos", res['acertos'])
                            st.caption(f"{res['qtd_numeros']} números")

                        with col3:
                            if res['vai_jogar']:
                                st.success("✓ Vai jogar")
                            else:
                                st.info("Teste")

                        # Mostrar números acertados
                        if res['acertos'] > 0:
                            acertados = sorted(
                                set(res['dezenas']) & set(dezenas_resultado_int))
                            st.markdown(
                                f"**Números acertados:** {' - '.join([f'🎯 {n:02d}' for n in acertados])}")

                # Botão para gerar relatório em texto
                st.markdown("---")
                if st.button("📄 Gerar Relatório Completo em Texto"):
                    relatorio = f"""
=================================================================
   RELATÓRIO DE RESULTADOS - MEGA SENA
   Concurso: {concurso_verificar}
   Data: {resultado.get('data', 'N/A')}
=================================================================

RESULTADO DO SORTEIO:
{' - '.join([f'{n:02d}' for n in sorted(resultado['dezenas'])])}

-----------------------------------------------------------------
RESUMO GERAL:
-----------------------------------------------------------------
Total de cartões verificados: {len(resultados_cartoes)}
Quadras ou mais: {quadras}
Quinas ou mais: {quinas}
Senas: {senas}

-----------------------------------------------------------------
MELHOR RESULTADO:
-----------------------------------------------------------------
Estratégia: {melhor['estrategia'].upper()}
Acertos: {melhor['acertos']} números
Números: {' - '.join([f'{n:02d}' for n in melhor['dezenas']])}

-----------------------------------------------------------------
DETALHAMENTO POR CARTÃO:
-----------------------------------------------------------------
"""
                    for i, res in enumerate(resultados_cartoes, 1):
                        acertados = sorted(
                            set(res['dezenas']) & set(resultado['dezenas']))
                        relatorio += f"""
#{i} | {res['estrategia'].upper()} | {res['acertos']} acertos
Números: {' - '.join([f'{n:02d}' for n in res['dezenas']])}
Acertou: {' - '.join([f'{n:02d}' for n in acertados]) if acertados else 'Nenhum'}
{'='*60}
"""

                    st.text_area("Relatório Completo", relatorio, height=400)
                    st.download_button(
                        "💾 Baixar Relatório",
                        relatorio,
                        file_name=f"relatorio_concurso_{concurso_verificar}.txt",
                        mime="text/plain"
                    )
            else:
                st.info(
                    "📭 Nenhum cartão da estratégia Escada encontrado. Gere cartões nas abas acima!")

        elif resultado:
            st.warning(
                f"⚠️ Concurso {concurso_verificar} ainda não foi sorteado ou não encontrado.")
        else:
            st.info(
                "🔍 Busque um concurso para verificar os resultados dos seus cartões.")


def _descricao_estrategia(estrategia):
    """Retorna descrição da estratégia"""
    descricoes = {
        'escada': '🔄 Foca em números que estão invertendo tendência (frios que esquentaram recentemente)',
        'atrasados': '⏰ Prioriza números que há mais tempo não saem',
        'quentes': '🔥 Seleciona números que saíram mais recentemente',
        'equilibrado': '⚖️ Balanceia números quentes, frios e médios',
        'misto': '🎨 Combina diferentes critérios estatísticos',
        'consenso': '🤝 Usa média ponderada de todas as estratégias',
        'aleatorio_smart': '🎲 Aleatório mas respeitando padrões estatísticos',
        'automl': '🤖 Usa Machine Learning (PyCaret) para prever probabilidades de cada número'
    }
    return descricoes.get(estrategia, 'Estratégia baseada em análise estatística')


def _calcular_custo(qtd_numeros):
    """Calcula o custo aproximado do jogo baseado na quantidade de números"""
    # Valores aproximados da Mega-Sena (podem variar)
    custos = {
        6: 6.00,
        7: 42.00,
        8: 168.00,
        9: 504.00,
        10: 1260.00,
        11: 2772.00,
        12: 5544.00,
        13: 10296.00,
        14: 18018.00,
        15: 30030.00,
        16: 48048.00,
        17: 74256.00,
        18: 111384.00,
        19: 162792.00,
        20: 232560.00
    }
    return custos.get(qtd_numeros, 0.0)


def _calcular_combinacoes(qtd_numeros):
    """Calcula quantas combinações de 6 números são geradas"""
    from math import comb
    if qtd_numeros < 6:
        return 0
    return comb(qtd_numeros, 6)
