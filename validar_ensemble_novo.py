"""
Validação backtest: novo ensemble (10 estratégias × 14 via expandir_jogo)
vs antigo (10 estratégias × 6). Usa as 10 estratégias do ENSEMBLE_TOP10.
"""

import json
import os
import random
import time
from collections import Counter

import pandas as pd

from modules import statistics as stats
from modules import game_generator as gen


N_CONCURSOS = 400
N_CARTOES = 5
NUMS_POR_CARTAO = 14

ENSEMBLE_TOP10 = [
    'atrasados', 'candidatos_ouro', 'ciclos', 'consenso', 'equilibrado',
    'escada', 'frequencia_desvio', 'momentum', 'pares_frequentes', 'sequencias'
]

ARQUIVO = 'validacao_ensemble_novo.json'


def carregar():
    with open(os.path.join('data', 'historico_completo.json'), 'r', encoding='utf-8') as f:
        dados = json.load(f)
    df = pd.DataFrame(dados)
    for col in ['concurso'] + [f'dez{i}' for i in range(1, 7)]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['concurso']).sort_values('concurso').reset_index(drop=True)


def votar_top(votos, contagem_recente, k=NUMS_POR_CARTAO):
    if not votos:
        return sorted(random.sample(range(1, 61), k))
    ordenados = sorted(
        votos.keys(),
        key=lambda n: (votos[n], contagem_recente.get(n, 0)),
        reverse=True
    )
    if len(ordenados) < k:
        extras = [n for n in range(1, 61) if n not in ordenados]
        random.shuffle(extras)
        ordenados.extend(extras[:k - len(ordenados)])
    return sorted(ordenados[:k])


def cartao_novo(ct, cr, da, df):
    votos = Counter()
    for est in ENSEMBLE_TOP10:
        try:
            base = gen.gerar_jogo(est, ct, cr, da, df=df)
            exp = gen.expandir_jogo(base, NUMS_POR_CARTAO, est, ct, cr, da, df=df)
            for n in exp:
                votos[int(n)] += 1
        except Exception:
            pass
    return votar_top(votos, cr)


def cartao_antigo(ct, cr, da, df):
    votos = Counter()
    for est in ENSEMBLE_TOP10:
        try:
            base = gen.gerar_jogo(est, ct, cr, da, df=df)
            for n in base:
                votos[int(n)] += 1
        except Exception:
            pass
    return votar_top(votos, cr)


def main():
    print("=" * 70)
    print(f"VALIDACAO: ensemble NOVO vs ANTIGO  ({N_CONCURSOS} concursos × {N_CARTOES} cartoes)")
    print("=" * 70)

    df = carregar()
    ultimo = int(df['concurso'].max())
    inicio = ultimo - N_CONCURSOS + 1
    concursos = list(range(inicio, ultimo + 1))
    print(f"Historico: {len(df)} concursos | Testando {len(concursos)} (de {inicio} a {ultimo})")

    # Resultados por metodo
    res = {
        'novo': {'acertos': [], 'melhor_por_conc': [], 'dist': Counter()},
        'antigo': {'acertos': [], 'melhor_por_conc': [], 'dist': Counter()},
    }

    t_inicio = time.time()
    for idx, conc in enumerate(concursos):
        mask = df['concurso'] == conc
        if not mask.any():
            continue
        row = df[mask].iloc[0]
        real = sorted([int(row[f'dez{i}']) for i in range(1, 7)])

        df_treino = df[df['concurso'] < conc].reset_index(drop=True)
        if len(df_treino) < 100:
            continue

        ct, cr, da = stats.calcular_estatisticas(df_treino)

        for metodo in ('novo', 'antigo'):
            melhor = 0
            for i in range(N_CARTOES):
                random.seed(conc * 1000 + i + (0 if metodo == 'novo' else 500))
                func = cartao_novo if metodo == 'novo' else cartao_antigo
                cartao = func(ct, cr, da, df_treino)
                ac = len(set(cartao) & set(real))
                res[metodo]['acertos'].append(ac)
                res[metodo]['dist'][ac] += 1
                if ac > melhor:
                    melhor = ac
            res[metodo]['melhor_por_conc'].append(melhor)

        if (idx + 1) % 20 == 0 or idx == len(concursos) - 1:
            elapsed = time.time() - t_inicio
            rate = (idx + 1) / elapsed
            eta = (len(concursos) - idx - 1) / rate if rate > 0 else 0
            novo_m = sum(res['novo']['acertos']) / len(res['novo']['acertos'])
            antigo_m = sum(res['antigo']['acertos']) / len(res['antigo']['acertos'])
            print(f"  [{idx+1:3d}/{len(concursos)}] {elapsed/60:.1f}m "
                  f"ETA {eta/60:.1f}m | novo_med={novo_m:.3f}  antigo_med={antigo_m:.3f}")

    elapsed = time.time() - t_inicio
    print(f"\nConcluido em {elapsed/60:.1f} minutos")

    # Relatorio
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"{'METODO':<8} {'MEDIA':>7} {'MELHOR_MED':>11} {'MAX':>4} "
          f"{'3+':>4} {'4+':>4} {'5+':>4} {'6':>3}")
    for metodo in ('novo', 'antigo'):
        d = res[metodo]
        media = sum(d['acertos']) / len(d['acertos']) if d['acertos'] else 0
        melhor_med = sum(d['melhor_por_conc']) / len(d['melhor_por_conc']) if d['melhor_por_conc'] else 0
        maximo = max(d['melhor_por_conc']) if d['melhor_por_conc'] else 0
        t3 = sum(c for k, c in d['dist'].items() if k >= 3)
        t4 = sum(c for k, c in d['dist'].items() if k >= 4)
        t5 = sum(c for k, c in d['dist'].items() if k >= 5)
        t6 = d['dist'].get(6, 0)
        print(f"{metodo:<8} {media:7.4f} {melhor_med:11.3f} {maximo:4d} "
              f"{t3:4d} {t4:4d} {t5:4d} {t6:3d}")

    # Por concurso: em quantos o novo ganhou
    venceu_novo = 0
    venceu_antigo = 0
    empate = 0
    for i in range(len(res['novo']['melhor_por_conc'])):
        n = res['novo']['melhor_por_conc'][i]
        a = res['antigo']['melhor_por_conc'][i]
        if n > a: venceu_novo += 1
        elif a > n: venceu_antigo += 1
        else: empate += 1
    print(f"\nComparacao por concurso (melhor cartao):")
    print(f"  Novo venceu:   {venceu_novo:4d}")
    print(f"  Antigo venceu: {venceu_antigo:4d}")
    print(f"  Empate:        {empate:4d}")

    # Salvar
    with open(ARQUIVO, 'w', encoding='utf-8') as f:
        json.dump({
            'config': {
                'n_concursos': N_CONCURSOS,
                'n_cartoes': N_CARTOES,
                'estrategias': ENSEMBLE_TOP10,
                'nums_por_cartao': NUMS_POR_CARTAO,
            },
            'resultados': {
                'novo': {
                    'media': sum(res['novo']['acertos'])/len(res['novo']['acertos']),
                    'dist': dict(res['novo']['dist']),
                    'melhor_por_conc': res['novo']['melhor_por_conc'],
                },
                'antigo': {
                    'media': sum(res['antigo']['acertos'])/len(res['antigo']['acertos']),
                    'dist': dict(res['antigo']['dist']),
                    'melhor_por_conc': res['antigo']['melhor_por_conc'],
                },
            },
            'comparacao': {
                'novo_venceu': venceu_novo,
                'antigo_venceu': venceu_antigo,
                'empate': empate,
            },
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo em {ARQUIVO}")


if __name__ == '__main__':
    main()
