"""
Funções helper para conversão de dados e constantes compartilhadas
"""

# ── Custos oficiais da Mega-Sena por quantidade de números ────
# Fonte: Caixa Econômica Federal (atualizado 2025)
CUSTOS_CARTAO = {
    6: 5.00, 7: 35.00, 8: 140.00, 9: 420.00, 10: 1050.00,
    11: 2310.00, 12: 4620.00, 13: 8580.00, 14: 15015.00,
    15: 25025.00, 16: 40040.00, 17: 61880.00, 18: 92820.00,
    19: 135660.00, 20: 193800.00
}

# ── Versionamento de estratégias ──────────────────────────────
# Bumpar a versão sempre que alterar a lógica de geração/filtros.
# Formato: "major.minor"  (major = redesign, minor = ajuste/tuning)
VERSOES_ESTRATEGIAS = {
    'escada':          {'versao': '1.0', 'nota': 'Inversões da escada temporal, pool top-20'},
    'atrasados':       {'versao': '1.0', 'nota': 'Top-20 menos frequentes'},
    'quentes':         {'versao': '1.0', 'nota': 'Top-20 mais frequentes recentes'},
    'equilibrado':     {'versao': '1.0', 'nota': '3 pares + 3 ímpares'},
    'misto':           {'versao': '1.0', 'nota': '2 atrasados + 2 quentes + 2 atraso_rec'},
    'consenso':        {'versao': '1.0', 'nota': 'Interseção de 3 análises (≥2 votos)'},
    'aleatorio_smart': {'versao': '1.0', 'nota': 'Aleatório com filtro soma/paridade'},
    'ensemble':        {'versao': '1.0', 'nota': 'Votação de 7 estratégias base'},
    'sequencias':      {'versao': '1.0', 'nota': 'KMeans 4 clusters + vizinhança N±1 + filtros'},
    'wheel':           {'versao': '1.0', 'nota': 'Greedy covering design K=3, pool 18 consenso'},
    'automl':          {'versao': '1.1', 'nota': 'RF + features geométricas (paridade, amplitude, seq, quadrante)'},
    'Manual':          {'versao': '-',   'nota': 'Cartão manual do usuário'},
}


def versao_estrategia(estrategia):
    """Retorna a versão atual de uma estratégia."""
    info = VERSOES_ESTRATEGIAS.get(estrategia, {})
    return info.get('versao', '?')


def converter_dezenas_para_int(dezenas):
    """
    Converte dezenas para lista de inteiros de forma robusta

    Args:
        dezenas: pode ser lista, string, ou qualquer formato

    Returns:
        list: Lista de inteiros
    """
    # Se já é lista de inteiros
    if isinstance(dezenas, list):
        try:
            return [int(n) for n in dezenas]
        except (ValueError, TypeError):
            pass

    # Se é string (formato "[1, 2, 3]" ou "1,2,3")
    if isinstance(dezenas, str):
        # Remover colchetes e espaços
        dezenas = dezenas.replace('[', '').replace(']', '').replace(' ', '')
        # Dividir por vírgula
        try:
            return [int(n) for n in dezenas.split(',') if n]
        except (ValueError, TypeError):
            pass

    # Se é pandas Series ou array
    try:
        return [int(n) for n in list(dezenas)]
    except:
        pass

    # Último recurso: retornar lista vazia
    return []
