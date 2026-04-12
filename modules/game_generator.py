"""
================================================================================
🎲 MÓDULO DE GERAÇÃO DE JOGOS
================================================================================
Geração de jogos com diferentes estratégias
"""

import random
import numpy as np
from collections import Counter
from modules.statistics import (
    calcular_escada_temporal,
    calcular_candidatos_ouro,
    calcular_quadrantes,
    calcular_soma_gaussiana,
    validar_soma_jogo,
    preparar_dados_pycaret
)

# PyCaret será importado sob demanda (lazy) para não travar o carregamento
PYCARET_DISPONIVEL = None  # None = ainda não verificado
setup_clf = None
predict_model = None
create_model = None

def _carregar_pycaret():
    """Carrega PyCaret sob demanda"""
    global PYCARET_DISPONIVEL, setup_clf, predict_model, create_model
    if PYCARET_DISPONIVEL is not None:
        return PYCARET_DISPONIVEL
    try:
        from pycaret.classification import setup as _setup, predict_model as _predict, create_model as _create
        setup_clf = _setup
        predict_model = _predict
        create_model = _create
        PYCARET_DISPONIVEL = True
    except (ImportError, RuntimeError):
        PYCARET_DISPONIVEL = False
    return PYCARET_DISPONIVEL


def gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos):
    """
    Gera um jogo baseado na estratégia

    Args:
        estrategia (str): Nome da estratégia
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos

    Returns:
        list: Lista com 6 dezenas ordenadas
    """
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(20).index.tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'quentes':
        candidatos = contagem_recente.head(20).index.tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'atraso_recente':
        candidatos = df_atrasos.head(20)['numero'].tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'equilibrado':
        pares = [n for n in range(2, 61, 2)]
        impares = [n for n in range(1, 61, 2)]
        jogo = random.sample(pares, 3) + random.sample(impares, 3)
        jogo = sorted(jogo)

    elif estrategia == 'escada':
        candidatos = contagem_total.sort_values().head(15).index.tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'consenso':
        atrasados = set(contagem_total.sort_values().head(15).index.tolist())
        quentes = set(contagem_recente.head(15).index.tolist())
        atraso_rec = set(df_atrasos.head(15)['numero'].tolist())

        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        contagem = Counter(todos)
        consenso = [num for num, count in contagem.items() if count >= 2]

        if len(consenso) >= 6:
            jogo = sorted(random.sample(consenso, 6))
        else:
            candidatos = contagem_total.sort_values().head(20).index.tolist()
            jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'aleatorio_smart':
        jogo = sorted(random.sample(range(1, 61), 6))
        tentativas = 0
        while tentativas < 100:
            jogo = sorted(random.sample(range(1, 61), 6))
            pares = sum(1 for n in jogo if n % 2 == 0)
            soma = sum(jogo)
            if 2 <= pares <= 4 and 140 <= soma <= 210:
                break
            tentativas += 1

    elif estrategia == 'ensemble':
        jogo = gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos)

    else:  # misto
        atrasados = contagem_total.sort_values().head(15).index.tolist()
        quentes = contagem_recente.head(15).index.tolist()
        atraso_rec = df_atrasos.head(15)['numero'].tolist()

        jogo = []
        jogo.extend(random.sample(atrasados, 2))
        quentes_filtrado = [n for n in quentes if n not in jogo]
        jogo.extend(random.sample(quentes_filtrado, 2))
        atraso_filtrado = [n for n in atraso_rec if n not in jogo]
        if len(atraso_filtrado) >= 2:
            jogo.extend(random.sample(atraso_filtrado, 2))
        else:
            restantes = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(restantes, 2))
        jogo = sorted(jogo)

    return jogo


def gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos):
    """
    Estratégia ensemble: gera um jogo de cada estratégia base,
    conta a frequência de cada número nas 7 saídas e seleciona
    os 6 mais votados. Validação por soma gaussiana e paridade.
    """
    estrategias = [
        'escada', 'atrasados', 'quentes',
        'equilibrado', 'misto', 'consenso', 'aleatorio_smart'
    ]

    votos = Counter()
    for est in estrategias:
        try:
            jogo = gerar_jogo(est, contagem_total, contagem_recente, df_atrasos)
            for n in jogo:
                votos[n] += 1
        except Exception:
            pass

    # Selecionar por votação; desempate por frequência recente
    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    # Tentar montar jogo válido (soma 140-210, 2-4 pares)
    for _ in range(100):
        pool = candidatos[:20]
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if 2 <= pares <= 4 and 140 <= soma <= 210:
            return jogo

    # Fallback: top 6 mais votados
    return sorted(candidatos[:6])


def gerar_jogo_avancado(contagem_total, contagem_recente, df_atrasos, df,
                        usar_inversoes=True, usar_candidatos_ouro=True,
                        usar_quadrantes=True, validar_soma=True,
                        validar_linhas=True):
    """
    Gera jogo utilizando todas as análises avançadas

    Args:
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos
        df (pd.DataFrame): DataFrame com histórico completo
        usar_inversoes (bool): Usar análise de inversões
        usar_candidatos_ouro (bool): Usar candidatos ouro
        usar_quadrantes (bool): Usar análise de quadrantes
        validar_soma (bool): Validar soma gaussiana
        validar_linhas (bool): Validar linhas e colunas

    Returns:
        tuple: (jogo, pesos) - jogo gerado e pesos utilizados
    """
    pesos = Counter()
    jogo = None

    # 1. Escada Temporal - Inversões
    if usar_inversoes:
        _, _, _, _, _, inversoes = calcular_escada_temporal(df)
        for inv in inversoes[:10]:
            pesos[inv['numero']] += 3

    # 2. Candidatos Ouro
    if usar_candidatos_ouro:
        candidatos_ouro = calcular_candidatos_ouro(contagem_total, df_atrasos)
        for co in candidatos_ouro[:10]:
            pesos[co['numero']] += co['score']

    # 3. Quadrantes
    if usar_quadrantes:
        _, _, quadrante_frio = calcular_quadrantes(df)
        nome_frio, info_frio = quadrante_frio
        for num in info_frio['numeros'][:8]:
            pesos[num] += 2

    # Gerar jogo com os melhores candidatos
    if pesos:
        melhores = [num for num, _ in pesos.most_common(20)]
    else:
        melhores = contagem_total.sort_values().head(20).index.tolist()

    if len(melhores) < 6:
        melhores = list(range(1, 61))

    # Validar soma
    if validar_soma:
        _, stats_soma, _ = calcular_soma_gaussiana(df)
        for _ in range(100):
            jogo = sorted(random.sample(melhores, 6))
            valido, soma, _ = validar_soma_jogo(jogo, stats_soma)
            if valido:
                break
        if jogo is None:
            jogo = sorted(random.sample(melhores, 6))
    else:
        jogo = sorted(random.sample(melhores, 6))

    return jogo, pesos


def gerar_cartoes(n_cartoes, contagem_total, contagem_recente, df_atrasos):
    """
    Gera múltiplos cartões com diferentes estratégias

    Args:
        n_cartoes (int): Quantidade de cartões a gerar
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos

    Returns:
        list: Lista de cartões gerados
    """
    estrategias = [
        'atrasados', 'quentes', 'atraso_recente', 'equilibrado', 'misto',
        'escada', 'consenso', 'aleatorio_smart'
    ]

    cartoes = []
    for i in range(n_cartoes):
        estrategia = estrategias[i % len(estrategias)]
        jogo = gerar_jogo(estrategia, contagem_total,
                          contagem_recente, df_atrasos)
        cartoes.append({
            'numero': i + 1,
            'estrategia': estrategia,
            'dezenas': jogo
        })

    return cartoes


def validar_jogo(jogo):
    """
    Valida se um jogo atende aos critérios básicos

    Args:
        jogo (list): Lista de 6 dezenas

    Returns:
        tuple: (valido, erros) - bool e lista de erros encontrados
    """
    erros = []

    if len(jogo) != 6:
        erros.append(f"Jogo deve ter 6 dezenas (tem {len(jogo)})")

    if len(set(jogo)) != 6:
        erros.append("Jogo contém dezenas duplicadas")

    for num in jogo:
        if not isinstance(num, int) or num < 1 or num > 60:
            erros.append(f"Dezena inválida: {num}")

    return len(erros) == 0, erros


def gerar_jogo_automl(df, contagem_total, contagem_recente, df_atrasos):
    """
    Gera um jogo usando AutoML (PyCaret) para prever probabilidades

    Args:
        df (pd.DataFrame): DataFrame com histórico completo
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos

    Returns:
        list: Lista com 6 dezenas ordenadas
    """
    if not _carregar_pycaret():
        # Fallback: usar estratégia mista se PyCaret não estiver instalado
        return gerar_jogo('misto', contagem_total, contagem_recente, df_atrasos)

    try:
        # Calcular probabilidade para cada número usando modelo rápido
        probabilidades = {}

        # Usar apenas um modelo rápido (Decision Tree) para não demorar muito
        for numero in range(1, 61):
            # Preparar dados para este número
            dados = preparar_dados_pycaret(df, numero, n_concursos=200)

            if dados is not None and len(dados) > 50:
                import io
                import sys
                import logging

                # Suprimir output
                logging.getLogger('pycaret').setLevel(logging.ERROR)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()

                try:
                    # Setup silencioso
                    clf_setup = setup_clf(
                        data=dados,
                        target='saiu',
                        session_id=42,
                        verbose=False,
                        html=False,
                        log_experiment=False,
                        system_log=False
                    )

                    # Criar modelo rápido (Decision Tree)
                    modelo = create_model('dt', verbose=False)

                    # Prever probabilidade para próximo sorteio
                    ultimo_dado = dados.tail(1).drop('saiu', axis=1)
                    previsao = predict_model(
                        modelo, data=ultimo_dado, verbose=False)

                    # Extrair probabilidade de saída
                    if 'prediction_score' in previsao.columns:
                        prob = previsao['prediction_score'].values[0]
                    elif 'Score' in previsao.columns:
                        prob = previsao['Score'].values[0]
                    else:
                        # Tentar pegar primeira coluna numérica
                        prob = previsao.iloc[0, -
                                             1] if len(previsao.columns) > 0 else 0.5

                    probabilidades[numero] = prob

                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                # Dados insuficientes: usar probabilidade padrão
                probabilidades[numero] = 0.5

        # Selecionar top 15 números com maior probabilidade
        top_numeros = sorted(probabilidades.items(),
                             key=lambda x: x[1], reverse=True)[:15]
        candidatos = [num for num, prob in top_numeros]

        # Gerar jogo a partir dos candidatos
        jogo = sorted(random.sample(candidatos, 6))

        return jogo

    except Exception as e:
        # Em caso de erro, usar estratégia mista como fallback
        print(f"Erro no AutoML: {e}. Usando estratégia mista.")
        return gerar_jogo('misto', contagem_total, contagem_recente, df_atrasos)
