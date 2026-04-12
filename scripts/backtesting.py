"""
================================================================================
📊 BACKTESTING HISTÓRICO DE ESTRATÉGIAS
================================================================================
Simula cada estratégia nos últimos N concursos reais e compara performance.
Resultado: ranking com intervalo de confiança — resposta imediata sobre
qual estratégia realmente funciona.

Uso: python scripts/backtesting.py [--concursos 200] [--cartoes 10] [--numeros 14]
================================================================================
"""

import sys
import os
import json
import random
import argparse
import statistics as st_mod
from datetime import datetime
from collections import defaultdict

# Fix encoding no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np
import pandas as pd
from modules import statistics as stats
from modules import game_generator as gen


# ── Configuração ──────────────────────────────────────────────

ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso',
    'aleatorio_smart', 'ensemble', 'sequencias'
]


def carregar_historico_completo():
    """Carrega todos os concursos da API ou arquivo local."""
    # Tentar cache local primeiro
    cache_file = os.path.join(ROOT, "data", "historico_completo.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            data = json.load(f)
        if len(data) > 2000:
            print(f"  Usando cache local ({len(data)} concursos)")
            df = pd.DataFrame(data)
            for i in range(1, 7):
                df[f'dez{i}'] = df[f'dez{i}'].astype(int)
            return df

    # Baixar da API
    import requests
    print("  Baixando histórico completo da API...")
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        r = requests.get(url, timeout=60)
        data = r.json()
        if isinstance(data, dict):
            data = [data]

        df = pd.DataFrame(data)
        df['dezenas'] = df['dezenas'].apply(lambda x: str(x))
        div = df['dezenas'].str.split(',')
        for i in range(6):
            df[f'dez{i+1}'] = div.str.get(i).apply(
                lambda x: int(x.strip().replace("'", "").replace("[", "").replace("]", "")) if x else 0
            )

        # Salvar cache
        os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
        cache_data = []
        for _, row in df.iterrows():
            cache_data.append({
                'concurso': int(row['concurso']),
                **{f'dez{i}': int(row[f'dez{i}']) for i in range(1, 7)}
            })
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print(f"  Cache salvo: {len(cache_data)} concursos")

        return df
    except Exception as e:
        print(f"  ERRO ao carregar dados: {e}")
        return None


def executar_backtesting(df, n_concursos=200, cartoes_por_estrategia=10, qtd_numeros=14):
    """
    Para cada concurso dos últimos N:
    1. Usa os dados ANTERIORES ao concurso para calcular estatísticas
    2. Gera cartões com cada estratégia
    3. Confere contra o resultado real
    """
    resultados = defaultdict(lambda: {'acertos': [], 'ternos': 0, 'quadras': 0, 'quinas': 0, 'senas': 0})

    total_concursos = len(df)
    if total_concursos < n_concursos + 100:
        n_concursos = total_concursos - 100
        print(f"  Ajustando para {n_concursos} concursos (dados insuficientes)")

    # Concursos para testar (do mais recente para trás)
    concursos_teste = range(n_concursos)

    print(f"\n  Backtesting: {n_concursos} concursos × {len(ESTRATEGIAS)} estratégias × {cartoes_por_estrategia} cartões")
    print(f"  Total de jogos simulados: {n_concursos * len(ESTRATEGIAS) * cartoes_por_estrategia:,}")
    print(f"  Números por cartão: {qtd_numeros}")
    print()

    for idx in concursos_teste:
        # O concurso a ser testado
        resultado_row = df.iloc[idx]
        resultado = [int(resultado_row[f'dez{i}']) for i in range(1, 7)]

        # Dados disponíveis: todos os concursos ANTES deste (simulando previsão real)
        df_historico = df.iloc[idx + 1:]  # Tudo que veio antes (df está em ordem decrescente)

        if len(df_historico) < 50:
            continue

        # Calcular estatísticas com dados passados
        contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df_historico)

        # Gerar cartões para cada estratégia
        for estrategia in ESTRATEGIAS:
            for _ in range(cartoes_por_estrategia):
                try:
                    # Gerar jogo base
                    dezenas_base = gen.gerar_jogo(
                        estrategia, contagem_total, contagem_recente, df_atrasos,
                        df=df_historico
                    )

                    # Expandir se necessário
                    if qtd_numeros > 6:
                        dezenas = gen.expandir_jogo(
                            dezenas_base, qtd_numeros, estrategia,
                            contagem_total, contagem_recente, df_atrasos,
                            df=df_historico
                        )
                    else:
                        dezenas = dezenas_base

                    # Conferir acertos
                    acertos = len(set(dezenas) & set(resultado))
                    resultados[estrategia]['acertos'].append(acertos)

                    if acertos >= 6:
                        resultados[estrategia]['senas'] += 1
                    elif acertos == 5:
                        resultados[estrategia]['quinas'] += 1
                    elif acertos == 4:
                        resultados[estrategia]['quadras'] += 1
                    elif acertos == 3:
                        resultados[estrategia]['ternos'] += 1

                except Exception:
                    pass

        # Progresso
        if (idx + 1) % 20 == 0:
            print(f"  [{idx+1}/{n_concursos}] concursos processados...")

    return resultados


def calcular_estatisticas_resultado(resultados):
    """Calcula média, IC95%, e ranking."""
    ranking = []

    for est, dados in resultados.items():
        acertos = dados['acertos']
        if not acertos:
            continue

        n = len(acertos)
        media = sum(acertos) / n
        desvio = st_mod.stdev(acertos) if n > 1 else 0
        ic95 = 1.96 * desvio / (n ** 0.5)

        ranking.append({
            'estrategia': est,
            'jogos': n,
            'media': media,
            'desvio': desvio,
            'ic95_inf': media - ic95,
            'ic95_sup': media + ic95,
            'ternos': dados['ternos'],
            'quadras': dados['quadras'],
            'quinas': dados['quinas'],
            'senas': dados['senas'],
        })

    ranking.sort(key=lambda x: x['media'], reverse=True)
    return ranking


def imprimir_resultado(ranking, n_concursos, qtd_numeros):
    """Imprime tabela de resultados formatada."""
    print("\n" + "=" * 85)
    print(f"  RESULTADO DO BACKTESTING ({n_concursos} concursos, {qtd_numeros} números/cartão)")
    print("=" * 85)

    print(f"\n  {'#':<3} {'Estratégia':<20} {'Jogos':>6} {'Média':>6} {'IC95%':>14} {'Ternos':>6} {'Quadr':>5} {'Quina':>5} {'Sena':>4}")
    print("  " + "-" * 80)

    medalhas = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(ranking):
        medalha = medalhas[i] if i < 3 else f"{i+1:>2}"
        ic_str = f"[{r['ic95_inf']:.3f}, {r['ic95_sup']:.3f}]"
        print(f"  {medalha} {r['estrategia']:<20} {r['jogos']:>6} {r['media']:>6.3f} {ic_str:>14} {r['ternos']:>6} {r['quadras']:>5} {r['quinas']:>5} {r['senas']:>4}")

    # Análise de sobreposição
    print("\n  " + "-" * 80)
    print("  ANÁLISE DE SIGNIFICÂNCIA:")
    if len(ranking) >= 2:
        melhor = ranking[0]
        for r in ranking[1:]:
            # Verifica se os ICs se sobrepõem
            sobrepoe = melhor['ic95_inf'] < r['ic95_sup'] and r['ic95_inf'] < melhor['ic95_sup']
            status = "INDISTINGUÍVEL" if sobrepoe else "SIGNIFICATIVAMENTE PIOR"
            print(f"    {melhor['estrategia']} vs {r['estrategia']}: {status}")

    print("\n" + "=" * 85)


def salvar_resultado(ranking, n_concursos, qtd_numeros):
    """Salva resultado em JSON para referência futura."""
    resultado = {
        'data': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'parametros': {
            'n_concursos': n_concursos,
            'qtd_numeros': qtd_numeros,
        },
        'ranking': ranking
    }

    arquivo = os.path.join(ROOT, "data", "backtesting_resultado.json")
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"\n  Resultado salvo em: {arquivo}")


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Backtesting de estratégias da Mega-Sena')
    parser.add_argument('--concursos', type=int, default=100,
                        help='Número de concursos para testar (default: 100)')
    parser.add_argument('--cartoes', type=int, default=5,
                        help='Cartões por estratégia por concurso (default: 5)')
    parser.add_argument('--numeros', type=int, default=14,
                        help='Quantidade de números por cartão (default: 14)')
    args = parser.parse_args()

    print("=" * 60)
    print("📊 BACKTESTING HISTÓRICO DE ESTRATÉGIAS")
    print("=" * 60)

    # Carregar dados
    print("\n📥 Carregando dados históricos...")
    df = carregar_historico_completo()
    if df is None:
        print("ERRO: Não foi possível carregar dados.")
        return

    print(f"  Total de concursos disponíveis: {len(df)}")

    # Executar backtesting
    print("\n🔄 Executando backtesting...")
    resultados = executar_backtesting(
        df,
        n_concursos=args.concursos,
        cartoes_por_estrategia=args.cartoes,
        qtd_numeros=args.numeros
    )

    # Calcular e exibir resultado
    ranking = calcular_estatisticas_resultado(resultados)
    imprimir_resultado(ranking, args.concursos, args.numeros)
    salvar_resultado(ranking, args.concursos, args.numeros)


if __name__ == '__main__':
    main()
