"""
================================================================================
📊 MÓDULO DE GERENCIAMENTO DE DADOS
================================================================================
Gerencia carregamento, salvamento e verificação de dados e cartões
"""

import json
import os
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

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
                dezenas_str = data['dezenas']
                if isinstance(dezenas_str, str):
                    dezenas = [int(x.strip().replace("'", "").replace("[", "").replace("]", ""))
                               for x in dezenas_str.split(',')]
                elif isinstance(dezenas_str, list):
                    dezenas = [int(x) for x in dezenas_str]
                return sorted(dezenas)
        return None
    except Exception as e:
        return None


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

