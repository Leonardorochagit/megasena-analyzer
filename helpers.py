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
