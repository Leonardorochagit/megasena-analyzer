"""
Compara ensemble com 7 estratégias (original) vs 15 estratégias (novo)
usando os mesmos concursos e seed para comparação justa.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import random
from collections import Counter

from modules.statistics import calcular_estatisticas
from modules.game_generator import gerar_jogo, gerar_jogo_ensemble


# Monkey-patch para testar ensemble com 7 vs 15 estratégias
def gerar_ensemble_7(contagem_total, contagem_recente, df_atrasos, df=None):
    """Ensemble original com 7 estratégias"""
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
    candidatos = sorted(votos.keys(), key=lambda n: (votos[n], contagem_recente.get(n, 0)), reverse=True)
    for _ in range(100):
        pool = candidatos[:20]
        jogo = sorted(random.sample(pool, 6))
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        if 2 <= pares <= 4 and 140 <= soma <= 210:
            return jogo
    return sorted(candidatos[:6])


def gerar_ensemble_15(contagem_total, contagem_recente, df_atrasos, df=None):
    """Ensemble novo com 15 estratégias"""
    return gerar_jogo_ensemble(contagem_total, contagem_recente, df_atrasos, df=df)


def carregar_dados_api():
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "historico_completo.json")
    df = pd.read_json(cache_file)
    for i in range(1, 7):
        df[f'dez{i}'] = pd.to_numeric(df[f'dez{i}'], errors='coerce').fillna(0).astype(int)
    df['concurso'] = df['concurso'].astype(int)
    df = df.sort_values('concurso', ascending=False).reset_index(drop=True)
    return df


def testar_ensemble(df, n_concursos=10, n_jogos=50):
    """Compara ensemble 7 vs 15 em múltiplos concursos"""
    ultimo = df['concurso'].max()
    concursos = list(range(ultimo - n_concursos + 1, ultimo + 1))

    resultados = {'ensemble_7': {'acertos': [], 'melhores': [], 'dist': Counter()},
                  'ensemble_15': {'acertos': [], 'melhores': [], 'dist': Counter()}}

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

        print(f"\n  Concurso {conc} - Resultado: {resultado_real}")

        for nome, func in [('ensemble_7', gerar_ensemble_7), ('ensemble_15', gerar_ensemble_15)]:
            melhor = 0
            random.seed(conc)  # Mesmo seed para comparação justa
            for _ in range(n_jogos):
                try:
                    jogo = func(contagem_total, contagem_recente, df_atrasos, df=df_treino)
                    ac = len(set(jogo) & set(resultado_real))
                    resultados[nome]['acertos'].append(ac)
                    resultados[nome]['dist'][ac] += 1
                    if ac > melhor:
                        melhor = ac
                except Exception:
                    pass
            resultados[nome]['melhores'].append(melhor)
            print(f"    {nome:>12}: melhor={melhor}  (seed={conc})")

    # Consolidado
    print("\n" + "=" * 70)
    print(f"  COMPARACAO ENSEMBLE: 7 vs 15 ESTRATEGIAS")
    print(f"  {n_concursos} concursos, {n_jogos} jogos cada")
    print("=" * 70)
    print(f"  {'VERSAO':<15} {'MEDIA':>7} {'MELHOR_MED':>11} {'MAX':>5}  DISTRIBUICAO")
    print("-" * 70)

    for nome in ['ensemble_7', 'ensemble_15']:
        r = resultados[nome]
        media = sum(r['acertos']) / len(r['acertos']) if r['acertos'] else 0
        melhor_med = sum(r['melhores']) / len(r['melhores']) if r['melhores'] else 0
        maximo = max(r['melhores']) if r['melhores'] else 0
        dist = r['dist']
        dist_str = "  ".join(f"{k}ac:{v}x" for k, v in sorted(dist.items(), reverse=True))
        print(f"  {nome:<15} {media:>5.2f}   {melhor_med:>9.2f}   {maximo:>3}  {dist_str}")

    # Detalhamento por concurso
    print("\n  POR CONCURSO (melhor de cada):")
    print(f"  {'CONCURSO':<12} {'7-EST':>6} {'15-EST':>7}")
    print("  " + "-" * 28)
    for i, conc in enumerate(concursos):
        if i < len(resultados['ensemble_7']['melhores']):
            m7 = resultados['ensemble_7']['melhores'][i]
            m15 = resultados['ensemble_15']['melhores'][i]
            marcador = " <--" if m7 > m15 else (" **" if m15 > m7 else "")
            print(f"  {conc:<12} {m7:>4}    {m15:>4}  {marcador}")

    print()


if __name__ == "__main__":
    print("Carregando dados...")
    df = carregar_dados_api()
    print(f"OK: {len(df)} concursos")
    testar_ensemble(df, n_concursos=15, n_jogos=50)
