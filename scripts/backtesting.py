"""
================================================================================
📊 VALIDAÇÃO WALK-FORWARD DE ESTRATÉGIAS
================================================================================
Executa validação concurso a concurso em modo walk-forward:
1. Escolhe um concurso alvo real
2. Usa apenas concursos ANTERIORES para calcular estatísticas
3. Gera cartões com cada estratégia
4. Confere contra o resultado real
5. Repete até o concurso final (ou atual)

Uso:
  python scripts/backtesting.py --concurso-inicial 2500 --cartoes 10 --numeros 14
  python scripts/backtesting.py --concurso-inicial 2500 --concurso-final 2950 --cartoes 20
  python scripts/backtesting.py --concursos 300 --cartoes 10 --numeros 14

Observações:
  - O padrão é validar os últimos N concursos disponíveis.
  - Para grande volume, AutoML e Wheel ficam fora do padrão porque são mais lentos
    e, no caso do Wheel, a avaliação correta é de portfólio e não de ticket isolado.
================================================================================
"""

import argparse
import json
import math
import os
import random
import statistics as st_mod
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import binomtest, hypergeom, norm

# Fix encoding no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from helpers import VERSOES_ESTRATEGIAS, converter_dezenas_para_int
from modules import game_generator as gen
from modules import statistics as stats


ESTRATEGIAS_PADRAO = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso',
    'aleatorio_smart', 'ensemble', 'sequencias',
    'candidatos_ouro', 'momentum', 'vizinhanca',
    'frequencia_desvio', 'pares_frequentes', 'ciclos'
]


def carregar_historico_completo():
    """Carrega todos os concursos da API ou do cache local."""
    cache_file = os.path.join(ROOT, 'data', 'historico_completo.json')

    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if len(data) > 2000:
            print(f"  Usando cache local ({len(data)} concursos)")
            df = pd.DataFrame(data)
            for i in range(1, 7):
                df[f'dez{i}'] = pd.to_numeric(df[f'dez{i}'], errors='coerce').fillna(0).astype(int)
            df['concurso'] = pd.to_numeric(df['concurso'], errors='coerce').fillna(0).astype(int)
            return df.sort_values('concurso', ascending=False).reset_index(drop=True)

    import requests

    print('  Baixando histórico completo da API...')
    try:
        url = 'https://loteriascaixa-api.herokuapp.com/api/megasena'
        response = requests.get(url, timeout=60)
        data = response.json()
        if isinstance(data, dict):
            data = [data]

        registros = []
        for item in data:
            dezenas = converter_dezenas_para_int(item.get('dezenas') or item.get('listaDezenas'))
            if len(dezenas) != 6:
                continue

            registro = {'concurso': int(item.get('concurso') or item.get('numero') or 0)}
            for idx, dezena in enumerate(sorted(dezenas), start=1):
                registro[f'dez{idx}'] = int(dezena)
            registros.append(registro)

        df = pd.DataFrame(registros)
        df = df.sort_values('concurso', ascending=False).reset_index(drop=True)

        os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(df.to_dict(orient='records'), f, indent=2, ensure_ascii=False)

        print(f"  Cache salvo: {len(df)} concursos")
        return df
    except Exception as exc:
        print(f"  ERRO ao carregar dados: {exc}")
        return None


def resolver_estrategias(args):
    """Resolve a lista final de estratégias a validar."""
    if args.estrategias:
        estrategias = [item.strip() for item in args.estrategias.split(',') if item.strip()]
    else:
        estrategias = list(ESTRATEGIAS_PADRAO)

    if args.incluir_wheel and 'wheel' not in estrategias:
        estrategias.append('wheel')

    if args.incluir_automl and 'automl' not in estrategias:
        estrategias.append('automl')

    return estrategias


def resolver_indices_validacao(df, concurso_inicial=None, concurso_final=None,
                               n_concursos=None, min_historico=50):
    """Resolve quais concursos serão validados em ordem cronológica."""
    concursos = df['concurso'].astype(int)

    if concurso_final is None:
        concurso_final = int(concursos.max())

    if concurso_inicial is not None:
        mask = (concursos >= int(concurso_inicial)) & (concursos <= int(concurso_final))
        indices = df.index[mask].tolist()
    else:
        quantidade = int(n_concursos or 200)
        indices = list(range(min(quantidade, len(df))))

    indices = [idx for idx in indices if len(df.iloc[idx + 1:]) >= min_historico]
    indices.sort(reverse=True)
    return indices


def benchmark_aleatorio(qtd_numeros):
    """Calcula benchmark hipergeométrico para um cartão com N números."""
    probs = {k: float(hypergeom.pmf(k, 60, 6, qtd_numeros)) for k in range(0, 7)}
    media = qtd_numeros * 6 / 60
    variancia = qtd_numeros * (6 / 60) * (1 - 6 / 60) * ((60 - qtd_numeros) / 59)

    return {
        'media_esperada': media,
        'desvio_esperado': math.sqrt(variancia),
        'p_terno_ou_mais': sum(probs[k] for k in range(3, 7)),
        'p_quadra_ou_mais': sum(probs[k] for k in range(4, 7)),
        'p_quina_ou_mais': sum(probs[k] for k in range(5, 7)),
        'probabilidades': probs,
    }


def gerar_dezenas_validacao(estrategia, qtd_numeros, contagem_total,
                            contagem_recente, df_atrasos, df_historico):
    """Gera dezenas para uma estratégia no contexto de validação."""
    if estrategia == 'automl':
        dezenas_base = gen.gerar_jogo_automl(
            df_historico, contagem_total, contagem_recente, df_atrasos
        )
    else:
        dezenas_base = gen.gerar_jogo(
            estrategia, contagem_total, contagem_recente, df_atrasos,
            df=df_historico
        )

    if qtd_numeros > 6:
        return gen.expandir_jogo(
            dezenas_base, qtd_numeros, estrategia,
            contagem_total, contagem_recente, df_atrasos,
            df=df_historico
        )

    return dezenas_base


def executar_validacao_walk_forward(df, indices_teste, estrategias,
                                    cartoes_por_estrategia=10,
                                    qtd_numeros=14,
                                    base_seed=42):
    """Executa validação walk-forward real concurso a concurso."""
    resultados = defaultdict(lambda: {
        'acertos': [],
        'melhor_por_concurso': [],
        'media_por_concurso': [],
        'ternos': 0,
        'quadras': 0,
        'quinas': 0,
        'senas': 0,
        'concursos_com_terno_ou_mais': 0,
        'concursos_com_quadra_ou_mais': 0,
        'concursos_com_quina_ou_mais': 0,
        'concursos': 0,
    })
    detalhes = []

    total_passos = len(indices_teste)
    print(
        f"\n  Validação walk-forward: {total_passos} concursos × "
        f"{len(estrategias)} estratégias × {cartoes_por_estrategia} cartões"
    )
    print(f"  Total de jogos simulados: {total_passos * len(estrategias) * cartoes_por_estrategia:,}")
    print(f"  Números por cartão: {qtd_numeros}")
    print()

    for passo, idx in enumerate(indices_teste, start=1):
        resultado_row = df.iloc[idx]
        concurso = int(resultado_row['concurso'])
        resultado = [int(resultado_row[f'dez{i}']) for i in range(1, 7)]
        df_historico = df.iloc[idx + 1:].copy()

        if len(df_historico) < 50:
            continue

        contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df_historico)
        detalhe_concurso = {
            'concurso': concurso,
            'resultado': resultado,
            'historico_disponivel': len(df_historico),
            'estrategias': {},
        }

        for est_idx, estrategia in enumerate(estrategias):
            acertos_estrategia = []
            melhor = 0

            for cartao_idx in range(cartoes_por_estrategia):
                seed = base_seed + passo * 100_000 + est_idx * 1_000 + cartao_idx
                random.seed(seed)
                np.random.seed(seed % (2 ** 32 - 1))

                try:
                    dezenas = gerar_dezenas_validacao(
                        estrategia,
                        qtd_numeros,
                        contagem_total,
                        contagem_recente,
                        df_atrasos,
                        df_historico,
                    )
                    acertos = len(set(dezenas) & set(resultado))
                except Exception:
                    continue

                resultados[estrategia]['acertos'].append(acertos)
                acertos_estrategia.append(acertos)
                melhor = max(melhor, acertos)

                if acertos == 3:
                    resultados[estrategia]['ternos'] += 1
                elif acertos == 4:
                    resultados[estrategia]['quadras'] += 1
                elif acertos == 5:
                    resultados[estrategia]['quinas'] += 1
                elif acertos >= 6:
                    resultados[estrategia]['senas'] += 1

            if not acertos_estrategia:
                continue

            media_concurso = sum(acertos_estrategia) / len(acertos_estrategia)
            resultados[estrategia]['concursos'] += 1
            resultados[estrategia]['melhor_por_concurso'].append(melhor)
            resultados[estrategia]['media_por_concurso'].append(media_concurso)

            if melhor >= 3:
                resultados[estrategia]['concursos_com_terno_ou_mais'] += 1
            if melhor >= 4:
                resultados[estrategia]['concursos_com_quadra_ou_mais'] += 1
            if melhor >= 5:
                resultados[estrategia]['concursos_com_quina_ou_mais'] += 1

            detalhe_concurso['estrategias'][estrategia] = {
                'media_acertos': round(media_concurso, 4),
                'melhor_acerto': int(melhor),
                'ternos_ou_mais': int(sum(1 for x in acertos_estrategia if x >= 3)),
                'quadras_ou_mais': int(sum(1 for x in acertos_estrategia if x >= 4)),
                'quinas_ou_mais': int(sum(1 for x in acertos_estrategia if x >= 5)),
            }

        detalhes.append(detalhe_concurso)

        if passo % 20 == 0 or passo == total_passos:
            print(f"  [{passo}/{total_passos}] concursos processados... último={concurso}")

    return resultados, detalhes


def calcular_estatisticas_resultado(resultados, qtd_numeros):
    """Calcula métricas finais e benchmark contra o acaso."""
    ranking = []
    benchmark = benchmark_aleatorio(qtd_numeros)
    media_esperada = benchmark['media_esperada']
    p_quadra_ou_mais = benchmark['p_quadra_ou_mais']

    for estrategia, dados in resultados.items():
        acertos = dados['acertos']
        if not acertos:
            continue

        n = len(acertos)
        media = sum(acertos) / n
        desvio = st_mod.stdev(acertos) if n > 1 else 0.0
        ic95 = 1.96 * desvio / math.sqrt(n) if n > 1 else 0.0
        se = desvio / math.sqrt(n) if n > 1 else 0.0
        z_score = (media - media_esperada) / se if se else 0.0
        p_media = 2 * (1 - norm.cdf(abs(z_score))) if se else 1.0

        quadra_plus = dados['quadras'] + dados['quinas'] + dados['senas']
        p_quadra = binomtest(quadra_plus, n, p_quadra_ou_mais).pvalue if n else 1.0

        concursos = max(dados['concursos'], 1)
        ranking.append({
            'estrategia': estrategia,
            'versao': VERSOES_ESTRATEGIAS.get(estrategia, {}).get('versao', '?'),
            'nota_versao': VERSOES_ESTRATEGIAS.get(estrategia, {}).get('nota', ''),
            'concursos': dados['concursos'],
            'jogos': n,
            'media_por_cartao': media,
            'desvio_por_cartao': desvio,
            'ic95_inf': media - ic95,
            'ic95_sup': media + ic95,
            'delta_vs_aleatorio': media - media_esperada,
            'p_media_vs_aleatorio': p_media,
            'media_melhor_cartao_concurso': (
                sum(dados['melhor_por_concurso']) / concursos if dados['melhor_por_concurso'] else 0.0
            ),
            'media_media_concurso': (
                sum(dados['media_por_concurso']) / concursos if dados['media_por_concurso'] else 0.0
            ),
            'taxa_jogo_terno_ou_mais': (dados['ternos'] + dados['quadras'] + dados['quinas'] + dados['senas']) / n,
            'taxa_jogo_quadra_ou_mais': (dados['quadras'] + dados['quinas'] + dados['senas']) / n,
            'taxa_jogo_quina_ou_mais': (dados['quinas'] + dados['senas']) / n,
            'taxa_concurso_terno_ou_mais': dados['concursos_com_terno_ou_mais'] / concursos,
            'taxa_concurso_quadra_ou_mais': dados['concursos_com_quadra_ou_mais'] / concursos,
            'taxa_concurso_quina_ou_mais': dados['concursos_com_quina_ou_mais'] / concursos,
            'p_quadra_ou_mais_vs_aleatorio': p_quadra,
            'ternos': dados['ternos'],
            'quadras': dados['quadras'],
            'quinas': dados['quinas'],
            'senas': dados['senas'],
        })

    ranking.sort(
        key=lambda item: (
            item['media_por_cartao'],
            item['taxa_concurso_quadra_ou_mais'],
            item['taxa_concurso_terno_ou_mais'],
        ),
        reverse=True,
    )
    return ranking, benchmark


def imprimir_resultado(ranking, benchmark, parametros):
    """Imprime tabela de resultados formatada."""
    print('\n' + '=' * 110)
    print(
        f"  RESULTADO DA VALIDAÇÃO WALK-FORWARD "
        f"({parametros['concursos_validos']} concursos, {parametros['qtd_numeros']} números/cartão)"
    )
    print('=' * 110)

    print(
        f"\n  Benchmark aleatório: média={benchmark['media_esperada']:.3f} | "
        f"quadra+={benchmark['p_quadra_ou_mais'] * 100:.2f}% | "
        f"terno+={benchmark['p_terno_ou_mais'] * 100:.2f}%"
    )

    print(
        f"\n  {'#':<3} {'Estratégia':<18} {'Ver':<5} {'Jogos':>6} {'Média':>7} "
        f"{'Δ Aleat.':>9} {'p(média)':>9} {'Q+ jogo':>8} {'Q+ conc':>8} {'p(q+)':>8} {'Melhor/Conc':>12}"
    )
    print('  ' + '-' * 114)

    medalhas = ['🥇', '🥈', '🥉']
    for idx, item in enumerate(ranking):
        prefixo = medalhas[idx] if idx < 3 else f"{idx + 1:>2}"
        print(
            f"  {prefixo} "
            f"{item['estrategia']:<18} "
            f"{item['versao']:<5} "
            f"{item['jogos']:>6} "
            f"{item['media_por_cartao']:>7.3f} "
            f"{item['delta_vs_aleatorio']:>9.3f} "
            f"{item['p_media_vs_aleatorio']:>9.4f} "
            f"{item['taxa_jogo_quadra_ou_mais'] * 100:>7.2f}% "
            f"{item['taxa_concurso_quadra_ou_mais'] * 100:>7.2f}% "
            f"{item['p_quadra_ou_mais_vs_aleatorio']:>8.4f} "
            f"{item['media_melhor_cartao_concurso']:>12.3f}"
        )

    print('\n  ' + '-' * 114)
    print('  Leitura rápida:')
    for item in ranking[:5]:
        status_media = 'acima' if item['delta_vs_aleatorio'] > 0 else 'abaixo'
        signif = 'evidência fraca' if item['p_media_vs_aleatorio'] >= 0.05 else 'evidência estatística'
        print(
            f"    {item['estrategia']} v{item['versao']}: {status_media} do acaso "
            f"({item['delta_vs_aleatorio']:+.3f}) com {signif} "
            f"(p={item['p_media_vs_aleatorio']:.4f})"
        )

    print('\n' + '=' * 110)


def salvar_resultado(ranking, benchmark, detalhes, parametros):
    """Salva resumo e detalhamento em JSON."""
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)

    resumo = {
        'data_execucao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'parametros': parametros,
        'benchmark_aleatorio': benchmark,
        'ranking': ranking,
    }

    arquivo_resumo = os.path.join(ROOT, 'data', 'backtesting_resultado.json')
    arquivo_detalhe = os.path.join(ROOT, 'data', 'backtesting_detalhado.json')

    with open(arquivo_resumo, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    with open(arquivo_detalhe, 'w', encoding='utf-8') as f:
        json.dump({
            'data_execucao': resumo['data_execucao'],
            'parametros': parametros,
            'detalhes': detalhes,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n  Resumo salvo em: {arquivo_resumo}")
    print(f"  Detalhes salvos em: {arquivo_detalhe}")


def main():
    parser = argparse.ArgumentParser(description='Validação walk-forward de estratégias da Mega-Sena')
    parser.add_argument('--concurso-inicial', type=int,
                        help='Primeiro concurso a validar (ex: 2500)')
    parser.add_argument('--concurso-final', type=int,
                        help='Último concurso a validar (default: concurso atual)')
    parser.add_argument('--concursos', type=int, default=300,
                        help='Quantidade de concursos a validar se --concurso-inicial não for usado')
    parser.add_argument('--cartoes', type=int, default=10,
                        help='Cartões por estratégia por concurso (default: 10)')
    parser.add_argument('--numeros', type=int, default=14,
                        help='Quantidade de números por cartão (default: 14)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Seed base para tornar a validação reproduzível')
    parser.add_argument('--estrategias', type=str,
                        help='Lista separada por vírgula. Ex: sequencias,equilibrado,consenso')
    parser.add_argument('--incluir-wheel', action='store_true',
                        help='Inclui a estratégia wheel na validação')
    parser.add_argument('--incluir-automl', action='store_true',
                        help='Inclui a estratégia automl na validação (mais lenta)')
    args = parser.parse_args()

    print('=' * 68)
    print('📊 VALIDAÇÃO WALK-FORWARD DE ESTRATÉGIAS')
    print('=' * 68)

    print('\n📥 Carregando dados históricos...')
    df = carregar_historico_completo()
    if df is None or df.empty:
        print('ERRO: Não foi possível carregar dados.')
        return

    estrategias = resolver_estrategias(args)
    indices_teste = resolver_indices_validacao(
        df,
        concurso_inicial=args.concurso_inicial,
        concurso_final=args.concurso_final,
        n_concursos=args.concursos,
        min_historico=50,
    )

    if not indices_teste:
        print('ERRO: Nenhum concurso válido encontrado para a faixa escolhida.')
        return

    concursos_validos = [int(df.iloc[idx]['concurso']) for idx in indices_teste]
    parametros = {
        'concurso_inicial': min(concursos_validos),
        'concurso_final': max(concursos_validos),
        'concursos_validos': len(concursos_validos),
        'cartoes_por_estrategia': args.cartoes,
        'qtd_numeros': args.numeros,
        'seed': args.seed,
        'estrategias': estrategias,
    }

    print(f"  Total de concursos disponíveis: {len(df)}")
    print(
        f"  Faixa validada: {parametros['concurso_inicial']} → "
        f"{parametros['concurso_final']} ({parametros['concursos_validos']} concursos)"
    )
    print(f"  Estratégias: {', '.join(estrategias)}")

    print('\n🔄 Executando validação...')
    resultados, detalhes = executar_validacao_walk_forward(
        df,
        indices_teste,
        estrategias,
        cartoes_por_estrategia=args.cartoes,
        qtd_numeros=args.numeros,
        base_seed=args.seed,
    )

    ranking, benchmark = calcular_estatisticas_resultado(resultados, args.numeros)
    imprimir_resultado(ranking, benchmark, parametros)
    salvar_resultado(ranking, benchmark, detalhes, parametros)


if __name__ == '__main__':
    main()
