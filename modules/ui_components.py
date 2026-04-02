"""
================================================================================
🎨 MÓDULO DE COMPONENTES DE INTERFACE
================================================================================
Componentes reutilizáveis para a interface Streamlit
"""

import streamlit as st
import pandas as pd


def exibir_header(titulo, icone="🎰"):
    """
    Exibe cabeçalho principal da página

    Args:
        titulo (str): Título da página
        icone (str): Emoji do ícone
    """
    st.markdown(
        f'<h1 class="main-header">{icone} {titulo}</h1>',
        unsafe_allow_html=True
    )


def exibir_metricas(metricas_dict):
    """
    Exibe métricas em colunas

    Args:
        metricas_dict (dict): Dicionário com {label: valor, ...}
    """
    cols = st.columns(len(metricas_dict))
    for col, (label, valor) in zip(cols, metricas_dict.items()):
        with col:
            st.metric(label, valor)


def criar_card(titulo, conteudo, cor_fundo="#1e3c72"):
    """
    Cria um card visual

    Args:
        titulo (str): Título do card
        conteudo (str): Conteúdo do card
        cor_fundo (str): Cor de fundo em hex
    """
    html = f"""
    <div class="card-box" style="background: linear-gradient(135deg, {cor_fundo} 0%, #2a5298 100%);">
        <h3 style="margin-top: 0;">{titulo}</h3>
        <div class="numero-destaque">{conteudo}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def exibir_numero(numero, tamanho="normal", cor="#209869"):
    """
    Exibe um número formatado em círculo

    Args:
        numero (int): Número a exibir
        tamanho (str): 'pequeno', 'normal' ou 'grande'
        cor (str): Cor de fundo em hex

    Returns:
        str: HTML do número formatado
    """
    tamanhos = {
        'pequeno': ('35px', '14px'),
        'normal': ('45px', '18px'),
        'grande': ('60px', '24px')
    }

    width, font_size = tamanhos.get(tamanho, tamanhos['normal'])

    return f'<div style="background-color: {cor}; color: white; width: {width}; height: {width}; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: {font_size}; font-weight: bold; margin: 5px;">{numero:02d}</div>'


def exibir_numeros_linha(numeros, titulo=None):
    """
    Exibe uma linha de números formatados

    Args:
        numeros (list): Lista de números
        titulo (str): Título opcional
    """
    if titulo:
        st.write(f"**{titulo}**")

    html_parts = []
    for num in sorted(numeros):
        html_parts.append(exibir_numero(num))

    html = f'<div style="display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0;">{"".join(html_parts)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def criar_tag_estrategia(estrategia):
    """
    Cria uma tag visual para estratégia

    Args:
        estrategia (str): Nome da estratégia

    Returns:
        str: HTML da tag
    """
    cores_estrategias = {
        'atrasados': '#e74c3c',
        'quentes': '#e67e22',
        'equilibrado': '#3498db',
        'misto': '#9b59b6',
        'escada': '#1abc9c',
        'consenso': '#f39c12',
        'atraso_recente': '#c0392b',
        'aleatorio_smart': '#16a085'
    }

    cor = cores_estrategias.get(estrategia.lower(), '#95a5a6')

    return f"""
    <span class="estrategia-tag" style="background-color: {cor};">
        {estrategia}
    </span>
    """


def exibir_tabela_cartoes(cartoes, mostrar_acoes=True):
    """
    Exibe tabela de cartões com formatação

    Args:
        cartoes (list): Lista de cartões
        mostrar_acoes (bool): Se deve mostrar colunas de ações
    """
    if not cartoes:
        st.info("Nenhum cartão disponível")
        return

    dados_tabela = []
    for i, cartao in enumerate(cartoes):
        dados_tabela.append({
            '#': i + 1,
            'ID': cartao.get('id', f'CART-{i+1}'),
            'Estratégia': cartao.get('estrategia', 'N/A'),
            'Dezenas': ' - '.join([f"{n:02d}" for n in sorted(cartao.get('dezenas', []))]),
            'Status': cartao.get('status', 'não_marcado'),
            'Concurso': cartao.get('concurso_alvo', 'N/A')
        })

    df = pd.DataFrame(dados_tabela)
    st.dataframe(df, width="stretch", hide_index=True)


def criar_sidebar_filtros():
    """
    Cria sidebar com filtros comuns

    Returns:
        dict: Dicionário com valores dos filtros
    """
    st.sidebar.header("⚙️ Filtros e Configurações")

    filtros = {
        'janela_recente': st.sidebar.slider(
            "Jogos Recentes",
            min_value=10,
            max_value=100,
            value=50,
            step=5
        ),
        'limite_atraso': st.sidebar.slider(
            "Limite de Atraso",
            min_value=10,
            max_value=100,
            value=30,
            step=5
        ),
        'quantidade_cartoes': st.sidebar.slider(
            "Quantidade de Cartões",
            min_value=1,
            max_value=10,
            value=5,
            step=1
        )
    }

    return filtros


def exibir_info_box(titulo, conteudo, tipo="info"):
    """
    Exibe caixa de informação com estilo

    Args:
        titulo (str): Título da caixa
        conteudo (str): Conteúdo da caixa
        tipo (str): 'info', 'success', 'warning', 'error'
    """
    cores = {
        'info': '#3498db',
        'success': '#27ae60',
        'warning': '#f39c12',
        'error': '#e74c3c'
    }

    cor = cores.get(tipo, cores['info'])

    html = f"""
    <div style="background-color: {cor}20; border-left: 4px solid {cor}; 
                padding: 15px; border-radius: 5px; margin: 10px 0;">
        <h4 style="color: {cor}; margin-top: 0;">{titulo}</h4>
        <p style="margin-bottom: 0;">{conteudo}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def criar_botao_download(dados, nome_arquivo, label="📥 Download"):
    """
    Cria botão de download

    Args:
        dados (str): Dados para download (JSON, CSV, etc)
        nome_arquivo (str): Nome do arquivo
        label (str): Texto do botão
    """
    return st.download_button(
        label=label,
        data=dados,
        file_name=nome_arquivo,
        mime="application/json"
    )


def exibir_legenda_cores():
    """Exibe legenda de cores das estratégias"""
    st.markdown("### 🎨 Legenda de Cores")

    estrategias = {
        'Atrasados': '#e74c3c',
        'Quentes': '#e67e22',
        'Equilibrado': '#3498db',
        'Misto': '#9b59b6',
        'Escada': '#1abc9c',
        'Consenso': '#f39c12',
        'Atraso Recente': '#c0392b',
        'Aleatório Smart': '#16a085'
    }

    cols = st.columns(4)
    for i, (estrategia, cor) in enumerate(estrategias.items()):
        with cols[i % 4]:
            st.markdown(
                f'<div style="background-color: {cor}; color: white; padding: 5px; '
                f'border-radius: 5px; text-align: center; margin: 5px 0;">{estrategia}</div>',
                unsafe_allow_html=True
            )


def criar_progresso(valor, maximo, label=""):
    """
    Cria barra de progresso personalizada

    Args:
        valor (int): Valor atual
        maximo (int): Valor máximo
        label (str): Rótulo
    """
    percentual = (valor / maximo * 100) if maximo > 0 else 0

    if label:
        st.write(label)

    st.progress(percentual / 100)
    st.caption(f"{valor}/{maximo} ({percentual:.1f}%)")
