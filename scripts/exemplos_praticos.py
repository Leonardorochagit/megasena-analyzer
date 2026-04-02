"""
================================================================================
🎯 EXEMPLOS PRÁTICOS: COMO USAR OS RESULTADOS DA ANÁLISE
================================================================================
Este script demonstra como usar os padrões descobertos (Clusters, Saltos, Soma)
para gerar e filtrar jogos da Mega-Sena de forma mais inteligente.
"""

import random
import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# 1. DADOS DESCOBERTOS NA ANÁLISE
# ──────────────────────────────────────────────────────────────────────────────

# Clusters de Co-ocorrência (Dezenas que costumam sair juntas)
CLUSTERS = {
    0: [13, 24, 27, 28, 33, 34, 37, 44, 52, 53],
    1: [1, 2, 8, 10, 11, 16, 17, 25, 29, 31, 35, 54, 60],
    2: [3, 6, 7, 9, 12, 14, 15, 18, 20, 21, 22, 23, 26, 39, 40, 48, 55, 58, 59],
    3: [4, 5, 19, 30, 32, 36, 38, 41, 42, 43, 45, 46, 47, 49, 50, 51, 56, 57]
}

# Limites Estatísticos (Baseados na média e desvio padrão)
SOMA_MIN = 143  # Média (183) - 1 DP (40)
SOMA_MAX = 223  # Média (183) + 1 DP (40)
AMPLITUDE_MIN = 30 # Evitar jogos muito "espremidos" (ex: 1,2,3,4,5,6)
AMPLITUDE_MAX = 58 # Evitar jogos que pegam só os extremos absolutos


# ──────────────────────────────────────────────────────────────────────────────
# ESTRATÉGIA 1: GERAÇÃO BALANCEADA POR CLUSTERS
# ──────────────────────────────────────────────────────────────────────────────
def gerar_jogo_balanceado_clusters():
    """
    Gera um jogo garantindo que as dezenas venham de clusters diferentes.
    Como temos 4 clusters e 6 dezenas, pegamos pelo menos 1 de cada cluster,
    e as 2 restantes de clusters aleatórios.
    """
    jogo = []
    
    # 1. Garantir pelo menos 1 dezena de cada cluster
    for c_id, dezenas in CLUSTERS.items():
        escolha = random.choice(dezenas)
        jogo.append(escolha)
        
    # 2. Escolher mais 2 dezenas de clusters aleatórios (sem repetir dezenas)
    todas_dezenas = [d for dezenas in CLUSTERS.values() for d in dezenas]
    dezenas_disponiveis = list(set(todas_dezenas) - set(jogo))
    
    jogo.extend(random.sample(dezenas_disponiveis, 2))
    
    return sorted(jogo)


# ──────────────────────────────────────────────────────────────────────────────
# ESTRATÉGIA 2: FILTRO ESTATÍSTICO (SOMA E AMPLITUDE)
# ──────────────────────────────────────────────────────────────────────────────
def jogo_passa_nos_filtros(jogo: list[int]) -> bool:
    """
    Verifica se um jogo gerado aleatoriamente obedece aos padrões estatísticos
    descobertos na análise (Soma e Amplitude).
    """
    soma = sum(jogo)
    amplitude = max(jogo) - min(jogo)
    
    # Regra 1: A soma deve estar dentro de 1 Desvio Padrão da média (143 a 223)
    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
        
    # Regra 2: A amplitude (espalhamento) deve ser razoável (30 a 58)
    if not (AMPLITUDE_MIN <= amplitude <= AMPLITUDE_MAX):
        return False
        
    # Regra 3: Evitar sequências muito longas (ex: 10, 11, 12, 13)
    # A análise de saltos mostrou que o salto médio é ~10.
    saltos = np.diff(jogo)
    if (saltos == 1).sum() > 2: # Máximo de 2 números consecutivos permitidos
        return False
        
    return True


def gerar_jogo_com_filtros():
    """Gera jogos aleatórios até encontrar um que passe nos filtros estatísticos."""
    tentativas = 0
    while True:
        tentativas += 1
        jogo = sorted(random.sample(range(1, 61), 6))
        if jogo_passa_nos_filtros(jogo):
            return jogo, tentativas


# ──────────────────────────────────────────────────────────────────────────────
# ESTRATÉGIA 3: VIZINHANÇA DE SAÍDA (USANDO O ÚLTIMO SORTEIO)
# ──────────────────────────────────────────────────────────────────────────────
def gerar_jogo_baseado_em_vizinhanca(ultimo_sorteio: list[int]):
    """
    A análise mostrou que há ~19% de chance de um vizinho (N-1 ou N+1) do 
    último sorteio sair no próximo.
    Esta estratégia força a inclusão de 1 ou 2 vizinhos do último sorteio.
    """
    # 1. Calcular todos os vizinhos possíveis do último sorteio
    vizinhos_possiveis = set()
    for n in ultimo_sorteio:
        if n > 1: vizinhos_possiveis.add(n - 1)
        if n < 60: vizinhos_possiveis.add(n + 1)
        
    # Remover números que já saíram no último sorteio (pois repetições são raras)
    vizinhos_possiveis = list(vizinhos_possiveis - set(ultimo_sorteio))
    
    # 2. Escolher 1 ou 2 vizinhos
    qtd_vizinhos = random.choice([1, 2])
    jogo = random.sample(vizinhos_possiveis, min(qtd_vizinhos, len(vizinhos_possiveis)))
    
    # 3. Completar o jogo com números aleatórios (que não sejam do último sorteio)
    dezenas_restantes = list(set(range(1, 61)) - set(ultimo_sorteio) - set(jogo))
    jogo.extend(random.sample(dezenas_restantes, 6 - len(jogo)))
    
    return sorted(jogo)


# ──────────────────────────────────────────────────────────────────────────────
# DEMONSTRAÇÃO
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*60)
    print(" 🎲 EXEMPLOS PRÁTICOS DE USO DA ANÁLISE ESTATÍSTICA")
    print("="*60)
    
    print("\n1. ESTRATÉGIA DE CLUSTERS (Balanceamento de Co-ocorrência)")
    print("   Garante que o jogo tenha dezenas de diferentes 'famílias'.")
    for i in range(3):
        jogo = gerar_jogo_balanceado_clusters()
        print(f"   Jogo {i+1}: {jogo} (Soma: {sum(jogo)})")
        
    print("\n2. ESTRATÉGIA DE FILTROS (Soma, Amplitude e Saltos)")
    print(f"   Garante Soma entre {SOMA_MIN}-{SOMA_MAX} e Amplitude {AMPLITUDE_MIN}-{AMPLITUDE_MAX}.")
    for i in range(3):
        jogo, tentativas = gerar_jogo_com_filtros()
        print(f"   Jogo {i+1}: {jogo} (Encontrado em {tentativas} tentativas)")
        
    print("\n3. ESTRATÉGIA DE VIZINHANÇA (Baseado no último sorteio)")
    ultimo = [4, 6, 11, 38, 49, 54] # Exemplo: Concurso 2949
    print(f"   Último sorteio: {ultimo}")
    print("   Força a inclusão de 1 ou 2 vizinhos (N±1) do último sorteio.")
    for i in range(3):
        jogo = gerar_jogo_baseado_em_vizinhanca(ultimo)
        # Destacar os vizinhos escolhidos
        vizinhos_escolhidos = [n for n in jogo if (n-1 in ultimo or n+1 in ultimo)]
        print(f"   Jogo {i+1}: {jogo} -> Vizinhos incluídos: {vizinhos_escolhidos}")
    print("\n"+"="*60)
