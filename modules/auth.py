"""
================================================================================
🔐 MÓDULO DE AUTENTICAÇÃO (Simplificado - Sem Login)
================================================================================
Gerencia sessão do usuário sem necessidade de autenticação
"""

import streamlit as st


def inicializar_sessao():
    """
    Inicializa a sessão do usuário sem necessidade de login

    Returns:
        None: Configura st.session_state com dados padrão
    """
    if 'autenticado' not in st.session_state:
        st.session_state['autenticado'] = True
        st.session_state['usuario'] = 'usuario'
        st.session_state['dados_usuario'] = {
            'nome': 'Usuário',
            'email': '',
            'admin': True
        }


def verificar_autenticacao():
    """
    Verifica se o usuário está autenticado (sempre True agora)

    Returns:
        bool: Sempre retorna True
    """
    inicializar_sessao()
    return True


def pagina_login():
    """
    Página de login simplificada - apenas inicializa a sessão
    """
    inicializar_sessao()
    st.rerun()


def logout():
    """
    Mantém compatibilidade - não faz logout real (sempre autenticado)
    """
    pass


def obter_usuario_atual():
    """
    Retorna dados do usuário atual

    Returns:
        dict: Dados do usuário padrão
    """
    inicializar_sessao()
    return st.session_state.get('dados_usuario', {
        'nome': 'Usuário',
        'email': '',
        'admin': True
    })
