"""
================================================================================
SIMULADOR AUTOMATICO DE COMBINACOES DE ESTRATEGIAS
================================================================================
Testa automaticamente todas as combinações possíveis de estratégias
no ensemble para encontrar o subconjunto ótimo.

Roda no terminal: python -u simular_combinacoes.py
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ARQUIVO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_resultado.txt")
_log_file = None

def log(msg=""):
    """Escreve no arquivo e no console."""
    global _log_file
    if _log_file is None:
        _log_file = open(ARQUIVO_SAIDA, 'w', encoding='utf-8')
    _log_file.write(msg + '\n')
    _log_file.flush()
    os.fsync(_log_file.fileno())
    try:
        print(msg, flush=True)
    except (UnicodeEncodeError, OSError):
        pass

import pandas as pd
import random
import json
import time
from collections import Counter
from itertools import combinations
from math import comb

from modules.statistics import calcular_estatisticas
from modules.game_generator import gerar_jogo


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
N_CONCURSOS = 400       # Concursos para testar cada combo
N_JOGOS = 40            # Cartoes ensemble por concurso
TAM_MIN = 3             # Menor combinação a testar
TAM_MAX = 10            # Maior combinação a testar
MAX_COMBOS_POR_TAM = 80   # Se houver mais combos que isso, amostra aleatória
TOP_N = 20              # Mostrar top N no ranking final

ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes', 'equilibrado', 'misto',
    'consenso', 'aleatorio_smart', 'sequencias', 'wheel',
    'candidatos_ouro', 'momentum', 'vizinhanca',
    'frequencia_desvio', 'pares_frequentes', 'ciclos'
]

NOMES = {
    'escada': 'Escada', 'atrasados': 'Atrasados', 'quentes': 'Quentes',
    'equilibrado': 'Equilib.', 'misto': 'Misto', 'consenso': 'Consenso',
    'aleatorio_smart': 'Aleat.', 'sequencias': 'Sequenc.', 'wheel': 'Wheel',
    'candidatos_ouro': 'C.Ouro', 'momentum': 'Moment.', 'vizinhanca': 'Vizin.',
    'frequencia_desvio': 'F.Desv.', 'pares_frequentes': 'Pares', 'ciclos': 'Ciclos'
}


# =============================================================================
# FUNÇÕES
# =============================================================================

def carregar_dados():
    """Carrega dados via API."""
    import requests
    from helpers import converter_dezenas_para_int
    log("Carregando dados da API...")
    url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
    response = requests.get(url, timeout=30)
    data = response.json()
    if isinstance(data, dict):
        data = [data]
    df = pd.DataFrame(data)
    for idx, row in df.iterrows():
        dezenas = converter_dezenas_para_int(row.get('dezenas', []))
        for i, d in enumerate(dezenas[:6], 1):
            df.at[idx, f'dez{i}'] = str(d)
    df['concurso'] = df['concurso'].astype(int)
    df = df.sort_values('concurso', ascending=False).reset_index(drop=True)
    log(f"OK: {len(df)} concursos carregados\n")
    return df


def gerar_ensemble_custom(estrategias_lista, contagem_total, contagem_recente, df_atrasos, df=None):
    """Gera um jogo ensemble usando uma lista customizada de estratégias."""
    votos = Counter()
    for est in estrategias_lista:
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

    pool_size = min(20, len(candidatos))
    for _ in range(100):
        pool = candidatos[:pool_size]
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if 2 <= pares <= 4 and 140 <= soma <= 210:
            return jogo

    return sorted(candidatos[:6]) if len(candidatos) >= 6 else sorted(random.sample(range(1, 61), 6))


def preparar_concursos(df, n_concursos):
    """Pré-calcula dados dos concursos de teste para não repetir."""
    ultimo = df['concurso'].max()
    concursos = list(range(ultimo - n_concursos + 1, ultimo + 1))

    dados_concursos = []
    for conc in concursos:
        mask = df['concurso'] == conc
        if not mask.any():
            continue
        row = df[mask].iloc[0]
        resultado_real = sorted([int(row[f'dez{i}']) for i in range(1, 7)])
        df_treino = df[df['concurso'] < conc].copy().reset_index(drop=True)
        if len(df_treino) < 100:
            continue
        contagem_total, contagem_recente, df_atrasos = calcular_estatisticas(df_treino)
        dados_concursos.append({
            'concurso': conc,
            'resultado': resultado_real,
            'contagem_total': contagem_total,
            'contagem_recente': contagem_recente,
            'df_atrasos': df_atrasos,
            'df_treino': df_treino,
        })

    return dados_concursos


def avaliar_combo(combo, dados_concursos, n_jogos):
    """Avalia uma combinação de estratégias nos concursos pré-calculados."""
    acertos_total = []
    melhores = []
    dist = Counter()

    for dc in dados_concursos:
        melhor = 0
        random.seed(dc['concurso'])
        for _ in range(n_jogos):
            try:
                jogo = gerar_ensemble_custom(
                    list(combo),
                    dc['contagem_total'], dc['contagem_recente'],
                    dc['df_atrasos'], df=dc['df_treino']
                )
                ac = len(set(jogo) & set(dc['resultado']))
                acertos_total.append(ac)
                dist[ac] += 1
                if ac > melhor:
                    melhor = ac
            except Exception:
                pass
        melhores.append(melhor)

    media = sum(acertos_total) / len(acertos_total) if acertos_total else 0
    maximo = max(melhores) if melhores else 0
    melhor_med = sum(melhores) / len(melhores) if melhores else 0
    ternos_plus = sum(v for k, v in dist.items() if k >= 3)
    quadras_plus = sum(v for k, v in dist.items() if k >= 4)
    quinas_plus = sum(v for k, v in dist.items() if k >= 5)

    return {
        'combo': list(combo),
        'tam': len(combo),
        'media': media,
        'max': maximo,
        'melhor_med': melhor_med,
        'ternos_plus': ternos_plus,
        'quadras': quadras_plus,
        'quinas': quinas_plus,
        'dist': dict(dist),
    }


def imprimir_ranking(ranking, titulo, n=20):
    """Imprime tabela de ranking."""
    log(f"\n{'='*90}")
    log(f"  {titulo}")
    log(f"{'='*90}")
    log(f"  {'POS':<5} {'TAM':<4} {'MEDIA':>6} {'M.MED':>6} {'MAX':>4} {'3+ac':>5}  ESTRATEGIAS")
    log(f"  {'-'*84}")

    for i, r in enumerate(ranking[:n]):
        nomes = [NOMES.get(e, e) for e in r['combo']]
        tag = ""
        if i == 0:
            tag = " <<< MELHOR"
        log(
            f"  {i+1:<5} {r['tam']:<4} {r['media']:>6.3f} {r['melhor_med']:>6.2f} {r['max']:>4} {r['ternos_plus']:>5}  "
            f"{'+'.join(nomes)}{tag}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():
    t_inicio = time.time()

    log("=" * 90)
    log("  🔬 SIMULADOR AUTOMÁTICO DE COMBINAÇÕES DE ESTRATÉGIAS")
    log("=" * 90)
    log(f"  Estratégias: {len(ESTRATEGIAS)}")
    log(f"  Tamanhos: {TAM_MIN} a {TAM_MAX}")
    log(f"  Concursos: {N_CONCURSOS} | Jogos/concurso: {N_JOGOS}")
    log(f"  Max combos por tamanho: {MAX_COMBOS_POR_TAM}")

    # Calcular total estimado
    total_combos = 0
    for tam in range(TAM_MIN, TAM_MAX + 1):
        n = comb(len(ESTRATEGIAS), tam)
        total_combos += min(n, MAX_COMBOS_POR_TAM)
    log(f"  Total estimado de combinações: ~{total_combos}")
    log(f"  Total estimado de jogos: ~{total_combos * N_CONCURSOS * N_JOGOS:,}")
    log("=" * 90)

    # Carregar dados e pré-calcular concursos
    df = carregar_dados()
    log("Pré-calculando estatísticas dos concursos de teste...")
    dados_concursos = preparar_concursos(df, N_CONCURSOS)
    log(f"OK: {len(dados_concursos)} concursos preparados\n")

    # Ranking global
    ranking_global = []
    combos_testadas = 0

    for tam in range(TAM_MIN, TAM_MAX + 1):
        todas_combos = list(combinations(ESTRATEGIAS, tam))
        n_total = len(todas_combos)
        n_testar = min(n_total, MAX_COMBOS_POR_TAM)

        if n_total > MAX_COMBOS_POR_TAM:
            random.seed(42)
            combos = random.sample(todas_combos, MAX_COMBOS_POR_TAM)
            tipo = f"amostra {MAX_COMBOS_POR_TAM}/{n_total}"
        else:
            combos = todas_combos
            tipo = f"todas {n_total}"

        log(f"\n{'─'*90}")
        log(f"  TAMANHO {tam} estratégias ({tipo})")
        log(f"{'─'*90}")

        melhores_tam = []
        t_tam = time.time()

        for idx, combo in enumerate(combos):
            resultado = avaliar_combo(combo, dados_concursos, N_JOGOS)
            melhores_tam.append(resultado)
            ranking_global.append(resultado)
            combos_testadas += 1

            # Progresso a cada combo
            elapsed = time.time() - t_tam
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            restante_tam = (len(combos) - idx - 1) / rate if rate > 0 else 0
            nomes = [NOMES.get(e, e) for e in resultado['combo']]
            if (idx + 1) % 5 == 0 or idx == len(combos) - 1 or idx == 0:
                log(
                    f"  [{idx+1:>4}/{len(combos)}] "
                    f"med={resultado['media']:.3f} max={resultado['max']} "
                    f"| {rate:.1f} combo/s | ETA tam: {restante_tam:.0f}s "
                    f"| ultima: {'+'.join(nomes)}"
                )

        # Top 5 deste tamanho
        melhores_tam.sort(key=lambda r: (r['media'], r['max'], r['melhor_med']), reverse=True)
        imprimir_ranking(melhores_tam, f"TOP 5 — TAMANHO {tam}", n=5)

        dt = time.time() - t_tam
        log(f"\n  Tamanho {tam}: {len(combos)} combos em {dt:.1f}s ({dt/len(combos):.2f}s/combo)")

    # =========================================================================
    # RANKING FINAL GLOBAL
    # =========================================================================
    ranking_global.sort(key=lambda r: (r['media'], r['max'], r['melhor_med']), reverse=True)

    log(f"\n\n{'#'*90}")
    log(f"{'#'*90}")
    imprimir_ranking(ranking_global, f"🏆 RANKING GLOBAL — TOP {TOP_N} (de {combos_testadas} combinações testadas)", n=TOP_N)

    # Melhor por tamanho
    log(f"\n{'='*90}")
    log(f"  🎯 MELHOR COMBINAÇÃO POR TAMANHO")
    log(f"{'='*90}")

    for tam in range(TAM_MIN, TAM_MAX + 1):
        candidatos = [r for r in ranking_global if r['tam'] == tam]
        if candidatos:
            melhor = candidatos[0]
            nomes = [NOMES.get(e, e) for e in melhor['combo']]
            log(
                f"  Tam {tam:>2}: med={melhor['media']:.3f} max={melhor['max']} 3+ac={melhor['ternos_plus']:>3}  "
                f"{'+'.join(nomes)}"
            )

    # Frequência das estratégias no top 20
    log(f"\n{'='*90}")
    log(f"  📊 FREQUÊNCIA DAS ESTRATÉGIAS NO TOP {TOP_N}")
    log(f"{'='*90}")

    freq_top = Counter()
    for r in ranking_global[:TOP_N]:
        for e in r['combo']:
            freq_top[e] += 1

    for est, cnt in freq_top.most_common():
        barra = '█' * cnt
        log(f"  {NOMES.get(est, est):<12} {cnt:>2}x  {barra}")

    # Salvar resultados em JSON (formato compatível com aba Histórico do Streamlit)
    arquivo_json = "sim_combinacoes_resultado.json"

    entrada = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'n_concursos': N_CONCURSOS,
            'n_jogos': N_JOGOS,
            'total_combos': combos_testadas,
        },
        'tempo_segundos': round(time.time() - t_inicio, 1),
        'ranking_top20': [
            {
                'combo': r['combo'],
                'media': round(r['media'], 4),
                'max': r['max'],
                'melhor_med': round(r['melhor_med'], 2),
                'ternos': r['ternos_plus'],
                'quadras': r.get('quadras', 0),
                'quinas': r.get('quinas', 0),
            }
            for r in ranking_global[:20]
        ],
    }

    # Append ao histórico existente
    historico = []
    if os.path.exists(arquivo_json):
        try:
            with open(arquivo_json, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                if isinstance(conteudo, list):
                    historico = conteudo
                else:
                    historico = [conteudo]
        except Exception:
            pass
    historico.append(entrada)
    historico = historico[-20:]  # manter últimos 20

    with open(arquivo_json, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
    log(f"\n  Resultados salvos em {arquivo_json} (historico: {len(historico)} simulacoes)")

    dt_total = time.time() - t_inicio
    minutos = int(dt_total // 60)
    segundos = int(dt_total % 60)
    log(f"\n  ⏱️  Tempo total: {minutos}m {segundos}s ({combos_testadas} combinações)")
    log(f"  🏆 MELHOR: {'+'.join(NOMES.get(e,e) for e in ranking_global[0]['combo'])} "
        f"(med={ranking_global[0]['media']:.3f}, max={ranking_global[0]['max']})")
    log("=" * 90)


if __name__ == "__main__":
    main()

