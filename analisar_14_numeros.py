"""
================================================================================
🔬 ANÁLISE COM 14 NÚMEROS POR CARTÃO
================================================================================
Mesmo teste do analisar_tamanho_ideal.py mas com cartões de 14 números.
Com 14 nums, temos C(14,6) = 3.003 combinações de 6 dentro do cartão.
Se X dos 6 sorteados estão nos nossos 14:
  X=6 → Sena | X=5 → Quina | X=4 → Quadra | X=3 → Terno
================================================================================
"""

import json
import os
import random
import time
from collections import Counter

import pandas as pd

from modules import statistics as stats
from modules import game_generator as gen

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

N_CONCURSOS = 100
N_JOGOS = 10            # Cartões de 14 números por concurso
NUMS_POR_CARTAO = 14    # <<< DIFERENÇA: 14 ao invés de 6
TAMANHOS = list(range(7, 16))
COMBOS_POR_TAMANHO = 30

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

ARQUIVO_RESULTADO = 'analise_14_numeros.json'


# =============================================================================
# FUNÇÕES
# =============================================================================

def carregar_historico():
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

        if (ci + 1) % 10 == 0 or ci == n_conc - 1:
            elapsed = time.time() - t0
            pct = (ci + 1) / n_conc * 100
            rate = count / elapsed if elapsed > 0 else 0
            print(f"    Concurso {ci+1}/{n_conc} ({pct:.0f}%) - {rate:.0f} outputs/s")

    dt = time.time() - t0
    print(f"  Pré-cálculo completo: {count:,} outputs em {dt:.1f}s ({count/dt:.0f}/s)")
    return outputs


def ensemble_14_from_precomputed(combo, conc_outputs_jogo, contagem_recente):
    """
    Gera um cartão de 14 números a partir de outputs pré-computados.
    Pega os 14 números mais votados pelo ensemble.
    """
    votos = Counter()
    for est in combo:
        nums = conc_outputs_jogo.get(est)
        if nums:
            for n in nums:
                votos[n] += 1

    if not votos:
        return sorted(random.sample(range(1, 61), 14))

    candidatos = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )

    # Pegar os top 14 mais votados
    if len(candidatos) >= 14:
        return sorted(candidatos[:14])
    else:
        # Completar com números aleatórios fora do pool
        extras = [n for n in range(1, 61) if n not in candidatos]
        random.shuffle(extras)
        todos = candidatos + extras[:14 - len(candidatos)]
        return sorted(todos[:14])


def avaliar_combo_14(combo, dados_concursos, outputs, n_jogos):
    """Avalia combinação com cartões de 14 números."""
    acertos = []
    melhores = []
    dist = Counter()

    for ci, dc in enumerate(dados_concursos):
        melhor = 0
        for ji in range(n_jogos):
            random.seed(dc['concurso'] * 1000 + ji + hash(tuple(combo)) % 997)
            jogo14 = ensemble_14_from_precomputed(
                combo, outputs[ci][ji], dc['contagem_recente']
            )
            # Com 14 números, quantos dos 6 sorteados estão no nosso cartão?
            ac = len(set(jogo14) & set(dc['resultado']))
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
        'senas': dist.get(6, 0),
        'quinas': dist.get(5, 0),
        'quadras': dist.get(4, 0),
        'ternos': dist.get(3, 0),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("🔬 ANÁLISE COM 14 NÚMEROS POR CARTÃO")
    print("=" * 70)
    print(f"  Configuração:")
    print(f"    Concursos: {N_CONCURSOS}")
    print(f"    Cartões/concurso: {N_JOGOS} (cada com {NUMS_POR_CARTAO} números)")
    print(f"    Tamanhos ensemble: {TAMANHOS[0]} a {TAMANHOS[-1]}")
    print(f"    Combos por tamanho: {COMBOS_POR_TAMANHO}")
    print(f"    C(14,6) = 3.003 combinações por cartão!")
    print("=" * 70)

    # 1. Carregar
    print("\n📂 Carregando histórico...")
    df = carregar_historico()
    if df is None:
        return

    # 2. Preparar concursos
    print(f"\n⚙️  Pré-calculando {N_CONCURSOS} concursos...")
    t0 = time.time()
    dados_concursos = preparar_concursos(df, N_CONCURSOS)
    print(f"  Preparados: {len(dados_concursos)} concursos em {time.time()-t0:.1f}s")

    # 3. Pré-computar outputs
    print(f"\n🔧 Pré-computando outputs...")
    outputs = pre_computar_outputs(dados_concursos, N_JOGOS, ESTRATEGIAS)

    # 4. Gerar combos
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

    # 5. Avaliar
    print(f"\n{'=' * 70}")
    print(f"🚀 AVALIANDO {total_real} COMBOS COM 14 NÚMEROS")
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

            resultado = avaliar_combo_14(combo, dados_concursos, outputs, N_JOGOS)
            dt = time.time() - t_combo
            resultado['tempo'] = round(dt, 1)
            todos_resultados.append(resultado)

            elapsed = time.time() - t_inicio
            rate = combo_idx / elapsed if elapsed > 0 else 0
            restante = (total_real - combo_idx) / rate if rate > 0 else 0
            min_r = int(restante // 60)
            sec_r = int(restante % 60)

            nomes = [NOMES.get(e, e) for e in combo[:5]]
            sufixo = f"+{len(combo)-5}" if len(combo) > 5 else ""
            label = " + ".join(nomes) + (f" {sufixo}" if sufixo else "")

            marcador = ""
            if resultado['senas'] > 0:
                marcador = " 🎯🎯🎯 SENA!"
            elif resultado['quinas'] > 0:
                marcador = " ⭐ QUINA!"

            print(
                f"  [{combo_idx:3d}/{total_real}] "
                f"Média={resultado['media']:.3f}  "
                f"MAX={resultado['max']}  "
                f"6={resultado['senas']}  "
                f"5={resultado['quinas']:2d}  "
                f"4={resultado['quadras']:3d}  "
                f"3={resultado['ternos']:4d}  "
                f"({dt:.1f}s)  "
                f"{label}{marcador}"
            )

    elapsed_total = time.time() - t_inicio
    print(f"\n{'=' * 70}")
    print(f"✅ Concluído em {int(elapsed_total//60)}m {int(elapsed_total%60)}s")
    print(f"{'=' * 70}")

    # 6. Salvar
    with open(ARQUIVO_RESULTADO, 'w', encoding='utf-8') as f:
        json.dump({
            'config': {
                'n_concursos': N_CONCURSOS,
                'n_jogos': N_JOGOS,
                'nums_por_cartao': NUMS_POR_CARTAO,
                'tamanhos': TAMANHOS,
                'combos_por_tamanho': COMBOS_POR_TAMANHO,
            },
            'resultados': todos_resultados,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Resultados salvos em {ARQUIVO_RESULTADO}")

    # =========================================================================
    # RELATÓRIO
    # =========================================================================

    todos_resultados.sort(key=lambda r: (r['media'], r['max']), reverse=True)

    # Distribuição total
    total_dist = Counter()
    for r in todos_resultados:
        for k, v in r['dist'].items():
            total_dist[int(k)] += v

    total_jogos = sum(total_dist.values())
    print(f"\n{'=' * 70}")
    print(f"📊 DISTRIBUIÇÃO TOTAL ({total_jogos:,} cartões de 14 números)")
    print(f"{'=' * 70}")
    for ac in sorted(total_dist.keys(), reverse=True):
        pct = total_dist[ac] / total_jogos * 100
        label = {6: 'SENA  ', 5: 'QUINA ', 4: 'QUADRA', 3: 'TERNO ', 2: '2 ac. ', 1: '1 ac. ', 0: '0 ac. '}.get(ac, f'{ac} ac. ')
        barra = '█' * max(1, int(pct))
        print(f"  {label}: {total_dist[ac]:>8,}  ({pct:6.3f}%)  {barra}")

    # TOP 20
    print(f"\n{'=' * 70}")
    print(f"🏆 TOP 20 MELHORES (14 NÚMEROS)")
    print(f"{'=' * 70}")
    print(f"{'#':>3}  {'Tam':>3}  {'Média':>7}  {'MAX':>3}  {'6':>3}  {'5':>3}  {'4':>4}  {'3':>5}  Combinação")
    print(f"{'-'*3}  {'-'*3}  {'-'*7}  {'-'*3}  {'-'*3}  {'-'*3}  {'-'*4}  {'-'*5}  {'-'*40}")
    for i, r in enumerate(todos_resultados[:20]):
        nomes = [NOMES.get(e, e) for e in r['combo'][:6]]
        sufixo = f"+{len(r['combo'])-6}" if len(r['combo']) > 6 else ""
        label = ", ".join(nomes) + (f" {sufixo}" if sufixo else "")
        print(
            f"{i+1:3d}  {r['tam']:3d}  {r['media']:7.4f}  "
            f"{r['max']:3d}  {r['senas']:3d}  {r['quinas']:3d}  "
            f"{r['quadras']:4d}  {r['ternos']:5d}  {label}"
        )

    # Média por tamanho
    print(f"\n{'=' * 70}")
    print(f"📊 DESEMPENHO MÉDIO POR TAMANHO (14 NÚMEROS)")
    print(f"{'=' * 70}")
    print(f"{'Tam':>3}  {'Combos':>6}  {'Média':>7}  {'Quinas':>6}  {'Quadras':>7}  {'Ternos':>6}  {'Melhor':>7}")
    print(f"{'-'*3}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*7}")

    for tam in TAMANHOS:
        rt = [r for r in todos_resultados if r['tam'] == tam]
        if not rt:
            continue
        media_m = sum(r['media'] for r in rt) / len(rt)
        total_q5 = sum(r['quinas'] for r in rt)
        total_q4 = sum(r['quadras'] for r in rt)
        total_q3 = sum(r['ternos'] for r in rt)
        melhor = max(rt, key=lambda r: r['media'])
        barra = '█' * int(media_m * 5)
        print(
            f"{tam:3d}  {len(rt):6d}  {media_m:7.4f}  "
            f"{total_q5:6d}  {total_q4:7d}  {total_q3:6d}  "
            f"{melhor['media']:7.4f}  {barra}"
        )

    # Melhor por tamanho
    print(f"\n{'=' * 70}")
    print(f"🥇 MELHOR COMBINAÇÃO DE CADA TAMANHO (14 NÚMEROS)")
    print(f"{'=' * 70}")
    for tam in TAMANHOS:
        rt = [r for r in todos_resultados if r['tam'] == tam]
        if not rt:
            continue
        melhor = max(rt, key=lambda r: (r['media'], r['max']))
        nomes = [NOMES.get(e, e) for e in melhor['combo']]
        print(f"\n  Tamanho {tam} (Média={melhor['media']:.4f}, MAX={melhor['max']}, "
              f"Senas={melhor['senas']}, Quinas={melhor['quinas']}, Quadras={melhor['quadras']}):")
        print(f"    {', '.join(nomes)}")

    # Top estratégias
    print(f"\n{'=' * 70}")
    print(f"⭐ ESTRATÉGIAS MAIS FREQUENTES NOS MELHORES (top 30%)")
    print(f"{'=' * 70}")

    n_top = max(1, len(todos_resultados) * 30 // 100)
    top_res = todos_resultados[:n_top]
    freq = Counter()
    for r in top_res:
        for e in r['combo']:
            freq[e] += 1

    total_top = len(top_res)
    for est, count in freq.most_common():
        pct = count / total_top * 100
        barra = '█' * int(pct / 2)
        nome = NOMES.get(est, est)
        print(f"  {nome:<20}  {count:4d}  {pct:5.1f}%  {barra}")

    # Comparar com 6 números
    print(f"\n{'=' * 70}")
    print(f"📈 COMPARATIVO: 6 NÚMEROS vs 14 NÚMEROS")
    print(f"{'=' * 70}")
    # Probabilidade teórica de X acertos com cartão de N números
    # P(X=k | N=14) vs P(X=k | N=6)
    from math import comb
    print(f"\n  Probabilidade teórica (por cartão):")
    print(f"  {'Acertos':<10}  {'6 números':>15}  {'14 números':>15}  {'Fator':>8}")
    for k in range(7):
        p6 = comb(6, k) * comb(54, 6-k) / comb(60, 6)
        p14 = comb(14, k) * comb(46, 6-k) / comb(60, 6) if k <= 6 else 0
        fator = p14 / p6 if p6 > 0 else 0
        print(f"  {k} acertos   {p6:15.8f}  {p14:15.8f}  {fator:7.1f}x")

    print(f"\n{'=' * 70}")
    print(f"  Fim!")
    print(f"{'=' * 70}\n")


if __name__ == '__main__':
    main()
