# 🧹 Guia de Limpeza - Arquivos Organizados

## ✅ Organização Concluída!

### 📁 Nova Estrutura

```
megasena-analyzer/
├── megasena_app_simple.py    ← 🎯 USAR ESTE!
├── modules/                  ← Código modular
├── docs/                     ← Documentação
├── scripts/                  ← Scripts auxiliares
├── data/                     ← Simulações e dados
├── backup/                   ← Arquivos antigos
└── old_files/                ← Outros arquivos antigos
```

## 📂 O que foi movido para cada pasta:

### 📚 docs/
- README_MODULAR.md
- MODULARIZACAO_COMPLETA.md
- INICIO_RAPIDO.md
- MODULARIZACAO_RESUMO.txt

### 🔧 scripts/
- testar_estrutura.py
- exemplos_uso_modulos.py
- mostrar_estrutura.py

### 💾 data/
- Todos os arquivos simulacao_*.json
- Todos os cartoes_concurso_*.json
- Todos os resultado_*.json

### 📂 backup/
- megasena_app.py (original 7.388 linhas)
- megasena_analise.py
- analise_estrategias_2949.py
- buscar_resultado_2949.py
- executar_analise.py
- fix_limits.py
- recuperar_cartoes.py
- testar_concurso_2949.py

### 🗂️ old_files/
- ACOMPANHAMENTO.md
- MELHORIAS_V2.md
- logs.log
- teste 1.png

## 🎯 Arquivos na Raiz (mantidos)

### ✨ PRINCIPAIS (usar)
- **megasena_app_simple.py** - App modular (USE ESTE!)
- **megasena_utils.py** - Utilitários
- **meus_cartoes.json** - Seus cartões
- **usuarios.json** - Usuários do sistema

### 📖 DOCUMENTAÇÃO
- **README.md** - Readme principal (existente)
- **README_ESTRUTURA.md** - Este guia da nova estrutura
- **CHANGELOG.md** - Histórico de mudanças
- **DOCUMENTACAO.md** - Documentação geral
- **DEPLOY.md** - Guia de deploy
- **LICENSE** - Licença

### ⚙️ CONFIGURAÇÃO
- **requirements.txt** - Dependências Python
- **runtime.txt** - Versão Python (Streamlit Cloud)
- **packages.txt** - Pacotes sistema (Streamlit Cloud)
- **Iniciar_MegaSena.bat** - Atalho Windows
- **.streamlit/** - Configurações Streamlit
- **.gitignore** - Arquivos ignorados pelo Git
- **MegaSena.ipynb** - Notebook Jupyter

### 📦 MÓDULOS
- **modules/** - Pasta com 6 módulos Python

## 🗑️ Pode Excluir Depois (opcional)

Se quiser limpar ainda mais, pode excluir:

### Pasta old_files/
```bash
# Arquivos antigos que não são mais usados
rm -rf old_files/
```

### Logs antigos
```bash
rm logs.log
```

### Pycache
```bash
rm -rf __pycache__
rm -rf modules/__pycache__
```

## ⚠️ NÃO Exclua

### 💾 Dados importantes
- **meus_cartoes.json** - Seus cartões salvos
- **usuarios.json** - Configurações de usuários
- **data/** - Suas simulações (pode limpar dentro se quiser)

### 📦 Módulos
- **modules/** - Código do sistema

### ⚙️ Configuração
- **requirements.txt**
- **.streamlit/**
- **runtime.txt**
- **packages.txt**

## 🚀 Comandos Úteis

### Limpar cache Python
```bash
# PowerShell
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force

# Ou simplesmente:
python -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
```

### Limpar simulações antigas
```bash
# Se quiser apagar simulações para liberar espaço:
cd data
Remove-Item simulacao_*.json
```

### Limpar logs do Git
```bash
git clean -fdx  # CUIDADO: remove tudo não rastreado
```

## 📊 Espaço Liberado

Antes da organização:
- **Raiz:** ~200 arquivos
- **Desorganizado**

Depois da organização:
- **Raiz:** ~20 arquivos principais
- **Pastas organizadas:** 6 pastas temáticas
- **80% mais limpo!**

## ✅ Checklist de Limpeza

- [x] Documentação movida para `docs/`
- [x] Scripts auxiliares em `scripts/`
- [x] Dados em `data/`
- [x] Arquivos antigos em `backup/`
- [x] Outros arquivos antigos em `old_files/`
- [x] Estrutura documentada
- [x] README atualizado

## 🎉 Resultado

Seu projeto agora está:
- ✅ **Organizado** em pastas temáticas
- ✅ **Limpo** com apenas arquivos essenciais na raiz
- ✅ **Documentado** com guias claros
- ✅ **Modular** com código separado
- ✅ **Profissional** pronto para produção

---

**Para voltar a trabalhar:**
```bash
streamlit run megasena_app_simple.py
```

**Para consultar documentação:**
- Veja `docs/README_MODULAR.md`
- Veja `docs/INICIO_RAPIDO.md`

**Para testar:**
```bash
python scripts/testar_estrutura.py
```
