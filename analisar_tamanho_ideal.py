"""
================================================================================
🔬 ANÁLISE DE TAMANHO IDEAL DO ENSEMBLE
================================================================================
Roda uma simulação completa testando tamanhos de ensemble de 7 a 15
com 10 cartões por concurso, e mostra:
  - Qual tamanho tem melhor média de acertos
  - Quais combinações específicas acertaram mais
  - Quais estratégias individuais aparecem mais nos melhores resultados

OTIMIZAÇÃO: Pré-calcula TODOS os outputs de cada estratégia uma única vez,
depois combina votos instantaneamente para qualquer combinação.
================================================================================
Uso: python analisar_tamanho_ideal.py
================================================================================
"""

import json
import os
import random
import time
from collections import Counter
from itertools import combinations

import pandas as pd

# Importar módulos do projeto
from modules import statistics as stats
from modules import game_generator as gen

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

N_CONCURSOS = 100       # Concursos a testar (últimos N)
N_JOGOS = 10            # Cartões por concurso (10 conforme pedido)
TAMANHOS = list(range(7, 16))  # 7, 8, 9, 10, 11, 12, 13, 14, 15
COMBOS_POR_TAMANHO = 30  # Combos aleatórias por tamanho

ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes', 'equilibrado', 'misto',
    'consenso', 'aleatorio_smart', 'sequencias', 'wheel',
    'candidatos_ouro', 'momentum', 'vizinhanca',
    'frequencia_desvio', 'pares_frequentes', 'ciclos'
]

NOMES = {
    'escada': 'Escada', 'atrasados': 'Atrasados', 'quentes': 'Quentes',
    'equilibrado': 'Equilibrado', 'misto': 'Misto', 'consenso': 'Consenso',
    'aleatorio_smart': 'Aleat.Smart', 'sequencias': 'Sequências', 'wheel': 'Wheel',
    'candidatos_ouro': 'Cand.Ouro', 'momentum': 'Momentum', 'vizinhanca': 'Vizinhança',
    'frequencia_desvio': 'Freq.Desvio', 'pares_frequentes': 'Pares.Freq', 'ciclos': 'Ciclos'
}

ARQUIVO_RESULTADO = 'analise_tamanho_ideal.json'

# =============================================================================
# FUNÇÕES
# =============================================================================

def carregar_historico():
    """Carrega histórico completo da Mega-Sena."""
    path = os.path.join('data', 'historico_completo.json')
    if not os.path.exists(path):
        print("ERRO: data/historico_completo.json não encontrado!")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    df = pd.DataFrame(dados)
    for col in ['concurso'] + [f'dez{i}' for i in range(1, 7)]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['concurso']).sort_values('concurso').reset_index(drop=True)
    print(f"  Histórico: {len(df)} concursos (último: {int(df['concurso'].max())})")
    return df


def preparar_concursos(df, n_concursos):
    """Pré-calcula dados de N concursos para teste."""
    ultimo = df['concurso'].max()
    concursos = list(range(int(ultimo) - n_concursos + 1, int(ultimo) + 1))
    dados = []
    for conc in concursos:
        mask = df['concurso'] == conc
        if not mask.any():
            continue
        row = df[mask].iloc[0]
        resultado = sorted([int(row[f'dez{i}']) for i in range(1, 7)])
        df_treino = df[df['concurso'] < conc].copy().reset_index(drop=True)
        if len(df_treino) < 100:
            continue
        contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df_treino)
        dados.append({
            'concurso': int(conc),
            'resultado': resultado,
            'contagem_total': contagem_total,
            'contagem_recente': contagem_recente,
            'df_atrasos': df_atrasos,
            'df_treino': df_treino,
        })
    return dados


def pre_computar_outputs(dados_concursos, n_jogos, estrategias):
    """
    Pré-computa TODOS os outputs de cada estratégia para cada concurso/jogo.
    Retorna: outputs[conc_idx][jogo_idx][estrategia] = [6 números]
    Isso evita recalcular gerar_jogo repetidamente para diferentes combos.
    """
    n_conc = len(dados_concursos)
    n_est = len(estrategias)
    total = n_conc * n_jogos * n_est
    outputs = []

    print(f"  Gerando {total:,} outputs ({n_conc} conc × {n_jogos} jogos × {n_est} est)...")
    t0 = time.time()
    count = 0

    for ci, dc in enumerate(dados_concursos):
        conc_outputs = []
        for ji in range(n_jogos):
            jogo_outputs = {}
            for est in estrategias:
                random.seed(dc['concurso'] * 10000 + ji * 100 + hash(est) % 97)
                try:
                    nums = gen.gerar_jogo(
                        est, dc['contagem_total'], dc['contagem_recente'],
                        dc['df_atrasos'], df=dc['df_treino']
                    )
                    jogo_outputs[est] = nums
                except Exception:
                    jogo_outputs[est] = None
                count += 1
            conc_outputs.append(jogo_outputs)
        outputs.append(conc_outputs)

        # Progresso a cada 10 concursos
        if (ci + 1) % 10 == 0 or ci == n_conc - 1:
            elapsed = time.time() - t0
            pct = (ci + 1) / n_conc * 100
            rate = count / elapsed if elapsed > 0 else 0
            print(f"    Concurso {ci+1}/{n_conc} ({pct:.0f}%) - {rate:.0f} outputs/s")

    dt = time.time() - t0
    print(f"  Pré-cálculo completo: {count:,} outputs em {dt:.1f}s ({count/dt:.0f}/s)")
    return outputs


def ensemble_from_precomputed(combo, conc_outputs_jogo, contagem_recente):
    """
    Gera um jogo ensemble a partir de outputs pré-computados.
    combo: lista de estratégias
    conc_outputs_jogo: dict[estrategia] → [6 números] (um jogo_idx específico)
    """
    votos = Counter()
    for est in combo:
        nums = conc_outputs_jogo.get(est)
        if nums:
            for n in nums:
                votos[n] += 1

    if not votos:
        return sorted(random.sample(range(1, 61), 6))

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    pool_size = min(20, len(candidatos))
    pool = candidatos[:pool_size]

    if len(pool) < 6:
        extras = [n for n in range(1, 61) if n not in pool]
        pool += extras[:6 - len(pool)]

    for _ in range(100):
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if 2 <= pares <= 4 and 140 <= soma <= 210:
            return jogo

    return sorted(candidatos[:6]) if len(candidatos) >= 6 else sorted(random.sample(range(1, 61), 6))


def avaliar_combo_rapido(combo, dados_concursos, outputs, n_jogos):
    """Avalia uma combinação usando outputs pré-computados (muito rápido)."""
    acertos = []
    melhores = []
    dist = Counter()

    for ci, dc in enumerate(dados_concursos):
        melhor = 0
        for ji in range(n_jogos):
            random.seed(dc['concurso'] * 1000 + ji + hash(tuple(combo)) % 997)
            jogo = ensemble_from_precomputed(
                combo, outputs[ci][ji], dc['contagem_recente']
            )
            ac = len(set(jogo) & set(dc['resultado']))
            acertos.append(ac)
            dist[ac] += 1
            if ac > melhor:
                melhor = ac
        melhores.append(melhor)

    media = sum(acertos) / len(acertos) if acertos else 0
    maximo = max(melhores) if melhores else 0
    melhor_med = sum(melhores) / len(melhores) if melhores else 0

    return {
        'combo': list(combo),
        'tam': len(combo),
        'media': round(media, 4),
        'max': maximo,
        'melhor_med': round(melhor_med, 3),
        'dist': dict(dist),
        'total_jogos': len(acertos),
        'ternos': sum(v for k, v in dist.items() if k >= 3),
        'quadras': sum(v for k, v in dist.items() if k >= 4),
        'quinas': sum(v for k, v in dist.items() if k >= 5),
    }


# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("🔬 ANÁLISE DE TAMANHO IDEAL DO ENSEMBLE")
    print("=" * 70)
    print(f"  Configuração:")
    print(f"    Concursos: {N_CONCURSOS}")
    print(f"    Cartões/concurso: {N_JOGOS}")
    print(f"    Tamanhos: {TAMANHOS[0]} a {TAMANHOS[-1]}")
    print(f"    Combos por tamanho: {COMBOS_POR_TAMANHO}")
    total_combos = len(TAMANHOS) * COMBOS_POR_TAMANHO
    print(f"    Total de combos estimado: ~{total_combos}")
    print("=" * 70)

    # 1. Carregar histórico
    print("\n📂 Carregando histórico...")
    df = carregar_historico()
    if df is None:
        return

    # 2. Pré-calcular concursos
    print(f"\n⚙️  Pré-calculando {N_CONCURSOS} concursos...")
    t0 = time.time()
    dados_concursos = preparar_concursos(df, N_CONCURSOS)
    print(f"  Preparados: {len(dados_concursos)} concursos em {time.time()-t0:.1f}s")

    # 3. PRÉ-COMPUTAR outputs de todas as estratégias (OTIMIZAÇÃO CHAVE)
    print(f"\n🔧 Pré-computando outputs de TODAS as estratégias...")
    outputs = pre_computar_outputs(dados_concursos, N_JOGOS, ESTRATEGIAS)

    # 4. Gerar combos por tamanho
    print(f"\n🎲 Gerando combos...")
    combos_por_tam = {}
    for tam in TAMANHOS:
        if tam >= len(ESTRATEGIAS):
            combos_por_tam[tam] = [tuple(ESTRATEGIAS)]
        else:
            todas = set()
            tentativas = 0
            while len(todas) < COMBOS_POR_TAMANHO and tentativas < COMBOS_POR_TAMANHO * 50:
                c = tuple(sorted(random.sample(ESTRATEGIAS, tam)))
                todas.add(c)
                tentativas += 1
            combos_por_tam[tam] = list(todas)
        print(f"  Tamanho {tam:2d}: {len(combos_por_tam[tam]):3d} combos")

    total_real = sum(len(v) for v in combos_por_tam.values())

    # 5. Rodar simulação (RÁPIDO - só voting, sem gerar_jogo)
    print(f"\n{'=' * 70}")
    print(f"🚀 AVALIANDO {total_real} COMBOS (voting pré-computado)")
    print(f"{'=' * 70}")

    todos_resultados = []
    combo_idx = 0
    t_inicio = time.time()

    for tam in TAMANHOS:
        combos = combos_por_tam[tam]
        print(f"\n--- Tamanho {tam} ({len(combos)} combos) ---")

        for combo in combos:
            combo_idx += 1
            t_combo = time.time()

            resultado = avaliar_combo_rapido(combo, dados_concursos, outputs, N_JOGOS)
            dt = time.time() - t_combo
            resultado['tempo'] = round(dt, 1)
            todos_resultados.append(resultado)

            # Progresso
            elapsed = time.time() - t_inicio
            rate = combo_idx / elapsed if elapsed > 0 else 0
            restante = (total_real - combo_idx) / rate if rate > 0 else 0
            min_r = int(restante // 60)
            sec_r = int(restante % 60)

            nomes = [NOMES.get(e, e) for e in combo[:5]]
            sufixo = f"+{len(combo)-5}" if len(combo) > 5 else ""
            label = " + ".join(nomes) + (f" {sufixo}" if sufixo else "")

            print(
                f"  [{combo_idx:3d}/{total_real}] "
                f"Média={resultado['media']:.3f}  "
                f"MAX={resultado['max']}  "
                f"3+={resultado['ternos']:4d}  "
                f"4+={resultado['quadras']:2d}  "
                f"({dt:.1f}s, ETA {min_r}m{sec_r:02d}s)  "
                f"{label}"
            )

    elapsed_total = time.time() - t_inicio
    print(f"\n{'=' * 70}")
    print(f"✅ Simulação concluída em {int(elapsed_total//60)}m {int(elapsed_total%60)}s")
    print(f"{'=' * 70}")

    # 5. Salvar resultados
    with open(ARQUIVO_RESULTADO, 'w', encoding='utf-8') as f:
        json.dump({
            'config': {
                'n_concursos': N_CONCURSOS,
                'n_jogos': N_JOGOS,
                'tamanhos': TAMANHOS,
                'combos_por_tamanho': COMBOS_POR_TAMANHO,
            },
            'resultados': todos_resultados,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Resultados salvos em {ARQUIVO_RESULTADO}")

    # =========================================================================
    # RELATÓRIO FINAL
    # =========================================================================

    # Ordenar por média
    todos_resultados.sort(key=lambda r: (r['media'], r['max'], r['melhor_med']), reverse=True)

    # --- TOP 20 GERAL ---
    print(f"\n{'=' * 70}")
    print(f"🏆 TOP 20 MELHORES COMBINAÇÕES (GERAL)")
    print(f"{'=' * 70}")
    print(f"{'#':>3}  {'Tam':>3}  {'Média':>7}  {'Melhor':>6}  {'MAX':>3}  {'3+':>5}  {'4+':>3}  {'5+':>3}  Combinação")
    print(f"{'-'*3}  {'-'*3}  {'-'*7}  {'-'*6}  {'-'*3}  {'-'*5}  {'-'*3}  {'-'*3}  {'-'*40}")
    for i, r in enumerate(todos_resultados[:20]):
        nomes = [NOMES.get(e, e) for e in r['combo'][:6]]
        sufixo = f"+{len(r['combo'])-6}" if len(r['combo']) > 6 else ""
        label = ", ".join(nomes) + (f" {sufixo}" if sufixo else "")
        print(
            f"{i+1:3d}  {r['tam']:3d}  {r['media']:7.4f}  {r['melhor_med']:6.3f}  "
            f"{r['max']:3d}  {r['ternos']:5d}  {r['quadras']:3d}  {r['quinas']:3d}  {label}"
        )

    # --- MÉDIA POR TAMANHO ---
    print(f"\n{'=' * 70}")
    print(f"📊 DESEMPENHO MÉDIO POR TAMANHO DE ENSEMBLE")
    print(f"{'=' * 70}")
    print(f"{'Tam':>3}  {'Combos':>6}  {'Média':>7}  {'Melhor':>6}  {'3+/combo':>8}  {'4+/combo':>8}  {'Melhor Média':>12}")
    print(f"{'-'*3}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*8}  {'-'*8}  {'-'*12}")

    stats_por_tam = {}
    for tam in TAMANHOS:
        resultados_tam = [r for r in todos_resultados if r['tam'] == tam]
        if not resultados_tam:
            continue
        media_media = sum(r['media'] for r in resultados_tam) / len(resultados_tam)
        media_melhor = sum(r['melhor_med'] for r in resultados_tam) / len(resultados_tam)
        total_ternos = sum(r['ternos'] for r in resultados_tam) / len(resultados_tam)
        total_quadras = sum(r['quadras'] for r in resultados_tam) / len(resultados_tam)
        melhor_combo = max(resultados_tam, key=lambda r: r['media'])

        stats_por_tam[tam] = {
            'media': media_media,
            'melhor_med': media_melhor,
            'ternos_avg': total_ternos,
            'quadras_avg': total_quadras,
            'melhor_media': melhor_combo['media'],
        }

        barra = '█' * int(media_media * 20)
        print(
            f"{tam:3d}  {len(resultados_tam):6d}  {media_media:7.4f}  "
            f"{media_melhor:6.3f}  {total_ternos:8.1f}  {total_quadras:8.1f}  "
            f"{melhor_combo['media']:12.4f}  {barra}"
        )

    # --- MELHOR COMBO DE CADA TAMANHO ---
    print(f"\n{'=' * 70}")
    print(f"🥇 MELHOR COMBINAÇÃO DE CADA TAMANHO")
    print(f"{'=' * 70}")
    for tam in TAMANHOS:
        resultados_tam = [r for r in todos_resultados if r['tam'] == tam]
        if not resultados_tam:
            continue
        melhor = max(resultados_tam, key=lambda r: (r['media'], r['max']))
        nomes = [NOMES.get(e, e) for e in melhor['combo']]
        print(f"\n  Tamanho {tam} (Média={melhor['media']:.4f}, MAX={melhor['max']}, "
              f"3+={melhor['ternos']}, 4+={melhor['quadras']}):")
        print(f"    {', '.join(nomes)}")

    # --- FREQUÊNCIA DE ESTRATÉGIAS NOS TOP 30% ---
    print(f"\n{'=' * 70}")
    print(f"⭐ ESTRATÉGIAS MAIS FREQUENTES NOS MELHORES RESULTADOS (top 30%)")
    print(f"{'=' * 70}")

    n_top = max(1, len(todos_resultados) * 30 // 100)
    top_resultados = todos_resultados[:n_top]

    freq = Counter()
    for r in top_resultados:
        for e in r['combo']:
            freq[e] += 1

    total_top = len(top_resultados)
    print(f"\n  Analisando as {n_top} melhores combinações:\n")
    print(f"  {'Estratégia':<20}  {'Aparições':>9}  {'%':>6}  Barra")
    print(f"  {'-'*20}  {'-'*9}  {'-'*6}  {'-'*30}")

    for est, count in freq.most_common():
        pct = count / total_top * 100
        barra = '█' * int(pct / 2)
        nome = NOMES.get(est, est)
        print(f"  {nome:<20}  {count:9d}  {pct:5.1f}%  {barra}")

    # --- RECOMENDAÇÃO ---
    print(f"\n{'=' * 70}")
    print(f"💡 RECOMENDAÇÃO")
    print(f"{'=' * 70}")

    # Melhor tamanho
    if stats_por_tam:
        melhor_tam = max(stats_por_tam, key=lambda t: stats_por_tam[t]['media'])
        print(f"\n  Melhor tamanho médio: {melhor_tam} estratégias "
              f"(média {stats_por_tam[melhor_tam]['media']:.4f})")

    # Top 5 estratégias
    top_5_est = freq.most_common(5)
    print(f"\n  Top 5 estratégias individuais (mais presentes nos melhores resultados):")
    for est, count in top_5_est:
        nome = NOMES.get(est, est)
        pct = count / total_top * 100
        print(f"    {nome}: aparece em {pct:.0f}% dos melhores")

    # Melhor combo geral
    best = todos_resultados[0]
    nomes_best = [NOMES.get(e, e) for e in best['combo']]
    print(f"\n  Melhor combinação encontrada (tamanho {best['tam']}):")
    print(f"    {', '.join(nomes_best)}")
    print(f"    Média={best['media']:.4f}, MAX={best['max']}, "
          f"3+={best['ternos']}, 4+={best['quadras']}, 5+={best['quinas']}")

    print(f"\n{'=' * 70}")
    print(f"  Fim da análise!")
    print(f"{'=' * 70}\n")


if __name__ == '__main__':
    main()
