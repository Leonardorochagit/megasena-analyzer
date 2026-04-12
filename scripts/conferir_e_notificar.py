"""
================================================================================
🤖 SCRIPT STANDALONE: CONFERIR E NOTIFICAR (GitHub Actions)
================================================================================
Roda fora do Streamlit — confere cartões pendentes, envia WhatsApp,
gera cartões para o próximo concurso e salva tudo de volta nos JSONs.

Uso: python scripts/conferir_e_notificar.py
Variáveis de ambiente necessárias:
  WHATSAPP_TELEFONE  — número com DDI (ex: 5561999999999)
  WHATSAPP_APIKEY    — chave CallMeBot
================================================================================
"""

import json
import os
import sys
import random
import requests
from datetime import datetime
from collections import Counter

# Adicionar raiz do projeto ao path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from modules import data_manager as dm
from modules import statistics as stats
from modules import game_generator as gen
from modules import notificacoes as notif

# ── Configuração ──────────────────────────────────────────────

TODAS_ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart'
]

QTD_NUMEROS = 14
CARTOES_POR_ESTRATEGIA = 20


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── Buscar resultado da API ──────────────────────────────────

def buscar_ultimo_resultado():
    """Busca o último concurso sorteado direto da API oficial da Caixa."""
    apis = [
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
        "https://loteriascaixa-api.herokuapp.com/api/megasena/latest",
    ]
    for url in apis:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()

            numero = data.get('numero') or data.get('concurso')
            dezenas_raw = data.get('listaDezenas') or data.get('dezenas')

            if isinstance(dezenas_raw, str):
                dezenas = [int(x.strip().replace("'", "").replace("[", "").replace("]", ""))
                           for x in dezenas_raw.split(',')]
            elif isinstance(dezenas_raw, list):
                dezenas = [int(x) for x in dezenas_raw]
            else:
                continue

            if numero and len(dezenas) == 6:
                return {
                    'numero': int(numero),
                    'dezenas': sorted(dezenas),
                    'acumulou': data.get('acumulou'),
                    'valor_proximo': (
                        data.get('valorEstimadoProximoConcurso')
                        or data.get('valorAcumuladoProximoConcurso')
                    ),
                }
        except Exception as e:
            log(f"  API {url} falhou: {e}")
            continue
    return None


def buscar_resultado_concurso(numero):
    """Busca resultado de um concurso específico."""
    apis = [
        f"https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/{numero}",
        f"https://loteriascaixa-api.herokuapp.com/api/megasena/{numero}",
    ]
    for url in apis:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            dezenas_raw = data.get('listaDezenas') or data.get('dezenas')

            if isinstance(dezenas_raw, str):
                dezenas = [int(x.strip().replace("'", "").replace("[", "").replace("]", ""))
                           for x in dezenas_raw.split(',')]
            elif isinstance(dezenas_raw, list):
                dezenas = [int(x) for x in dezenas_raw]
            else:
                continue

            if len(dezenas) == 6:
                return {
                    'dezenas': sorted(dezenas),
                    'acumulou': data.get('acumulou'),
                    'valor_proximo': (
                        data.get('valorEstimadoProximoConcurso')
                        or data.get('valorAcumuladoProximoConcurso')
                    ),
                }
        except Exception:
            continue
    return None


# ── Conferir cartões ─────────────────────────────────────────

def conferir_cartoes():
    """Confere todos os cartões pendentes e retorna dados da conferência."""
    todos_cartoes = dm.carregar_cartoes_salvos()

    pendentes_por_concurso = {}
    for c in todos_cartoes:
        if not c.get('verificado', False) and c.get('concurso_alvo'):
            conc = c['concurso_alvo']
            pendentes_por_concurso.setdefault(conc, []).append(c)

    if not pendentes_por_concurso:
        log("Nenhum cartão pendente de conferência.")
        return None, todos_cartoes

    conferidos = []
    alterou = False

    for concurso in sorted(pendentes_por_concurso.keys()):
        log(f"Buscando resultado do concurso {concurso}...")
        res = buscar_resultado_concurso(concurso)
        if not res:
            log(f"  Concurso {concurso} ainda não sorteado.")
            continue

        resultado = res['dezenas']
        jogos = pendentes_por_concurso[concurso]
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
                    'senas': 0, 'quinas': 0, 'quadras': 0, 'ternos': 0,
                    'melhor_acerto': 0, 'media_acertos': 0
                }
            s = stats_concurso[est]
            s['total_jogos'] += 1
            s['total_acertos'] += acertos
            s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
            if acertos == 6:
                s['senas'] += 1
            elif acertos == 5:
                s['quinas'] += 1
            elif acertos == 4:
                s['quadras'] += 1
            elif acertos == 3:
                s['ternos'] += 1

        for est in stats_concurso:
            t = stats_concurso[est]['total_jogos']
            stats_concurso[est]['media_acertos'] = round(
                stats_concurso[est]['total_acertos'] / t, 2) if t > 0 else 0

        dm.salvar_historico_analise(
            concurso,
            datetime.now().strftime("%Y-%m-%d"),
            stats_concurso,
            resultado
        )

        melhor = max(j.get('acertos', 0) for j in jogos)
        conferidos.append({
            'concurso': concurso,
            'resultado': resultado,
            'total_jogos': len(jogos),
            'melhor_acerto': melhor,
            'stats': stats_concurso,
            'acumulou': res.get('acumulou'),
            'valor_proximo_concurso': res.get('valor_proximo'),
        })
        alterou = True
        log(f"  ✅ Concurso {concurso} conferido — melhor acerto: {melhor}")

    if alterou:
        dm.salvar_cartoes(todos_cartoes)

    if conferidos:
        return {'status': 'conferido', 'conferidos': conferidos}, todos_cartoes
    return None, todos_cartoes


# ── Gerar novos cartões ──────────────────────────────────────

def gerar_cartoes_proximo_concurso(todos_cartoes):
    """Gera cartões para o próximo concurso se ainda não existem."""
    ultimo = buscar_ultimo_resultado()
    if not ultimo:
        log("Não foi possível obter o último concurso da API.")
        return 0

    proximo = ultimo['numero'] + 1

    # Verificar se "proximo" já foi sorteado (APIs podem estar defasadas)
    res_proximo = buscar_resultado_concurso(proximo)
    if res_proximo:
        log(f"Concurso {proximo} já foi sorteado, avançando para {proximo + 1}.")
        proximo += 1

    ja_existem = [c for c in todos_cartoes
                  if c.get('concurso_alvo') == proximo and not c.get('verificado', False)]
    if ja_existem:
        log(f"Já existem {len(ja_existem)} cartões para o concurso {proximo}.")
        return 0

    log(f"Gerando cartões para o concurso {proximo}...")

    # Carregar dados para estatísticas
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        r = requests.get(url, timeout=30)
        data = r.json()
        if isinstance(data, dict):
            data = [data]
        import pandas as pd
        df = pd.DataFrame(data)
        df['dezenas'] = df['dezenas'].apply(lambda x: str(x))
        div = df['dezenas'].str.split(',')
        for i in range(6):
            df[f'dez{i+1}'] = div.str.get(i).apply(
                lambda x: x.replace("['", '').replace("'", '').replace("]", '').strip() if x else x
            )
    except Exception as e:
        log(f"Erro ao carregar dados para geração: {e}")
        return 0

    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)
    novos = []

    for estrategia in TODAS_ESTRATEGIAS:
        for i in range(CARTOES_POR_ESTRATEGIA):
            try:
                dezenas_base = gen.gerar_jogo(
                    estrategia=estrategia,
                    contagem_total=contagem_total,
                    contagem_recente=contagem_recente,
                    df_atrasos=df_atrasos
                )
                if QTD_NUMEROS > 6:
                    dezenas = _expandir_jogo(
                        dezenas_base, QTD_NUMEROS, estrategia,
                        contagem_total, contagem_recente, df_atrasos, df
                    )
                else:
                    dezenas = dezenas_base

                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                novos.append({
                    'id': f'AUTO-{estrategia.upper()}-{ts}-{i+1:02d}',
                    'dezenas': sorted(dezenas),
                    'estrategia': estrategia,
                    'vai_jogar': True,
                    'verificado': False,
                    'concurso_alvo': proximo,
                    'status': 'aguardando',
                    'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'qtd_numeros': QTD_NUMEROS,
                    'origem': 'github_actions'
                })
            except Exception:
                pass

    if novos:
        todos_cartoes.extend(novos)
        dm.salvar_cartoes(todos_cartoes)
        log(f"  ✅ {len(novos)} cartões gerados para o concurso {proximo}")

    return len(novos)


def _expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                   contagem_total, contagem_recente, df_atrasos, df):
    """Expande um jogo de 6 para N números."""
    pool_size = max(40, qtd_numeros + 10)
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(pool_size).index.tolist()
    elif estrategia == 'quentes':
        candidatos = contagem_recente.nlargest(pool_size).index.tolist()
    elif estrategia == 'escada':
        try:
            _, _, _, _, _, inversoes = stats.calcular_escada_temporal(df)
            candidatos = [inv['numero'] for inv in inversoes[:pool_size]] if inversoes else list(range(1, 61))
        except Exception:
            candidatos = list(range(1, 61))
    else:
        candidatos = list(range(1, 61))

    candidatos = [n for n in candidatos if n not in dezenas_base]
    random.shuffle(candidatos)
    extras = candidatos[:qtd_numeros - 6]
    return sorted(dezenas_base + extras)


# ── Enviar WhatsApp ──────────────────────────────────────────

def enviar_whatsapp(resultado_conferencia):
    """Envia resultado por WhatsApp via CallMeBot."""
    telefone = os.environ.get('WHATSAPP_TELEFONE', '')
    apikey = os.environ.get('WHATSAPP_APIKEY', '')

    if not telefone or not apikey:
        log("⚠️  WHATSAPP_TELEFONE ou WHATSAPP_APIKEY não configurados.")
        return False

    mensagem = notif.formatar_resultado_concurso(resultado_conferencia)
    res = notif.enviar_whatsapp(telefone, apikey, mensagem)

    if res['sucesso']:
        log("📲 WhatsApp enviado com sucesso!")
        return True
    else:
        log(f"❌ Falha no WhatsApp: {res['mensagem']}")
        return False


# ── Main ─────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("🤖 CONFERIR E NOTIFICAR — GitHub Actions")
    log("=" * 60)

    # 1. Conferir cartões pendentes
    log("\n📋 Etapa 1: Conferindo cartões pendentes...")
    resultado_conferencia, todos_cartoes = conferir_cartoes()

    # 2. Enviar WhatsApp se houve conferência
    if resultado_conferencia and resultado_conferencia.get('status') == 'conferido':
        log("\n📲 Etapa 2: Enviando notificação WhatsApp...")
        enviar_whatsapp(resultado_conferencia)
    else:
        log("\n📲 Etapa 2: Nada a notificar (sem conferências novas).")

    # 3. Gerar cartões para o próximo concurso
    log("\n🎲 Etapa 3: Gerando cartões para o próximo concurso...")
    gerados = gerar_cartoes_proximo_concurso(todos_cartoes)

    # Resumo
    log("\n" + "=" * 60)
    if resultado_conferencia and resultado_conferencia.get('conferidos'):
        for conf in resultado_conferencia['conferidos']:
            log(f"✅ Concurso {conf['concurso']}: {conf['total_jogos']} jogos, melhor acerto: {conf['melhor_acerto']}")
    log(f"🎲 Cartões gerados: {gerados}")
    log("=" * 60)


if __name__ == '__main__':
    main()
