"""
Teste de estratégias: escolhe um concurso de corte, gera números usando
os dados anteriores ao corte e compara com o resultado real.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import random
from collections import Counter

from modules.statistics import calcular_estatisticas, calcular_escada_temporal
from modules.game_generator import gerar_jogo


def carregar_dados_api():
    """Carrega dados do histórico local."""
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "historico_completo.json")
    df = pd.read_json(cache_file)
    for i in range(1, 7):
        df[f'dez{i}'] = pd.to_numeric(df[f'dez{i}'], errors='coerce').fillna(0).astype(int)

    # Garantir que concurso seja int
    df['concurso'] = df['concurso'].astype(int)
    df = df.sort_values('concurso', ascending=False).reset_index(drop=True)
    return df


def testar_estrategias(df, concurso_corte, n_jogos_por_estrategia=10):
    """
    Testa todas as estratégias usando dados anteriores ao concurso de corte.

    Args:
        df: DataFrame completo
        concurso_corte: Número do concurso a prever
        n_jogos_por_estrategia: Quantos jogos gerar por estratégia
    """
    # Separar: resultado real e dados de treino
    mask_resultado = df['concurso'] == concurso_corte
    if not mask_resultado.any():
        print(f"Concurso {concurso_corte} nao encontrado nos dados!")
        return

    row_resultado = df[mask_resultado].iloc[0]
    resultado_real = sorted([int(row_resultado[f'dez{i}']) for i in range(1, 7)])

    # Dados de treino: apenas concursos ANTERIORES ao corte
    df_treino = df[df['concurso'] < concurso_corte].copy().reset_index(drop=True)

    if len(df_treino) < 100:
        print(f"Dados insuficientes antes do concurso {concurso_corte} ({len(df_treino)} registros)")
        return

    print("=" * 70)
    print(f"  TESTE DE ESTRATEGIAS - Concurso {concurso_corte}")
    print(f"  Resultado real: {resultado_real}")
    print(f"  Dados de treino: {len(df_treino)} concursos anteriores")
    print(f"  Jogos por estrategia: {n_jogos_por_estrategia}")
    print("=" * 70)

    # Calcular estatísticas com dados de treino
    contagem_total, contagem_recente, df_atrasos = calcular_estatisticas(df_treino)

    estrategias = [
        'atrasados', 'quentes', 'atraso_recente', 'equilibrado',
        'misto', 'escada', 'consenso', 'aleatorio_smart',
        'ensemble', 'sequencias', 'wheel',
        'candidatos_ouro', 'momentum', 'vizinhanca',
        'frequencia_desvio', 'pares_frequentes', 'ciclos'
    ]

    resultados = {}

    for est in estrategias:
        acertos_lista = []
        melhor_jogo = None
        melhor_acertos = 0
        todos_jogos = []

        for _ in range(n_jogos_por_estrategia):
            try:
                jogo = gerar_jogo(est, contagem_total, contagem_recente, df_atrasos, df=df_treino)
                acertos = len(set(jogo) & set(resultado_real))
                acertos_lista.append(acertos)
                todos_jogos.append((jogo, acertos))

                if acertos > melhor_acertos:
                    melhor_acertos = acertos
                    melhor_jogo = jogo
            except Exception as e:
                print(f"  [ERRO] {est}: {e}")

        if acertos_lista:
            media = sum(acertos_lista) / len(acertos_lista)
            resultados[est] = {
                'media': media,
                'melhor': melhor_acertos,
                'melhor_jogo': melhor_jogo,
                'distribuicao': Counter(acertos_lista),
                'jogos': len(acertos_lista),
                'todos_jogos': todos_jogos,
            }

    # Exibir resultados ordenados pelo melhor acerto
    print()
    print("-" * 70)
    print(f"  {'ESTRATEGIA':<20} {'MELHOR':>7} {'MEDIA':>7} {'JOGOS':>6}  DISTRIBUICAO DE ACERTOS")
    print("-" * 70)

    for est, res in sorted(resultados.items(), key=lambda x: (-x[1]['melhor'], -x[1]['media'])):
        dist_str = "  ".join(f"{k}ac:{v}x" for k, v in sorted(res['distribuicao'].items(), reverse=True))
        print(f"  {est:<20} {res['melhor']:>5}   {res['media']:>5.2f}  {res['jogos']:>5}  {dist_str}")

    # Mostrar os melhores jogos de cada estratégia
    print()
    print("=" * 70)
    print("  MELHORES JOGOS POR ESTRATEGIA")
    print("=" * 70)

    for est, res in sorted(resultados.items(), key=lambda x: (-x[1]['melhor'], -x[1]['media'])):
        jogo = res['melhor_jogo']
        if jogo is None:
            print(f"  {est:<20} -> (nenhum jogo valido gerado)")
            continue
        acertados = sorted(set(jogo) & set(resultado_real))
        jogo_fmt = []
        for n in jogo:
            if n in resultado_real:
                jogo_fmt.append(f"[{n:02d}]")
            else:
                jogo_fmt.append(f" {n:02d} ")
        print(f"  {est:<20} -> {' '.join(jogo_fmt)}  ({res['melhor']} acertos: {acertados})")

    # Números mais escolhidos pelas estratégias
    print()
    print("=" * 70)
    print("  NUMEROS MAIS FREQUENTES NOS JOGOS GERADOS (todas estrategias)")
    print("=" * 70)

    todos_numeros = []
    for est, res in resultados.items():
        for jogo, _ in res['todos_jogos']:
            todos_numeros.extend(jogo)

    freq = Counter(todos_numeros)
    top20 = freq.most_common(20)
    for num, count in top20:
        marcador = " <-- ACERTO!" if num in resultado_real else ""
        print(f"  Num {num:02d}: {count:>4}x escolhido{marcador}")

    print()
    print(f"  Dos 20 mais frequentes, {sum(1 for n,_ in top20 if n in resultado_real)} estavam no resultado real")

    return resultados


def testar_multiplos_concursos(df, n_concursos=10, n_jogos=20):
    """Testa estratégias em múltiplos concursos e consolida."""
    ultimo = df['concurso'].max()
    concursos = list(range(ultimo - n_concursos + 1, ultimo + 1))

    consolidado = {}  # estrategia -> {acertos_total, jogos_total, melhores, distribuicao}

    for conc in concursos:
        random.seed(conc)  # seed diferente mas reprodutível por concurso
        res = testar_estrategias(df, conc, n_jogos_por_estrategia=n_jogos)
        if res is None:
            continue
        for est, dados in res.items():
            if est not in consolidado:
                consolidado[est] = {
                    'acertos_total': 0, 'jogos_total': 0,
                    'melhores': [], 'distribuicao': Counter()
                }
            consolidado[est]['acertos_total'] += sum(a for _, a in dados['todos_jogos'] if a is not None)
            consolidado[est]['jogos_total'] += dados['jogos']
            consolidado[est]['melhores'].append(dados['melhor'])
            consolidado[est]['distribuicao'] += dados['distribuicao']

    # Relatório consolidado
    print("\n" + "=" * 70)
    print(f"  CONSOLIDADO: {n_concursos} CONCURSOS ({concursos[0]} a {concursos[-1]})")
    print(f"  {n_jogos} jogos por estrategia por concurso")
    print("=" * 70)
    print(f"  {'ESTRATEGIA':<20} {'MEDIA':>7} {'MELHOR':>7} {'MAX':>5}  DISTRIBUICAO")
    print("-" * 70)

    for est, dados in sorted(consolidado.items(),
                              key=lambda x: (-max(x[1]['melhores']),
                                             -x[1]['acertos_total']/max(x[1]['jogos_total'],1))):
        media = dados['acertos_total'] / max(dados['jogos_total'], 1)
        melhor_medio = sum(dados['melhores']) / len(dados['melhores'])
        maximo = max(dados['melhores'])
        dist = dados['distribuicao']
        dist_str = "  ".join(f"{k}ac:{v}x" for k, v in sorted(dist.items(), reverse=True))
        print(f"  {est:<20} {media:>5.2f}   {melhor_medio:>5.2f}   {maximo:>3}  {dist_str}")

    print()


if __name__ == "__main__":
    print("Carregando dados da API...")
    df = carregar_dados_api()
    print(f"Dados carregados: {len(df)} concursos")

    ultimo_concurso = df['concurso'].max()
    print(f"Ultimo concurso disponivel: {ultimo_concurso}")

    # TESTE 1: Concurso mais recente
    print("\n" + "#" * 70)
    print("# TESTE 1: Ultimo concurso")
    print("#" * 70)
    random.seed(42)
    testar_estrategias(df, ultimo_concurso, n_jogos_por_estrategia=20)

    # TESTE 2: Consolidado dos ultimos 10 concursos
    print("\n" + "#" * 70)
    print("# TESTE 2: Consolidado dos ultimos 10 concursos")
    print("#" * 70)
    testar_multiplos_concursos(df, n_concursos=10, n_jogos=20)
