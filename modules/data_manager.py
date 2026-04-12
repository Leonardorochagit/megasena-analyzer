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
# SORTEIOS — API DA CAIXA (sem alteração)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def carregar_dados():
    """
    Carrega dados da API da Mega Sena.
    Returns:
        pd.DataFrame: DataFrame com histórico de sorteios
    """
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        response = requests.get(url, timeout=30)
        data = response.json()

        if isinstance(data, dict):
            data = [data]
        df = pd.DataFrame(data)

        df['dezenas'] = df['dezenas'].apply(lambda x: str(x))
        div = df['dezenas'].str.split(',')

        for i in range(6):
            col_name = f'dez{i+1}'
            df[col_name] = div.str.get(i).apply(
                lambda x: x.replace("['", '').replace(
                    "'", '').replace("]", '').strip() if x else x
            )

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
                st.success(f"Concurso {concurso_num} atualizado da API oficial!")
        except Exception:
            pass

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


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
    """
    Persiste lista de cartões no banco SQLite.
    Assinatura idêntica à versão JSON para compatibilidade.
    """
    normalizados = [_normalizar_cartao(c, concurso_alvo) for c in cartoes]
    ok = salvar_cartoes_db(normalizados)
    if not ok:
        st.error("Erro ao salvar cartões no banco de dados.")
    return ok


def carregar_cartoes_salvos() -> list:
    """
    Carrega todos os cartões do banco.
    Retorna lista de dicts no formato legado.
    """
    try:
        return carregar_cartoes_db()
    except Exception as e:
        st.warning(f"Erro ao carregar cartões: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAÇÃO DE RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────

def verificar_acertos(dezenas_cartao: list, dezenas_resultado: list) -> int:
    return len(set(dezenas_cartao) & set(dezenas_resultado))


def buscar_resultado_concurso(numero_concurso: int):
    """Busca dezenas de um concurso específico na API."""
    try:
        url = f"https://loteriascaixa-api.herokuapp.com/api/megasena/{numero_concurso}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'dezenas' in data:
                from helpers import converter_dezenas_para_int
                dezenas = converter_dezenas_para_int(data['dezenas'])
                return sorted(dezenas)
        return None
    except Exception:
        return None


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
    """Retorna histórico no formato legado [{concurso, estatisticas, ...}]."""
    try:
        return carregar_historico_db()
    except Exception as e:
        st.warning(f'Erro ao carregar histórico: {e}')
        return []


def salvar_historico_analise(concurso: int, data_analise: str,
                              estatisticas: dict, dezenas_sorteadas: list = None) -> bool:
    """Salva/atualiza resultado de análise no banco."""
    ok = salvar_historico_db(concurso, data_analise, estatisticas, dezenas_sorteadas)
    if not ok:
        st.error('Erro ao salvar histórico no banco de dados.')
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# ARQUIVAMENTO (mantido para compatibilidade — agora é no-op via banco)
# ─────────────────────────────────────────────────────────────────────────────

def arquivar_cartoes_verificados() -> tuple:
    """
    No SQLite os cartões verificados já estão no banco com status='verificado'.
    Função mantida para compatibilidade — retorna contagens do banco.
    """
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
