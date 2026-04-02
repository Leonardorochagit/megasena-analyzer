"""
================================================================================
🤖 AUTOMAÇÃO - DIA DE JOGO
================================================================================
Script para rodar automaticamente nos dias de sorteio.
Faz duas coisas:
  1. Confere resultados de cartões pendentes (concursos já sorteados)
  2. Gera um novo lote de cartões para o PRÓXIMO concurso

Mega-Sena: sorteios às terças, quintas e sábados.

Uso:
  python scripts/automacao_dia_jogo.py
  python scripts/automacao_dia_jogo.py --qtd-numeros 10 --cartoes-por-estrategia 3
  python scripts/automacao_dia_jogo.py --apenas-conferir
  python scripts/automacao_dia_jogo.py --apenas-gerar
================================================================================
"""

import sys
import os
import json
import random
import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter
from math import comb

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURAÇÕES PADRÃO
# =============================================================================

ARQUIVO_CARTOES = "meus_cartoes.json"
ARQUIVO_HISTORICO = "historico_analises.json"

TODAS_ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart'
]

NOMES_ESTRATEGIAS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Números Atrasados',
    'quentes': '🔥 Números Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Inteligente',
}

CUSTOS_CARTAO = {
    6: 6.00, 7: 42.00, 8: 168.00, 9: 504.00, 10: 1260.00,
    11: 2772.00, 12: 5544.00, 13: 10296.00, 14: 18018.00, 15: 30030.00,
    16: 48048.00, 17: 74256.00, 18: 111384.00, 19: 162792.00, 20: 232560.00
}


# =============================================================================
# FUNÇÕES DE DADOS (sem Streamlit)
# =============================================================================

def carregar_dados_api():
    """Carrega dados da API sem depender do Streamlit"""
    print("📡 Carregando histórico da API...")
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        response = requests.get(url, timeout=30)
        data = response.json()

        if isinstance(data, dict):
            data = [data]
        df = pd.DataFrame(data)

        # Processar dezenas
        df['dezenas'] = df['dezenas'].apply(lambda x: str(x))
        div = df['dezenas'].str.split(',')
        for i in range(6):
            col_name = f'dez{i+1}'
            df[col_name] = div.str.get(i).apply(
                lambda x: x.replace("['", '').replace("'", '').replace("]", '').strip() if x else x
            )

        # Tentar atualizar com API oficial
        try:
            url_oficial = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
            resp_oficial = requests.get(url_oficial, timeout=10)
            concurso_oficial = resp_oficial.json()
            concurso_num = concurso_oficial.get('numero', 0)

            if concurso_num > df['concurso'].max():
                novo_row = {
                    'concurso': concurso_num,
                    'data': concurso_oficial.get('dataApuracao', ''),
                    'dezenas': ','.join(concurso_oficial.get('listaDezenas', []))
                }
                for i, dez in enumerate(concurso_oficial.get('listaDezenas', []), 1):
                    novo_row[f'dez{i}'] = str(dez)
                df = pd.concat([pd.DataFrame([novo_row]), df], ignore_index=True)
                print(f"  ✨ Concurso {concurso_num} atualizado da API oficial!")
        except:
            pass

        print(f"  ✅ {len(df)} concursos carregados. Último: {int(df['concurso'].max())}")
        return df

    except Exception as e:
        print(f"  ❌ Erro ao carregar dados: {e}")
        return None


def carregar_cartoes():
    """Carrega cartões do arquivo JSON"""
    try:
        if os.path.exists(ARQUIVO_CARTOES):
            with open(ARQUIVO_CARTOES, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            cartoes = []
            for i, cartao in enumerate(dados, 1):
                if isinstance(cartao, list):
                    cartoes.append({
                        'id': f'CART-{i}', 'dezenas': cartao,
                        'estrategia': 'Importado', 'vai_jogar': False,
                        'verificado': False, 'concurso_alvo': None
                    })
                else:
                    cartoes.append(cartao)
            return cartoes
        return []
    except Exception as e:
        print(f"  ⚠️ Erro ao carregar cartões: {e}")
        return []


def salvar_cartoes(cartoes):
    """Salva cartões no arquivo JSON"""
    try:
        cartoes_limpos = []
        for cartao in cartoes:
            c = {}
            for key, value in cartao.items():
                if hasattr(value, 'item'):
                    c[key] = value.item()
                elif isinstance(value, list):
                    c[key] = [int(x) if hasattr(x, 'item') else x for x in value]
                elif isinstance(value, set):
                    c[key] = list(value)
                elif isinstance(value, (np.integer,)):
                    c[key] = int(value)
                elif isinstance(value, (np.floating,)):
                    c[key] = float(value)
                else:
                    c[key] = value
            cartoes_limpos.append(c)

        with open(ARQUIVO_CARTOES, 'w', encoding='utf-8') as f:
            json.dump(cartoes_limpos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"  ❌ Erro ao salvar cartões: {e}")
        return False


def buscar_resultado(numero_concurso):
    """Busca resultado de um concurso na API"""
    try:
        url = f"https://loteriascaixa-api.herokuapp.com/api/megasena/{numero_concurso}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'dezenas' in data:
                dezenas_str = data['dezenas']
                if isinstance(dezenas_str, str):
                    dezenas = [int(x.strip().replace("'", "").replace("[", "").replace("]", ""))
                               for x in dezenas_str.split(',')]
                elif isinstance(dezenas_str, list):
                    dezenas = [int(x) for x in dezenas_str]
                return sorted(dezenas)
        return None
    except:
        return None


def salvar_historico(concurso, stats_concurso, dezenas_sorteadas):
    """Salva no histórico de análises"""
    historico = []
    try:
        if os.path.exists(ARQUIVO_HISTORICO):
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                historico = json.load(f)
    except:
        pass

    novo = {
        'concurso': concurso,
        'data_analise': datetime.now().strftime('%Y-%m-%d'),
        'dezenas_sorteadas': dezenas_sorteadas,
        'estatisticas': stats_concurso,
        'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    historico = [novo if item.get('concurso') == concurso else item for item in historico]
    if not any(item.get('concurso') == concurso for item in historico):
        historico.append(novo)

    try:
        with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


# =============================================================================
# FUNÇÕES DE ESTATÍSTICAS (sem Streamlit)
# =============================================================================

def calcular_estatisticas(df, ultimos=50):
    """Calcula estatísticas básicas"""
    todas_dezenas = []
    for i in range(1, 7):
        todas_dezenas.extend(df[f'dez{i}'].astype(int).tolist())

    contagem_total = pd.Series(todas_dezenas).value_counts().sort_index()
    for num in range(1, 61):
        if num not in contagem_total.index:
            contagem_total[num] = 0
    contagem_total = contagem_total.sort_index()

    df_recentes = df.head(ultimos)
    dezenas_recentes = []
    for i in range(1, 7):
        dezenas_recentes.extend(df_recentes[f'dez{i}'].astype(int).tolist())
    contagem_recente = pd.Series(dezenas_recentes).value_counts()

    atrasos = {}
    for num in range(1, 61):
        for idx, row in df.iterrows():
            numeros = [int(row[f'dez{i}']) for i in range(1, 7)]
            if num in numeros:
                atrasos[num] = idx
                break
        else:
            atrasos[num] = len(df)

    df_atrasos = pd.DataFrame(list(atrasos.items()), columns=['numero', 'jogos_sem_sair'])
    df_atrasos = df_atrasos.sort_values('jogos_sem_sair', ascending=False)

    return contagem_total, contagem_recente, df_atrasos


def calcular_escada_temporal(df, janela_recente=50):
    """Calcula escada temporal para inversões"""
    todas_dezenas = []
    for i in range(1, 7):
        todas_dezenas.extend(df[f'dez{i}'].astype(int).tolist())
    freq_total = pd.Series(todas_dezenas).value_counts()
    for num in range(1, 61):
        if num not in freq_total.index:
            freq_total[num] = 0
    freq_total = freq_total.sort_index()

    df_recentes = df.head(janela_recente)
    dezenas_recentes = []
    for i in range(1, 7):
        dezenas_recentes.extend(df_recentes[f'dez{i}'].astype(int).tolist())
    freq_recente = pd.Series(dezenas_recentes).value_counts()
    for num in range(1, 61):
        if num not in freq_recente.index:
            freq_recente[num] = 0
    freq_recente = freq_recente.sort_index()

    freq_total_norm = (freq_total / freq_total.sum() * 100).round(2)
    freq_recente_norm = (freq_recente / freq_recente.sum() * 100).round(2)
    variacao = freq_recente_norm - freq_total_norm

    media_total = freq_total.mean()
    media_recente = freq_recente.mean()
    inversoes = []

    for num in range(1, 61):
        eh_frio_total = freq_total[num] < media_total
        eh_quente_recente = freq_recente[num] >= media_recente
        variacao_positiva = variacao[num] > 0.3

        if (eh_frio_total and eh_quente_recente) or (eh_frio_total and variacao_positiva):
            inversoes.append({
                'numero': num,
                'freq_total': int(freq_total[num]),
                'freq_recente': int(freq_recente[num]),
                'variacao': round(float(variacao[num]), 2),
                'tipo': 'Inversão Alta'
            })

    inversoes = sorted(inversoes, key=lambda x: x['variacao'], reverse=True)
    return freq_total, freq_recente, freq_total_norm, freq_recente_norm, variacao, inversoes


# =============================================================================
# GERAÇÃO DE JOGOS (sem Streamlit)
# =============================================================================

def gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos, df=None):
    """Gera um jogo de 6 números baseado na estratégia"""
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(20).index.tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'quentes':
        candidatos = contagem_recente.head(20).index.tolist()
        jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'equilibrado':
        pares = [n for n in range(2, 61, 2)]
        impares = [n for n in range(1, 61, 2)]
        jogo = random.sample(pares, 3) + random.sample(impares, 3)
        jogo = sorted(jogo)

    elif estrategia == 'escada':
        if df is not None:
            _, _, _, _, _, inversoes = calcular_escada_temporal(df)
            if inversoes and len(inversoes) >= 6:
                candidatos = [inv['numero'] for inv in inversoes[:20]]
                jogo = sorted(random.sample(candidatos, 6))
            else:
                candidatos = contagem_total.sort_values().head(15).index.tolist()
                jogo = sorted(random.sample(candidatos, 6))
        else:
            candidatos = contagem_total.sort_values().head(15).index.tolist()
            jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'consenso':
        atrasados = set(contagem_total.sort_values().head(15).index.tolist())
        quentes = set(contagem_recente.head(15).index.tolist())
        df_atr_top = set(df_atrasos.head(15)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(df_atr_top)
        contagem = Counter(todos)
        consenso = [num for num, count in contagem.items() if count >= 2]
        if len(consenso) >= 6:
            jogo = sorted(random.sample(consenso, 6))
        else:
            candidatos = contagem_total.sort_values().head(20).index.tolist()
            jogo = sorted(random.sample(candidatos, 6))

    elif estrategia == 'aleatorio_smart':
        jogo = sorted(random.sample(range(1, 61), 6))
        for _ in range(100):
            jogo = sorted(random.sample(range(1, 61), 6))
            pares = sum(1 for n in jogo if n % 2 == 0)
            soma = sum(jogo)
            if 2 <= pares <= 4 and 140 <= soma <= 210:
                break

    else:  # misto
        atrasados = contagem_total.sort_values().head(15).index.tolist()
        quentes = contagem_recente.head(15).index.tolist()
        df_atr_top = df_atrasos.head(15)['numero'].tolist()
        jogo = []
        jogo.extend(random.sample(atrasados, 2))
        quentes_f = [n for n in quentes if n not in jogo]
        jogo.extend(random.sample(quentes_f, 2))
        atraso_f = [n for n in df_atr_top if n not in jogo]
        if len(atraso_f) >= 2:
            jogo.extend(random.sample(atraso_f, 2))
        else:
            restantes = [n for n in range(1, 61) if n not in jogo]
            jogo.extend(random.sample(restantes, 2))
        jogo = sorted(jogo)

    return jogo


def expandir_jogo(dezenas_base, qtd_numeros, estrategia, contagem_total, contagem_recente, df_atrasos, df):
    """Expande um jogo de 6 para N números baseado na estratégia"""
    pool_size = max(40, qtd_numeros + 10)
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(pool_size).index.tolist()
    elif estrategia == 'quentes':
        candidatos = contagem_recente.nlargest(pool_size).index.tolist()
    elif estrategia == 'escada':
        _, _, _, _, _, inversoes = calcular_escada_temporal(df)
        candidatos = [inv['numero'] for inv in inversoes[:pool_size]] if inversoes else list(range(1, 61))
    else:
        candidatos = list(range(1, 61))

    candidatos = [n for n in candidatos if n not in dezenas_base]
    random.shuffle(candidatos)
    extras = candidatos[:qtd_numeros - 6]

    # Garantir que temos números suficientes
    if len(extras) < qtd_numeros - 6:
        todos_restantes = [n for n in range(1, 61) if n not in dezenas_base and n not in extras]
        random.shuffle(todos_restantes)
        extras.extend(todos_restantes[:qtd_numeros - 6 - len(extras)])

    return sorted(dezenas_base + extras)


# =============================================================================
# 1. CONFERIR RESULTADOS PENDENTES
# =============================================================================

def conferir_pendentes(df, cartoes):
    """Confere resultados de todos os cartões pendentes"""
    print("\n" + "=" * 65)
    print("  ✅ CONFERINDO RESULTADOS PENDENTES")
    print("=" * 65)

    concursos_pendentes = sorted(set(
        c.get('concurso_alvo') for c in cartoes
        if c.get('concurso_alvo') and not c.get('verificado', False)
    ))

    if not concursos_pendentes:
        print("\n  ✅ Nenhum cartão pendente de conferência!")
        return cartoes, {}

    print(f"\n  📋 {len(concursos_pendentes)} concurso(s) pendente(s): {concursos_pendentes}")

    resultados_gerais = {}

    for concurso in concursos_pendentes:
        jogos = [c for c in cartoes if c.get('concurso_alvo') == concurso and not c.get('verificado', False)]
        print(f"\n  🎯 Concurso {concurso}: {len(jogos)} cartões para conferir")

        # Buscar resultado
        resultado = buscar_resultado(concurso)

        # Tentar do DataFrame se não encontrou na API
        if not resultado and 'concurso' in df.columns:
            max_c = int(df['concurso'].max())
            if concurso <= max_c:
                linha = df[df['concurso'] == concurso]
                if not linha.empty:
                    row = linha.iloc[0]
                    dezenas = []
                    for i in range(1, 7):
                        try:
                            dezenas.append(int(row.get(f'dez{i}')))
                        except:
                            pass
                    if len(dezenas) == 6:
                        resultado = sorted(dezenas)

        if not resultado:
            print(f"     ⏳ Resultado do concurso {concurso} ainda não disponível")
            continue

        print(f"     🎲 Resultado: {' - '.join(f'{n:02d}' for n in resultado)}")

        # Conferir cada jogo
        stats_concurso = {}
        for jogo in jogos:
            acertos = len(set(jogo['dezenas']) & set(resultado))
            jogo['acertos'] = acertos
            jogo['verificado'] = True
            jogo['resultado_concurso'] = resultado
            jogo['data_verificacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            est = jogo.get('estrategia', 'N/A')
            if est not in stats_concurso:
                stats_concurso[est] = {
                    'total_jogos': 0, 'total_acertos': 0,
                    'senas': 0, 'quinas': 0, 'quadras': 0,
                    'melhor_acerto': 0, 'acertos_list': []
                }
            s = stats_concurso[est]
            s['total_jogos'] += 1
            s['total_acertos'] += acertos
            s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
            s['acertos_list'].append(acertos)
            if acertos == 6: s['senas'] += 1
            elif acertos == 5: s['quinas'] += 1
            elif acertos == 4: s['quadras'] += 1

        # Calcular médias
        for est in stats_concurso:
            s = stats_concurso[est]
            s['media_acertos'] = round(s['total_acertos'] / s['total_jogos'], 2) if s['total_jogos'] > 0 else 0

        resultados_gerais[concurso] = stats_concurso

        # Exibir resumo
        total_jogos = sum(s['total_jogos'] for s in stats_concurso.values())
        total_quadras = sum(s['quadras'] for s in stats_concurso.values())
        total_quinas = sum(s['quinas'] for s in stats_concurso.values())
        total_senas = sum(s['senas'] for s in stats_concurso.values())
        melhor = max(s['melhor_acerto'] for s in stats_concurso.values())

        print(f"\n     📊 RESUMO CONCURSO {concurso}:")
        print(f"        Jogos: {total_jogos} | Melhor: {melhor} acertos")
        if total_quadras: print(f"        🥉 Quadras: {total_quadras}")
        if total_quinas:  print(f"        🥈 Quinas: {total_quinas}")
        if total_senas:   print(f"        🏆 SENAS: {total_senas}")

        print(f"\n     📊 Por estratégia:")
        ranking = sorted(stats_concurso.items(), key=lambda x: x[1]['media_acertos'], reverse=True)
        for pos, (est, dados) in enumerate(ranking, 1):
            medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f" {pos}."
            nome = NOMES_ESTRATEGIAS.get(est, est)
            print(f"        {medalha} {nome}: média {dados['media_acertos']:.2f} | melhor {dados['melhor_acerto']} acertos | {dados['total_jogos']} jogos")

        # Salvar no histórico
        # Converter acertos_list para não serializar
        stats_para_salvar = {}
        for est, dados in stats_concurso.items():
            stats_para_salvar[est] = {k: v for k, v in dados.items() if k != 'acertos_list'}
        salvar_historico(concurso, stats_para_salvar, resultado)

    return cartoes, resultados_gerais


# =============================================================================
# 2. GERAR LOTE PARA PRÓXIMO CONCURSO
# =============================================================================

def gerar_lote_proximo(df, cartoes, qtd_numeros=10, cartoes_por_estrategia=3, estrategias=None):
    """Gera lote de cartões para o próximo concurso"""
    if estrategias is None:
        estrategias = TODAS_ESTRATEGIAS

    proximo = int(df['concurso'].max()) + 1

    # Verificar se já existem cartões para esse concurso
    existentes = [c for c in cartoes if c.get('concurso_alvo') == proximo]
    if existentes:
        print(f"\n  ⚠️ Já existem {len(existentes)} cartões para o concurso {proximo}.")
        print(f"     Pulando geração. Use --forcar para gerar mesmo assim.")
        return cartoes, proximo

    print("\n" + "=" * 65)
    print(f"  🎲 GERANDO CARTÕES PARA O CONCURSO {proximo}")
    print("=" * 65)

    total = cartoes_por_estrategia * len(estrategias)
    custo_unitario = CUSTOS_CARTAO.get(qtd_numeros, 0)
    custo_total = total * custo_unitario

    print(f"\n  ⚙️ Configuração:")
    print(f"     Concurso alvo: {proximo}")
    print(f"     Números por cartão: {qtd_numeros}")
    print(f"     Estratégias: {len(estrategias)}")
    print(f"     Cartões por estratégia: {cartoes_por_estrategia}")
    print(f"     Total de cartões: {total}")
    print(f"     Custo por cartão: R$ {custo_unitario:,.2f}")
    print(f"     Custo total: R$ {custo_total:,.2f}")
    print(f"     Combinações por cartão: {comb(qtd_numeros, 6):,}")

    # Calcular estatísticas
    contagem_total, contagem_recente, df_atrasos = calcular_estatisticas(df)

    novos = []
    for estrategia in estrategias:
        nome = NOMES_ESTRATEGIAS.get(estrategia, estrategia)
        print(f"\n  📊 {nome}:")

        for i in range(cartoes_por_estrategia):
            # Gerar jogo base
            dezenas_base = gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos, df)

            # Expandir se necessário
            if qtd_numeros > 6:
                dezenas = expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                                        contagem_total, contagem_recente, df_atrasos, df)
            else:
                dezenas = dezenas_base

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cartao = {
                'id': f'{estrategia.upper()}-{timestamp}-{i+1:02d}',
                'dezenas': sorted(dezenas),
                'estrategia': estrategia,
                'vai_jogar': True,
                'verificado': False,
                'concurso_alvo': proximo,
                'status': 'aguardando',
                'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'qtd_numeros': qtd_numeros
            }
            novos.append(cartao)
            nums = ' - '.join(f'{n:02d}' for n in cartao['dezenas'])
            print(f"     #{i+1:02d}  {nums}")

    cartoes.extend(novos)
    print(f"\n  ✅ {len(novos)} cartões gerados para o concurso {proximo}!")
    return cartoes, proximo


# =============================================================================
# RANKING CONSOLIDADO
# =============================================================================

def exibir_ranking_geral(cartoes):
    """Exibe ranking geral de todas as estratégias"""
    verificados = [c for c in cartoes if c.get('verificado', False) and c.get('acertos') is not None]

    if not verificados:
        print("\n  📭 Nenhum cartão verificado ainda para gerar ranking.")
        return

    print("\n" + "=" * 65)
    print("  🏆 RANKING GERAL DE ESTRATÉGIAS")
    print("=" * 65)

    ranking = {}
    for c in verificados:
        est = c.get('estrategia', 'N/A')
        if est not in ranking:
            ranking[est] = {
                'jogos': 0, 'total_acertos': 0, 'senas': 0, 'quinas': 0,
                'quadras': 0, 'melhor': 0, 'concursos': set()
            }
        r = ranking[est]
        r['jogos'] += 1
        acertos = c.get('acertos', 0)
        r['total_acertos'] += acertos
        r['melhor'] = max(r['melhor'], acertos)
        if acertos == 6: r['senas'] += 1
        elif acertos == 5: r['quinas'] += 1
        elif acertos == 4: r['quadras'] += 1
        if c.get('concurso_alvo'):
            r['concursos'].add(c['concurso_alvo'])

    lista = []
    for est, dados in ranking.items():
        media = dados['total_acertos'] / dados['jogos'] if dados['jogos'] > 0 else 0
        score = dados['senas'] * 1000 + dados['quinas'] * 100 + dados['quadras'] * 10 + media
        lista.append({
            'estrategia': est,
            'nome': NOMES_ESTRATEGIAS.get(est, est),
            'jogos': dados['jogos'],
            'media': media,
            'melhor': dados['melhor'],
            'senas': dados['senas'],
            'quinas': dados['quinas'],
            'quadras': dados['quadras'],
            'concursos': len(dados['concursos']),
            'score': score
        })

    lista.sort(key=lambda x: x['score'], reverse=True)

    for pos, item in enumerate(lista, 1):
        medalha = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f" {pos}."
        print(f"\n  {medalha} {item['nome']}")
        print(f"     {item['jogos']} jogos em {item['concursos']} concurso(s)")
        print(f"     Média: {item['media']:.2f} | Melhor: {item['melhor']} acertos | Score: {item['score']:.2f}")
        premios = []
        if item['senas']: premios.append(f"🏆{item['senas']} Sena")
        if item['quinas']: premios.append(f"🥈{item['quinas']} Quina")
        if item['quadras']: premios.append(f"🥉{item['quadras']} Quadra")
        if premios:
            print(f"     Prêmios: {' | '.join(premios)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='🤖 Mega Sena Analyzer - Automação Dia de Jogo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/automacao_dia_jogo.py                           # Confere + gera (padrão: 10 nums, 3 cartões)
  python scripts/automacao_dia_jogo.py --qtd-numeros 12          # Cartões com 12 números
  python scripts/automacao_dia_jogo.py --cartoes-por-estrategia 5 # 5 cartões por estratégia
  python scripts/automacao_dia_jogo.py --apenas-conferir         # Só confere resultados
  python scripts/automacao_dia_jogo.py --apenas-gerar            # Só gera novos cartões
  python scripts/automacao_dia_jogo.py --forcar                  # Gera mesmo se já existirem cartões
        """
    )

    parser.add_argument('--qtd-numeros', type=int, default=10,
                        choices=range(6, 21),
                        help='Quantidade de números por cartão (6-20, padrão: 10)')
    parser.add_argument('--cartoes-por-estrategia', type=int, default=3,
                        help='Cartões por estratégia (padrão: 3)')
    parser.add_argument('--apenas-conferir', action='store_true',
                        help='Apenas conferir resultados pendentes')
    parser.add_argument('--apenas-gerar', action='store_true',
                        help='Apenas gerar novos cartões')
    parser.add_argument('--forcar', action='store_true',
                        help='Forçar geração mesmo se já existirem cartões para o próximo concurso')
    parser.add_argument('--estrategias', nargs='+', default=None,
                        choices=TODAS_ESTRATEGIAS,
                        help='Estratégias a usar (padrão: todas)')

    args = parser.parse_args()

    # Mudar para o diretório raiz do projeto
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print("\n" + "=" * 65)
    print("  🎰 MEGA SENA ANALYZER - AUTOMAÇÃO DIA DE JOGO")
    print(f"  📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 65)

    # Carregar dados
    df = carregar_dados_api()
    if df is None:
        print("\n❌ Impossível continuar sem dados. Abortando.")
        sys.exit(1)

    cartoes = carregar_cartoes()
    print(f"\n  💾 {len(cartoes)} cartões carregados")

    # 1. Conferir pendentes
    if not args.apenas_gerar:
        cartoes, resultados = conferir_pendentes(df, cartoes)
        salvar_cartoes(cartoes)

    # 2. Gerar lote para próximo
    if not args.apenas_conferir:
        if args.forcar:
            # Remover cartões existentes do próximo concurso
            proximo = int(df['concurso'].max()) + 1
            cartoes = [c for c in cartoes if c.get('concurso_alvo') != proximo]

        cartoes, proximo = gerar_lote_proximo(
            df, cartoes,
            qtd_numeros=args.qtd_numeros,
            cartoes_por_estrategia=args.cartoes_por_estrategia,
            estrategias=args.estrategias or TODAS_ESTRATEGIAS
        )
        salvar_cartoes(cartoes)

    # 3. Ranking geral
    exibir_ranking_geral(cartoes)

    # Resumo final
    pendentes = [c for c in cartoes if not c.get('verificado', False)]
    verificados = [c for c in cartoes if c.get('verificado', False)]

    print("\n" + "=" * 65)
    print("  📋 RESUMO FINAL")
    print("=" * 65)
    print(f"  Total de cartões: {len(cartoes)}")
    print(f"  Verificados: {len(verificados)}")
    print(f"  Pendentes: {len(pendentes)}")
    concursos_p = sorted(set(c.get('concurso_alvo') for c in pendentes if c.get('concurso_alvo')))
    if concursos_p:
        print(f"  Concursos pendentes: {concursos_p}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
