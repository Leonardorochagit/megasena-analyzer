"""Script temporário para gerar 2 cartões de 13 números para bolão"""
import pandas as pd
import random
import json
from modules import statistics as stats
from modules import game_generator as gen

# Carregar dados
with open('data/historico_megasena.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)
df = pd.DataFrame(dados)

# Processar dezenas do formato API para colunas dez1..dez6
for i in range(6):
    df[f'dez{i+1}'] = df['dezenas'].apply(lambda x: int(x[i]) if isinstance(x, list) and len(x) > i else 0)

# Ordenar por concurso decrescente (mais recente primeiro)
df = df.sort_values('concurso', ascending=False).reset_index(drop=True)

print(f'Dados carregados: {len(df)} concursos (último: {df["concurso"].iloc[0]})')

# Estatísticas
contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df, ultimos=50)

print('='*60)
print('  SUGESTÃO DE 2 CARTÕES DE 13 NÚMEROS PARA BOLÃO')
print('  Concurso: 2979')
print('='*60)

# ---- CARTÃO 1: MISTO (Score 11.13, melhor=4, única com QUADRA) ----
print()
print('CARTÃO 1 - Estratégia: MISTO (1º lugar no ranking)')
print('  Única estratégia que já acertou QUADRA')
print('  Média histórica: 1.13 acertos/jogo')
print('-'*60)

random.seed(42)
best_misto = None
best_score = -1

for tentativa in range(200):
    dezenas_base = gen.gerar_jogo('misto', contagem_total, contagem_recente, df_atrasos)
    atrasados_pool = contagem_total.sort_values().head(30).index.tolist()
    quentes_pool = contagem_recente.nlargest(30).index.tolist()
    
    candidatos = list(set(atrasados_pool + quentes_pool))
    candidatos = [n for n in candidatos if n not in dezenas_base]
    random.shuffle(candidatos)
    extras = candidatos[:7]
    jogo = sorted(dezenas_base + extras)
    
    if len(jogo) == 13:
        pares = sum(1 for n in jogo if n % 2 == 0)
        soma = sum(jogo)
        score = 0
        if 5 <= pares <= 8:
            score += 10
        if 350 <= soma <= 450:
            score += 10
        faixas = [0]*6
        for n in jogo:
            faixas[(n-1)//10] += 1
        cobertura = sum(1 for f in faixas if f > 0)
        score += cobertura * 3
        
        if score > best_score:
            best_score = score
            best_misto = jogo

print(f'  Números: {" - ".join([f"{n:02d}" for n in best_misto])}')
soma1 = sum(best_misto)
pares1 = sum(1 for n in best_misto if n % 2 == 0)
print(f'  Soma: {soma1} | Pares: {pares1} | Ímpares: {13-pares1}')
faixas1 = {}
for n in best_misto:
    faixa = f'{((n-1)//10)*10+1}-{((n-1)//10)*10+10}'
    faixas1[faixa] = faixas1.get(faixa, 0) + 1
print(f'  Distribuição: {faixas1}')

# ---- CARTÃO 2: ALEATÓRIO INTELIGENTE (3º lugar, média 1.02, melhor=3) ----
print()
print('CARTÃO 2 - Estratégia: ALEATÓRIO INTELIGENTE (3º lugar no ranking)')
print('  Filtros: equilíbrio par/ímpar + soma controlada')
print('  Média histórica: 1.02 acertos/jogo')
print('-'*60)

best_smart = None
best_score2 = -1

for tentativa in range(500):
    jogo = sorted(random.sample(range(1, 61), 13))
    pares = sum(1 for n in jogo if n % 2 == 0)
    soma = sum(jogo)
    
    if not (5 <= pares <= 8):
        continue
    if not (320 <= soma <= 480):
        continue
    
    faixas = [0]*6
    for n in jogo:
        faixas[(n-1)//10] += 1
    cobertura = sum(1 for f in faixas if f > 0)
    if cobertura < 5:
        continue
    
    quentes_top = set(contagem_recente.nlargest(15).index.tolist())
    quentes_no_jogo = len(set(jogo) & quentes_top)
    
    score = cobertura * 3 + quentes_no_jogo * 2
    if 370 <= soma <= 430:
        score += 5
    
    if score > best_score2:
        best_score2 = score
        best_smart = jogo

print(f'  Números: {" - ".join([f"{n:02d}" for n in best_smart])}')
soma2 = sum(best_smart)
pares2 = sum(1 for n in best_smart if n % 2 == 0)
print(f'  Soma: {soma2} | Pares: {pares2} | Ímpares: {13-pares2}')
faixas2 = {}
for n in best_smart:
    faixa = f'{((n-1)//10)*10+1}-{((n-1)//10)*10+10}'
    faixas2[faixa] = faixas2.get(faixa, 0) + 1
print(f'  Distribuição: {faixas2}')

# Sobreposição
comuns = set(best_misto) & set(best_smart)
print()
print('='*60)
print(f'  Números em comum entre os 2 cartões: {len(comuns)}')
if comuns:
    print(f'  Comuns: {" - ".join([f"{n:02d}" for n in sorted(comuns)])}')
print(f'  Cobertura total: {len(set(best_misto) | set(best_smart))} números distintos de 60')
print(f'  Custo total: 2 x R$ 10.296,00 = R$ 20.592,00')
print(f'  Combinações totais: 2 x 1.716 = 3.432 jogos de 6')
print('='*60)
