"""Salvar os 2 cartões do bolão Copilot no sistema"""
import json
from datetime import datetime

# Carregar cartões existentes
with open('meus_cartoes.json', 'r', encoding='utf-8') as f:
    cartoes = json.load(f)

print(f'Cartões existentes: {len(cartoes)}')

concurso_alvo = 2979
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

cartao1 = {
    'id': f'BOLAO-COPILOT-MISTO-{timestamp}-01',
    'dezenas': [7, 9, 14, 15, 21, 25, 29, 34, 36, 40, 45, 56, 58],
    'estrategia': 'Bolao-Copilot',
    'tecnica': 'misto',
    'vai_jogar': True,
    'verificado': False,
    'concurso_alvo': concurso_alvo,
    'status': 'aguardando',
    'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'qtd_numeros': 13,
    'observacao': 'Gerado pelo Copilot - Estrategia MISTO (1o no ranking, unica com QUADRA)'
}

cartao2 = {
    'id': f'BOLAO-COPILOT-SMART-{timestamp}-02',
    'dezenas': [1, 10, 13, 18, 20, 30, 33, 37, 38, 39, 44, 46, 56],
    'estrategia': 'Bolao-Copilot',
    'tecnica': 'aleatorio_smart',
    'vai_jogar': True,
    'verificado': False,
    'concurso_alvo': concurso_alvo,
    'status': 'aguardando',
    'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'qtd_numeros': 13,
    'observacao': 'Gerado pelo Copilot - Estrategia ALEATORIO INTELIGENTE (3o no ranking)'
}

cartoes.append(cartao1)
cartoes.append(cartao2)

with open('meus_cartoes.json', 'w', encoding='utf-8') as f:
    json.dump(cartoes, f, indent=2, ensure_ascii=False)

print(f'Cartões após salvar: {len(cartoes)}')
print()
print('Cartão 1 salvo:')
print(f'  ID: {cartao1["id"]}')
print(f'  Estratégia: {cartao1["estrategia"]} ({cartao1["tecnica"]})')
nums1 = ' - '.join([f'{n:02d}' for n in cartao1['dezenas']])
print(f'  Dezenas: {nums1}')
print(f'  Concurso alvo: {cartao1["concurso_alvo"]}')
print()
print('Cartão 2 salvo:')
print(f'  ID: {cartao2["id"]}')
print(f'  Estratégia: {cartao2["estrategia"]} ({cartao2["tecnica"]})')
nums2 = ' - '.join([f'{n:02d}' for n in cartao2['dezenas']])
print(f'  Dezenas: {nums2}')
print(f'  Concurso alvo: {cartao2["concurso_alvo"]}')
print()
print('OK! Cartões salvos com tag "Bolao-Copilot" para fácil identificação.')
