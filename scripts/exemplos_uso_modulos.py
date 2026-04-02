"""
================================================================================
📚 EXEMPLOS DE USO DOS MÓDULOS
================================================================================
Demonstra como usar cada módulo do sistema de forma independente
"""

# =============================================================================
# EXEMPLO 1: Usar módulo de dados
# =============================================================================
from modules import game_generator as gen
from modules import statistics as stats
from modules import data_manager as dm
print("=" * 80)
print("EXEMPLO 1: Carregando dados da Mega Sena")
print("=" * 80)


# Carregar dados da API
df = dm.carregar_dados()
if df is not None:
    print(f"✅ Dados carregados: {len(df)} sorteios")
    print(f"Último concurso: {df.iloc[0]['concurso']}")
else:
    print("❌ Erro ao carregar dados")

# =============================================================================
# EXEMPLO 2: Calcular estatísticas
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 2: Calculando estatísticas")
print("=" * 80)


if df is not None:
    contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(
        df)

    print(f"\n📊 Estatísticas Básicas:")
    print(
        f"  - Número mais frequente: {contagem_total.idxmax()} ({contagem_total.max()} vezes)")
    print(
        f"  - Número menos frequente: {contagem_total.idxmin()} ({contagem_total.min()} vezes)")
    print(
        f"  - Número mais atrasado: {df_atrasos.iloc[0]['numero']} ({df_atrasos.iloc[0]['jogos_sem_sair']} jogos)")

# =============================================================================
# EXEMPLO 3: Gerar jogos
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 3: Gerando jogos com diferentes estratégias")
print("=" * 80)


if df is not None:
    estrategias = ['atrasados', 'quentes', 'equilibrado', 'misto']

    for estrategia in estrategias:
        jogo = gen.gerar_jogo(estrategia, contagem_total,
                              contagem_recente, df_atrasos)
        jogo_str = " - ".join([f"{n:02d}" for n in jogo])
        print(f"\n🎲 {estrategia.upper()}: {jogo_str}")

# =============================================================================
# EXEMPLO 4: Análises avançadas
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 4: Análises avançadas")
print("=" * 80)

if df is not None:
    # Escada Temporal
    _, _, _, _, _, inversoes = stats.calcular_escada_temporal(df)
    print(f"\n📈 Números em inversão de tendência: {len(inversoes)}")
    if inversoes:
        print(f"Top 3:")
        for inv in inversoes[:3]:
            print(
                f"  - Nº {inv['numero']:02d}: Variação de {inv['variacao']:+.2f}%")

    # Candidatos Ouro
    candidatos = stats.calcular_candidatos_ouro(
        contagem_total, df_atrasos, limite_atraso=30)
    print(f"\n🏆 Candidatos Ouro (frios + atrasados): {len(candidatos)}")
    if candidatos:
        print(f"Top 3:")
        for c in candidatos[:3]:
            print(
                f"  - Nº {c['numero']:02d}: Score {c['score']:.2f} (Freq: {c['frequencia']}, Atraso: {c['atraso']})")

    # Quadrantes
    quadrantes, stats_quadrantes, quadrante_frio = stats.calcular_quadrantes(
        df)
    print(f"\n🎯 Quadrante mais frio: {quadrante_frio[0]}")
    print(f"  Frequência recente: {quadrante_frio[1]['freq_recente']}")

    # Soma Gaussiana
    somas, stats_soma, faixas = stats.calcular_soma_gaussiana(df)
    print(f"\n➕ Análise de Soma (Gaussiana):")
    print(f"  Média: {stats_soma['media']:.0f}")
    print(
        f"  Faixa ideal: {stats_soma['faixa_ideal_min']:.0f} - {stats_soma['faixa_ideal_max']:.0f}")

# =============================================================================
# EXEMPLO 5: Validar jogos
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 5: Validando jogos")
print("=" * 80)

if df is not None:
    # Gerar um jogo
    jogo_teste = gen.gerar_jogo(
        'atrasados', contagem_total, contagem_recente, df_atrasos)

    # Validar estrutura
    valido, erros = gen.validar_jogo(jogo_teste)
    print(f"\n✅ Jogo válido: {valido}")
    if erros:
        print(f"Erros encontrados:")
        for erro in erros:
            print(f"  - {erro}")

    # Validar soma
    _, stats_soma, _ = stats.calcular_soma_gaussiana(df)
    valido_soma, soma, msg = stats.validar_soma_jogo(jogo_teste, stats_soma)
    print(f"\n{msg}")

# =============================================================================
# EXEMPLO 6: Salvar e carregar cartões
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 6: Salvando e carregando cartões")
print("=" * 80)

# Criar alguns cartões
cartoes_exemplo = []
for i in range(3):
    jogo = gen.gerar_jogo('misto', contagem_total,
                          contagem_recente, df_atrasos)
    cartoes_exemplo.append({
        'id': f'EXEMPLO-{i+1}',
        'dezenas': jogo,
        'estrategia': 'misto',
        'vai_jogar': False,
        'verificado': False,
        'concurso_alvo': None,
        'status': 'não_marcado'
    })

print(f"\n💾 Salvando {len(cartoes_exemplo)} cartões...")

# Nota: Isso substituirá os cartões existentes - remova o comentário para testar
# if dm.salvar_cartoes(cartoes_exemplo):
#     print("✅ Cartões salvos com sucesso!")
#
#     # Carregar de volta
#     cartoes_carregados = dm.carregar_cartoes_salvos()
#     print(f"📂 Cartões carregados: {len(cartoes_carregados)}")
# else:
#     print("❌ Erro ao salvar cartões")

print("\n⚠️  Salvamento desativado neste exemplo para não sobrescrever seus cartões")

# =============================================================================
# EXEMPLO 7: Verificar resultados
# =============================================================================
print("\n" + "=" * 80)
print("EXEMPLO 7: Verificando acertos")
print("=" * 80)

# Simular um cartão e um resultado
cartao_teste = [5, 12, 23, 34, 45, 56]
resultado_teste = [5, 12, 23, 30, 40, 50]

acertos = dm.verificar_acertos(cartao_teste, resultado_teste)
print(f"\n🎯 Cartão: {' - '.join([f'{n:02d}' for n in cartao_teste])}")
print(f"🎲 Resultado: {' - '.join([f'{n:02d}' for n in resultado_teste])}")
print(f"✅ Acertos: {acertos}")

# =============================================================================
# RESUMO
# =============================================================================
print("\n" + "=" * 80)
print("📚 RESUMO DOS MÓDULOS DISPONÍVEIS")
print("=" * 80)

print("""
✅ Módulos criados com sucesso:

1. 🔐 auth.py              - Autenticação e login
2. 📊 data_manager.py      - Gerenciamento de dados e cartões
3. 📈 statistics.py        - Cálculos estatísticos avançados
4. 🎲 game_generator.py    - Geração de jogos com estratégias
5. 📉 visualizations.py    - Gráficos e visualizações
6. 🎨 ui_components.py     - Componentes de interface

Para usar no Streamlit:
  streamlit run megasena_app_simple.py

Para mais informações:
  Consulte README_MODULAR.md
""")

print("=" * 80)
print("✨ Exemplos executados com sucesso!")
print("=" * 80)
