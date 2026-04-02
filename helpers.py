"""
Funções helper para conversão de dados
"""


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
