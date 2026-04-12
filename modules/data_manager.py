"""
================================================================================
📊 MÓDULO DE GERENCIAMENTO DE DADOS
================================================================================
Gerencia carregamento, salvamento e verificação de dados e cartões
"""

import json
import os
import requests
import pandas as pd
import re
import shutil
from datetime import datetime

try:
    import streamlit as st
except ModuleNotFoundError:
    class _CacheDataFallback:
        """Fallback simples para uso em scripts CLI sem Streamlit instalado."""

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

ARQUIVO_CARTOES = "meus_cartoes.json"
ARQUIVO_HISTORICO = "historico_analises.json"


@st.cache_data(ttl=600)  # Cache por 10 minutos
def carregar_dados():
    """
    Carrega dados da API da Mega Sena (tenta API oficial primeiro)

    Returns:
        pd.DataFrame: DataFrame com histórico de sorteios
    """
    # Tentar API alternativa que tem histórico completo
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
                lambda x: x.replace("['", '').replace(
                    "'", '').replace("]", '').strip() if x else x
            )

        # Buscar último concurso da API oficial para atualizar
        try:
            url_oficial = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
            resp_oficial = requests.get(url_oficial, timeout=10)
            concurso_oficial = resp_oficial.json()

            concurso_num = concurso_oficial.get('numero', 0)

            # Se o concurso oficial é mais novo que o último da API alternativa
            if concurso_num > df['concurso'].max():
                novo_row = {
                    'concurso': concurso_num,
                    'data': concurso_oficial.get('dataApuracao', ''),
                    'dezenas': ','.join(concurso_oficial.get('listaDezenas', []))
                }
                for i, dez in enumerate(concurso_oficial.get('listaDezenas', []), 1):
                    novo_row[f'dez{i}'] = str(dez)

                # Adicionar no topo do DataFrame
                df = pd.concat([pd.DataFrame([novo_row]), df],
                               ignore_index=True)
                st.success(
                    f"✨ Concurso {concurso_num} atualizado da API oficial!")
        except:
            pass  # Se falhar, continua com dados da API alternativa

        return df

    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None


def salvar_cartoes(cartoes, concurso_alvo=None):
    """
    Salva cartões em arquivo JSON com informação do concurso

    Args:
        cartoes (list): Lista de cartões para salvar
        concurso_alvo(int, optional): Número do concurso alvo

    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Converter todos os valores para tipos nativos do Python
        cartoes_convertidos = []
        for cartao in cartoes:
            cartao_limpo = {}
            for key, value in cartao.items():
                # Converter numpy/pandas int64 para int nativo
                if hasattr(value, 'item'):  # numpy/pandas types
                    cartao_limpo[key] = value.item()
                elif isinstance(value, list):
                    # Converter lista de int64 para lista de int
                    cartao_limpo[key] = [int(x) if hasattr(
                        x, 'item') else x for x in value]
                else:
                    cartao_limpo[key] = value

            # Adicionar concurso_alvo se fornecido
            if concurso_alvo:
                if 'concurso_alvo' not in cartao_limpo or cartao_limpo['concurso_alvo'] is None:
                    cartao_limpo['concurso_alvo'] = int(concurso_alvo)
                    cartao_limpo['status'] = 'aguardando'

            cartoes_convertidos.append(cartao_limpo)

        with open(ARQUIVO_CARTOES, 'w', encoding='utf-8') as f:
            json.dump(cartoes_convertidos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar cartões: {e}")
        return False


def carregar_cartoes_salvos():
    """
    Carrega cartões salvos do arquivo

    Returns:
        list: Lista de cartões salvos
    """
    try:
        if os.path.exists(ARQUIVO_CARTOES):
            with open(ARQUIVO_CARTOES, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            # Converter formato se necessário (lista simples -> dicionário)
            cartoes_formatados = []
            for i, cartao in enumerate(dados, 1):
                if isinstance(cartao, list):
                    # Cartão no formato antigo (apenas lista de números)
                    cartoes_formatados.append({
                        'id': f'CART-{i}',
                        'dezenas': cartao,
                        'estrategia': 'Importado',
                        'vai_jogar': False,
                        'verificado': False,
                        'concurso_alvo': None,
                        'status': 'não_marcado'
                    })
                else:
                    # Garantir que concurso_alvo nunca seja string vazia ou inválido
                    ca = cartao.get('concurso_alvo')
                    if ca is not None:
                        try:
                            cartao['concurso_alvo'] = int(ca)
                        except (TypeError, ValueError):
                            cartao['concurso_alvo'] = None
                    # Cartão já está no formato de dicionário
                    cartoes_formatados.append(cartao)

            return cartoes_formatados
        return []
    except Exception as e:
        st.warning(f"Erro ao carregar cartões salvos: {e}")
        return []


def verificar_acertos(dezenas_cartao, dezenas_resultado):
    """
    Verifica quantos números acertou

    Args:
        dezenas_cartao(list): Dezenas do cartão
        dezenas_resultado(list): Dezenas do resultado

    Returns:
        int: Quantidade de acertos
    """
    acertos = len(set(dezenas_cartao) & set(dezenas_resultado))
    return acertos


def buscar_resultado_concurso(numero_concurso):
    """
    Busca resultado de um concurso específico na API

    Args:
        numero_concurso(int): Número do concurso

    Returns:
        list or None: Lista de dezenas sorteadas ou None se não encontrou
    """
    try:
        url = f"https://loteriascaixa-api.herokuapp.com/api/megasena/{numero_concurso}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Extrair dezenas
            if 'dezenas' in data:
                from helpers import converter_dezenas_para_int
                dezenas = converter_dezenas_para_int(data['dezenas'])
                return sorted(dezenas)
        return None
    except Exception as e:
        return None


def buscar_detalhes_concurso(numero_concurso):
    """
    Busca metadados do concurso para notificações (acumulou e próximo prêmio).

    Args:
        numero_concurso (int): Número do concurso

    Returns:
        dict: {'acumulou': bool|None, 'valor_proximo_concurso': float|None}
    """
    detalhes = {
        'acumulou': None,
        'valor_proximo_concurso': None
    }

    try:
        url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/{numero_concurso}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return detalhes

        data = response.json()
        detalhes['acumulou'] = data.get('acumulou')

        valor_txt = data.get('valorEstimadoProximoConcurso')
        if valor_txt is None:
            valor_txt = data.get('valorAcumuladoProximoConcurso')

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


def verificar_resultados_automatico(cartoes, df):
    """
    Verifica automaticamente os resultados dos cartões jogados

    Args:
        cartoes(list): Lista de cartões
        df(pd.DataFrame): DataFrame com histórico de sorteios

    Returns:
        list: Lista de resultados verificados
    """
    resultados = []

    for cartao in cartoes:
        if cartao.get('vai_jogar', False) and not cartao.get('verificado', False):
            concurso_alvo = cartao.get('concurso_alvo', 0)

            # Buscar resultado
            resultado = buscar_resultado_concurso(concurso_alvo)

            if resultado:
                acertos = verificar_acertos(cartao['dezenas'], resultado)

                # Atualizar cartão com resultado
                cartao['verificado'] = True
                cartao['resultado_concurso'] = resultado
                cartao['acertos'] = acertos
                cartao['data_verificacao'] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")

                resultados.append({
                    'cartao': cartao,
                    'acertos': acertos,
                    'resultado': resultado
                })

    return resultados


def limpar_cache():
    """Limpa o cache do Streamlit"""
    st.cache_data.clear()

def carregar_historico_analises():
    """
    Carrega o histórico de análises e resultados
    """
    try:
        if os.path.exists(ARQUIVO_HISTORICO):
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.warning(f'Erro ao carregar histórico: {e}')
        return []


def salvar_historico_analise(concurso, data_analise, estatisticas, dezenas_sorteadas=None):
    """
    Salva/Atualiza o resultado de uma análise no histórico
    """
    historico = carregar_historico_analises()
    
    # Verificar se já existe registro para este concurso
    registro_existente = next((item for item in historico if item['concurso'] == concurso), None)
    
    novo_registro = {
        'concurso': concurso,
        'data_analise': data_analise,
        'dezenas_sorteadas': dezenas_sorteadas,
        'estatisticas': estatisticas,
        'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if registro_existente:
        # Atualizar registro existente
        historico = [novo_registro if item['concurso'] == concurso else item for item in historico]
    else:
        # Adicionar novo registro
        historico.append(novo_registro)
        
    try:
        with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f'Erro ao salvar histórico: {e}')
        return False


def arquivar_cartoes_verificados():
    """
    Move cartões verificados para arquivo anual em data/, mantendo apenas
    cartões pendentes/não-verificados em meus_cartoes.json.

    Returns:
        tuple: (int: arquivados, int: mantidos)
    """
    cartoes = carregar_cartoes_salvos()
    if not cartoes:
        return 0, 0

    verificados = [c for c in cartoes if c.get('verificado', False)]
    pendentes = [c for c in cartoes if not c.get('verificado', False)]

    if not verificados:
        return 0, len(pendentes)

    # Agrupar por ano do concurso/verificação
    por_ano = {}
    for c in verificados:
        data_verif = c.get('data_verificacao', '')
        try:
            ano = datetime.strptime(data_verif, "%Y-%m-%d %H:%M:%S").year
        except (ValueError, TypeError):
            ano = datetime.now().year
        por_ano.setdefault(ano, []).append(c)

    os.makedirs("data", exist_ok=True)

    for ano, grupo in por_ano.items():
        arquivo_ano = os.path.join("data", f"cartoes_arquivo_{ano}.json")
        existentes = []
        if os.path.exists(arquivo_ano):
            try:
                with open(arquivo_ano, 'r', encoding='utf-8') as f:
                    existentes = json.load(f)
            except (json.JSONDecodeError, Exception):
                # Backup do arquivo corrompido
                shutil.copy2(arquivo_ano, arquivo_ano + ".bak")
                existentes = []

        # Evitar duplicatas por ID
        ids_existentes = {c.get('id') for c in existentes}
        novos = [c for c in grupo if c.get('id') not in ids_existentes]
        existentes.extend(novos)

        with open(arquivo_ano, 'w', encoding='utf-8') as f:
            json.dump(existentes, f, indent=2, ensure_ascii=False)

    # Manter apenas pendentes no arquivo principal
    salvar_cartoes(pendentes)

    return len(verificados), len(pendentes)

