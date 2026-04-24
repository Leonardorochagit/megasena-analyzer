"""
================================================================================
MÓDULO DE GERENCIAMENTO DE DADOS
================================================================================
Gerencia carregamento, salvamento e verificação de dados e cartões.

v4.0 — Backend migrado de JSON para SQLite (modules/db.py).
As assinaturas de todas as funções públicas são mantidas para compatibilidade
com o restante do app. Os arquivos JSON legados não são mais escritos,
mas são lidos durante a migração (scripts/migrar_json_para_sqlite.py).
================================================================================
"""

import json
import os
import re
import requests
import pandas as pd
from datetime import datetime

from modules.db import (
    salvar_cartoes_db,
    carregar_cartoes_db,
    salvar_historico_db,
    carregar_historico_db,
    stats_cartoes_db,
)

try:
    import streamlit as st
except ModuleNotFoundError:
    class _CacheDataFallback:
        def __call__(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def clear(self):
            return None

    class _StreamlitFallback:
        cache_data = _CacheDataFallback()

        @staticmethod
        def success(message):
            print(message)

        @staticmethod
        def warning(message):
            print(message)

        @staticmethod
        def error(message):
            print(message)

    st = _StreamlitFallback()


# ─────────────────────────────────────────────────────────────────────────────
# CAMINHOS DOS ARQUIVOS JSON LEGADOS
# ─────────────────────────────────────────────────────────────────────────────

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JSON_CARTOES = os.path.join(_ROOT, "meus_cartoes.json")
_JSON_HISTORICO = os.path.join(_ROOT, "historico_analises.json")


def _ler_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _escrever_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sincronizar_json_para_db():
    """Importa JSON → SQLite quando o banco estiver vazio. Chame na inicialização."""
    try:
        existentes = carregar_cartoes_db()
    except Exception:
        existentes = []

    if not existentes:
        cartoes_json = _ler_json(_JSON_CARTOES, [])
        if cartoes_json:
            normalizados = [_normalizar_cartao(c) for c in cartoes_json if isinstance(c, dict)]
            salvar_cartoes_db(normalizados)

    try:
        historico_db = carregar_historico_db()
    except Exception:
        historico_db = []

    if not historico_db:
        for r in _ler_json(_JSON_HISTORICO, []):
            if isinstance(r, dict) and r.get('concurso') and r.get('estatisticas'):
                salvar_historico_db(
                    r['concurso'], r.get('data_analise', ''),
                    r['estatisticas'], r.get('dezenas_sorteadas')
                )


# ─────────────────────────────────────────────────────────────────────────────
# SORTEIOS — API DA CAIXA (sem alteração)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def carregar_dados():
    """
    Carrega histórico local e atualiza concursos recentes pela API oficial da Caixa.
    Se a API falhar, retorna o histórico local disponível.
    """
    try:
        historico_json = os.path.join(_ROOT, "data", "historico_completo.json")
        data = _ler_json(historico_json, [])
        if not data:
            historico_csv = os.path.join(_ROOT, "data", "megasena_historico.csv")
            if os.path.exists(historico_csv):
                df = pd.read_csv(historico_csv)
            else:
                raise RuntimeError("Histórico local não encontrado.")
        else:
            df = pd.DataFrame(data)

        df['concurso'] = pd.to_numeric(df['concurso'], errors='coerce')
        df = df.dropna(subset=['concurso']).copy()
        df['concurso'] = df['concurso'].astype(int)

        from helpers import converter_dezenas_para_int
        for idx, row in df.iterrows():
            if not all(f'dez{i}' in df.columns and pd.notna(row.get(f'dez{i}')) for i in range(1, 7)):
                dezenas = converter_dezenas_para_int(row.get('dezenas', []))
                for i, d in enumerate(dezenas[:6], 1):
                    df.at[idx, f'dez{i}'] = str(d)

        for i in range(1, 7):
            df[f'dez{i}'] = pd.to_numeric(df[f'dez{i}'], errors='coerce')
        df = df.dropna(subset=[f'dez{i}' for i in range(1, 7)]).copy()
    except Exception as e:
        st.error(f"Erro ao carregar histórico local: {e}")
        return None

    try:
        url_oficial = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
        resp_oficial = requests.get(url_oficial, timeout=10)
        if resp_oficial.status_code == 200:
            ultimo = _extrair_resultado_api(resp_oficial.json())
            if ultimo and ultimo.get('numero'):
                max_local = int(df['concurso'].max())
                novos = []
                for concurso in range(max_local + 1, int(ultimo['numero']) + 1):
                    resp_concurso = requests.get(f"{url_oficial}/{concurso}", timeout=10)
                    if resp_concurso.status_code != 200:
                        continue
                    resultado = _extrair_resultado_api(resp_concurso.json(), concurso)
                    if not resultado:
                        continue
                    row = {
                        'concurso': int(concurso),
                        'data': resultado.get('data') or '',
                        'dezenas': ','.join(f"{n:02d}" for n in resultado['dezenas']),
                    }
                    for i, dez in enumerate(resultado['dezenas'], 1):
                        row[f'dez{i}'] = int(dez)
                    novos.append(row)

                if novos:
                    df = pd.concat([pd.DataFrame(novos), df], ignore_index=True)
                    st.success(f"{len(novos)} concurso(s) atualizado(s) da API oficial.")
    except Exception as e:
        st.warning(f"API da Caixa indisponível ({e}). Usando apenas histórico local.")

    return df.sort_values('concurso', ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# CARTÕES — INTERFACE PÚBLICA (compatibilidade com código existente)
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_cartao(cartao: dict, concurso_alvo: int = None) -> dict:
    """Normaliza tipos numpy/pandas e preenche campos opcionais."""
    c = {}
    for key, value in cartao.items():
        if hasattr(value, 'item'):
            c[key] = value.item()
        elif isinstance(value, list):
            c[key] = [int(x) if hasattr(x, 'item') else x for x in value]
        else:
            c[key] = value

    if concurso_alvo and (not c.get('concurso_alvo')):
        c['concurso_alvo'] = int(concurso_alvo)
        c['status'] = 'aguardando'

    if not c.get('data_criacao'):
        c['data_criacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return c


def salvar_cartoes(cartoes: list, concurso_alvo: int = None) -> bool:
    """Persiste cartões no SQLite e espelha no JSON para persistência entre deploys."""
    normalizados = [_normalizar_cartao(c, concurso_alvo) for c in cartoes]
    ok = salvar_cartoes_db(normalizados)
    if not ok:
        st.error("Erro ao salvar cartões no banco de dados.")
    else:
        try:
            _escrever_json(_JSON_CARTOES, normalizados)
        except Exception:
            pass
    return ok


def carregar_cartoes_salvos() -> list:
    """Carrega cartões do SQLite; se vazio, importa do JSON automaticamente."""
    try:
        dados = carregar_cartoes_db()
        if not dados:
            sincronizar_json_para_db()
            dados = carregar_cartoes_db()
        return dados
    except Exception as e:
        st.warning(f"Erro ao carregar cartões: {e}")
        return _ler_json(_JSON_CARTOES, [])


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAÇÃO DE RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────

def verificar_acertos(dezenas_cartao: list, dezenas_resultado: list) -> int:
    return len(set(dezenas_cartao) & set(dezenas_resultado))


def _normalizar_dezenas_resultado(dezenas_raw):
    """Converte e valida dezenas retornadas pelas APIs."""
    from helpers import converter_dezenas_para_int

    dezenas = converter_dezenas_para_int(dezenas_raw)
    if len(dezenas) != 6:
        return None
    if len(set(dezenas)) != 6:
        return None
    if any(n < 1 or n > 60 for n in dezenas):
        return None
    return sorted(dezenas)


def _extrair_resultado_api(data, numero_concurso: int = None):
    """Extrai resultado de payloads da API oficial da Caixa."""
    if isinstance(data, list):
        if numero_concurso is not None:
            for item in data:
                resultado = _extrair_resultado_api(item, numero_concurso)
                if resultado:
                    return resultado
            return None
        if not data:
            return None
        data = data[0]

    if not isinstance(data, dict):
        return None

    numero = data.get('numero') or data.get('concurso')
    try:
        numero_int = int(numero) if numero is not None else None
    except (TypeError, ValueError):
        numero_int = None

    if numero_concurso is not None and numero_int is not None and numero_int != int(numero_concurso):
        return None

    dezenas_raw = (
        data.get('listaDezenas')
        or data.get('dezenas')
        or data.get('dezenasSorteadasOrdemSorteio')
    )
    dezenas = _normalizar_dezenas_resultado(dezenas_raw)

    if not dezenas:
        campos_dezenas = [data.get(f'dez{i}') for i in range(1, 7)]
        if all(x is not None for x in campos_dezenas):
            dezenas = _normalizar_dezenas_resultado(campos_dezenas)

    if not dezenas:
        return None

    return {
        'numero': numero_int,
        'dezenas': dezenas,
        'data': data.get('dataApuracao') or data.get('data'),
        'numero_proximo': data.get('numeroConcursoProximo'),
        'data_proximo': data.get('dataProximoConcurso'),
        'acumulou': data.get('acumulou') if 'acumulou' in data else data.get('acumulado'),
        'valor_proximo': (
            data.get('valorEstimadoProximoConcurso')
            or data.get('valorAcumuladoProximoConcurso')
        ),
    }


@st.cache_data(ttl=300)
def buscar_resultado_concurso(numero_concurso: int):
    """Busca dezenas de um concurso específico na API oficial da Caixa."""
    apis = [
        f"https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/{numero_concurso}",
    ]
    for url in apis:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                continue
            resultado = _extrair_resultado_api(response.json(), numero_concurso)
            if resultado:
                return resultado['dezenas']
        except Exception:
            continue
    return None


@st.cache_data(ttl=300)
def buscar_ultimo_resultado_oficial() -> dict:
    """Busca resumo do último concurso publicado pela API oficial da Caixa."""
    apis = [
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
    ]
    for url in apis:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                continue
            resultado = _extrair_resultado_api(response.json())
            if resultado:
                return resultado
        except Exception:
            continue
    return {}


def limpar_cache_resultados():
    """Limpa caches de busca de resultados quando a API atualizar."""
    try:
        buscar_resultado_concurso.clear()
        buscar_ultimo_resultado_oficial.clear()
    except Exception:
        pass


@st.cache_data(ttl=300)
def buscar_detalhes_concurso(numero_concurso: int) -> dict:
    """Retorna {'acumulou': bool|None, 'valor_proximo_concurso': float|None}."""
    detalhes = {'acumulou': None, 'valor_proximo_concurso': None}
    try:
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/{numero_concurso}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return detalhes

        data = response.json()
        detalhes['acumulou'] = data.get('acumulou')

        valor_txt = data.get('valorEstimadoProximoConcurso') or data.get('valorAcumuladoProximoConcurso')
        if isinstance(valor_txt, (int, float)):
            detalhes['valor_proximo_concurso'] = float(valor_txt)
        elif isinstance(valor_txt, str):
            somente_numeros = re.sub(r"[^\d,.-]", "", valor_txt).replace(".", "").replace(",", ".")
            try:
                detalhes['valor_proximo_concurso'] = float(somente_numeros)
            except ValueError:
                pass
    except Exception:
        pass
    return detalhes


def verificar_resultados_automatico(cartoes: list, df: pd.DataFrame) -> list:
    """
    Verifica cartões não verificados, atualiza no banco e retorna lista de resultados.
    """
    resultados = []
    cartoes_atualizados = []

    for cartao in cartoes:
        if cartao.get('vai_jogar', False) and not cartao.get('verificado', False):
            concurso_alvo = cartao.get('concurso_alvo', 0)
            resultado = buscar_resultado_concurso(concurso_alvo)

            if resultado:
                acertos = verificar_acertos(cartao['dezenas'], resultado)
                cartao['verificado'] = True
                cartao['resultado_concurso'] = resultado
                cartao['acertos'] = acertos
                cartao['data_verificacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cartoes_atualizados.append(cartao)
                resultados.append({'cartao': cartao, 'acertos': acertos, 'resultado': resultado})

    if cartoes_atualizados:
        salvar_cartoes_db(cartoes_atualizados)

    return resultados


# ─────────────────────────────────────────────────────────────────────────────
# HISTÓRICO DE ANÁLISES
# ─────────────────────────────────────────────────────────────────────────────

def carregar_historico_analises() -> list:
    """Retorna histórico do SQLite; se vazio, importa do JSON automaticamente."""
    try:
        dados = carregar_historico_db()
        if not dados:
            sincronizar_json_para_db()
            dados = carregar_historico_db()
        return dados
    except Exception as e:
        st.warning(f'Erro ao carregar histórico: {e}')
        return _ler_json(_JSON_HISTORICO, [])


def salvar_historico_analise(concurso: int, data_analise: str,
                              estatisticas: dict, dezenas_sorteadas: list = None) -> bool:
    """Salva/atualiza análise no banco e espelha no JSON."""
    ok = salvar_historico_db(concurso, data_analise, estatisticas, dezenas_sorteadas)
    if not ok:
        st.error('Erro ao salvar histórico no banco de dados.')
    else:
        try:
            historico = carregar_historico_db()
            _escrever_json(_JSON_HISTORICO, historico)
        except Exception:
            pass
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# ARQUIVAMENTO (mantido para compatibilidade — agora é no-op via banco)
# ─────────────────────────────────────────────────────────────────────────────

def arquivar_cartoes_verificados() -> tuple:
    """
    Arquiva cartões verificados:
    1. No SQLite: já ficam com status='verificado' no banco
    2. No JSON (meus_cartoes.json): move verificados para data/cartoes_arquivo_YYYY.json
       e mantém apenas pendentes no arquivo principal
    Retorna (arquivados, pendentes).
    """
    import json as _json

    json_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "meus_cartoes.json")
    if not os.path.exists(json_file):
        try:
            s = stats_cartoes_db()
            return s.get('verificados', 0), s.get('pendentes', 0)
        except Exception:
            return 0, 0

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            todos = _json.load(f)

        verificados = [c for c in todos if c.get('verificado', False)]
        pendentes = [c for c in todos if not c.get('verificado', False)]

        if not verificados:
            return 0, len(pendentes)

        # Salvar verificados em arquivo de arquivo por ano
        ano = datetime.now().strftime('%Y')
        data_dir = os.path.join(os.path.dirname(json_file), "data")
        os.makedirs(data_dir, exist_ok=True)
        arquivo_destino = os.path.join(data_dir, f"cartoes_arquivo_{ano}.json")

        existentes = []
        if os.path.exists(arquivo_destino):
            with open(arquivo_destino, 'r', encoding='utf-8') as f:
                existentes = _json.load(f)

        existentes.extend(verificados)
        with open(arquivo_destino, 'w', encoding='utf-8') as f:
            _json.dump(existentes, f, indent=2, ensure_ascii=False)

        # Manter apenas pendentes no arquivo principal
        with open(json_file, 'w', encoding='utf-8') as f:
            _json.dump(pendentes, f, indent=2, ensure_ascii=False)

        return len(verificados), len(pendentes)

    except Exception:
        try:
            s = stats_cartoes_db()
            return s.get('verificados', 0), s.get('pendentes', 0)
        except Exception:
            return 0, 0


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────────────────────────

def limpar_cache():
    """Limpa o cache do Streamlit."""
    st.cache_data.clear()
