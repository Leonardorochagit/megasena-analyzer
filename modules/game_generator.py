"""
================================================================================
🎲 MÓDULO DE GERAÇÃO DE JOGOS
================================================================================
Geração de jogos com diferentes estratégias
"""

import random
import logging
import numpy as np
from collections import Counter, defaultdict
from itertools import combinations
from modules.statistics import (
    calcular_escada_temporal,
    calcular_candidatos_ouro,
    calcular_quadrantes,
    calcular_soma_gaussiana,
    validar_soma_jogo,
    preparar_dados_pycaret
)
from helpers import FILTROS_JOGO, JANELAS_ANALISE

logger = logging.getLogger(__name__)

# PyCaret será importado sob demanda (lazy) para não travar o carregamento
PYCARET_DISPONIVEL = None
setup_clf = None
predict_model = None
create_model = None


def _carregar_pycaret():
    """Carrega PyCaret sob demanda."""
    global PYCARET_DISPONIVEL, setup_clf, predict_model, create_model
    if PYCARET_DISPONIVEL is not None:
        return PYCARET_DISPONIVEL
    try:
        from pycaret.classification import setup as _setup
        from pycaret.classification import predict_model as _predict
        from pycaret.classification import create_model as _create
        setup_clf = _setup
        predict_model = _predict
        create_model = _create
        PYCARET_DISPONIVEL = True
    except (ImportError, RuntimeError):
        PYCARET_DISPONIVEL = False
    return PYCARET_DISPONIVEL


# Cache para clusters de sequências (evita recomputar KMeans por cartão)
_cache_sequencias = {'key': None, 'cluster_dict': None, 'ultimo_sorteio': None}


def gerar_jogo(
    estrategia: str,
    contagem_total,
    contagem_recente,
    df_atrasos,
    df=None
) -> list[int]:
    """
    Gera um jogo baseado na estratégia.

    Args:
        estrategia: Nome da estratégia
        contagem_total: Contagem total de frequência
        contagem_recente: Contagem recente de frequência
        df_atrasos: DataFrame com atrasos
        df: DataFrame completo (necessário para 'escada')

    Returns:
        list: Lista com 6 dezenas ordenadas
    """
    jogo = _gerar_pool_estrategia(
        estrategia=estrategia,
        tamanho=6,
        contagem_total=contagem_total,
        contagem_recente=contagem_recente,
        df_atrasos=df_atrasos,
        df=df
    )

    # Filtros universais: estratégias que já aplicam filtros internamente são excluídas
    if estrategia not in ('aleatorio_smart', 'sequencias'):
        jogo = _aplicar_filtros_basicos(
            jogo, estrategia, contagem_total, contagem_recente, df_atrasos, df
        )

    return jogo


def _aplicar_filtros_basicos(
    jogo: list[int],
    estrategia: str,
    contagem_total,
    contagem_recente,
    df_atrasos,
    df
) -> list[int]:
    """
    Valida soma, paridade e amplitude em um jogo de 6.
    Se falhar, tenta regenerar até `tentativas_max // 3`. Retorna o melhor encontrado.
    """
    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)
    amplitude = jogo[-1] - jogo[0] if len(jogo) >= 2 else 0

    soma_min = FILTROS_JOGO['soma_min']
    soma_max = FILTROS_JOGO['soma_max']
    pares_min = FILTROS_JOGO['pares_min']
    pares_max = FILTROS_JOGO['pares_max']
    amp_min = FILTROS_JOGO['amplitude_min']
    max_tentativas = FILTROS_JOGO['tentativas_max']

    soma_ok = soma_min <= soma <= soma_max
    pares_ok = pares_min <= pares <= pares_max
    amp_ok = amplitude >= amp_min

    if soma_ok and pares_ok and amp_ok:
        return jogo

    melhor = jogo
    melhor_score = int(soma_ok) + int(pares_ok) + int(amp_ok)

    for _ in range(max_tentativas // 3):
        candidato = _gerar_pool_estrategia(
            estrategia=estrategia,
            tamanho=6,
            contagem_total=contagem_total,
            contagem_recente=contagem_recente,
            df_atrasos=df_atrasos,
            df=df
        )
        s = sum(candidato)
        p = sum(1 for n in candidato if n % 2 == 0)
        a = candidato[-1] - candidato[0] if len(candidato) >= 2 else 0

        score = (
            int(soma_min <= s <= soma_max)
            + int(pares_min <= p <= pares_max)
            + int(a >= amp_min)
        )
        if score > melhor_score:
            melhor_score = score
            melhor = candidato
        if score == 3:
            return candidato

    return melhor


def _gerar_pool_estrategia(
    estrategia: str,
    tamanho: int,
    contagem_total,
    contagem_recente,
    df_atrasos,
    df=None
) -> list[int]:
    """
    Função unificada para gerar pool de candidatos por estratégia.
    Elimina duplicação de código entre gerar_jogo e helpers.
    """
    janela_recente = JANELAS_ANALISE['recente']
    janela_co = JANELAS_ANALISE['co_ocorrencia']
    janela_momentum_curta = JANELAS_ANALISE['momentum_curto']
    janela_momentum_longa = JANELAS_ANALISE['momentum_longo']
    ciclos_min = JANELAS_ANALISE['ciclos_min']

    top_n = tamanho + 14  # pool um pouco maior para sampling

    if estrategia == 'atrasados':
        candidatos = list(contagem_total.sort_values().head(top_n).index)
        return sorted(random.sample(candidatos, tamanho))

    elif estrategia == 'quentes':
        candidatos = list(contagem_recente.head(top_n).index)
        return sorted(random.sample(candidatos, tamanho))

    elif estrategia == 'equilibrado':
        pares_list = [n for n in range(2, 61, 2)]
        impares = [n for n in range(1, 61, 2)]
        return sorted(random.sample(pares_list, tamanho // 2) + random.sample(impares, tamanho - tamanho // 2))

    elif estrategia == 'escada':
        if df is not None:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            if inversoes and len(inversoes) >= tamanho:
                nums_inversao = [inv['numero'] for inv in inversoes]
                return sorted(random.sample(nums_inversao[:top_n], tamanho))
        return sorted(random.sample(list(contagem_total.sort_values().head(top_n).index), tamanho))

    elif estrategia == 'consenso':
        atrasados = set(contagem_total.sort_values().head(15).index.tolist())
        quentes = set(contagem_recente.head(15).index.tolist())
        atraso_rec = set(df_atrasos.head(15)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        contagem = Counter(todos)
        consenso_nums = [num for num, count in contagem.items() if count >= 2]
        if len(consenso_nums) >= tamanho:
            return sorted(random.sample(consenso_nums, tamanho))
        return sorted(random.sample(list(contagem_total.sort_values().head(top_n).index), tamanho))

    elif estrategia == 'candidatos_ouro':
        cands = calcular_candidatos_ouro(contagem_total, df_atrasos)
        if len(cands) >= tamanho:
            candidatos = [c['numero'] for c in cands[:top_n]]
        else:
            candidatos = list(contagem_total.sort_values().head(top_n).index)
        return sorted(random.sample(candidatos, tamanho))

    elif estrategia == 'momentum':
        if df is not None and len(df) >= janela_momentum_longa:
            freq_curta = Counter()
            freq_longa = Counter()
            for i in range(1, 7):
                freq_curta.update(df.head(janela_momentum_curta)[f'dez{i}'].astype(int).tolist())
                freq_longa.update(df.head(janela_momentum_longa)[f'dez{i}'].astype(int).tolist())
            ratios = {}
            for num in range(1, 61):
                f_curta = freq_curta.get(num, 0) / (janela_momentum_curta * 6 / 60)
                f_longa = freq_longa.get(num, 0) / (janela_momentum_longa * 6 / 60)
                ratios[num] = f_curta / f_longa if f_longa > 0 else f_curta
            candidatos = sorted(ratios, key=lambda n: ratios.get(n, 0), reverse=True)[:top_n]
        else:
            candidatos = list(contagem_recente.head(top_n).index)
        return sorted(random.sample(candidatos, tamanho))

    elif estrategia == 'vizinhanca':
        if df is not None and len(df) >= 1:
            ultimo = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
            viz = set()
            for n in ultimo:
                for delta in [-2, -1, 1, 2]:
                    v = n + delta
                    if 1 <= v <= 60 and v not in ultimo:
                        viz.add(v)
            if len(viz) >= tamanho:
                return sorted(random.sample(list(viz), tamanho))
            extras = [n for n in range(1, 61) if n not in viz and n not in ultimo]
            viz.update(random.sample(extras, max(0, tamanho - len(viz))))
            return sorted(random.sample(list(viz), min(tamanho, len(viz))))
        return sorted(random.sample(list(range(1, 61)), tamanho))

    elif estrategia == 'frequencia_desvio':
        freqs = np.array([contagem_total.get(n, 0) for n in range(1, 61)])
        media = freqs.mean()
        desvio = freqs.std()
        candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media + desvio]
        if len(candidatos) < tamanho:
            candidatos = [n for n in range(1, 61) if contagem_total.get(n, 0) > media]
        if len(candidatos) >= tamanho:
            return sorted(random.sample(candidatos[:top_n], tamanho))
        return sorted(random.sample(list(range(1, 61)), tamanho))

    elif estrategia == 'pares_frequentes':
        if df is not None and len(df) >= 50:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df.head(janela_co)[cols].values.astype(int)
            co_pairs = Counter()
            for row in mat:
                sr = sorted(row)
                for i_idx in range(6):
                    for j_idx in range(i_idx + 1, 6):
                        co_pairs[(sr[i_idx], sr[j_idx])] += 1
            cands_set = set()
            for (a, b), _ in co_pairs.most_common(30):
                cands_set.add(a)
                cands_set.add(b)
            if len(cands_set) >= tamanho:
                return sorted(random.sample(list(cands_set)[:top_n], tamanho))
        return sorted(random.sample(list(range(1, 61)), tamanho))

    elif estrategia == 'ciclos':
        if df is not None and len(df) >= ciclos_min:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df[cols].values.astype(int)
            scores = {}
            for num in range(1, 61):
                aparicoes = np.where(np.any(mat == num, axis=1))[0]
                if len(aparicoes) >= 3:
                    gaps = np.diff(aparicoes)
                    ciclo_medio = gaps.mean()
                    scores[num] = aparicoes[0] / ciclo_medio if ciclo_medio > 0 else 0
            candidatos = sorted(scores, key=lambda n: scores.get(n, 0), reverse=True)[:top_n]
            return sorted(random.sample(candidatos, tamanho))
        return sorted(random.sample(list(range(1, 61)), tamanho))

    elif estrategia == 'atraso_recente':
        janela = janela_recente * 2  # 100 jogos
        if df is not None and len(df) >= janela:
            ultimos = df.head(janela)
            freq_ultimos = Counter()
            for i in range(1, 7):
                freq_ultimos.update(ultimos[f'dez{i}'].astype(int).tolist())
            media_ultimos = sum(freq_ultimos.values()) / 60
            atrasados_recentes = [
                n for n in range(1, 61)
                if freq_ultimos.get(n, 0) < media_ultimos * 0.5
            ]
            if len(atrasados_recentes) >= tamanho:
                return sorted(random.sample(atrasados_recentes[:top_n], tamanho))
        candidatos = list(df_atrasos.head(top_n)['numero'])
        return sorted(random.sample(candidatos, tamanho))

    elif estrategia == 'aleatorio_smart':
        max_tentativas = FILTROS_JOGO['tentativas_max']
        soma_min = FILTROS_JOGO['soma_min']
        soma_max = FILTROS_JOGO['soma_max']
        pares_min = FILTROS_JOGO['pares_min']
        pares_max = FILTROS_JOGO['pares_max']
        for _ in range(max_tentativas):
            jogo = sorted(random.sample(range(1, 61), tamanho))
            pares = sum(1 for n in jogo if n % 2 == 0)
            soma = sum(jogo)
            if pares_min <= pares <= pares_max and soma_min <= soma <= soma_max:
                return jogo
        return sorted(random.sample(range(1, 61), tamanho))

    elif estrategia == 'sequencias':
        return _gerar_jogo_sequencias(df, contagem_total)

    elif estrategia == 'wheel':
        return _gerar_jogo_wheel(contagem_total, contagem_recente, df_atrasos, df)

    elif estrategia == 'ensemble':
        return gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos, df=df)

    else:  # misto e fallback
        atrasados = list(contagem_total.sort_values().head(15).index)
        quentes_list = list(contagem_recente.head(15).index)
        atraso_rec = list(df_atrasos.head(15)['numero'])
        jogo = []
        jogo.extend(random.sample(atrasados, min(2, len(atrasados))))
        q_filt = [n for n in quentes_list if n not in jogo]
        jogo.extend(random.sample(q_filt, min(2, len(q_filt))))
        a_filt = [n for n in atraso_rec if n not in jogo]
        if len(a_filt) >= 2:
            jogo.extend(random.sample(a_filt, 2))
        else:
            restantes = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(restantes, tamanho - len(jogo)))
        return sorted(jogo[:tamanho])


def _gerar_jogo_sequencias(df, contagem_total) -> list[int]:
    """
    Gera um jogo de 6 números usando clusters de co-ocorrência + vizinhança + filtros.
    Versão standalone sem dependência do Streamlit.
    """
    global _cache_sequencias

    if df is None or len(df) < 50:
        for _ in range(FILTROS_JOGO['tentativas_max']):
            jogo = sorted(random.sample(range(1, 61), 6))
            if FILTROS_JOGO['soma_min'] <= sum(jogo) <= FILTROS_JOGO['soma_max']:
                return jogo
        return sorted(random.sample(range(1, 61), 6))

    cache_key = len(df)
    if _cache_sequencias['key'] == cache_key:
        cluster_dict = _cache_sequencias['cluster_dict']
        ultimo_sorteio = _cache_sequencias['ultimo_sorteio']
    else:
        cols = [f'dez{i}' for i in range(1, 7)]
        for col in cols:
            if col not in df.columns:
                return sorted(random.sample(range(1, 61), 6))

        co = np.zeros((61, 61), dtype=int)
        mat = df[cols].values.astype(int)
        for row in mat:
            for i in range(6):
                for j in range(i + 1, 6):
                    co[row[i]][row[j]] += 1
                    co[row[j]][row[i]] += 1

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
            cluster_dict = {
                0: list(range(1, 16)),
                1: list(range(16, 31)),
                2: list(range(31, 46)),
                3: list(range(46, 61)),
            }

        ultimo_sorteio = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
        _cache_sequencias = {
            'key': cache_key,
            'cluster_dict': cluster_dict,
            'ultimo_sorteio': ultimo_sorteio
        }

    for _ in range(200):
        jogo = []
        for dezenas in cluster_dict.values():
            jogo.extend(random.sample(dezenas, min(2, len(dezenas))))

        viz = set()
        for n in ultimo_sorteio:
            if n > 1:
                viz.add(n - 1)
            if n < 60:
                viz.add(n + 1)
        viz = list(viz - set(ultimo_sorteio) - set(jogo))
        if viz:
            jogo.extend(random.sample(viz, min(1, len(viz))))

        if len(jogo) > 6:
            jogo = random.sample(jogo, 6)
        elif len(jogo) < 6:
            resto = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(resto, 6 - len(jogo)))
        jogo = sorted(jogo)

        soma = sum(jogo)
        amp = jogo[-1] - jogo[0]
        pares = sum(1 for n in jogo if n % 2 == 0)
        if 143 <= soma <= 223 and amp >= 30 and 2 <= pares <= 4:
            return jogo

    return sorted(random.sample(range(1, 61), 6))


def _gerar_jogo_wheel(contagem_total, contagem_recente, df_atrasos, df) -> list[int]:
    """Gera UM jogo usando a lógica de wheel/cobertura."""
    atrasados = set(contagem_total.sort_values().head(20).index.tolist())
    quentes = set(contagem_recente.head(20).index.tolist())
    atraso_rec = set(df_atrasos.head(20)['numero'].tolist())

    todos = list(atrasados) + list(quentes) + list(atraso_rec)
    contagem = Counter(todos)
    pool = [num for num, _ in contagem.most_common(18)]

    if len(pool) < 6:
        pool = list(range(1, 19))

    cartoes = gerar_wheel(pool, tamanho_cartao=6, cobertura_k=3)
    if cartoes:
        return random.choice(cartoes)
    return sorted(random.sample(pool, 6))


def gerar_wheel(pool, tamanho_cartao=6, cobertura_k=3) -> list[list[int]]:
    """
    Gera um conjunto de cartões que cobrem todas as combinações de K números
    dentro de um pool dado. Wheel reduzido (greedy covering design).
    """
    pool = sorted(set(pool))
    if len(pool) <= tamanho_cartao:
        return [pool[:tamanho_cartao]]

    alvos = set(combinations(pool, cobertura_k))
    cartoes = []
    while alvos:
        melhor_cartao = None
        melhor_cobertura = 0

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


def gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos, df=None) -> list[int]:
    """
    Estratégia ensemble: gera um jogo de cada estratégia disponível,
    conta a frequência de cada número nas saídas e seleciona
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
        except Exception as e:
            logger.warning("Erro ao gerar jogo ensemble para %s: %s", est, e)

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    pool_size = min(20, len(candidatos))
    soma_min = FILTROS_JOGO['soma_min']
    soma_max = FILTROS_JOGO['soma_max']
    pares_min = FILTROS_JOGO['pares_min']
    pares_max = FILTROS_JOGO['pares_max']

    for _ in range(100):
        pool = candidatos[:pool_size]
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if pares_min <= pares <= pares_max and soma_min <= soma <= soma_max:
            return jogo

    return sorted(candidatos[:6])


def gerar_jogo_avancado(
    contagem_total, contagem_recente, df_atrasos, df,
    usar_inversoes=True, usar_candidatos_ouro=True,
    usar_quadrantes=True, validar_soma=True,
    validar_linhas=True
):
    """
    Gera jogo utilizando todas as análises avançadas.

    Returns:
        tuple: (jogo, pesos)
    """
    pesos = Counter()

    if usar_inversoes:
        _, _, _, _, _, inversoes = calcular_escada_temporal(df)
        for inv in inversoes[:10]:
            pesos[inv['numero']] += 3

    if usar_candidatos_ouro:
        candidatos_ouro = calcular_candidatos_ouro(contagem_total, df_atrasos)
        for co in candidatos_ouro[:10]:
            pesos[co['numero']] += co['score']

    if usar_quadrantes:
        _, _, quadrante_frio = calcular_quadrantes(df)
        nome_frio, info_frio = quadrante_frio
        for num in info_frio['numeros'][:8]:
            pesos[num] += 2

    if pesos:
        melhores = [num for num, _ in pesos.most_common(20)]
    else:
        melhores = list(contagem_total.sort_values().head(20).index)

    if len(melhores) < 6:
        melhores = list(range(1, 61))

    if validar_soma:
        _, stats_soma, _ = calcular_soma_gaussiana(df)
        for _ in range(FILTROS_JOGO['tentativas_max']):
            jogo = sorted(random.sample(melhores, 6))
            valido, soma, _ = validar_soma_jogo(jogo, stats_soma)
            if valido:
                return jogo, pesos
        return sorted(random.sample(melhores, 6)), pesos
    else:
        return sorted(random.sample(melhores, 6)), pesos


def _pool_candidatos_expansao(
    estrategia, pool_size, contagem_total, contagem_recente, df_atrasos, df=None
) -> list[int]:
    """
    Retorna um pool de candidatos coerente com a lógica de cada estratégia,
    usado para expandir jogos de 6 para N números.
    """
    janela_co = JANELAS_ANALISE['co_ocorrencia']
    ciclos_min = JANELAS_ANALISE['ciclos_min']

    if estrategia == 'atrasados':
        return list(contagem_total.sort_values().head(pool_size).index)

    if estrategia == 'quentes':
        return list(contagem_recente.nlargest(pool_size).index)

    if estrategia == 'escada':
        cand = []
        try:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            cand = [int(inv['numero']) for inv in inversoes] if inversoes else []
        except Exception:
            pass
        if len(cand) < pool_size:
            atrasos = list(contagem_total.sort_values().head(pool_size).index)
            cand.extend([int(n) for n in atrasos if int(n) not in cand])
        return cand[:pool_size]

    if estrategia in ('consenso', 'wheel'):
        atrasados = set(contagem_total.sort_values().head(20).index.tolist())
        quentes = set(contagem_recente.nlargest(20).index.tolist())
        atraso_rec = set(df_atrasos.head(20)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        cand = [num for num, _ in Counter(todos).most_common(pool_size)]
        if len(cand) < pool_size:
            cand.extend([n for n in range(1, 61) if n not in cand])
        return cand[:pool_size]

    if estrategia == 'misto':
        atrasados = list(contagem_total.sort_values().head(25).index)
        quentes = list(contagem_recente.nlargest(25).index)
        cand = list(dict.fromkeys(atrasados + quentes))
        if len(cand) < pool_size:
            cand.extend([n for n in range(1, 61) if n not in cand])
        return cand[:pool_size]

    if estrategia == 'candidatos_ouro':
        cand = []
        try:
            cands = calcular_candidatos_ouro(contagem_total, df_atrasos)
            cand = [int(c['numero']) for c in cands]
        except Exception:
            pass
        if len(cand) < pool_size:
            atrasos = list(contagem_total.sort_values().head(pool_size).index)
            cand.extend([int(n) for n in atrasos if int(n) not in cand])
        return cand[:pool_size]

    if estrategia == 'momentum':
        if df is not None and len(df) >= 100:
            freq20 = Counter()
            freq100 = Counter()
            for i in range(1, 7):
                freq20.update(df.head(20)[f'dez{i}'].astype(int).tolist())
                freq100.update(df.head(100)[f'dez{i}'].astype(int).tolist())
            ratios = {}
            for num in range(1, 61):
                f20 = freq20.get(num, 0) / (20 * 6 / 60)
                f100 = freq100.get(num, 0) / (100 * 6 / 60)
                ratios[num] = f20 / f100 if f100 > 0 else f20
            return sorted(ratios, key=ratios.get, reverse=True)[:pool_size]
        return list(contagem_recente.nlargest(pool_size).index)

    if estrategia == 'vizinhanca':
        if df is not None and len(df) >= 1:
            ultimo = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
            viz = set()
            for n in ultimo:
                for delta in [-3, -2, -1, 1, 2, 3]:
                    v = n + delta
                    if 1 <= v <= 60 and v not in ultimo:
                        viz.add(v)
            cand = list(viz)
            if len(cand) < pool_size:
                extras = list(contagem_total.sort_values().head(pool_size).index)
                cand.extend([n for n in extras if n not in cand])
            return cand[:pool_size]
        return list(range(1, 61))

    if estrategia == 'frequencia_desvio':
        freqs = np.array([contagem_total.get(n, 0) for n in range(1, 61)])
        media = freqs.mean()
        cand = sorted(
            [n for n in range(1, 61) if contagem_total.get(n, 0) > media],
            key=lambda n: contagem_total.get(n, 0),
            reverse=True
        )
        if len(cand) < pool_size:
            cand.extend([n for n in range(1, 61) if n not in cand])
        return cand[:pool_size]

    if estrategia == 'pares_frequentes':
        if df is not None and len(df) >= 50:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df.head(janela_co)[cols].values.astype(int)
            co_pairs = Counter()
            for row in mat:
                sr = sorted(row)
                for i in range(6):
                    for j in range(i + 1, 6):
                        co_pairs[(sr[i], sr[j])] += 1
            num_score = Counter()
            for (a, b), cnt in co_pairs.most_common(80):
                num_score[a] += cnt
                num_score[b] += cnt
            cand = [n for n, _ in num_score.most_common(pool_size)]
            if len(cand) < pool_size:
                cand.extend([n for n in range(1, 61) if n not in cand])
            return cand[:pool_size]
        return list(range(1, 61))

    if estrategia == 'ciclos':
        if df is not None and len(df) >= ciclos_min:
            cols = [f'dez{i}' for i in range(1, 7)]
            mat = df[cols].values.astype(int)
            scores = {}
            for num in range(1, 61):
                aparicoes = np.where(np.any(mat == num, axis=1))[0]
                if len(aparicoes) >= 3:
                    gaps = np.diff(aparicoes)
                    ciclo_medio = gaps.mean()
                    scores[num] = aparicoes[0] / ciclo_medio if ciclo_medio > 0 else 0
            cand = sorted(scores, key=scores.get, reverse=True)[:pool_size]
            if len(cand) < pool_size:
                cand.extend([n for n in range(1, 61) if n not in cand])
            return cand[:pool_size]
        return list(range(1, 61))

    if estrategia == 'sequencias':
        cand = list(contagem_total.nlargest(30).index)
        if df is not None and len(df) >= 1:
            ultimo = [int(df.iloc[0][f'dez{i}']) for i in range(1, 7)]
            for n in ultimo:
                for delta in [-2, -1, 1, 2]:
                    v = n + delta
                    if 1 <= v <= 60 and v not in cand and v not in ultimo:
                        cand.append(v)
        if len(cand) < pool_size:
            cand.extend([n for n in range(1, 61) if n not in cand])
        return cand[:pool_size]

    return list(range(1, 61))


def expandir_jogo(
    dezenas_base, qtd_numeros, estrategia,
    contagem_total, contagem_recente, df_atrasos, df=None
) -> list[int]:
    """
    Expande um jogo de 6 para N números mantendo coerência da estratégia.
    Aplica filtros de soma, paridade e amplitude.
    """
    pool_size = max(40, qtd_numeros + 10)
    extras_necessarios = qtd_numeros - len(dezenas_base)

    if extras_necessarios <= 0:
        return sorted(dezenas_base[:qtd_numeros])

    candidatos = _pool_candidatos_expansao(
        estrategia, pool_size, contagem_total, contagem_recente, df_atrasos, df
    )
    candidatos = [int(n) for n in candidatos if int(n) not in dezenas_base]
    if len(candidatos) < extras_necessarios:
        candidatos.extend([n for n in range(1, 61) if n not in dezenas_base and n not in candidatos])

    melhor_jogo = None
    melhor_score = -1

    for _ in range(50):
        random.shuffle(candidatos)
        extras = candidatos[:extras_necessarios]
        jogo = sorted(dezenas_base + extras)

        soma = sum(jogo)
        pares = sum(1 for n in jogo if n % 2 == 0)
        amplitude = jogo[-1] - jogo[0]

        fator = qtd_numeros / 6.0
        soma_min = FILTROS_JOGO['soma_min'] * fator * 0.8
        soma_max = FILTROS_JOGO['soma_max'] * fator * 1.1
        pares_min = int(qtd_numeros * 0.3)
        pares_max = int(qtd_numeros * 0.7)
        amp_min = FILTROS_JOGO['amplitude_min']

        soma_ok = soma_min <= soma <= soma_max
        pares_ok = pares_min <= pares <= pares_max
        amp_ok = amplitude >= amp_min

        score = int(soma_ok) + int(pares_ok) + int(amp_ok)
        if score > melhor_score:
            melhor_score = score
            melhor_jogo = jogo
        if score == 3:
            break

    return melhor_jogo or sorted(dezenas_base + candidatos[:extras_necessarios])


def gerar_cartoes(n_cartoes, contagem_total, contagem_recente, df_atrasos) -> list[dict]:
    """
    Gera múltiplos cartões com diferentes estratégias.
    """
    estrategias = [
        'atrasados', 'quentes', 'atraso_recente', 'equilibrado', 'misto',
        'escada', 'consenso', 'aleatorio_smart'
    ]

    cartoes = []
    for i in range(n_cartoes):
        estrategia = estrategias[i % len(estrategias)]
        jogo = gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos)
        cartoes.append({
            'numero': i + 1,
            'estrategia': estrategia,
            'dezenas': jogo
        })

    return cartoes


def validar_jogo(jogo: list[int]) -> tuple[bool, list[str]]:
    """
    Valida se um jogo atende aos critérios básicos.

    Returns:
        tuple: (valido, erros)
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


def gerar_jogo_automl(df, contagem_total, contagem_recente, df_atrasos) -> list[int]:
    """
    Gera um jogo usando AutoML (PyCaret) para prever probabilidades.
    """
    if not _carregar_pycaret():
        return gerar_jogo('misto', contagem_total, contagem_recente, df_atrasos)

    try:
        import io
        import sys
        import logging

        probabilidades = {}

        for numero in range(1, 61):
            dados = preparar_dados_pycaret(df, numero, n_concursos=200)

            if dados is not None and len(dados) > 50:
                logging.getLogger('pycaret').setLevel(logging.ERROR)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()

                try:
                    clf_setup = setup_clf(
                        data=dados,
                        target='saiu',
                        session_id=42,
                        verbose=False,
                        html=False,
                        log_experiment=False,
                        system_log=False
                    )

                    modelo = create_model('dt', verbose=False)
                    ultimo_dado = dados.tail(1).drop('saiu', axis=1)
                    previsao = predict_model(modelo, data=ultimo_dado, verbose=False)

                    if 'prediction_score' in previsao.columns:
                        prob = previsao['prediction_score'].values[0]
                    elif 'Score' in previsao.columns:
                        prob = previsao['Score'].values[0]
                    else:
                        prob = previsao.iloc[0, -1] if len(previsao.columns) > 0 else 0.5

                    probabilidades[numero] = prob
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                probabilidades[numero] = 0.5

        top_numeros = sorted(probabilidades.items(), key=lambda x: x[1], reverse=True)[:15]
        candidatos = [num for num, prob in top_numeros]
        return sorted(random.sample(candidatos, 6))

    except Exception as e:
        logger.error("Erro no AutoML: %s. Usando estratégia mista.", e)
        return gerar_jogo('misto', contagem_total, contagem_recente, df_atrasos)