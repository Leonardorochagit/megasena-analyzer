"""
================================================================================
🤖 SCRIPT STANDALONE: CONFERIR E NOTIFICAR (GitHub Actions)
================================================================================
Roda fora do Streamlit — confere cartões pendentes, envia WhatsApp,
gera cartões para o próximo concurso, alerta bolão quando ≥R$100M,
e salva tudo de volta nos JSONs.

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
import glob
import requests
import pandas as pd
from datetime import datetime
from collections import Counter

# Adicionar raiz do projeto ao path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from modules import statistics as stats
from modules import game_generator as gen
from modules import notificacoes as notif
from helpers import converter_dezenas_para_int, versao_estrategia

# ── Persistência JSON direta (sem SQLite/Streamlit) ──────────────

CARTOES_FILE = os.path.join(ROOT, "meus_cartoes.json")
HISTORICO_FILE = os.path.join(ROOT, "historico_analises.json")


def _load_cartoes():
    try:
        with open(CARTOES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_cartoes(cartoes):
    with open(CARTOES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cartoes, f, indent=2, ensure_ascii=False)


def _load_historico():
    try:
        with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_historico_analise(concurso, data_analise, estatisticas, dezenas_sorteadas=None):
    historico = _load_historico()
    registro = {
        'concurso': concurso,
        'data_analise': data_analise,
        'estatisticas': estatisticas,
    }
    if dezenas_sorteadas:
        registro['dezenas_sorteadas'] = dezenas_sorteadas
    historico = [r for r in historico if r.get('concurso') != concurso]
    historico.append(registro)
    with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def _arquivar_verificados():
    todos = _load_cartoes()
    verificados = [c for c in todos if c.get('verificado', False)]
    pendentes = [c for c in todos if not c.get('verificado', False)]
    if not verificados:
        return 0, len(pendentes)
    ano = datetime.now().strftime('%Y')
    data_dir = os.path.join(ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    arquivo = os.path.join(data_dir, f"cartoes_arquivo_{ano}.json")
    existentes = []
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            existentes = json.load(f)
    existentes.extend(verificados)
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(existentes, f, indent=2, ensure_ascii=False)
    _save_cartoes(pendentes)
    return len(verificados), len(pendentes)


def _load_cartoes_arquivados():
    cartoes = []
    padrao = os.path.join(ROOT, "data", "cartoes_arquivo_*.json")
    for arquivo in sorted(glob.glob(padrao)):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            if isinstance(dados, list):
                cartoes.extend(dados)
        except Exception as e:
            log(f"  Não foi possível ler {arquivo}: {e}")
    return cartoes


def _normalizar_concurso_opcional(concurso):
    if concurso is None:
        return None
    concurso_txt = str(concurso).strip()
    if not concurso_txt:
        return None
    try:
        return int(concurso_txt)
    except ValueError:
        log(f"  Concurso de reenvio inválido ({concurso_txt!r}); usando o último histórico.")
        return None


def reconstruir_conferencia_historica(concurso=None):
    """Reconstrói uma conferência já salva para reenvio manual."""
    concurso = _normalizar_concurso_opcional(concurso)
    historico = _load_historico()
    if not historico:
        return None

    registros = [
        r for r in historico
        if r.get('concurso') and r.get('dezenas_sorteadas') and r.get('estatisticas')
    ]
    if concurso is not None:
        registros = [r for r in registros if int(r.get('concurso')) == concurso]
    if not registros:
        return None

    registro = max(registros, key=lambda r: int(r.get('concurso') or 0))
    concurso = int(registro['concurso'])
    resultado = registro.get('dezenas_sorteadas') or []
    stats_concurso = registro.get('estatisticas') or {}

    cartoes = [
        c for c in (_load_cartoes() + _load_cartoes_arquivados())
        if int(c.get('concurso_alvo') or 0) == concurso and c.get('verificado')
    ]
    total_jogos = len(cartoes) or sum(s.get('total_jogos', 0) for s in stats_concurso.values())
    melhor = max(
        [c.get('acertos', 0) for c in cartoes] +
        [s.get('melhor_acerto', 0) for s in stats_concurso.values()] +
        [0]
    )
    quase_acertos = [
        {'dezenas': c.get('dezenas', []), 'acertos': c.get('acertos', 0), 'estrategia': c.get('estrategia', 'N/A')}
        for c in cartoes if c.get('acertos', 0) >= 3
    ]

    return {
        'status': 'conferido',
        'conferidos': [{
            'concurso': concurso,
            'resultado': resultado,
            'total_jogos': total_jogos,
            'melhor_acerto': melhor,
            'stats': stats_concurso,
            'cartoes_raw': quase_acertos,
        }],
    }

# ── Configuração ──────────────────────────────────────────────

TODAS_ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart', 'ensemble',
    'sequencias', 'wheel'
]

CONFIG_FILE = os.path.join(ROOT, "piloto_config.json")


def _carregar_config():
    """Carrega configurações do piloto_config.json."""
    defaults = {
        'qtd_numeros': 14,
        'cartoes_por_est': 20,
        'bolao_threshold': 100_000_000,
        'bolao_qtd_numeros': 13,
        'bolao_estrategias': ['misto', 'consenso'],
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        pass
    return defaults


CONFIG = _carregar_config()
QTD_NUMEROS = CONFIG['qtd_numeros']
CARTOES_POR_ESTRATEGIA = CONFIG['cartoes_por_est']
CARTOES_ENSEMBLE = CONFIG.get('cartoes_ensemble', CARTOES_POR_ESTRATEGIA)
ENSEMBLE_ONLY = CONFIG.get('ensemble_only', False)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── Buscar resultado da API ──────────────────────────────────

def buscar_ultimo_resultado():
    """Busca o último concurso sorteado direto da API oficial da Caixa."""
    apis = [
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
    ]
    for url in apis:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()

            numero = data.get('numero') or data.get('concurso')
            dezenas_raw = data.get('listaDezenas') or data.get('dezenas')
            dezenas = converter_dezenas_para_int(dezenas_raw)

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
    ]
    for url in apis:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            dezenas_raw = data.get('listaDezenas') or data.get('dezenas')
            dezenas = converter_dezenas_para_int(dezenas_raw)

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
    todos_cartoes = _load_cartoes()

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

        _save_historico_analise(
            concurso,
            datetime.now().strftime("%Y-%m-%d"),
            stats_concurso,
            resultado
        )

        melhor = max(j.get('acertos', 0) for j in jogos)
        # Guardar cartões com 3+ acertos para dezenas faltantes no WhatsApp
        quase_acertos = [
            {'dezenas': j['dezenas'], 'acertos': j['acertos'], 'estrategia': j.get('estrategia', 'N/A')}
            for j in jogos if j.get('acertos', 0) >= 3
        ]
        conferidos.append({
            'concurso': concurso,
            'resultado': resultado,
            'total_jogos': len(jogos),
            'melhor_acerto': melhor,
            'stats': stats_concurso,
            'acumulou': res.get('acumulou'),
            'valor_proximo_concurso': res.get('valor_proximo'),
            'cartoes_raw': quase_acertos,
        })
        alterou = True
        log(f"  ✅ Concurso {concurso} conferido — melhor acerto: {melhor}")

    if alterou:
        _save_cartoes(todos_cartoes)

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

    # Carregar dados — tentar local primeiro (historico_analises.json + data/),
    # fallback para API
    df = None
    local_csv = os.path.join(ROOT, "data", "megasena_historico.csv")
    if os.path.exists(local_csv):
        try:
            df = pd.read_csv(local_csv)
            if 'concurso' in df.columns and len(df) > 100:
                log(f"  Dados locais carregados: {len(df)} concursos de {local_csv}")
            else:
                df = None
        except Exception:
            df = None

    if df is None:
        local_json = os.path.join(ROOT, "data", "historico_completo.json")
        try:
            with open(local_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            for col in ['concurso'] + [f'dez{i}' for i in range(1, 7)]:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['concurso'] + [f'dez{i}' for i in range(1, 7)]).copy()
            log(f"  Histórico local carregado: {len(df)} concursos de {local_json}")
        except Exception as e:
            log(f"Erro ao carregar histórico local: {e}")
            return 0

    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)
    novos = []

    estrategias_gerar = ['ensemble'] if ENSEMBLE_ONLY else TODAS_ESTRATEGIAS
    log(f"  Modo: {'ensemble_only' if ENSEMBLE_ONLY else 'todas estratégias'} | ensemble={CARTOES_ENSEMBLE} | outros={CARTOES_POR_ESTRATEGIA}")

    for estrategia in estrategias_gerar:
        qtd = CARTOES_ENSEMBLE if estrategia == 'ensemble' else CARTOES_POR_ESTRATEGIA
        for i in range(qtd):
            try:
                dezenas_base = gen.gerar_jogo(
                    estrategia=estrategia,
                    contagem_total=contagem_total,
                    contagem_recente=contagem_recente,
                    df_atrasos=df_atrasos,
                    df=df
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
                    'estrategia_versao': versao_estrategia(estrategia),
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
        _save_cartoes(todos_cartoes)
        log(f"  ✅ {len(novos)} cartões gerados para o concurso {proximo}")

    return len(novos)


def _expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                   contagem_total, contagem_recente, df_atrasos, df):
    """Expande um jogo de 6 para N números mantendo coerência da estratégia."""
    pool_size = max(40, qtd_numeros + 10)
    extras_necessarios = qtd_numeros - len(dezenas_base)

    # Pool de candidatos coerente com a estratégia
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
    elif estrategia == 'equilibrado':
        # Manter proporção par/ímpar equilibrada
        candidatos = list(range(1, 61))
    elif estrategia == 'consenso':
        # Pool dos que aparecem em múltiplas análises
        atrasados = set(contagem_total.sort_values().head(20).index.tolist())
        quentes = set(contagem_recente.nlargest(20).index.tolist())
        atraso_rec = set(df_atrasos.head(20)['numero'].tolist())
        todos = list(atrasados) + list(quentes) + list(atraso_rec)
        contagem = Counter(todos)
        candidatos = [num for num, _ in contagem.most_common(pool_size)]
    elif estrategia == 'misto':
        # Mix: 1/3 atrasados, 1/3 quentes, 1/3 restante
        atrasados = contagem_total.sort_values().head(20).index.tolist()
        quentes = contagem_recente.nlargest(20).index.tolist()
        candidatos = list(set(atrasados + quentes))
        if len(candidatos) < pool_size:
            candidatos.extend([n for n in range(1, 61) if n not in candidatos])
    else:
        candidatos = list(range(1, 61))

    candidatos = [n for n in candidatos if n not in dezenas_base]

    # Tentar gerar expansão com filtros de qualidade
    melhor_jogo = None
    melhor_score = -1

    for _ in range(50):
        random.shuffle(candidatos)
        extras = candidatos[:extras_necessarios]
        jogo = sorted(dezenas_base + extras)

        # Filtros de qualidade
        soma = sum(jogo)
        pares = sum(1 for n in jogo if n % 2 == 0)
        amplitude = jogo[-1] - jogo[0]

        # Faixas proporcionais ao qtd_numeros
        fator = qtd_numeros / 6.0
        soma_ok = (140 * fator * 0.8) <= soma <= (210 * fator * 1.1)
        pares_ok = (qtd_numeros * 0.3) <= pares <= (qtd_numeros * 0.7)
        amp_ok = amplitude >= 30

        score = int(soma_ok) + int(pares_ok) + int(amp_ok)
        if score > melhor_score:
            melhor_score = score
            melhor_jogo = jogo
        if score == 3:
            break

    return melhor_jogo or sorted(dezenas_base + candidatos[:extras_necessarios])


# ── Enviar WhatsApp ──────────────────────────────────────────

def enviar_whatsapp(resultado_conferencia):
    """Envia resultado por WhatsApp via CallMeBot."""
    telefone = os.environ.get('WHATSAPP_TELEFONE', '')
    apikey = os.environ.get('WHATSAPP_APIKEY', '')

    if not telefone or not apikey:
        log("⚠️  WHATSAPP_TELEFONE ou WHATSAPP_APIKEY não configurados.")
        log(f"  WHATSAPP_TELEFONE presente: {bool(telefone)}")
        log(f"  WHATSAPP_APIKEY presente: {bool(apikey)}")
        return False

    log(f"  Enviando para: ...{telefone[-4:]} (apikey: ...{apikey[-4:]})")
    mensagem = notif.formatar_resultado_concurso(resultado_conferencia)
    res = notif.enviar_whatsapp(telefone, apikey, mensagem)

    if res['sucesso']:
        log("📲 WhatsApp enviado com sucesso!")
        return True
    else:
        log(f"❌ Falha no WhatsApp: {res['mensagem']}")
        return False


def _enviar_whatsapp_raw(mensagem):
    """Envia mensagem de texto direta por WhatsApp."""
    telefone = os.environ.get('WHATSAPP_TELEFONE', '')
    apikey = os.environ.get('WHATSAPP_APIKEY', '')
    if not telefone or not apikey:
        return False
    res = notif.enviar_whatsapp(telefone, apikey, mensagem)
    return res['sucesso']


# ── Verificar valor do prêmio / Alerta Bolão ─────────────────

def verificar_alerta_bolao(resultado_conferencia):
    """Se prêmio acumulado ≥ threshold, envia alerta especial de bolão."""
    threshold = CONFIG.get('bolao_threshold', 100_000_000)

    if not resultado_conferencia or not resultado_conferencia.get('conferidos'):
        return

    for conf in resultado_conferencia['conferidos']:
        valor_proximo = conf.get('valor_proximo_concurso')
        if not valor_proximo:
            continue

        try:
            valor = float(valor_proximo)
        except (TypeError, ValueError):
            continue

        if valor < threshold:
            log(f"  Próximo prêmio: {notif._formatar_moeda_br(valor)} (abaixo do threshold {notif._formatar_moeda_br(threshold)})")
            continue

        log(f"  🚨 PRÊMIO ACIMA DO THRESHOLD: {notif._formatar_moeda_br(valor)}")
        proximo_concurso = conf['concurso'] + 1
        mensagem = notif.formatar_alerta_bolao(proximo_concurso, valor, CONFIG)
        if _enviar_whatsapp_raw(mensagem):
            log("  📲 Alerta de bolão enviado!")
        else:
            log("  ❌ Falha ao enviar alerta de bolão")


# ── Ranking global de estratégias ─────────────────────────────

def calcular_ranking_global():
    """Consolida historico_analises.json em ranking acumulado por estratégia."""
    historico = _load_historico()
    if not historico:
        return {}

    acumulado = {}
    for registro in historico:
        for est, dados in registro.get('estatisticas', {}).items():
            if est not in acumulado:
                acumulado[est] = {
                    'total_jogos': 0, 'total_acertos': 0,
                    'senas': 0, 'quinas': 0, 'quadras': 0, 'ternos': 0,
                    'concursos': 0, 'melhor_acerto_global': 0
                }
            a = acumulado[est]
            a['total_jogos'] += dados.get('total_jogos', 0)
            a['total_acertos'] += dados.get('total_acertos', 0)
            a['senas'] += dados.get('senas', 0)
            a['quinas'] += dados.get('quinas', 0)
            a['quadras'] += dados.get('quadras', 0)
            a['ternos'] += dados.get('ternos', 0)
            a['concursos'] += 1
            a['melhor_acerto_global'] = max(a['melhor_acerto_global'], dados.get('melhor_acerto', 0))

    for est, a in acumulado.items():
        a['media_acertos'] = round(a['total_acertos'] / a['total_jogos'], 2) if a['total_jogos'] > 0 else 0
        a['taxa_quadra'] = round(a['quadras'] / a['total_jogos'] * 100, 1) if a['total_jogos'] > 0 else 0
        a['taxa_terno'] = round(a['ternos'] / a['total_jogos'] * 100, 1) if a['total_jogos'] > 0 else 0

    return acumulado


def enviar_ranking_global():
    """Envia ranking acumulado de estratégias por WhatsApp."""
    ranking = calcular_ranking_global()
    if not ranking:
        log("  Nenhum histórico para ranking global.")
        return

    mensagem = notif.formatar_ranking_global(ranking)
    if _enviar_whatsapp_raw(mensagem):
        log("📲 Ranking global enviado!")
    else:
        log("❌ Falha ao enviar ranking global")


# ── Main ─────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("🤖 CONFERIR E NOTIFICAR — GitHub Actions")
    log("=" * 60)

    # 1. Conferir cartões pendentes
    log("\n📋 Etapa 1: Conferindo cartões pendentes...")
    resultado_conferencia, todos_cartoes = conferir_cartoes()
    reenvio_historico = False
    if not resultado_conferencia:
        reenviar = os.environ.get('REENVIAR_ULTIMA_CONFERENCIA', '').lower() in ('1', 'true', 'sim', 'yes')
        concurso_reenvio = os.environ.get('REENVIAR_CONCURSO')
        if reenviar:
            log("\nEtapa 2: Sem conferencias novas; tentando reenviar historico...")
            resultado_conferencia = reconstruir_conferencia_historica(concurso_reenvio)
            reenvio_historico = bool(resultado_conferencia)
            if resultado_conferencia:
                concurso_escolhido = resultado_conferencia['conferidos'][0]['concurso']
                log(f"  Reenvio historico selecionado: concurso {concurso_escolhido}.")
            else:
                log("  Nenhuma conferencia historica encontrada para reenvio.")

    # 2. Enviar WhatsApp com resultado (inclui dezenas faltantes)
    if resultado_conferencia and resultado_conferencia.get('status') == 'conferido':
        log("\n📲 Etapa 2: Enviando notificação WhatsApp...")
        whatsapp_enviado = enviar_whatsapp(resultado_conferencia)

        # Arquivar cartões já conferidos para manter meus_cartoes.json enxuto
        log("\n🗄️  Etapa 2b: Finalizando cartões verificados...")
        if whatsapp_enviado and not reenvio_historico:
            arquivados, mantidos = _arquivar_verificados()
            log(f"  {arquivados} arquivados, {mantidos} pendentes mantidos")
        elif whatsapp_enviado and reenvio_historico:
            log("  Reenvio historico concluido; nenhum arquivamento necessario.")
        else:
            log("  Arquivamento adiado porque o WhatsApp falhou.")
    else:
        log("\n📲 Etapa 2: Nada a notificar (sem conferências novas).")

    # 3. Verificar alerta de bolão (≥R$100M)
    log("\n💰 Etapa 3: Verificando valor do prêmio para alerta de bolão...")
    verificar_alerta_bolao(resultado_conferencia)

    # 4. Gerar cartões para o próximo concurso
    log("\n🎲 Etapa 4: Gerando cartões para o próximo concurso...")
    gerados = gerar_cartoes_proximo_concurso(todos_cartoes)

    # 5. Enviar ranking global (1x por semana — no sábado)
    hoje = datetime.now()
    if hoje.weekday() == 5:  # Sábado
        log("\n📊 Etapa 5: Enviando ranking global semanal...")
        enviar_ranking_global()
    else:
        log(f"\n📊 Etapa 5: Ranking global só no sábado (hoje: {hoje.strftime('%A')}).")

    # Resumo
    log("\n" + "=" * 60)
    if resultado_conferencia and resultado_conferencia.get('conferidos'):
        for conf in resultado_conferencia['conferidos']:
            log(f"✅ Concurso {conf['concurso']}: {conf['total_jogos']} jogos, melhor acerto: {conf['melhor_acerto']}")
    log(f"🎲 Cartões gerados: {gerados}")
    log("=" * 60)


if __name__ == '__main__':
    main()
