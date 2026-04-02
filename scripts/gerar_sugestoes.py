import random
import numpy as np

# Clusters de Co-ocorrência
CLUSTERS = {
    0: [13, 24, 27, 28, 33, 34, 37, 44, 52, 53],
    1: [1, 2, 8, 10, 11, 16, 17, 25, 29, 31, 35, 54, 60],
    2: [3, 6, 7, 9, 12, 14, 15, 18, 20, 21, 22, 23, 26, 39, 40, 48, 55, 58, 59],
    3: [4, 5, 19, 30, 32, 36, 38, 41, 42, 43, 45, 46, 47, 49, 50, 51, 56, 57]
}

# Limites Estatísticos para 10 dezenas (Ajustados proporcionalmente)
# Média de 6 dezenas = 183. Para 10 dezenas = 183 * (10/6) = 305
SOMA_MIN = 240
SOMA_MAX = 370
AMPLITUDE_MIN = 45 # Para 10 dezenas, a amplitude deve ser maior
AMPLITUDE_MAX = 59

def jogo_passa_nos_filtros(jogo: list[int]) -> bool:
    soma = sum(jogo)
    amplitude = max(jogo) - min(jogo)
    
    if not (SOMA_MIN <= soma <= SOMA_MAX): return False
    if not (AMPLITUDE_MIN <= amplitude <= AMPLITUDE_MAX): return False
        
    saltos = np.diff(jogo)
    if (saltos == 1).sum() > 3: # Máximo de 3 números consecutivos para 10 dezenas
        return False
        
    return True

def gerar_jogo_10_dezenas(ultimo_sorteio):
    while True:
        jogo = []
        
        # 1. Balanceamento de Clusters (2 de cada cluster = 8 dezenas)
        for c_id, dezenas in CLUSTERS.items():
            jogo.extend(random.sample(dezenas, 2))
            
        # 2. Vizinhança (1 ou 2 vizinhos do último sorteio)
        vizinhos_possiveis = set()
        for n in ultimo_sorteio:
            if n > 1: vizinhos_possiveis.add(n - 1)
            if n < 60: vizinhos_possiveis.add(n + 1)
        vizinhos_possiveis = list(vizinhos_possiveis - set(ultimo_sorteio) - set(jogo))
        
        if vizinhos_possiveis:
            qtd_vizinhos = min(random.choice([1, 2]), len(vizinhos_possiveis))
            jogo.extend(random.sample(vizinhos_possiveis, qtd_vizinhos))
            
        # 3. Completar até 10 dezenas
        dezenas_restantes = list(set(range(1, 61)) - set(jogo))
        if len(jogo) < 10:
            jogo.extend(random.sample(dezenas_restantes, 10 - len(jogo)))
        elif len(jogo) > 10:
            jogo = random.sample(jogo, 10) # Cortar se passou
            
        jogo = sorted(jogo)
        
        # 4. Aplicar Filtros Estatísticos
        if jogo_passa_nos_filtros(jogo):
            return jogo

ultimo = [3, 10, 12, 19, 37, 40] # Concurso 2974
print("SUGESTÕES DE CARTÕES DE 10 DEZENAS (Baseado no Concurso 2974)")
print("-" * 60)
for i in range(5):
    jogo = gerar_jogo_10_dezenas(ultimo)
    print(f"Cartão {i+1}: {jogo} (Soma: {sum(jogo)})")
