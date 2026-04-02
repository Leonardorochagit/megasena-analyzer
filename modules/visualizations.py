"""
================================================================================
📊 MÓDULO DE VISUALIZAÇÕES
================================================================================
Gráficos e visualizações com Plotly
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st


def criar_grafico_frequencia(contagem_total, titulo="Frequência de Números"):
    """
    Cria gráfico de barras para frequência de números

    Args:
        contagem_total (pd.Series): Série com contagem de números
        titulo (str): Título do gráfico

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    fig = px.bar(
        x=contagem_total.index,
        y=contagem_total.values,
        labels={'x': 'Número', 'y': 'Frequência'},
        title=titulo,
        color=contagem_total.values,
        color_continuous_scale='viridis'
    )
    fig.update_layout(showlegend=False, height=400)
    return fig


def criar_grafico_atrasos(df_atrasos, top_n=20):
    """
    Cria gráfico de barras para números atrasados

    Args:
        df_atrasos (pd.DataFrame): DataFrame com atrasos
        top_n (int): Quantidade de números a mostrar

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    top_atrasados = df_atrasos.head(top_n)

    fig = px.bar(
        top_atrasados,
        x='numero',
        y='jogos_sem_sair',
        labels={'numero': 'Número', 'jogos_sem_sair': 'Jogos sem Sair'},
        title=f'Top {top_n} Números Mais Atrasados',
        color='jogos_sem_sair',
        color_continuous_scale='reds'
    )
    fig.update_layout(showlegend=False, height=400)
    return fig


def criar_grafico_comparacao(freq_total_norm, freq_recente_norm, variacao):
    """
    Cria gráfico comparativo entre frequência total e recente

    Args:
        freq_total_norm (pd.Series): Frequência total normalizada
        freq_recente_norm (pd.Series): Frequência recente normalizada
        variacao (pd.Series): Variação entre as frequências

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Comparação: Total vs Recente (%)',
                        'Variação (Recente - Total)'),
        vertical_spacing=0.15
    )

    # Gráfico 1: Comparação
    fig.add_trace(
        go.Scatter(x=freq_total_norm.index, y=freq_total_norm.values,
                   name='Total', mode='lines', line=dict(color='blue')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=freq_recente_norm.index, y=freq_recente_norm.values,
                   name='Recente', mode='lines', line=dict(color='red')),
        row=1, col=1
    )

    # Gráfico 2: Variação
    cores = ['green' if v > 0 else 'red' for v in variacao.values]
    fig.add_trace(
        go.Bar(x=variacao.index, y=variacao.values, marker_color=cores,
               name='Variação', showlegend=False),
        row=2, col=1
    )

    fig.update_layout(height=700, showlegend=True)
    return fig


def criar_heatmap_quadrantes(stats_quadrantes):
    """
    Cria heatmap para análise de quadrantes

    Args:
        stats_quadrantes (dict): Estatísticas dos quadrantes

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    nomes = list(stats_quadrantes.keys())
    freq_total = [stats_quadrantes[n]['freq_total'] for n in nomes]
    freq_recente = [stats_quadrantes[n]['freq_recente'] for n in nomes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Frequência Total',
        x=nomes,
        y=freq_total,
        marker_color='lightblue'
    ))
    fig.add_trace(go.Bar(
        name='Frequência Recente',
        x=nomes,
        y=freq_recente,
        marker_color='darkblue'
    ))

    fig.update_layout(
        title='Distribuição por Quadrantes',
        barmode='group',
        height=400,
        xaxis_title='Quadrante',
        yaxis_title='Frequência'
    )
    return fig


def criar_grafico_soma_gaussiana(somas, stats_soma):
    """
    Cria histograma da distribuição de somas

    Args:
        somas (list): Lista de somas dos sorteios
        stats_soma (dict): Estatísticas de soma

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=somas,
        nbinsx=30,
        name='Distribuição de Somas',
        marker_color='steelblue'
    ))

    # Adicionar linhas de referência
    fig.add_vline(x=stats_soma['media'], line_dash="dash", line_color="red",
                  annotation_text=f"Média: {stats_soma['media']:.0f}")
    fig.add_vline(x=stats_soma['mediana'], line_dash="dash", line_color="green",
                  annotation_text=f"Mediana: {stats_soma['mediana']:.0f}")

    fig.update_layout(
        title='Distribuição de Somas (Gaussiana)',
        xaxis_title='Soma das Dezenas',
        yaxis_title='Frequência',
        height=400
    )
    return fig


def criar_grafico_linhas_colunas(linhas_vazias_count, colunas_vazias_count):
    """
    Cria gráficos para análise de linhas e colunas vazias

    Args:
        linhas_vazias_count (Counter): Contagem de linhas vazias
        colunas_vazias_count (Counter): Contagem de colunas vazias

    Returns:
        plotly.graph_objects.Figure: Gráfico plotly
    """
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Distribuição de Linhas Vazias',
                        'Distribuição de Colunas Vazias')
    )

    # Linhas vazias
    x_linhas = sorted(linhas_vazias_count.keys())
    y_linhas = [linhas_vazias_count[x] for x in x_linhas]
    fig.add_trace(
        go.Bar(x=x_linhas, y=y_linhas, marker_color='lightcoral', name='Linhas'),
        row=1, col=1
    )

    # Colunas vazias
    x_colunas = sorted(colunas_vazias_count.keys())
    y_colunas = [colunas_vazias_count[x] for x in x_colunas]
    fig.add_trace(
        go.Bar(x=x_colunas, y=y_colunas,
               marker_color='lightblue', name='Colunas'),
        row=1, col=2
    )

    fig.update_layout(height=400, showlegend=False)
    return fig


def exibir_cartao(dezenas, estrategia="", numero=None, destaque=False):
    """
    Exibe um cartão de forma visual

    Args:
        dezenas (list): Lista de dezenas do cartão
        estrategia (str): Nome da estratégia
        numero (int): Número do cartão
        destaque (bool): Se deve destacar o cartão
    """
    cor_fundo = "#e8f5e9" if destaque else "#f5f5f5"

    html = f"""
    <div style="background-color: {cor_fundo}; padding: 15px; border-radius: 10px; 
                border: 2px solid {'#27ae60' if destaque else '#ddd'}; margin: 10px 0;">
    """

    if numero:
        html += f"<h4 style='margin-top: 0;'>Cartão #{numero}</h4>"

    if estrategia:
        html += f"<p><strong>Estratégia:</strong> {estrategia}</p>"

    html += "<div style='display: flex; gap: 10px; flex-wrap: wrap;'>"

    for num in sorted(dezenas):
        html += f"""
        <div style="background-color: #209869; color: white; 
                    width: 45px; height: 45px; border-radius: 50%; 
                    display: flex; align-items: center; justify-content: center;
                    font-size: 18px; font-weight: bold;">
            {num:02d}
        </div>
        """

    html += "</div></div>"

    st.markdown(html, unsafe_allow_html=True)


def criar_tabela_estrategias(analise_estrategias):
    """
    Cria tabela formatada para análise de estratégias

    Args:
        analise_estrategias (list): Lista com análise por estratégia

    Returns:
        pd.DataFrame: DataFrame formatado
    """
    df = pd.DataFrame(analise_estrategias)

    # Formatar colunas numéricas
    if 'Média Acertos' in df.columns:
        df['Média Acertos'] = df['Média Acertos'].round(2)
    if 'Média Escolhidos' in df.columns:
        df['Média Escolhidos'] = df['Média Escolhidos'].round(2)
    if 'Média Descartados' in df.columns:
        df['Média Descartados'] = df['Média Descartados'].round(2)

    return df
