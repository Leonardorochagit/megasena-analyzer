"""
================================================================================
🎰 MEGA SENA - Módulo de Utilidades
================================================================================
Versão: 2.0.0
Autor: Leonardo
Data: Dezembro 2025

Funções reutilizáveis para geração e gerenciamento de cartões.
================================================================================
"""

import streamlit as st
import random
from typing import List, Dict, Optional, Tuple


# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

VERSAO = "2.0.0"
LIMITE_CARTOES = 20
RANGE_NUMEROS = (1, 60)
DEZENAS_POR_CARTAO = 6


# ============================================================================
# FUNÇÕES DE GERAÇÃO DE CARTÕES
# ============================================================================

def gerar_cartao_aleatorio(
    numeros_prioritarios: Optional[List[int]] = None,
    min_prioritarios: int = 3,
    estrategia: str = "Aleatório",
    concurso_alvo: int = 0
) -> Dict:
    """
    Gera um cartão com priorização opcional de números específicos.

    Args:
        numeros_prioritarios: Lista de números a priorizar
        min_prioritarios: Quantidade mínima de números prioritários
        estrategia: Nome da estratégia utilizada
        concurso_alvo: Número do concurso alvo

    Returns:
        Dicionário com estrutura de cartão padrão
    """
    dezenas = []

    # Adicionar números prioritários
    if numeros_prioritarios and len(numeros_prioritarios) >= min_prioritarios:
        qtd_prioritarios = min(min_prioritarios, len(numeros_prioritarios))
        dezenas = random.sample(numeros_prioritarios, qtd_prioritarios)

    # Completar com números aleatórios
    numeros_disponiveis = [
        n for n in range(RANGE_NUMEROS[0], RANGE_NUMEROS[1] + 1)
        if n not in dezenas
    ]

    qtd_faltante = DEZENAS_POR_CARTAO - len(dezenas)
    if qtd_faltante > 0:
        dezenas.extend(random.sample(numeros_disponiveis, qtd_faltante))

    return {
        'id': f"{estrategia[:4].upper()}-{random.randint(1000, 9999)}",
        'estrategia': estrategia,
        'dezenas': sorted(dezenas[:DEZENAS_POR_CARTAO]),
        'concurso_alvo': concurso_alvo
    }


def gerar_multiplos_cartoes(
    quantidade: int,
    numeros_prioritarios: Optional[List[int]] = None,
    min_prioritarios: int = 3,
    estrategia: str = "Aleatório",
    concurso_alvo: int = 0,
    peso_prioritarios: int = 70
) -> List[Dict]:
    """
    Gera múltiplos cartões com estratégia específica.

    Args:
        quantidade: Número de cartões a gerar
        numeros_prioritarios: Lista de números a priorizar
        min_prioritarios: Quantidade mínima de números prioritários
        estrategia: Nome da estratégia
        concurso_alvo: Número do concurso alvo
        peso_prioritarios: Peso (0-100) para usar números prioritários

    Returns:
        Lista de cartões gerados
    """
    cartoes = []

    for i in range(quantidade):
        # Calcular quantidade de números prioritários baseado no peso
        if numeros_prioritarios and peso_prioritarios > 0:
            qtd_prioritarios = max(
                min_prioritarios,
                int(DEZENAS_POR_CARTAO * (peso_prioritarios / 100))
            )
        else:
            qtd_prioritarios = min_prioritarios

        cartao = gerar_cartao_aleatorio(
            numeros_prioritarios=numeros_prioritarios,
            min_prioritarios=qtd_prioritarios,
            estrategia=estrategia,
            concurso_alvo=concurso_alvo
        )

        # Evitar duplicatas
        if not any(c['dezenas'] == cartao['dezenas'] for c in cartoes):
            cartoes.append(cartao)

    return cartoes


# ============================================================================
# FUNÇÕES DE GERENCIAMENTO DE SESSION STATE
# ============================================================================

def inicializar_session_state():
    """Inicializa variáveis essenciais no session state."""
    if 'cartoes_selecionados' not in st.session_state:
        st.session_state['cartoes_selecionados'] = []


def adicionar_cartao_a_lista(cartao: Dict, lista_key: str = 'cartoes_selecionados') -> Tuple[bool, str]:
    """
    Adiciona um cartão à lista do session state.

    Args:
        cartao: Cartão a adicionar
        lista_key: Chave da lista no session state

    Returns:
        (sucesso, mensagem)
    """
    inicializar_session_state()

    lista = st.session_state.get(lista_key, [])

    # Verificar limite
    if len(lista) >= LIMITE_CARTOES:
        return False, f"⚠️ Limite de {LIMITE_CARTOES} cartões atingido!"

    # Verificar duplicata
    if any(c['dezenas'] == cartao['dezenas'] for c in lista):
        return False, "⚠️ Este cartão já existe na lista!"

    # Adicionar
    lista.append(cartao.copy())
    st.session_state[lista_key] = lista

    return True, f"✅ Cartão adicionado! Total: {len(lista)}"


def cartao_existe_na_lista(dezenas: List[int], lista_key: str = 'cartoes_selecionados') -> bool:
    """Verifica se um cartão com as dezenas já existe na lista."""
    lista = st.session_state.get(lista_key, [])
    return any(c['dezenas'] == dezenas for c in lista)


# ============================================================================
# FUNÇÕES DE EXIBIÇÃO
# ============================================================================

def formatar_dezenas_com_destaque(
    dezenas: List[int],
    numeros_destaque: Optional[List[int]] = None,
    emoji_destaque: str = "⭐"
) -> str:
    """
    Formata dezenas com destaque visual para números específicos.

    Args:
        dezenas: Lista de dezenas do cartão
        numeros_destaque: Números a destacar
        emoji_destaque: Emoji para destacar

    Returns:
        String formatada com destaque
    """
    partes = []
    for d in dezenas:
        if numeros_destaque and d in numeros_destaque:
            partes.append(f"**{d:02d}**{emoji_destaque}")
        else:
            partes.append(f"{d:02d}")

    return " - ".join(partes)


def exibir_cartoes_com_selecao(
    cartoes: List[Dict],
    numeros_destaque: Optional[List[int]] = None,
    emoji_destaque: str = "⭐",
    titulo: str = "🎫 Cartões Gerados",
    key_prefix: str = "cartao"
):
    """
    Exibe cartões com botões individuais de seleção.

    Args:
        cartoes: Lista de cartões a exibir
        numeros_destaque: Números a destacar visualmente
        emoji_destaque: Emoji para destaque
        titulo: Título da seção
        key_prefix: Prefixo para keys dos botões
    """
    if not cartoes:
        st.info("ℹ️ Nenhum cartão gerado ainda.")
        return

    st.markdown("---")
    st.subheader(titulo)

    inicializar_session_state()

    for idx, cartao in enumerate(cartoes):
        col_id, col_nums, col_btn = st.columns([1, 4, 1])

        with col_id:
            st.write(f"**#{idx+1}**")
            st.caption(cartao.get('estrategia', 'N/A'))

        with col_nums:
            dezenas_formatadas = formatar_dezenas_com_destaque(
                cartao['dezenas'],
                numeros_destaque,
                emoji_destaque
            )
            st.write(dezenas_formatadas)

        with col_btn:
            ja_existe = cartao_existe_na_lista(cartao['dezenas'])

            if ja_existe:
                st.success("✅")
                st.caption("Adicionado")
            else:
                if st.button("➕", key=f"{key_prefix}_{idx}_{cartao['id']}"):
                    sucesso, msg = adicionar_cartao_a_lista(cartao)
                    if sucesso:
                        st.success("✅")
                        st.rerun()
                    else:
                        st.warning(msg)


def exibir_estatisticas_cartoes(cartoes: List[Dict]):
    """
    Exibe estatísticas sobre os cartões gerados.

    Args:
        cartoes: Lista de cartões
    """
    if not cartoes:
        return

    st.markdown("---")
    st.subheader("📊 Estatísticas dos Cartões Gerados")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de Cartões", len(cartoes))

    with col2:
        todas_dezenas = [d for c in cartoes for d in c['dezenas']]
        numero_mais_comum = max(set(todas_dezenas), key=todas_dezenas.count)
        st.metric("Número Mais Comum", f"{numero_mais_comum:02d}")

    with col3:
        estrategias = set(c.get('estrategia', 'N/A') for c in cartoes)
        st.metric("Estratégias Diferentes", len(estrategias))


# ============================================================================
# FUNÇÕES DE UI COMPONENTS
# ============================================================================

def criar_slider_quantidade(
    label: str = "Quantos cartões gerar?",
    min_val: int = 1,
    max_val: int = 10,
    default: int = 5,
    key: str = "qtd_cartoes"
) -> int:
    """
    Cria slider padronizado para seleção de quantidade.

    Returns:
        Quantidade selecionada
    """
    return st.slider(label, min_val, max_val, default, key=key)


def criar_slider_peso(
    label: str = "Peso dos números prioritários:",
    min_val: int = 50,
    max_val: int = 100,
    default: int = 70,
    key: str = "peso"
) -> int:
    """
    Cria slider padronizado para seleção de peso/prioridade.

    Returns:
        Peso selecionado (0-100)
    """
    return st.slider(
        label,
        min_val,
        max_val,
        default,
        key=key,
        help="Quanto maior, mais números prioritários serão incluídos"
    )


# ============================================================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================================================

def validar_cartao(dezenas: List[int]) -> Tuple[bool, str]:
    """
    Valida se um cartão está correto.

    Args:
        dezenas: Lista de dezenas

    Returns:
        (válido, mensagem)
    """
    # Verificar quantidade
    if len(dezenas) != DEZENAS_POR_CARTAO:
        return False, f"Deve ter exatamente {DEZENAS_POR_CARTAO} dezenas"

    # Verificar range
    if not all(RANGE_NUMEROS[0] <= d <= RANGE_NUMEROS[1] for d in dezenas):
        return False, f"Dezenas devem estar entre {RANGE_NUMEROS[0]} e {RANGE_NUMEROS[1]}"

    # Verificar duplicatas
    if len(set(dezenas)) != len(dezenas):
        return False, "Não pode haver dezenas duplicadas"

    return True, "✅ Cartão válido"


# ============================================================================
# INFORMAÇÕES DE VERSÃO
# ============================================================================

def exibir_info_versao():
    """Exibe informações de versão do módulo."""
    with st.expander("ℹ️ Informações da Versão"):
        st.write(f"**Versão:** {VERSAO}")
        st.write(f"**Limite de Cartões:** {LIMITE_CARTOES}")
        st.write(
            f"**Range de Números:** {RANGE_NUMEROS[0]}-{RANGE_NUMEROS[1]}")
        st.write(f"**Dezenas por Cartão:** {DEZENAS_POR_CARTAO}")


if __name__ == "__main__":
    print(f"🎰 Mega Sena Utils v{VERSAO}")
    print("Este módulo deve ser importado, não executado diretamente.")
