"""
================================================================================
📊 PÁGINA: RELATÓRIO GERAL E HISTÓRICO
================================================================================
Relatório consolidado com todos os cartões e histórico de análises
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules import data_manager as dm
from modules import visualizations as viz


def _mostrar_cartao_detalhado(numero, cartao, dezenas_sorteadas):
    """Função auxiliar para mostrar um cartão com todos os detalhes"""
    col1, col2, col3, col4 = st.columns([0.5, 4, 1.5, 1])

    with col1:
        st.markdown(f"**#{numero}**")

    with col2:
        nums = " - ".join([f"{n:02d}" for n in cartao['dezenas']])
        st.code(nums)

        if cartao['acertos'] > 0:
            acertados = sorted(set(cartao['dezenas']) & set(dezenas_sorteadas))
            nums_acertados = " ".join([f"✅{n:02d}" for n in acertados])
            st.caption(f"{nums_acertados}")

    with col3:
        # Mostrar info adicional
        st.caption(f"📅 {cartao.get('data_criacao', 'N/A')[:10]}")
        if cartao.get('concurso_alvo'):
            st.caption(f"🎯 Concurso: {cartao['concurso_alvo']}")
        st.caption(f"{cartao.get('tipo', 'N/A').capitalize()}")

    with col4:
        # Badge de acertos
        acertos = cartao['acertos']
        if acertos == 6:
            st.success(f"🎉 **{acertos} acertos**")
        elif acertos >= 4:
            st.warning(f"⭐ **{acertos} acertos**")
        elif acertos > 0:
            st.info(f"{acertos} acertos")
        else:
            st.caption(f"{acertos} acertos")


def _aba_verificar_tudo(df):
    """Verifica automaticamente TODOS os concursos pendentes"""
    st.markdown("### 🔄 Verificação Automática de Todos os Pendentes")
    st.caption("Busca resultados e confere automaticamente todos os cartões que ainda não foram verificados")

    todos_cartoes = dm.carregar_cartoes_salvos()
    
    # Encontrar concursos pendentes
    concursos_pendentes = sorted(set(
        c.get('concurso_alvo') for c in todos_cartoes
        if c.get('concurso_alvo') and not c.get('verificado', False) and c.get('vai_jogar', False)
    ))

    if not concursos_pendentes:
        st.success("✅ Todos os cartões já foram verificados!")
        st.info("💡 Gere novos jogos em 'Simulação & Conferência' para ter mais cartões para conferir.")
        return

    st.info(f"📋 **{len(concursos_pendentes)} concurso(s)** com jogos pendentes: {', '.join(str(c) for c in concursos_pendentes)}")

    # Resumo dos pendentes
    for concurso in concursos_pendentes:
        jogos = [c for c in todos_cartoes if c.get('concurso_alvo') == concurso and not c.get('verificado', False)]
        estrategias = set(c.get('estrategia', 'N/A') for c in jogos)
        st.markdown(f"- Concurso **{concurso}**: {len(jogos)} jogos ({', '.join(estrategias)})")

    st.markdown("---")

    if st.button("🚀 VERIFICAR TODOS AUTOMATICAMENTE", type="primary", width="stretch"):
        progresso = st.progress(0)
        resultados_gerais = {}
        
        for idx, concurso in enumerate(concursos_pendentes):
            progresso.progress((idx) / len(concursos_pendentes))
            
            # Buscar resultado
            resultado_dezenas = None
            max_c = int(df['concurso'].max()) if 'concurso' in df.columns else 0
            
            if concurso <= max_c:
                linha = df[df['concurso'] == concurso]
                if not linha.empty:
                    row = linha.iloc[0]
                    dezenas = []
                    if 'dez1' in df.columns:
                        for i in range(1, 7):
                            try:
                                dezenas.append(int(row.get(f'dez{i}')))
                            except:
                                pass
                    if len(dezenas) == 6:
                        resultado_dezenas = sorted(dezenas)

            if not resultado_dezenas:
                resultado_dezenas = dm.buscar_resultado_concurso(concurso)

            if not resultado_dezenas:
                resultados_gerais[concurso] = {'status': 'pendente', 'jogos': 0}
                continue

            # Conferir jogos
            jogos_concurso = [c for c in todos_cartoes if c.get('concurso_alvo') == concurso and not c.get('verificado', False)]
            stats_est = {}
            
            for jogo in jogos_concurso:
                acertos = len(set(jogo['dezenas']) & set(resultado_dezenas))
                jogo['acertos'] = acertos
                jogo['verificado'] = True
                jogo['resultado_concurso'] = resultado_dezenas
                jogo['data_verificacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                est = jogo.get('estrategia', 'N/A')
                qtd_nums = len(jogo.get('dezenas', []))
                if est not in stats_est:
                    stats_est[est] = {'total_jogos': 0, 'total_acertos': 0, 'senas': 0, 'quinas': 0, 'quadras': 0, 'ternas': 0, 'duques': 0, 'melhor_acerto': 0, 'media_acertos': 0, 'qtd_nums_usadas': []}
                s = stats_est[est]
                s['total_jogos'] += 1
                s['total_acertos'] += acertos
                s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
                if qtd_nums not in s['qtd_nums_usadas']:
                    s['qtd_nums_usadas'].append(qtd_nums)
                if acertos == 6: s['senas'] += 1
                elif acertos == 5: s['quinas'] += 1
                elif acertos == 4: s['quadras'] += 1
                elif acertos == 3: s['ternas'] += 1
                elif acertos == 2: s['duques'] += 1

            for est in stats_est:
                t = stats_est[est]['total_jogos']
                stats_est[est]['media_acertos'] = round(stats_est[est]['total_acertos'] / t, 2) if t > 0 else 0

            resultados_gerais[concurso] = {
                'status': 'verificado',
                'jogos': len(jogos_concurso),
                'resultado': resultado_dezenas,
                'stats': stats_est
            }

            # Arquivar no histórico
            dm.salvar_historico_analise(
                concurso,
                datetime.now().strftime("%Y-%m-%d"),
                stats_est,
                resultado_dezenas
            )

        progresso.progress(1.0)
        
        # Salvar cartões atualizados
        dm.salvar_cartoes(todos_cartoes)

        # Mostrar resultados
        st.markdown("---")
        st.subheader("📊 Resultado da Verificação em Lote")

        for concurso, info in sorted(resultados_gerais.items()):
            if info['status'] == 'pendente':
                st.warning(f"⏳ Concurso {concurso}: resultado ainda não disponível")
            else:
                stats_est = info.get('stats', {})
                total_d = sum(s.get('duques', 0) for s in stats_est.values())
                total_t = sum(s.get('ternas', 0) for s in stats_est.values())
                total_q = sum(s.get('quadras', 0) for s in stats_est.values())
                total_5 = sum(s.get('quinas', 0) for s in stats_est.values())
                total_6 = sum(s.get('senas', 0) for s in stats_est.values())
                melhor = max((s.get('melhor_acerto', 0) for s in stats_est.values()), default=0)
                
                emoji = "🎉" if total_6 > 0 else "⭐" if total_5 > 0 else "🏅" if total_q > 0 else "👍" if total_t > 0 else "✅"
                st.success(
                    f"{emoji} Concurso {concurso}: {info['jogos']} jogos | "
                    f"Melhor: {melhor} | Duques: {total_d} | Ternas: {total_t} | Quadras: {total_q} | Quinas: {total_5} | Senas: {total_6}"
                )

        st.balloons()


def _aba_verificacao_rapida(df):
    """Conferir jogos de um concurso específico"""
    st.markdown("### 🎯 Conferir Resultados")
    st.caption("Digite o número do concurso e confira automaticamente todos os jogos marcados para ele")

    # Configurar concurso
    df_ordenado = df.sort_values('concurso')
    ultimo_concurso = int(df_ordenado['concurso'].max())

    col1, col2 = st.columns([3, 1])
    
    with col1:
        concurso_conferir = st.number_input(
            "📅 Número do concurso",
            min_value=1,
            max_value=9999,
            value=ultimo_concurso,
            step=1,
            key="concurso_conferir",
            help="Digite o concurso que deseja conferir"
        )

    with col2:
        st.markdown("##### ")
        if st.button("🔍 Conferir", type="primary", width="stretch"):
            if 'resultado_conferir' in st.session_state:
                del st.session_state['resultado_conferir']
            st.rerun()
    
    st.markdown("---")

    # Buscar jogos deste concurso
    todos_cartoes = dm.carregar_cartoes_salvos()
    jogos_concurso = [c for c in todos_cartoes if c.get('concurso_alvo') == concurso_conferir]
    
    if not jogos_concurso:
        st.info(f"📭 Nenhum jogo marcado para o concurso {concurso_conferir}.")
        st.markdown("""
        **Como marcar jogos para um concurso?**
        - Vá em **Escada Temporal** ou **Análise de Estratégia**
        - Ao gerar jogos, escolha o concurso alvo
        - Os jogos ficarão disponíveis aqui para conferência
        """)
        return
    
    st.success(f"✅ Encontrados **{len(jogos_concurso)} jogo(s)** marcados para o concurso {concurso_conferir}")

    # Buscar resultado do concurso
    if 'resultado_conferir' not in st.session_state or st.session_state.get('concurso_conferir_num') != concurso_conferir:
        with st.spinner(f"Buscando resultado do concurso {concurso_conferir}..."):
            max_concurso_df = int(df['concurso'].max()) if 'concurso' in df.columns else len(df)

            if concurso_conferir > max_concurso_df:
                # Tentar API para concurso futuro
                dezenas_api = dm.buscar_resultado_concurso(concurso_conferir)
                resultado = {'dezenas': dezenas_api, 'data': 'N/A'} if dezenas_api else None
            else:
                # Buscar do dataframe
                linha = df_ordenado[df_ordenado['concurso'] == concurso_conferir]
                if not linha.empty:
                    row = linha.iloc[0]
                    dezenas_int = []
                    
                    if 'dez1' in df.columns:
                        for i in range(1, 7):
                            try:
                                dezenas_int.append(int(row.get(f'dez{i}')))
                            except:
                                pass
                    else:
                        dezenas_raw = row['dezenas']
                        if isinstance(dezenas_raw, list):
                            dezenas_int = [int(n) for n in dezenas_raw]
                        elif isinstance(dezenas_raw, str):
                            limpo = dezenas_raw.replace('[', '').replace(']', '').replace("'", "").replace('"', '')
                            dezenas_int = [int(n.strip()) for n in limpo.split(',') if n.strip().isdigit()]
                    
                    dezenas_int.sort()
                    data_val = row.get('data', 'N/A')
                    data_formatada = data_val.strftime("%d/%m/%Y") if hasattr(data_val, 'strftime') else str(data_val)
                    
                    resultado = {'dezenas': dezenas_int, 'data': data_formatada} if dezenas_int else None
                else:
                    resultado = None

            st.session_state['resultado_conferir'] = resultado
            st.session_state['concurso_conferir_num'] = concurso_conferir

    resultado = st.session_state.get('resultado_conferir')

    # Mostrar jogos e resultado
    if not resultado or not resultado.get('dezenas'):
        st.warning(f"⏳ Concurso {concurso_conferir} ainda sem resultado disponível")
        
        st.markdown("---")
        st.subheader(f"📋 Jogos Aguardando Sorteio ({len(jogos_concurso)})")
        
        por_estrategia = {}
        for jogo in jogos_concurso:
            est = jogo.get('estrategia', 'Outros')
            por_estrategia.setdefault(est, []).append(jogo)
        
        for estrategia, jogos in por_estrategia.items():
            with st.expander(f"📊 {estrategia} ({len(jogos)} jogos)", expanded=True):
                for i, jogo in enumerate(jogos, 1):
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        nums = " - ".join([f"{n:02d}" for n in jogo['dezenas']])
                        st.code(f"#{i:02d}  {nums}")
                    with col2:
                        if jogo.get('vai_jogar'):
                            st.caption("🎯 Jogar")
        return

    # TEM RESULTADO - CONFERIR!
    st.success(f"✅ Resultado do concurso {concurso_conferir} disponível!")
    
    col_res1, col_res2 = st.columns([3, 1])
    with col_res1:
        st.markdown("#### 🎲 Números Sorteados")
        nums_resultado = " - ".join([f"**{n:02d}**" for n in sorted(resultado['dezenas'])])
        st.markdown(nums_resultado)
    with col_res2:
        st.info(f"📅 {resultado['data']}")

    st.markdown("---")

    # Calcular acertos
    total_quadras = 0
    total_quinas = 0
    total_senas = 0
    
    for jogo in jogos_concurso:
        acertos = len(set(jogo['dezenas']) & set(resultado['dezenas']))
        jogo['acertos'] = acertos
        if acertos == 4: total_quadras += 1
        if acertos == 5: total_quinas += 1
        if acertos == 6: total_senas += 1

    # Métricas
    st.markdown("### 📊 Resultado da Conferência")
    cols = st.columns(4)
    cols[0].metric("Total Jogos", len(jogos_concurso))
    cols[1].metric("Quadras", total_quadras)
    cols[2].metric("Quinas", total_quinas)
    if total_senas > 0:
        cols[3].success(f"🎉 **{total_senas} SENA(S)!**")
    else:
        cols[3].metric("Senas", total_senas)

    st.markdown("---")

    # Detalhamento
    st.subheader("🎯 Detalhamento dos Jogos")
    
    # Ordenar por acertos
    jogos_concurso.sort(key=lambda x: x.get('acertos', 0), reverse=True)
    
    por_estrategia = {}
    for jogo in jogos_concurso:
        est = jogo.get('estrategia', 'Outros')
        por_estrategia.setdefault(est, []).append(jogo)
    
    for estrategia, jogos in por_estrategia.items():
        with st.expander(f"📊 {estrategia} ({len(jogos)} jogos)", expanded=True):
            for i, jogo in enumerate(jogos, 1):
                acertos = jogo.get('acertos', 0)
                
                col1, col2, col3 = st.columns([5, 2, 1])
                
                with col1:
                    nums = " - ".join([f"{n:02d}" for n in jogo['dezenas']])
                    st.code(f"#{i:02d}  {nums}")
                    
                    if acertos > 0:
                        acertados = sorted(set(jogo['dezenas']) & set(resultado['dezenas']))
                        nums_acertados = " ".join([f"✅ {n:02d}" for n in acertados])
                        st.caption(nums_acertados)
                
                with col2:
                    if acertos == 6:
                        st.success(f"🎉 **{acertos} acertos**")
                    elif acertos >= 4:
                        st.warning(f"⭐ **{acertos} acertos**")
                    elif acertos > 0:
                        st.info(f"{acertos} acertos")
                    else:
                        st.caption(f"{acertos} acertos")
                
                with col3:
                    if jogo.get('vai_jogar'):
                        st.caption("🎯 Jogar")
    
    # Marcar jogos como verificados automaticamente
    for jogo in jogos_concurso:
        if not jogo.get('verificado'):
            jogo['verificado'] = True
    dm.salvar_cartoes(todos_cartoes)


def _aba_historico_consolidado():
    """Aba de histórico consolidado"""
    st.markdown("### 📚 Banco de Dados de Performance")
    st.caption("Histórico das análises salvas através da página 'Verificar Resultados'")

    historico = dm.carregar_historico_analises()
    
    if not historico:
        st.info("📭 Nenhum histórico arquivado ainda.")
        st.markdown("""
        **Como arquivar histórico?**
        1. Vá para a página **Verificar Resultados**
        2. Selecione um concurso
        3. Após verificar, clique no botão **Arquivar Resultados no Histórico**
        """)
        return

    # Transformar em DataFrame para facilitar visualização
    dados_tabela = []
    
    for item in historico:
        concurso = item.get('concurso')
        data_analise = item.get('data_analise')
        stats = item.get('estatisticas', {})
        
        # Calcular totais do concurso
        total_jogos = sum(s.get('total_jogos', 0) for s in stats.values())
        total_duques = sum(s.get('duques', 0) for s in stats.values())
        total_ternas = sum(s.get('ternas', 0) for s in stats.values())
        total_quadras = sum(s.get('quadras', 0) for s in stats.values())
        total_quinas = sum(s.get('quinas', 0) for s in stats.values())
        total_senas = sum(s.get('senas', 0) for s in stats.values())
        
        # Estrategias usadas
        estrategias = ", ".join(stats.keys())
        
        dados_tabela.append({
            'Concurso': concurso,
            'Data Análise': data_analise, 
            'Jogos': total_jogos,
            'Duques (2ac)': total_duques,
            'Ternas (3ac)': total_ternas,
            'Quadras': total_quadras,
            'Quinas': total_quinas,
            'Senas': total_senas,
            'Estratégias': estrategias
        })
    
    df_hist = pd.DataFrame(dados_tabela)
    # Ordenar por concurso decrescente
    if not df_hist.empty:
        df_hist = df_hist.sort_values('Concurso', ascending=False)
    
    # Exibir tabela resumo
    colunas_hist = ['Concurso', 'Data Análise', 'Jogos', 'Duques (2ac)', 'Ternas (3ac)', 'Quadras', 'Quinas', 'Senas', 'Estratégias']
    colunas_disponiveis = [c for c in colunas_hist if c in df_hist.columns]
    st.dataframe(
        df_hist[colunas_disponiveis],
        use_container_width=True,
        hide_index=True
    )

    # Ranking geral de estratégias (todas as análises arquivadas)
    st.markdown("#### 🏆 Ranking Geral de Estratégias")
    st.caption("Inclui Duques (2 acertos) e Ternas (3 acertos) — acertos consistentes valem mais que sorte pontual")
    ranking_global = {}
    for item in historico:
        stats = item.get('estatisticas', {})
        for est, dados in stats.items():
            agg = ranking_global.setdefault(est, {
                'jogos': 0,
                'duques': 0,
                'ternas': 0,
                'quadras': 0,
                'quinas': 0,
                'senas': 0,
                'melhor_acerto': 0,
                'qtd_nums': set()
            })
            agg['jogos'] += dados.get('total_jogos', 0)
            agg['duques'] += dados.get('duques', 0)
            agg['ternas'] += dados.get('ternas', 0)
            agg['quadras'] += dados.get('quadras', 0)
            agg['quinas'] += dados.get('quinas', 0)
            agg['senas'] += dados.get('senas', 0)
            agg['melhor_acerto'] = max(agg['melhor_acerto'], dados.get('melhor_acerto', 0))
            for q in dados.get('qtd_nums_usadas', []):
                agg['qtd_nums'].add(q)

    ranking_lista = []
    for est, agg in ranking_global.items():
        qtds = sorted(agg['qtd_nums']) if agg['qtd_nums'] else []
        ranking_lista.append({
            'Estratégia': est,
            'Jogos': agg['jogos'],
            'Nº Números': '/'.join(str(q) for q in qtds) if qtds else '-',
            'Duques (2ac)': agg['duques'],
            'Ternas (3ac)': agg['ternas'],
            'Quadras (4ac)': agg['quadras'],
            'Quinas (5ac)': agg['quinas'],
            'Senas (6ac)': agg['senas'],
            'Melhor Acerto': agg['melhor_acerto']
        })

    # Ordenar: prioriza ternas consistentes, depois quadras, depois melhor acerto
    ranking_lista.sort(key=lambda x: (
        x['Senas (6ac)'], x['Quinas (5ac)'], x['Quadras (4ac)'],
        x['Ternas (3ac)'], x['Duques (2ac)'],
        x['Melhor Acerto'], x['Jogos']
    ), reverse=True)

    if ranking_lista:
        top = ranking_lista[0]
        st.success(
            f"🥇 **{top['Estratégia']}** — "
            f"ternas: {top['Ternas (3ac)']}, quadras: {top['Quadras (4ac)']}, "
            f"melhor acerto: {top['Melhor Acerto']}, jogos: {top['Jogos']} "
            f"({top['Nº Números']} nums)"
        )
    st.dataframe(pd.DataFrame(ranking_lista), hide_index=True, use_container_width=True)

    # Gráficos de tendência e ranking
    ranking_chart_data = {}
    for est, agg in ranking_global.items():
        ranking_chart_data[est] = {
            'quadras': agg['quadras'],
            'ternos': agg['ternas'],
            'senas': agg['senas'],
            'quinas': agg['quinas'],
            'media_acertos': round(agg.get('duques', 0) + agg.get('ternas', 0) * 2 + agg.get('quadras', 0) * 3 + agg.get('quinas', 0) * 5 + agg.get('senas', 0) * 10, 2) / max(agg['jogos'], 1)
        }

    fig_ranking = viz.criar_grafico_ranking_global(ranking_chart_data)
    if fig_ranking:
        st.plotly_chart(fig_ranking, use_container_width=True)

    fig_tendencia = viz.criar_grafico_tendencia_estrategias(historico)
    if fig_tendencia:
        st.markdown("#### 📈 Evolução da Média de Acertos por Estratégia")
        st.plotly_chart(fig_tendencia, use_container_width=True)

    # Botão para exportar HTML
    if st.button("📥 Exportar Histórico Completo em HTML"):
        html = f"""
        <html>
        <head>
            <title>Histórico Mega Sena Analyzer</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                h1 {{ color: #2e86de; }}
                .badge {{ padding: 5px 10px; border-radius: 4px; color: white; }}
                .green {{ background-color: #2ecc71; }}
                .blue {{ background-color: #3498db; }}
            </style>
        </head>
        <body>
            <h1>📚 Histórico de Análises - Mega Sena</h1>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <table>
                <tr>
                    <th>Concurso</th>
                    <th>Data Análise</th>
                    <th>Jogos</th>
                    <th>Quadras</th>
                    <th>Quinas</th>
                    <th>Senas</th>
                    <th>Estratégias</th>
                </tr>
        """
        for row in dados_tabela:
            html += f"""
                <tr>
                    <td><b>{row['Concurso']}</b></td>
                    <td>{row['Data Análise']}</td>
                    <td>{row['Jogos']}</td>
                    <td>{row['Quadras']}</td>
                    <td>{row['Quinas']}</td>
                    <td><span class="badge { 'green' if row['Senas'] > 0 else 'blue' }">{row['Senas']}</span></td>
                    <td>{row['Estratégias']}</td>
                </tr>
            """
        html += """
            </table>
        </body>
        </html>
        """
        st.download_button(
            label="💾 Baixar Arquivo HTML",
            data=html,
            file_name="historico_megasena.html",
            mime="text/html"
        )
    
    st.markdown("---")
    st.markdown("#### 🔍 Detalhes do Concurso Selecionado")
    
    lista_concursos = df_hist['Concurso'].unique() if not df_hist.empty else []
    concurso_detalhe = st.selectbox(
        "Selecione um concurso para ver detalhes:",
        options=lista_concursos
    )

def pagina_relatorio_geral(df):
    """Entrypoint da página de relatório geral."""
    st.title("📊 Relatório Geral & Histórico")
    st.markdown("### Conferência rápida, histórico consolidado e ranking completo")

    tab_rapida, tab_auto_verificar, tab_historico = st.tabs([
        "⚡ Verificação Rápida",
        "🔄 Verificar Todos Pendentes",
        "📚 Histórico & Ranking"
    ])

    with tab_rapida:
        _aba_verificacao_rapida(df)

    with tab_auto_verificar:
        _aba_verificar_tudo(df)

    with tab_historico:
        _aba_historico_consolidado()
