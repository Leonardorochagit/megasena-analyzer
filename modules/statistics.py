"""
================================================================================
📈 MÓDULO DE ESTATÍSTICAS
================================================================================
Cálculos estatísticos e análises avançadas
"""

import pandas as pd
import numpy as np
from collections import Counter


def calcular_estatisticas(df, ultimos=50):
    """
    Calcula todas as estatísticas básicas

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios

    Returns:
        tuple: (contagem_total, contagem_recente, df_atrasos)
    """
    # Todas as dezenas
    todas_dezenas = []
    for i in range(1, 7):
        todas_dezenas.extend(df[f'dez{i}'].astype(int).tolist())

    contagem_total = pd.Series(todas_dezenas).value_counts().sort_index()

    # Garantir todos os números
    for num in range(1, 61):
        if num not in contagem_total.index:
            contagem_total[num] = 0
    contagem_total = contagem_total.sort_index()

    # Contagem recente
    df_recentes = df.head(ultimos)
    dezenas_recentes = []
    for i in range(1, 7):
        dezenas_recentes.extend(df_recentes[f'dez{i}'].astype(int).tolist())
    contagem_recente = pd.Series(dezenas_recentes).value_counts()

    # Atrasos
    atrasos = {}
    for num in range(1, 61):
        for idx, row in df.iterrows():
            numeros = [int(row[f'dez{i}']) for i in range(1, 7)]
            if num in numeros:
                atrasos[num] = idx
                break
        else:
            atrasos[num] = len(df)

    df_atrasos = pd.DataFrame(list(atrasos.items()), columns=[
                              'numero', 'jogos_sem_sair'])
    df_atrasos = df_atrasos.sort_values('jogos_sem_sair', ascending=False)

    return contagem_total, contagem_recente, df_atrasos


def calcular_escada_temporal(df, janela_recente=50):
    """
    Calcula a escada temporal - comparação entre frequência total e recente.
    Identifica números em inversão de tendência.

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
        janela_recente (int): Quantidade de jogos recentes para análise

    Returns:
        tuple: (freq_total, freq_recente, freq_total_norm, freq_recente_norm, variacao, inversoes)
    """
    # Frequência total
    todas_dezenas = []
    for i in range(1, 7):
        todas_dezenas.extend(df[f'dez{i}'].astype(int).tolist())
    freq_total = pd.Series(todas_dezenas).value_counts()

    # Garantir todos os números
    for num in range(1, 61):
        if num not in freq_total.index:
            freq_total[num] = 0
    freq_total = freq_total.sort_index()

    # Frequência recente
    df_recentes = df.head(janela_recente)
    dezenas_recentes = []
    for i in range(1, 7):
        dezenas_recentes.extend(df_recentes[f'dez{i}'].astype(int).tolist())
    freq_recente = pd.Series(dezenas_recentes).value_counts()

    for num in range(1, 61):
        if num not in freq_recente.index:
            freq_recente[num] = 0
    freq_recente = freq_recente.sort_index()

    # Normalizar para comparação (percentual)
    freq_total_norm = (freq_total / freq_total.sum() * 100).round(2)
    freq_recente_norm = (freq_recente / freq_recente.sum() * 100).round(2)

    # Calcular variação (diferença recente - total)
    variacao = freq_recente_norm - freq_total_norm

    # Identificar inversões de tendência
    media_total = freq_total.mean()
    media_recente = freq_recente.mean()
    inversoes = []

    for num in range(1, 61):
        eh_frio_total = freq_total[num] < media_total
        eh_quente_recente = freq_recente[num] >= media_recente
        variacao_positiva = variacao[num] > 0.3

        if (eh_frio_total and eh_quente_recente) or (eh_frio_total and variacao_positiva):
            inversoes.append({
                'numero': num,
                'freq_total': int(freq_total[num]),
                'freq_recente': int(freq_recente[num]),
                'variacao': round(float(variacao[num]), 2),
                'tipo': 'Inversão Alta 📈'
            })

    inversoes = sorted(inversoes, key=lambda x: x['variacao'], reverse=True)

    return freq_total, freq_recente, freq_total_norm, freq_recente_norm, variacao, inversoes


def calcular_candidatos_ouro(contagem_total, df_atrasos, limite_atraso=30):
    """
    Identifica 'Candidatos Ouro' - números frios E muito atrasados

    Args:
        contagem_total (pd.Series): Contagem total de cada número
        df_atrasos (pd.DataFrame): DataFrame com atrasos
        limite_atraso (int): Limite mínimo de atraso

    Returns:
        list: Lista de candidatos ouro com scores
    """
    media_freq = contagem_total.mean()
    candidatos_ouro = []

    for _, row in df_atrasos.iterrows():
        num = row['numero']
        atraso = row['jogos_sem_sair']
        freq = contagem_total[num]

        if freq < media_freq and atraso >= limite_atraso:
            score = (media_freq - freq) + (atraso / 10)
            candidatos_ouro.append({
                'numero': num,
                'frequencia': freq,
                'atraso': atraso,
                'score': round(score, 2),
                'motivo': f"Freq abaixo da média ({freq:.0f} < {media_freq:.0f}) + Atraso de {atraso} jogos"
            })

    candidatos_ouro = sorted(
        candidatos_ouro, key=lambda x: x['score'], reverse=True)
    return candidatos_ouro


def calcular_quadrantes(df, n_ultimos=50):
    """
    Divide o volante em 4 quadrantes e analisa distribuição

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
        n_ultimos (int): Quantidade de jogos recentes para análise

    Returns:
        tuple: (quadrantes, stats_quadrantes, quadrante_frio)
    """
    quadrantes = {
        'Q1 (Superior Esq)': [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25],
        'Q2 (Superior Dir)': [6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30],
        'Q3 (Inferior Esq)': [31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55],
        'Q4 (Inferior Dir)': [36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60]
    }

    todas_dezenas = []
    for i in range(1, 7):
        todas_dezenas.extend(df[f'dez{i}'].astype(int).tolist())
    contagem_total = Counter(todas_dezenas)

    df_recentes = df.head(n_ultimos)
    dezenas_recentes = []
    for i in range(1, 7):
        dezenas_recentes.extend(df_recentes[f'dez{i}'].astype(int).tolist())
    contagem_recente = Counter(dezenas_recentes)

    stats_quadrantes = {}
    for nome, numeros in quadrantes.items():
        total = sum(contagem_total.get(n, 0) for n in numeros)
        recente = sum(contagem_recente.get(n, 0) for n in numeros)
        stats_quadrantes[nome] = {
            'numeros': numeros,
            'freq_total': total,
            'freq_recente': recente,
            'media_por_numero_total': total / len(numeros),
            'media_por_numero_recente': recente / len(numeros)
        }

    quadrante_frio = min(stats_quadrantes.items(),
                         key=lambda x: x[1]['freq_recente'])

    return quadrantes, stats_quadrantes, quadrante_frio


def calcular_soma_gaussiana(df):
    """
    Analisa a soma das 6 dezenas - Lei de Gauss

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios

    Returns:
        tuple: (somas, stats_soma, faixas)
    """
    somas = []
    for _, row in df.iterrows():
        dezenas = [int(row[f'dez{i}']) for i in range(1, 7)]
        somas.append(sum(dezenas))

    soma_serie = pd.Series(somas)

    stats_soma = {
        'media': soma_serie.mean(),
        'mediana': soma_serie.median(),
        'desvio_padrao': soma_serie.std(),
        'minimo': soma_serie.min(),
        'maximo': soma_serie.max(),
        'percentil_25': soma_serie.quantile(0.25),
        'percentil_75': soma_serie.quantile(0.75),
        'faixa_ideal_min': soma_serie.quantile(0.10),
        'faixa_ideal_max': soma_serie.quantile(0.90),
    }

    faixas = {
        '100-130': 0, '131-150': 0, '151-180': 0, '181-200': 0,
        '201-220': 0, '221-250': 0, '251-280': 0, '281+': 0
    }
    for s in somas:
        if s <= 130:
            faixas['100-130'] += 1
        elif s <= 150:
            faixas['131-150'] += 1
        elif s <= 180:
            faixas['151-180'] += 1
        elif s <= 200:
            faixas['181-200'] += 1
        elif s <= 220:
            faixas['201-220'] += 1
        elif s <= 250:
            faixas['221-250'] += 1
        elif s <= 280:
            faixas['251-280'] += 1
        else:
            faixas['281+'] += 1

    return somas, stats_soma, faixas


def validar_soma_jogo(dezenas, stats_soma):
    """
    Valida se a soma de um jogo está dentro da faixa ideal

    Args:
        dezenas (list): Lista de dezenas do jogo
        stats_soma (dict): Estatísticas de soma

    Returns:
        tuple: (valido, soma, mensagem)
    """
    soma = sum(dezenas)
    faixa_min = stats_soma['faixa_ideal_min']
    faixa_max = stats_soma['faixa_ideal_max']

    if faixa_min <= soma <= faixa_max:
        return True, soma, f"✅ Soma {soma} está na faixa ideal ({faixa_min:.0f}-{faixa_max:.0f})"
    elif soma < faixa_min:
        return False, soma, f"⚠️ Soma {soma} muito BAIXA (mín ideal: {faixa_min:.0f})"
    else:
        return False, soma, f"⚠️ Soma {soma} muito ALTA (máx ideal: {faixa_max:.0f})"


def calcular_linhas_colunas(df, n_ultimos=100):
    """
    Analisa distribuição por linhas e colunas do volante

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
        n_ultimos (int): Quantidade de jogos recentes para análise

    Returns:
        tuple: (linhas, colunas, linhas_vazias_count, colunas_vazias_count, 
                sorteios_detalhes, media_linhas_vazias, media_colunas_vazias)
    """
    linhas = {f'L{i+1}': list(range(i*10+1, i*10+11)) for i in range(6)}
    colunas = {f'C{i+1}': [i+1 + j*10 for j in range(6)] for i in range(10)}

    df_ultimos = df.head(n_ultimos)
    linhas_vazias_count = Counter()
    colunas_vazias_count = Counter()
    sorteios_detalhes = []

    for _, row in df_ultimos.iterrows():
        dezenas = set([int(row[f'dez{i}']) for i in range(1, 7)])

        linhas_vazias = []
        for nome, nums in linhas.items():
            if not dezenas.intersection(nums):
                linhas_vazias.append(nome)

        colunas_vazias = []
        for nome, nums in colunas.items():
            if not dezenas.intersection(nums):
                colunas_vazias.append(nome)

        linhas_vazias_count[len(linhas_vazias)] += 1
        colunas_vazias_count[len(colunas_vazias)] += 1

        sorteios_detalhes.append({
            'concurso': row['concurso'],
            'dezenas': sorted(dezenas),
            'linhas_vazias': linhas_vazias,
            'colunas_vazias': colunas_vazias,
            'n_linhas_vazias': len(linhas_vazias),
            'n_colunas_vazias': len(colunas_vazias)
        })

    media_linhas_vazias = np.mean(
        [d['n_linhas_vazias'] for d in sorteios_detalhes])
    media_colunas_vazias = np.mean(
        [d['n_colunas_vazias'] for d in sorteios_detalhes])

    return linhas, colunas, linhas_vazias_count, colunas_vazias_count, sorteios_detalhes, media_linhas_vazias, media_colunas_vazias


def preparar_dados_pycaret(df, numero_alvo, n_concursos=300):
    """
    Prepara dados para o PyCaret - classificação binária se o número vai sair ou não

    Args:
        df (pd.DataFrame): DataFrame com histórico de sorteios
        numero_alvo (int): Número de 1 a 60 para prever
        n_concursos (int): Quantidade de concursos para treino

    Returns:
        pd.DataFrame: DataFrame preparado para AutoML
    """
    dados = []

    n_concursos = min(n_concursos, len(df) - 15)

    for i in range(n_concursos - 10):
        # Features: estatísticas dos últimos 10 concursos
        ultimos_10 = df.iloc[i+1:i+11]

        # Contagem do número alvo nos últimos 10
        contagem_alvo = 0
        for _, row in ultimos_10.iterrows():
            nums = [int(row[f'dez{j}']) for j in range(1, 7)]
            if numero_alvo in nums:
                contagem_alvo += 1

        # Atraso do número (quantos jogos desde última vez)
        atraso = 0
        for idx in range(i+1, min(i+51, len(df))):
            nums = [int(df.iloc[idx][f'dez{j}']) for j in range(1, 7)]
            if numero_alvo in nums:
                break
            atraso += 1

        # Contagem geral nos últimos 10
        contagem_geral = Counter()
        for _, row in ultimos_10.iterrows():
            for j in range(1, 7):
                contagem_geral[int(row[f'dez{j}'])] += 1

        # Soma média
        somas = []
        for _, row in ultimos_10.iterrows():
            soma = sum(int(row[f'dez{j}']) for j in range(1, 7))
            somas.append(soma)

        # Features
        features = {
            'contagem_numero_10': contagem_alvo,
            'atraso': atraso,
            'soma_media': np.mean(somas),
            'soma_std': np.std(somas),
            'media_frequencia': np.mean(list(contagem_geral.values())),
            'numero_par': 1 if numero_alvo % 2 == 0 else 0,
            'numero_baixo': 1 if numero_alvo <= 30 else 0,
            'dezena': numero_alvo // 10,
        }

        # Target: se o número saiu no concurso atual
        resultado_atual = [int(df.iloc[i][f'dez{j}']) for j in range(1, 7)]
        features['saiu'] = 1 if numero_alvo in resultado_atual else 0

        dados.append(features)

    return pd.DataFrame(dados)
