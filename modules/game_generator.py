"""
================================================================================
🎲 MÓDULO DE GERAÇÃO DE JOGOS
================================================================================
Geração de jogos com diferentes estratégias
"""

import random
import numpy as np
from collections import Counter, defaultdict
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


from itertools import combinations


def gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos, df=None):
    """
    Gera um jogo baseado na estratégia

    Args:
        estrategia (str): Nome da estratégia
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos
        df (pd.DataFrame, optional): DataFrame completo (necessário para 'escada')

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
        # Usar inversões reais da escada temporal (números esquentando)
        if df is not None:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            if inversoes and len(inversoes) >= 6:
                candidatos = [inv['numero'] for inv in inversoes[:20]]
                jogo = sorted(random.sample(candidatos, min(6, len(candidatos))))
            else:
                candidatos = contagem_total.sort_values().head(15).index.tolist()
                jogo = sorted(random.sample(candidatos, 6))
        else:
            # Fallback sem df: usar números com variação positiva recente
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
        jogo = gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos, df=df)

    elif estrategia == 'sequencias':
        # Clusters + vizinhança + filtros de soma/amplitude
        jogo = _gerar_jogo_sequencias(df, contagem_total)

    elif estrategia == 'wheel':
        # Cobertura combinatória: retorna um jogo do wheel gerado internamente
        jogo = _gerar_jogo_wheel(contagem_total, contagem_recente, df_atrasos, df)

    elif estrategia == 'candidatos_ouro':
        cands = calcular_candidatos_ouro(contagem_total, df_atrasos)
        if len(cands) >= 6:
            candidatos = [c['numero'] for c in cands[:20]]
            jogo = sorted(random.sample(candidatos, 6))
        else:
            candidatos = contagem_total.sort_values().head(20).index.tolist()
            jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'momentum':
        # Razão freq_recente(20) / freq_recente(100); ratio > 1.2 = acelerando
        if df is not None and len(df) >= 100:
            freq20 = Counter()
            for i in range(1, 7):
                freq20.update(df.head(20)[f'dez{i}'].astype(int).tolist())
            freq100 = Counter()
            for i in range(1, 7):
                freq100.update(df.head(100)[f'dez{i}'].astype(int).tolist())
            ratios = {}
            for num in range(1, 61):
                f20 = freq20.get(num, 0) / (20 * 6 / 60)
                f100 = freq100.get(num, 0) / (100 * 6 / 60)
                ratios[num] = f20 / f100 if f100 > 0 else f20
            candidatos = sorted(ratios, key=ratios.get, reverse=True)[:20]
            jogo = sorted(random.sample(candidatos, 6))
        else:
            candidatos = contagem_recente.head(20).index.tolist()
            jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'vizinhanca':
        # Números ±2 do último sorteio como candidatos
        if df is not None and len(df) >= 1:
            ultimo = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
            viz = set()
            for n in ultimo:
                for delta in [-2, -1, 1, 2]:
                    v = n + delta
                    if 1 <= v <= 60 and v not in ultimo:
                        viz.add(v)
            candidatos = list(viz)
            if len(candidatos) >= 6:
                jogo = sorted(random.sample(candidatos, 6))
            else:
                extras = [n for n in range(1, 61) if n not in candidatos and n not in ultimo]
                candidatos.extend(random.sample(extras, 6 - len(candidatos)))
                jogo = sorted(random.sample(candidatos, 6))
        else:
            jogo = sorted(random.sample(range(1, 61), 6))

    elif estrategia == 'frequencia_desvio':
        # Números com freq real > 1 desvio padrão acima da esperada
        freqs = np.array([contagem_total.get(n, 0) for n in range(1, 61)])
        media = freqs.mean()
        desvio = freqs.std()
        candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media + desvio]
        if len(candidatos) < 6:
            candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media]
        if len(candidatos) >= 6:
            jogo = sorted(random.sample(candidatos[:20], min(6, len(candidatos[:20]))))
        else:
            jogo = sorted(random.sample(range(1, 61), 6))

    elif estrategia == 'pares_frequentes':
        # Pares (i,j) mais co-ocorrentes; top pares → números únicos (vetorizado)
        if df is not None and len(df) >= 50:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df.head(200)[cols].values.astype(int)
            co_pairs = Counter()
            for row in mat:
                sr = sorted(row)
                for i in range(6):
                    for j in range(i + 1, 6):
                        co_pairs[(sr[i], sr[j])] += 1
            top_pairs = co_pairs.most_common(30)
            candidatos_set = set()
            for (a, b), _ in top_pairs:
                candidatos_set.add(a)
                candidatos_set.add(b)
            candidatos = list(candidatos_set)
            if len(candidatos) >= 6:
                jogo = sorted(random.sample(candidatos[:20], 6))
            else:
                jogo = sorted(random.sample(range(1, 61), 6))
        else:
            jogo = sorted(random.sample(range(1, 61), 6))

    elif estrategia == 'ciclos':
        # Números cujo gap atual está próximo do ciclo médio (vetorizado)
        if df is not None and len(df) >= 100:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df[cols].values.astype(int)
            scores = {}
            for num in range(1, 61):
                aparicoes = np.where(np.any(mat == num, axis=1))[0]
                if len(aparicoes) >= 3:
                    gaps = np.diff(aparicoes)
                    ciclo_medio = gaps.mean()
                    proximidade = aparicoes[0] / ciclo_medio if ciclo_medio > 0 else 0
                    scores[num] = proximidade
            candidatos = sorted(scores, key=scores.get, reverse=True)[:20]
            if len(candidatos) >= 6:
                jogo = sorted(random.sample(candidatos, 6))
            else:
                jogo = sorted(random.sample(range(1, 61), 6))
        else:
            jogo = sorted(random.sample(range(1, 61), 6))

    elif estrategia == 'ensemble_v2':
        jogo = gerar_jogo_ensemble_v2(contagem_total, contagem_recente, df_atrasos, df=df)

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

    # Filtros universais: se o jogo não passa, tentar regenerar (máx 30x)
    # Estratégias que já aplicam filtros internamente são excluídas
    if estrategia not in ('aleatorio_smart', 'sequencias'):
        jogo = _aplicar_filtros_basicos(
            jogo, estrategia, contagem_total, contagem_recente, df_atrasos, df
        )

    return jogo


def _aplicar_filtros_basicos(jogo, estrategia, contagem_total, contagem_recente, df_atrasos, df):
    """
    Valida soma (140-210), paridade (2-4 pares) e amplitude (>=30) em um jogo de 6.
    Se falhar, tenta regenerar até 30x. Retorna o melhor encontrado.
    """
    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)
    amplitude = jogo[-1] - jogo[0] if len(jogo) >= 2 else 0

    soma_ok = 140 <= soma <= 210
    pares_ok = 2 <= pares <= 4
    amp_ok = amplitude >= 30

    if soma_ok and pares_ok and amp_ok:
        return jogo

    # Tentar regenerar com o mesmo algoritmo
    melhor = jogo
    melhor_score = int(soma_ok) + int(pares_ok) + int(amp_ok)

    for _ in range(30):
        candidato = _gerar_jogo_sem_filtro(
            estrategia, contagem_total, contagem_recente, df_atrasos, df
        )
        s = sum(candidato)
        p = sum(1 for n in candidato if n % 2 == 0)
        a = candidato[-1] - candidato[0] if len(candidato) >= 2 else 0

        score = int(140 <= s <= 210) + int(2 <= p <= 4) + int(a >= 30)
        if score > melhor_score:
            melhor_score = score
            melhor = candidato
        if score == 3:
            return candidato

    return melhor


def _gerar_jogo_sem_filtro(estrategia, contagem_total, contagem_recente, df_atrasos, df):
    """Gera um jogo raw (sem filtros) para uma estratégia. Usado internamente."""
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(20).index.tolist()
        return sorted(random.sample(candidatos, 6))
    elif estrategia == 'quentes':
        candidatos = contagem_recente.head(20).index.tolist()
        return sorted(random.sample(candidatos, 6))
    elif estrategia == 'equilibrado':
        pares = [n for n in range(2, 61, 2)]
        impares = [n for n in range(1, 61, 2)]
        return sorted(random.sample(pares, 3) + random.sample(impares, 3))
    elif estrategia == 'escada':
        if df is not None:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            if inversoes and len(inversoes) >= 6:
                candidatos = [inv['numero'] for inv in inversoes[:20]]
                return sorted(random.sample(candidatos, min(6, len(candidatos))))
        return sorted(random.sample(contagem_total.sort_values().head(15).index.tolist(), 6))
    elif estrategia == 'consenso':
        atrasados = set(contagem_total.sort_values().head(15).index.tolist())
        quentes = set(contagem_recente.head(15).index.tolist())
        atraso_rec = set(df_atrasos.head(15)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        contagem = Counter(todos)
        consenso_nums = [num for num, count in contagem.items() if count >= 2]
        if len(consenso_nums) >= 6:
            return sorted(random.sample(consenso_nums, 6))
        return sorted(random.sample(contagem_total.sort_values().head(20).index.tolist(), 6))
    elif estrategia == 'candidatos_ouro':
        cands = calcular_candidatos_ouro(contagem_total, df_atrasos)
        if len(cands) >= 6:
            candidatos = [c['numero'] for c in cands[:20]]
            return sorted(random.sample(candidatos, 6))
        return sorted(random.sample(contagem_total.sort_values().head(20).index.tolist(), 6))
    elif estrategia == 'momentum':
        if df is not None and len(df) >= 100:
            freq20 = Counter()
            for i in range(1, 7):
                freq20.update(df.head(20)[f'dez{i}'].astype(int).tolist())
            freq100 = Counter()
            for i in range(1, 7):
                freq100.update(df.head(100)[f'dez{i}'].astype(int).tolist())
            ratios = {}
            for num in range(1, 61):
                f20 = freq20.get(num, 0) / (20 * 6 / 60)
                f100 = freq100.get(num, 0) / (100 * 6 / 60)
                ratios[num] = f20 / f100 if f100 > 0 else f20
            candidatos = sorted(ratios, key=ratios.get, reverse=True)[:20]
            return sorted(random.sample(candidatos, 6))
        return sorted(random.sample(contagem_recente.head(20).index.tolist(), 6))
    elif estrategia == 'vizinhanca':
        if df is not None and len(df) >= 1:
            ultimo = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
            viz = set()
            for n in ultimo:
                for delta in [-2, -1, 1, 2]:
                    v = n + delta
                    if 1 <= v <= 60 and v not in ultimo:
                        viz.add(v)
            candidatos = list(viz)
            if len(candidatos) >= 6:
                return sorted(random.sample(candidatos, 6))
            extras = [n for n in range(1, 61) if n not in candidatos and n not in ultimo]
            candidatos.extend(random.sample(extras, 6 - len(candidatos)))
            return sorted(random.sample(candidatos, 6))
        return sorted(random.sample(range(1, 61), 6))
    elif estrategia == 'frequencia_desvio':
        freqs = np.array([contagem_total.get(n, 0) for n in range(1, 61)])
        media = freqs.mean()
        desvio = freqs.std()
        candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media + desvio]
        if len(candidatos) < 6:
            candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media]
        if len(candidatos) >= 6:
            return sorted(random.sample(candidatos[:20], min(6, len(candidatos[:20]))))
        return sorted(random.sample(range(1, 61), 6))
    elif estrategia == 'pares_frequentes':
        if df is not None and len(df) >= 50:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df.head(200)[cols].values.astype(int)
            co_pairs = Counter()
            for row in mat:
                sr = sorted(row)
                for i_idx in range(6):
                    for j_idx in range(i_idx + 1, 6):
                        co_pairs[(sr[i_idx], sr[j_idx])] += 1
            top_pairs = co_pairs.most_common(30)
            cands_set = set()
            for (a, b), _ in top_pairs:
                cands_set.add(a)
                cands_set.add(b)
            candidatos = list(cands_set)
            if len(candidatos) >= 6:
                return sorted(random.sample(candidatos[:20], 6))
        return sorted(random.sample(range(1, 61), 6))
    elif estrategia == 'ciclos':
        if df is not None and len(df) >= 100:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df[cols].values.astype(int)
            scores = {}
            for num in range(1, 61):
                aparicoes = np.where(np.any(mat == num, axis=1))[0]
                if len(aparicoes) >= 3:
                    gaps = np.diff(aparicoes)
                    ciclo_medio = gaps.mean()
                    proximidade = aparicoes[0] / ciclo_medio if ciclo_medio > 0 else 0
                    scores[num] = proximidade
            candidatos = sorted(scores, key=scores.get, reverse=True)[:20]
            if len(candidatos) >= 6:
                return sorted(random.sample(candidatos, 6))
        return sorted(random.sample(range(1, 61), 6))
    else:  # misto e outros
        atrasados = contagem_total.sort_values().head(15).index.tolist()
        quentes_list = contagem_recente.head(15).index.tolist()
        atraso_rec = df_atrasos.head(15)['numero'].tolist()
        jogo = []
        jogo.extend(random.sample(atrasados, 2))
        q_filt = [n for n in quentes_list if n not in jogo]
        jogo.extend(random.sample(q_filt, min(2, len(q_filt))))
        a_filt = [n for n in atraso_rec if n not in jogo]
        if len(a_filt) >= 2:
            jogo.extend(random.sample(a_filt, 2))
        else:
            restantes = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(restantes, 6 - len(jogo)))
        return sorted(jogo[:6])


# Cache para clusters de sequências (evita recomputar KMeans por cartão)
_cache_sequencias = {'key': None, 'cluster_dict': None, 'ultimo_sorteio': None}


def _gerar_jogo_sequencias(df, contagem_total):
    """
    Gera um jogo de 6 números usando clusters de co-ocorrência + vizinhança + filtros.
    Versão standalone sem dependência do Streamlit.
    """
    global _cache_sequencias

    if df is None or len(df) < 50:
        # Fallback: aleatório com filtros básicos
        for _ in range(100):
            jogo = sorted(random.sample(range(1, 61), 6))
            if 140 <= sum(jogo) <= 210:
                return jogo
        return sorted(random.sample(range(1, 61), 6))

    cache_key = len(df)
    if _cache_sequencias['key'] == cache_key:
        cluster_dict = _cache_sequencias['cluster_dict']
        ultimo_sorteio = _cache_sequencias['ultimo_sorteio']
    else:
        # Construir matriz de co-ocorrência
        cols = [f'dez{i}' for i in range(1, 7)]
        co = np.zeros((61, 61), dtype=int)

        for col in cols:
            if col not in df.columns:
                return sorted(random.sample(range(1, 61), 6))

        mat = df[cols].values.astype(int)
        for row in mat:
            for i in range(6):
                for j in range(i + 1, 6):
                    co[row[i]][row[j]] += 1
                    co[row[j]][row[i]] += 1

        # KMeans em 4 clusters
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.cluster import KMeans

            features = co[1:, 1:]
            scaled = StandardScaler().fit_transform(features)
            clusters = KMeans(n_clusters=4, random_state=42, n_init=10).fit_predict(scaled)

            cluster_dict = {}
            for c in range(4):
                cluster_dict[c] = [d + 1 for d in range(60) if clusters[d] == c]
        except Exception:
            # Fallback: dividir em 4 faixas
            cluster_dict = {
                0: list(range(1, 16)),
                1: list(range(16, 31)),
                2: list(range(31, 46)),
                3: list(range(46, 61)),
            }

        # Último sorteio para vizinhança
        ultimo_sorteio = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
        _cache_sequencias = {'key': cache_key, 'cluster_dict': cluster_dict, 'ultimo_sorteio': ultimo_sorteio}

    # Gerar jogo: 1-2 de cada cluster + vizinhança + filtros
    for _ in range(200):
        jogo = []
        for dezenas in cluster_dict.values():
            jogo.extend(random.sample(dezenas, min(2, len(dezenas))))

        # Vizinhança do último sorteio
        viz = set()
        for n in ultimo_sorteio:
            if n > 1:
                viz.add(n - 1)
            if n < 60:
                viz.add(n + 1)
        viz = list(viz - set(ultimo_sorteio) - set(jogo))
        if viz:
            jogo.extend(random.sample(viz, min(1, len(viz))))

        # Ajustar para exatamente 6
        if len(jogo) > 6:
            jogo = random.sample(jogo, 6)
        elif len(jogo) < 6:
            resto = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(resto, 6 - len(jogo)))
        jogo = sorted(jogo)

        # Filtros de qualidade
        soma = sum(jogo)
        amp = jogo[-1] - jogo[0]
        pares = sum(1 for n in jogo if n % 2 == 0)
        if 143 <= soma <= 223 and amp >= 30 and 2 <= pares <= 4:
            return jogo

    return sorted(random.sample(range(1, 61), 6))


def gerar_wheel(pool, tamanho_cartao=6, cobertura_k=3):
    """
    Gera um conjunto de cartões que cobrem todas as combinações de K números
    dentro de um pool dado. Wheel reduzido (greedy covering design).

    Args:
        pool (list): Pool de números candidatos (ex: 18 melhores)
        tamanho_cartao (int): Números por cartão (6 para Mega-Sena)
        cobertura_k (int): Garantia de cobertura — todo subconjunto de K números
                           do pool aparece em pelo menos um cartão (padrão: 3)

    Returns:
        list[list[int]]: Lista de cartões (cada um é uma lista ordenada)
    """
    pool = sorted(set(pool))
    if len(pool) <= tamanho_cartao:
        return [pool[:tamanho_cartao]]

    # Gerar todos os subconjuntos de tamanho K que precisam ser cobertos
    alvos = set(combinations(pool, cobertura_k))

    cartoes = []
    while alvos:
        # Greedy: escolher o cartão de 6 números que cobre mais alvos restantes
        melhor_cartao = None
        melhor_cobertura = 0

        # Amostrar candidatos para não explodir combinatoriamente
        todos_cartoes_possiveis = list(combinations(pool, tamanho_cartao))
        if len(todos_cartoes_possiveis) > 2000:
            candidatos_sample = random.sample(todos_cartoes_possiveis, 2000)
        else:
            candidatos_sample = todos_cartoes_possiveis

        for cartao in candidatos_sample:
            subcombos = set(combinations(cartao, cobertura_k))
            cobertura = len(subcombos & alvos)
            if cobertura > melhor_cobertura:
                melhor_cobertura = cobertura
                melhor_cartao = cartao

        if melhor_cartao is None:
            break

        cartoes.append(sorted(melhor_cartao))
        subcombos_cobertos = set(combinations(melhor_cartao, cobertura_k))
        alvos -= subcombos_cobertos

    return cartoes


def _gerar_jogo_wheel(contagem_total, contagem_recente, df_atrasos, df):
    """
    Gera UM jogo usando a lógica de wheel/cobertura.
    Seleciona pool dos 18 melhores candidatos (consenso), monta wheel
    e retorna o primeiro cartão.
    """
    # Montar pool de 18 números por consenso
    atrasados = set(contagem_total.sort_values().head(20).index.tolist())
    quentes = set(contagem_recente.head(20).index.tolist())
    atraso_rec = set(df_atrasos.head(20)['numero'].tolist())

    todos = list(atrasados) + list(quentes) + list(atraso_rec)
    contagem = Counter(todos)
    pool = [num for num, _ in contagem.most_common(18)]

    if len(pool) < 6:
        pool = list(range(1, 19))

    # Gerar wheel e retornar um cartão aleatório do set
    cartoes = gerar_wheel(pool, tamanho_cartao=6, cobertura_k=3)
    if cartoes:
        return random.choice(cartoes)
    return sorted(random.sample(pool, 6))


def gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos, df=None):
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
            jogo = gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
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


def gerar_jogo_ensemble_v2(contagem_total, contagem_recente, df_atrasos, df=None):
    """
    Ensemble V2: vota apenas com as 7 melhores estratégias (exclui escada e atrasados).
    Estratégias votantes: quentes, sequencias, consenso, atraso_recente,
    candidatos_ouro, momentum, vizinhanca.
    """
    estrategias = [
        'quentes', 'frequencia_desvio', 'consenso', 'atraso_recente',
        'candidatos_ouro', 'momentum', 'vizinhanca'
    ]

    votos = Counter()
    for est in estrategias:
        try:
            jogo = gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
            for n in jogo:
                votos[n] += 1
        except Exception:
            pass

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    for _ in range(100):
        pool = candidatos[:20]
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if 2 <= pares <= 4 and 140 <= soma <= 210:
            return jogo

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


def expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                  contagem_total, contagem_recente, df_atrasos, df=None):
    """
    Expande um jogo de 6 para N números mantendo coerência da estratégia.
    Aplica filtros de soma, paridade e amplitude.

    Args:
        dezenas_base (list): Jogo base com 6 números
        qtd_numeros (int): Quantidade final de números desejada
        estrategia (str): Estratégia usada para gerar a base
        contagem_total (pd.Series): Contagem total de frequência
        contagem_recente (pd.Series): Contagem recente de frequência
        df_atrasos (pd.DataFrame): DataFrame com atrasos
        df (pd.DataFrame, optional): DataFrame completo para 'escada'

    Returns:
        list: Jogo expandido e ordenado
    """
    pool_size = max(40, qtd_numeros + 10)
    extras_necessarios = qtd_numeros - len(dezenas_base)

    if extras_necessarios <= 0:
        return sorted(dezenas_base[:qtd_numeros])

    # Pool de candidatos coerente com a estratégia
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(pool_size).index.tolist()
    elif estrategia == 'quentes':
        candidatos = contagem_recente.nlargest(pool_size).index.tolist()
    elif estrategia == 'escada':
        try:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            candidatos = [inv['numero'] for inv in inversoes[:pool_size]] if inversoes else list(range(1, 61))
        except Exception:
            candidatos = list(range(1, 61))
    elif estrategia == 'equilibrado':
        candidatos = list(range(1, 61))
    elif estrategia == 'consenso':
        atrasados = set(contagem_total.sort_values().head(20).index.tolist())
        quentes = set(contagem_recente.nlargest(20).index.tolist())
        atraso_rec = set(df_atrasos.head(20)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        contagem = Counter(todos)
        candidatos = [num for num, _ in contagem.most_common(pool_size)]
    elif estrategia == 'misto':
        atrasados = contagem_total.sort_values().head(20).index.tolist()
        quentes = contagem_recente.nlargest(20).index.tolist()
        candidatos = list(set(atrasados + quentes))
        if len(candidatos) < pool_size:
            candidatos.extend([n for n in range(1, 61) if n not in candidatos])
    else:
        candidatos = list(range(1, 61))

    candidatos = [n for n in candidatos if n not in dezenas_base]

    # Tentar gerar expansão com filtros de qualidade
    melhor_jogo = None
    melhor_score = -1

    for _ in range(50):
        random.shuffle(candidatos)
        extras = candidatos[:extras_necessarios]
        jogo = sorted(dezenas_base + extras)

        # Filtros proporcionais ao qtd_numeros
        soma = sum(jogo)
        pares = sum(1 for n in jogo if n % 2 == 0)
        amplitude = jogo[-1] - jogo[0]

        fator = qtd_numeros / 6.0
        soma_ok = (140 * fator * 0.8) <= soma <= (210 * fator * 1.1)
        pares_ok = (qtd_numeros * 0.3) <= pares <= (qtd_numeros * 0.7)
        amp_ok = amplitude >= 30

        score = int(soma_ok) + int(pares_ok) + int(amp_ok)
        if score > melhor_score:
            melhor_score = score
            melhor_jogo = jogo
        if score == 3:
            break

    return melhor_jogo or sorted(dezenas_base + candidatos[:extras_necessarios])


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
