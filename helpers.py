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
# Ver docs/MELHORIAS.md para histórico completo e avaliação técnica.
VERSOES_ESTRATEGIAS = {
    'escada': {
        'versao': '1.1',
        'nota': 'Inversões reais da escada temporal (v1.0 fazia fallback para atrasados quando inversoes<6)',
    },
    'atrasados': {
        'versao': '1.0',
        'nota': 'Top-20 menos frequentes historicamente + filtros básicos (soma/paridade/amplitude)',
    },
    'quentes': {
        'versao': '1.0',
        'nota': 'Top-20 mais frequentes nos últimos 50 sorteios + filtros básicos',
    },
    'equilibrado': {
        'versao': '1.0',
        'nota': '3 pares exatos + 3 ímpares exatos',
    },
    'misto': {
        'versao': '1.0',
        'nota': '2 atrasados + 2 quentes + 2 atraso_recente + filtros básicos',
    },
    'consenso': {
        'versao': '1.0',
        'nota': 'Interseção de 3 pools (atrasados/quentes/atraso_rec) com >= 2 votos + filtros básicos',
    },
    'aleatorio_smart': {
        'versao': '1.0',
        'nota': 'Aleatório puro com rejeição: soma 140-210 e paridade 2-4 (max 100 tentativas)',
    },
    'ensemble': {
        'versao': '1.0',
        'nota': 'Votação de 7 estratégias base; top-20 votados com filtro soma/paridade',
    },
    'sequencias': {
        'versao': '1.1',
        'nota': 'KMeans 4 clusters (co-ocorrência + StandardScaler) + vizinhança N±1 + filtros geométricos',
    },
    'wheel': {
        'versao': '1.0',
        'nota': 'Greedy covering design K=3, pool 18 por consenso; garante cobertura de todas as ternas do pool',
    },
    'automl': {
        'versao': '2.0',
        'nota': (
            'RF calibrado (CalibratedClassifierCV isotônico + TimeSeriesSplit) + '
            'class_weight=balanced + cache joblib por hash do dataset + '
            '13 features incluindo combinação (soma, amplitude, paridade, consecutivos, quadrante)'
        ),
    },
    'Manual': {
        'versao': '-',
        'nota': 'Cartão inserido manualmente pelo usuário',
    },
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
