"""
================================================================================
🧪 TESTE RÁPIDO DA ESTRUTURA MODULAR
================================================================================
Verifica se todos os módulos foram criados corretamente
"""

import os
import sys

print("=" * 80)
print("🧪 VERIFICANDO ESTRUTURA MODULAR")
print("=" * 80)

# Verificar se a pasta modules existe
if os.path.exists('modules'):
    print("\n✅ Pasta 'modules' encontrada")
else:
    print("\n❌ Pasta 'modules' NÃO encontrada!")
    sys.exit(1)

# Lista de módulos esperados
modulos_esperados = [
    '__init__.py',
    'auth.py',
    'data_manager.py',
    'statistics.py',
    'game_generator.py',
    'visualizations.py',
    'ui_components.py'
]

print("\n📁 Verificando arquivos dos módulos:")
todos_ok = True

for modulo in modulos_esperados:
    caminho = os.path.join('modules', modulo)
    if os.path.exists(caminho):
        tamanho = os.path.getsize(caminho)
        print(f"  ✅ {modulo:25s} ({tamanho:,} bytes)")
    else:
        print(f"  ❌ {modulo:25s} NÃO ENCONTRADO")
        todos_ok = False

# Verificar arquivos principais
print("\n📄 Verificando arquivos principais:")

arquivos_principais = [
    'megasena_app.py',
    'megasena_app_simple.py',
    'README_MODULAR.md',
    'exemplos_uso_modulos.py'
]

for arquivo in arquivos_principais:
    if os.path.exists(arquivo):
        tamanho = os.path.getsize(arquivo)
        print(f"  ✅ {arquivo:30s} ({tamanho:,} bytes)")
    else:
        print(f"  ⚠️  {arquivo:30s} NÃO ENCONTRADO")

# Verificar sintaxe Python
print("\n🐍 Verificando sintaxe dos módulos:")

for modulo in modulos_esperados:
    if not modulo.endswith('.py'):
        continue

    caminho = os.path.join('modules', modulo)
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, caminho, 'exec')
        print(f"  ✅ {modulo:25s} - Sintaxe OK")
    except SyntaxError as e:
        print(f"  ❌ {modulo:25s} - Erro de sintaxe: {e}")
        todos_ok = False
    except Exception as e:
        print(f"  ⚠️  {modulo:25s} - Erro: {e}")

# Contar linhas de código
print("\n📊 Estatísticas de linhas de código:")


def contar_linhas(arquivo):
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            linhas = len(f.readlines())
        return linhas
    except:
        return 0


total_linhas_modulos = 0
for modulo in modulos_esperados:
    if not modulo.endswith('.py'):
        continue
    caminho = os.path.join('modules', modulo)
    linhas = contar_linhas(caminho)
    total_linhas_modulos += linhas
    print(f"  {modulo:25s} {linhas:4d} linhas")

print(f"\n  {'TOTAL (módulos)':25s} {total_linhas_modulos:4d} linhas")

# Comparar com arquivo original
linhas_original = contar_linhas('megasena_app.py')
linhas_simplificado = contar_linhas('megasena_app_simple.py')

print(f"\n  {'megasena_app.py (original)':30s} {linhas_original:5d} linhas")
print(f"  {'megasena_app_simple.py (novo)':30s} {linhas_simplificado:5d} linhas")

if linhas_original > 0:
    reducao = ((linhas_original - linhas_simplificado) / linhas_original * 100)
    print(f"\n  🎯 Redução no arquivo principal: {reducao:.1f}%")

# Estrutura de diretórios
print("\n📂 Estrutura criada:")
print("""
megasena-analyzer/
├── modules/
│   ├── __init__.py
│   ├── auth.py
│   ├── data_manager.py
│   ├── statistics.py
│   ├── game_generator.py
│   ├── visualizations.py
│   └── ui_components.py
├── megasena_app.py (original)
├── megasena_app_simple.py (novo)
├── README_MODULAR.md
└── exemplos_uso_modulos.py
""")

# Resultado final
print("\n" + "=" * 80)
if todos_ok:
    print("✅ SUCESSO! Todos os módulos foram criados corretamente!")
    print("\n🚀 Próximos passos:")
    print("   1. Execute: streamlit run megasena_app_simple.py")
    print("   2. Consulte: README_MODULAR.md")
    print("   3. Migre funcionalidades restantes do megasena_app.py")
else:
    print("⚠️  ATENÇÃO! Alguns problemas foram encontrados.")
    print("   Verifique os erros acima e corrija-os.")

print("=" * 80)

# Criar um arquivo de resumo
with open('MODULARIZACAO_RESUMO.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("📦 RESUMO DA MODULARIZAÇÃO\n")
    f.write("=" * 80 + "\n\n")

    f.write(
        f"Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    f.write("MÓDULOS CRIADOS:\n")
    for modulo in modulos_esperados:
        if modulo.endswith('.py'):
            caminho = os.path.join('modules', modulo)
            linhas = contar_linhas(caminho)
            f.write(f"  ✅ {modulo:25s} - {linhas:4d} linhas\n")

    f.write(f"\nTOTAL: {total_linhas_modulos} linhas nos módulos\n")
    f.write(f"Arquivo original: {linhas_original} linhas\n")
    f.write(f"Arquivo simplificado: {linhas_simplificado} linhas\n")

    if linhas_original > 0:
        reducao = ((linhas_original - linhas_simplificado) /
                   linhas_original * 100)
        f.write(f"Redução: {reducao:.1f}%\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("ESTRUTURA:\n")
    f.write("=" * 80 + "\n")
    f.write("""
modules/
├── __init__.py          - Inicialização
├── auth.py              - Autenticação e login
├── data_manager.py      - Gerenciamento de dados
├── statistics.py        - Cálculos estatísticos
├── game_generator.py    - Geração de jogos
├── visualizations.py    - Gráficos
└── ui_components.py     - Componentes UI

COMO USAR:
  streamlit run megasena_app_simple.py

DOCUMENTAÇÃO:
  README_MODULAR.md
""")

print("\n✅ Resumo salvo em: MODULARIZACAO_RESUMO.txt")
