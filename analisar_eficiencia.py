"""Análise: Eficiência de acertos vs quantidade de números por cartão"""
import json
from collections import defaultdict

with open('meus_cartoes.json', 'r', encoding='utf-8') as f:
    cartoes = json.load(f)

verificados = [c for c in cartoes if c.get('verificado') and c.get('acertos') is not None]
print(f'Total de cartões verificados: {len(verificados)}')

# Agrupar por estratégia + qtd_numeros
dados = defaultdict(lambda: {'jogos': 0, 'acertos': [], 'estrategia': '', 'qtd': 0})

for c in verificados:
    est = c.get('estrategia', 'N/A')
    qtd = c.get('qtd_numeros', len(c.get('dezenas', [])))
    acertos = c.get('acertos', 0)
    key = f'{est}|{qtd}'
    dados[key]['jogos'] += 1
    dados[key]['acertos'].append(acertos)
    dados[key]['estrategia'] = est
    dados[key]['qtd'] = qtd

print()
print('='*85)
print('  ANÁLISE: ACERTOS vs QUANTIDADE DE NÚMEROS POR CARTÃO')
print('  (Eficiência = média_acertos / qtd_números × 100)')
print('='*85)
print()

header = f"{'Estratégia':<25} {'Nums':>5} {'Jogos':>6} {'Média':>7} {'Melhor':>7} {'>=3':>4} {'>=4':>4} {'Efic%':>7}"
print(header)
print('-'*85)

resultados = []
for key, d in dados.items():
    media = sum(d['acertos']) / len(d['acertos'])
    melhor = max(d['acertos'])
    terno_plus = sum(1 for a in d['acertos'] if a >= 3)
    quadra_plus = sum(1 for a in d['acertos'] if a >= 4)
    eficiencia = media / d['qtd'] * 100
    resultados.append((d['estrategia'], d['qtd'], d['jogos'], media, melhor, terno_plus, quadra_plus, eficiencia))

resultados.sort(key=lambda x: x[7], reverse=True)

for est, qtd, jogos, media, melhor, t3, t4, ef in resultados:
    marca = ''
    if t4 > 0:
        marca = ' <<<< QUADRA!'
    elif t3 > 0:
        marca = ' << TERNO'
    print(f"{est:<25} {qtd:>5} {jogos:>6} {media:>7.2f} {melhor:>7} {t3:>4} {t4:>4} {ef:>7.2f}{marca}")

# Análise por tamanho de cartão (independente de estratégia)
print()
print('='*85)
print('  RESUMO POR TAMANHO DE CARTÃO (todas as estratégias)')
print('='*85)
print()

por_tamanho = defaultdict(lambda: {'jogos': 0, 'acertos': [], 'ternos': 0, 'quadras': 0})
for c in verificados:
    qtd = c.get('qtd_numeros', len(c.get('dezenas', [])))
    ac = c.get('acertos', 0)
    por_tamanho[qtd]['jogos'] += 1
    por_tamanho[qtd]['acertos'].append(ac)
    if ac >= 3:
        por_tamanho[qtd]['ternos'] += 1
    if ac >= 4:
        por_tamanho[qtd]['quadras'] += 1

print(f"{'Tamanho':>8} {'Jogos':>7} {'Média':>7} {'Melhor':>7} {'Ternos':>7} {'Quadras':>8} {'Efic%':>7} {'%Terno':>7}")
print('-'*70)

for qtd in sorted(por_tamanho.keys()):
    d = por_tamanho[qtd]
    media = sum(d['acertos']) / len(d['acertos'])
    melhor = max(d['acertos'])
    ef = media / qtd * 100
    pct_terno = d['ternos'] / d['jogos'] * 100 if d['jogos'] > 0 else 0
    print(f"{qtd:>8} {d['jogos']:>7} {media:>7.2f} {melhor:>7} {d['ternos']:>7} {d['quadras']:>8} {ef:>7.2f} {pct_terno:>6.1f}%")

# Detalhe dos ternos e quadras
print()
print('='*85)
print('  TODOS OS CARTÕES COM 3+ ACERTOS (detalhado)')
print('='*85)
print()

destaques = sorted(
    [c for c in verificados if c.get('acertos', 0) >= 3],
    key=lambda x: x.get('acertos', 0), reverse=True
)

if not destaques:
    print('  Nenhum cartão com 3+ acertos encontrado nos verificados.')
else:
    for c in destaques:
        est = c.get('estrategia', 'N/A')
        qtd = c.get('qtd_numeros', len(c.get('dezenas', [])))
        acertos = c.get('acertos', 0)
        concurso = c.get('concurso_alvo', '?')
        dezenas = ' - '.join([f'{n:02d}' for n in c.get('dezenas', [])])
        tipo = 'SENA' if acertos == 6 else 'QUINA' if acertos == 5 else 'QUADRA' if acertos == 4 else 'TERNO'
        print(f"  [{tipo}] {acertos} acertos | {est} | {qtd} nums | C{concurso}")
        print(f"         Dezenas: {dezenas}")
        if c.get('resultado_concurso'):
            res = ' - '.join([f'{n:02d}' for n in sorted(c['resultado_concurso'])])
            acertados = sorted(set(c['dezenas']) & set(c['resultado_concurso']))
            ac_str = ' - '.join([f'{n:02d}' for n in acertados])
            print(f"         Sorteio: {res}")
            print(f"         Acertou: {ac_str}")
        print()
