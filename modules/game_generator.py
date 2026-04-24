"""
================================================================================
🎲 MÓDULO DE GERAÇÃO DE JOGOS
================================================================================
Geração de jogos com diferentes estratégias
"""

import random
import logging
import json
import os
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

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORICO_ANALISES_FILE = os.path.join(ROOT_DIR, 'historico_analises.json')
BACKTESTING_RESULTADO_FILE = os.path.join(ROOT_DIR, 'data', 'backtesting_resultado.json')

ESTRATEGIAS_ENSEMBLE_CLASSICO = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart'
]

ESTRATEGIAS_ENSEMBLE_ELEGIVEIS = [
    'ciclos', 'frequencia_desvio', 'pares_frequentes', 'consenso', 'sequencias',
    'quentes', 'equilibrado', 'misto', 'candidatos_ouro', 'aleatorio_smart',
    'momentum', 'vizinhanca', 'atrasados', 'atraso_recente', 'escada'
]

QTD_ESTRATEGIAS_ENSEMBLE = 5
JANELA_RECENTE_ENSEMBLE = 8
MAX_STREAK_SEM_TERNO_DEFAULT = 2

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


def _carregar_json_local(caminho):
    """Carrega JSON local. Retorna None em qualquer falha."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _ranking_historico_recente_ensemble(
    max_estrategias=QTD_ESTRATEGIAS_ENSEMBLE,
    janela_concursos=JANELA_RECENTE_ENSEMBLE
):
    """
    Monta ranking recente a partir do histórico real já conferido.
    Prioriza o que vem performando melhor agora, não só no backtesting antigo.
    """
    historico = _carregar_json_local(HISTORICO_ANALISES_FILE)
    if not isinstance(historico, list) or not historico:
        return []

    historico_ordenado = sorted(historico, key=lambda item: int(item.get('concurso', 0)))
    recentes = historico_ordenado[-janela_concursos:]
    min_concursos = min(3, len(recentes))
    agregados = defaultdict(lambda: {
        'jogos': 0,
        'acertos': 0.0,
        'quadras': 0,
        'quinas': 0,
        'senas': 0,
        'concursos': 0,
        'concursos_3_mais': 0,
        'melhor_acerto': 0,
    })

    for registro in recentes:
        estatisticas = registro.get('estatisticas', {})
        for estrategia, dados in estatisticas.items():
            if estrategia not in ESTRATEGIAS_ENSEMBLE_ELEGIVEIS:
                continue

            jogos = int(dados.get('total_jogos', 0) or 0)
            if jogos <= 0:
                continue

            total_acertos = dados.get('total_acertos')
            if total_acertos is None:
                total_acertos = float(dados.get('media_acertos', 0) or 0) * jogos

            melhor_acerto = int(dados.get('melhor_acerto', 0) or 0)
            quadras = int(dados.get('quadras', 0) or 0)
            quinas = int(dados.get('quinas', 0) or 0)
            senas = int(dados.get('senas', 0) or 0)

            agg = agregados[estrategia]
            agg['jogos'] += jogos
            agg['acertos'] += float(total_acertos or 0)
            agg['quadras'] += quadras
            agg['quinas'] += quinas
            agg['senas'] += senas
            agg['concursos'] += 1
            agg['melhor_acerto'] = max(agg['melhor_acerto'], melhor_acerto)
            if melhor_acerto >= 3 or quadras > 0 or quinas > 0 or senas > 0:
                agg['concursos_3_mais'] += 1

    ranking = []
    for estrategia, dados in agregados.items():
        if dados['concursos'] < min_concursos or dados['jogos'] <= 0:
            continue

        ranking.append({
            'estrategia': estrategia,
            'media_acertos': dados['acertos'] / dados['jogos'],
            'concursos_3_mais': dados['concursos_3_mais'],
            'quadras': dados['quadras'],
            'quinas': dados['quinas'],
            'senas': dados['senas'],
            'melhor_acerto': dados['melhor_acerto'],
            'concursos': dados['concursos'],
            'jogos': dados['jogos'],
        })

    ranking.sort(
        key=lambda item: (
            item['media_acertos'],
            item['concursos_3_mais'],
            item['quadras'],
            item['quinas'],
            item['melhor_acerto'],
            item['concursos'],
            item['jogos'],
        ),
        reverse=True,
    )
    return ranking[:max_estrategias]


def _ranking_backtesting_ensemble(max_estrategias=QTD_ESTRATEGIAS_ENSEMBLE):
    """Usa o backtesting salvo como fallback quando não há histórico recente suficiente."""
    payload = _carregar_json_local(BACKTESTING_RESULTADO_FILE)
    ranking_raw = payload.get('ranking', []) if isinstance(payload, dict) else []
    ranking = []

    for item in ranking_raw:
        estrategia = item.get('estrategia')
        if estrategia not in ESTRATEGIAS_ENSEMBLE_ELEGIVEIS:
            continue

        ranking.append({
            'estrategia': estrategia,
            'media_acertos': float(item.get('media_por_cartao', 0) or 0),
            'concursos_3_mais': float(item.get('taxa_concurso_terno_ou_mais', 0) or 0),
            'quadras': float(item.get('taxa_concurso_quadra_ou_mais', 0) or 0),
            'quinas': float(item.get('taxa_concurso_quina_ou_mais', 0) or 0),
            'senas': int(item.get('senas', 0) or 0),
            'melhor_acerto': float(item.get('media_melhor_cartao_concurso', 0) or 0),
            'concursos': int(item.get('concursos', 0) or 0),
            'jogos': int(item.get('jogos', 0) or 0),
        })

    ranking.sort(
        key=lambda item: (
            item['media_acertos'],
            item['quadras'],
            item['concursos_3_mais'],
            item['melhor_acerto'],
            item['quinas'],
            item['concursos'],
            item['jogos'],
        ),
        reverse=True,
    )
    return ranking[:max_estrategias]


def _resolver_estrategias_ensemble(max_estrategias=QTD_ESTRATEGIAS_ENSEMBLE):
    """
    Resolve quais estratégias votam no ensemble.
    Ordem de prioridade:
    1. Histórico real recente
    2. Backtesting salvo
    3. Ensemble clássico
    """
    ranking_recente = _ranking_historico_recente_ensemble(max_estrategias=max_estrategias)
    if len(ranking_recente) >= 3:
        return [item['estrategia'] for item in ranking_recente], 'historico_recente'

    ranking_backtesting = _ranking_backtesting_ensemble(max_estrategias=max_estrategias)
    if len(ranking_backtesting) >= 3:
        return [item['estrategia'] for item in ranking_backtesting], 'backtesting'

    return list(ESTRATEGIAS_ENSEMBLE_CLASSICO), 'classico'


def _teve_terno_ou_mais(dados: dict) -> bool:
    """Verifica se a estratégia marcou >= 3 acertos em algum cartão do concurso."""
    ternos = int(dados.get('ternos', 0) or 0)
    quadras = int(dados.get('quadras', 0) or 0)
    quinas = int(dados.get('quinas', 0) or 0)
    senas = int(dados.get('senas', 0) or 0)
    melhor = int(dados.get('melhor_acerto', 0) or 0)
    return (ternos + quadras + quinas + senas) > 0 or melhor >= 3


def composicao_ensemble_atual(
    max_streak=MAX_STREAK_SEM_TERNO_DEFAULT,
    estrategias=None
):
    """
    Retorna a composição atual do ensemble baseada no histórico de conferências.
    Uma estratégia sai quando acumula `max_streak` concursos consecutivos
    (mais recentes) sem marcar terno ou mais.
    """
    historico = _carregar_json_local(HISTORICO_ANALISES_FILE)
    if not isinstance(historico, list) or not historico:
        return []

    estrategias_alvo = list(estrategias) if estrategias else list(ESTRATEGIAS_ENSEMBLE_ELEGIVEIS)
    historico_desc = sorted(
        historico,
        key=lambda item: int(item.get('concurso', 0)),
        reverse=True
    )

    composicao = []
    for est in estrategias_alvo:
        streak = 0
        ultimo_terno_concurso = None
        total_concursos = 0
        concursos_com_terno = 0
        ainda_em_streak = True

        for reg in historico_desc:
            dados = (reg.get('estatisticas') or {}).get(est)
            if not dados:
                continue
            jogos = int(dados.get('total_jogos', 0) or 0)
            if jogos <= 0:
                continue

            total_concursos += 1
            tem_terno = _teve_terno_ou_mais(dados)

            if tem_terno:
                concursos_com_terno += 1
                if ultimo_terno_concurso is None:
                    ultimo_terno_concurso = int(reg.get('concurso') or 0) or None
                ainda_em_streak = False
            elif ainda_em_streak:
                streak += 1

        if total_concursos == 0:
            status = 'sem_dados'
        elif streak >= max_streak:
            status = 'fora'
        else:
            status = 'dentro'

        composicao.append({
            'estrategia': est,
            'status': status,
            'streak_sem_terno': streak,
            'ultimo_terno_concurso': ultimo_terno_concurso,
            'total_concursos_avaliados': total_concursos,
            'concursos_com_terno': concursos_com_terno,
        })

    status_ordem = {'dentro': 0, 'sem_dados': 1, 'fora': 2}
    composicao.sort(key=lambda x: (
        status_ordem.get(x['status'], 99),
        x['streak_sem_terno'],
        -x['concursos_com_terno'],
        x['estrategia'],
    ))
    return composicao


def estrategias_ensemble_ativas(max_streak=MAX_STREAK_SEM_TERNO_DEFAULT):
    """Lista das estratégias atualmente DENTRO do ensemble (streak < max_streak)."""
    composicao = composicao_ensemble_atual(max_streak=max_streak)
    dentro = [c['estrategia'] for c in composicao if c['status'] == 'dentro']
    if len(dentro) >= 3:
        return dentro, 'historico_streak'

    estrategias_resolvidas, origem = _resolver_estrategias_ensemble()
    return estrategias_resolvidas, origem


def _gerar_jogo_ensemble_votacao(
    estrategias,
    contagem_total,
    contagem_recente,
    df_atrasos,
    df=None,
    ponderar_por_rank=False
):
    """Executa a votação do ensemble usando a lista de estratégias informada."""
    if not estrategias:
        return []

    votos = Counter()
    total_estrategias = len(estrategias)

    for idx, est in enumerate(estrategias):
        peso = max(1, total_estrategias - idx) if ponderar_por_rank else 1
        try:
            jogo = gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df)
            for n in jogo:
                votos[n] += peso
        except Exception as e:
            logger.warning("Erro ao gerar jogo ensemble para %s: %s", est, e)

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    if len(candidatos) < 6:
        return []

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


def gerar_jogo_ensemble(
    contagem_total, contagem_recente, df_atrasos, df=None,
    max_streak=MAX_STREAK_SEM_TERNO_DEFAULT
) -> list[int]:
    """
    Ensemble adaptativo: vota apenas com as estratégias que marcaram
    terno ou mais em pelo menos 1 dos últimos `max_streak` concursos.
    Fallback: ranking recente, backtesting, ensemble clássico.
    """
    estrategias, origem = estrategias_ensemble_ativas(max_streak=max_streak)
    jogo = _gerar_jogo_ensemble_votacao(
        estrategias,
        contagem_total,
        contagem_recente,
        df_atrasos,
        df=df,
        ponderar_por_rank=(origem != 'classico')
    )
    if jogo:
        return jogo

    return _gerar_jogo_ensemble_votacao(
        ESTRATEGIAS_ENSEMBLE_CLASSICO,
        contagem_total,
        contagem_recente,
        df_atrasos,
        df=df,
        ponderar_por_rank=False
    )


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
