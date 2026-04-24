"""
Funções helper para conversão de dados e constantes compartilhadas
"""

# ── Custos oficiais da Mega-Sena por quantidade de números ────
# Fonte: Caixa Econômica Federal (atualizado 2026)
# Preço base: R$ 6,00 (conforme README.md)
CUSTOS_CARTAO = {
    6: 6.00, 7: 42.00, 8: 168.00, 9: 504.00, 10: 1260.00,
    11: 2772.00, 12: 5544.00, 13: 10296.00, 14: 18018.00,
    15: 30030.00, 16: 48048.00, 17: 74256.00, 18: 111384.00,
    19: 162792.00, 20: 232560.00
}

# ── Filtros e Parâmetros de Qualidade ─────────────────────────
# Centralizados para facilitar ajustes e testes
FILTROS_JOGO = {
    'soma_min': 140,
    'soma_max': 210,
    'pares_min': 2,
    'pares_max': 4,
    'amplitude_min': 30,
    'tentativas_max': 100,  # Máximo de tentativas para gerar jogo válido
}

# ── Janelas de Análise Estatística ─────────────────────────────
JANELAS_ANALISE = {
    'recente': 50,       # Jogos recentes para análise de tendência
    'momentum_curto': 20, # Jogos para cálculo de momentum
    'momentum_longo': 100, # Jogos para base de comparação momentum
    'co_ocorrencia': 200, # Jogos para análise de pares frequentes
    'ciclos_min': 100,    # Jogos mínimos para análise de ciclos
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
        'versao': '3.0',
        'nota': 'Ensemble adaptativo por streak: só entram estratégias que marcaram terno+ em algum dos últimos N concursos (default N=2); fallback para ranking recente, backtesting e ensemble clássico',
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
    'candidatos_ouro': {
        'versao': '1.0',
        'nota': 'Números frios + muito atrasados (score = deficit_freq + atraso/10)',
    },
    'momentum': {
        'versao': '1.0',
        'nota': 'Razão freq(20 últimos) / freq(100 últimos); ratio > 1.2 = acelerando',
    },
    'vizinhanca': {
        'versao': '1.0',
        'nota': 'Números ±2 do último sorteio como pool de candidatos',
    },
    'frequencia_desvio': {
        'versao': '1.0',
        'nota': 'Números com frequência > 1 desvio padrão acima da média',
    },
    'pares_frequentes': {
        'versao': '1.0',
        'nota': 'Top 30 pares co-ocorrentes nos últimos 200 sorteios → números únicos',
    },
    'ciclos': {
        'versao': '1.0',
        'nota': 'Números cujo gap atual está próximo do ciclo médio de aparição',
    },
    'atraso_recente': {
        'versao': '1.0',
        'nota': 'Números que não saem há mais concursos do que o normal nos últimos 100 sorteios',
    },
    'Manual': {
        'versao': '-',
        'nota': 'Cartão inserido manualmente pelo usuário',
    },
}


def versao_estrategia(estrategia: str) -> str:
    """Retorna a versão atual de uma estratégia."""
    info = VERSOES_ESTRATEGIAS.get(estrategia, {})
    return info.get('versao', '?')


def obter_preco_cartao(qtd_numeros: int) -> float:
    """Retorna o preço de um cartão com a quantidade de números informada."""
    return CUSTOS_CARTAO.get(qtd_numeros, 0.0)


def obter_parametros_filtro() -> dict:
    """Retorna os parâmetros de filtro para validação de jogos."""
    return FILTROS_JOGO.copy()


def obter_janelas_analise() -> dict:
    """Retorna as janelas de análise estatística configuradas."""
    return JANELAS_ANALISE.copy()


def converter_dezenas_para_int(dezenas) -> list[int]:
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
    except Exception:
        pass

    # Último recurso: retornar lista vazia
    return []
