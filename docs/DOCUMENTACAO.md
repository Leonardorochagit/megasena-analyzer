# 🎰 MEGA SENA ANALYZER - Documentação Completa

**Autor:** Leonardo  
**Data:** Dezembro 2025  
**Versão:** 2.0  

---
##Execute: streamlit run megasena_app_simple.py
## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Requisitos](#requisitos)
3. [Como Executar](#como-executar)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Funcionalidades por Página](#funcionalidades-por-página)
6. [Funções Principais](#funções-principais)
7. [Fluxo de Uso Recomendado](#fluxo-de-uso-recomendado)
8. [Pendências e Melhorias Futuras](#pendências-e-melhorias-futuras)

---

## 🎯 Visão Geral

Sistema completo para análise estatística da Mega Sena com:
- Análise de frequência de números
- Análise de padrões (gaps/escada)
- Machine Learning (PyCaret AutoML)
- Geração inteligente de cartões
- Comparação com resultados oficiais
- Backtesting de estratégias

---

## 📦 Requisitos

### Dependências Python
```
streamlit
requests
pandas
numpy
plotly
scikit-learn
pycaret>=3.0
```

### Instalação
```bash
pip install streamlit requests pandas numpy plotly scikit-learn pycaret
```

### Python
- Versão: **3.11** (testado)
- Caminho: `C:\Users\User\AppData\Local\Programs\Python\Python311\python.exe`

---

## 🚀 Como Executar

```bash
cd "c:\Users\User\OneDrive\2.Leonardo\1. Python\1.Megasena"
streamlit run megasena_app.py --server.port 8505 --server.headless true
```

Acesse: **http://localhost:8505**

---

## 📁 Estrutura do Projeto

```
1.Megasena/
├── megasena_app.py          # Aplicação principal Streamlit (3023 linhas)
├── megasena_analise.py      # Script de análise original (CLI)
├── MegaSena.ipynb           # Notebook Jupyter
├── executar_analise.py      # Script auxiliar
├── cartoes_concurso_XXXX.json  # Cartões salvos por concurso
├── DOCUMENTACAO.md          # Esta documentação
└── .vscode/                 # Configurações VS Code
```

---

## 📱 Funcionalidades por Página

### 1. 🏠 Início
- Dashboard com estatísticas gerais
- Último resultado oficial
- Próximo concurso
- Números quentes/frios/atrasados

### 2. 📊 Análise de Escada
- **Gráfico de frequência** de cada número (1-60)
- Números abaixo da média (candidatos a sair)
- **Análise de Gaps** (4 abas):
  - 📊 Distribuição de Gaps
  - 🎯 Padrões Mais Comuns
  - 📈 Evolução Temporal
  - 🔮 Previsão de Padrão
- Geração de 10 cartões com estratégia escada
- Criação manual de cartões

### 3. 🔥 Números Quentes/Frios
- Top 15 números quentes (últimos 50 jogos)
- Top 15 números frios (total)
- Números mais atrasados
- Geração de cartões quentes/atrasados
- Criação manual de cartões

### 4. 🧠 Smart / IA
- **Geração de 10 cartões com IA** (principal)
- Métodos disponíveis:
  - Consenso IA (todos os métodos)
  - Probabilidades (Gradient Boosting)
  - Clusters (K-Means)
  - Sequências
- Criação manual de cartões
- **Análises Detalhadas** (expandível):
  - 🏆 AutoML (PyCaret)
  - 📊 Probabilidades
  - 🎯 Clusters
  - 🔗 Sequências

### 5. 🎯 Meus Cartões
- Visualização dos cartões selecionados (até 20)
- Estratégias usadas
- Botão para salvar em JSON
- Exportação para comparação futura

### 6. 📈 Comparar Resultados
- Carregar cartões salvos
- Digitar resultado oficial
- Ver acertos por cartão
- Estatísticas de desempenho
- Histórico de comparações

### 7. 📜 Histórico
- Lista de todos os sorteios
- Filtros por período
- Estatísticas históricas

### 8. 🧪 Backtesting
- Testar estratégias em sorteios passados
- Comparar desempenho das estratégias
- Gráficos de resultados

---

## ⚙️ Funções Principais

### Dados
| Função | Linha | Descrição |
|--------|-------|-----------|
| `carregar_dados()` | 93 | Carrega dados da API da Mega Sena |
| `calcular_estatisticas(df)` | 120 | Calcula frequências e atrasos |

### Geração de Jogos
| Função | Linha | Descrição |
|--------|-------|-----------|
| `gerar_jogo(estrategia, ...)` | 161 | Gera 1 jogo com estratégia específica |
| `gerar_cartoes(n, ...)` | 231 | Gera N cartões variados |
| `gerar_jogo_ia(probabilidades)` | 652 | Gera jogo com ML |
| `gerar_jogo_cluster(...)` | 665 | Gera jogo baseado em clusters |
| `gerar_jogo_sequencia(...)` | 694 | Gera jogo baseado em sequências |

### Machine Learning
| Função | Linha | Descrição |
|--------|-------|-----------|
| `preparar_dados_ml(df, n)` | 462 | Prepara features para ML |
| `treinar_modelo_probabilidade(X, y)` | 501 | Treina Gradient Boosting |
| `preparar_dados_pycaret(df, num, n)` | 529 | Prepara dados para PyCaret |
| `analisar_padroes_clusters(df, n)` | 587 | Análise K-Means |
| `analisar_sequencias(df, n)` | 633 | Análise de sequências |

### Persistência
| Função | Linha | Descrição |
|--------|-------|-----------|
| `salvar_cartoes(cartoes, concurso)` | 252 | Salva cartões em JSON |
| `carregar_cartoes_salvos(concurso)` | 271 | Carrega cartões salvos |
| `comparar_cartoes_com_resultado(...)` | 313 | Compara com resultado |

### Backtesting
| Função | Linha | Descrição |
|--------|-------|-----------|
| `executar_backtesting(df, n)` | 381 | Testa estratégias em histórico |

---

## 🔄 Fluxo de Uso Recomendado

```
1. 🏠 Início
   └── Ver último resultado e estatísticas

2. 📊 Análise de Escada
   ├── Ver gráfico de frequências
   ├── Analisar gaps (entender padrões)
   ├── Gerar 10 cartões escada
   └── Adicionar aos Meus Cartões

3. 🔥 Quentes/Frios
   ├── Ver números quentes e atrasados
   ├── Gerar 10 cartões quentes/atrasados
   └── Adicionar aos Meus Cartões

4. 🧠 Smart / IA
   ├── Gerar 10 cartões com IA (Consenso)
   ├── Criar cartões manuais (sua análise)
   └── Adicionar aos Meus Cartões

5. 🎯 Meus Cartões
   ├── Revisar os cartões selecionados
   ├── Remover os que não gostar
   └── SALVAR para o concurso

6. [APÓS O SORTEIO]
   📈 Comparar Resultados
   ├── Carregar cartões salvos
   ├── Digitar resultado oficial
   └── Ver quantos acertos teve
```

---

## 📊 Análise de Gaps - Explicação

### O que é Gap?
**Gap** = diferença entre dois números consecutivos em um sorteio.

**Exemplo:** Sorteio 03 - 07 - 15 - 28 - 45 - 52
- Gap 1: 07 - 03 = **4**
- Gap 2: 15 - 07 = **8**
- Gap 3: 28 - 15 = **13**
- Gap 4: 45 - 28 = **17**
- Gap 5: 52 - 45 = **7**

### Estatísticas Descobertas
| Métrica | Valor | Significado |
|---------|-------|-------------|
| Gap médio | 8.72 | Diferença média entre números |
| Gap mais comum | 1 | Números consecutivos são frequentes |
| Gap mínimo | 1 | Existem números "colados" |
| Gap máximo | 44 | Já houve grandes distâncias |

### Insight Principal
- **~41% dos gaps** são de 1 a 5 (números próximos)
- Um jogo "realista" deve ter gap médio próximo de **8-9**

---

## 🔧 Pendências e Melhorias Futuras

### ✅ Implementado
- [x] Menu reorganizado (Início → Escada → Quentes → Smart → Cartões → Comparar)
- [x] PyCaret AutoML visível na página Smart/IA
- [x] Geração de 10 cartões por página
- [x] Criação manual de cartões
- [x] Análise de gaps/escada
- [x] Sistema de cartões selecionados (até 20)
- [x] Comparação com resultados oficiais
- [x] Salvamento em JSON

### 🔄 Melhorias Sugeridas
- [ ] Gráfico visual dos gaps do jogo gerado
- [ ] Validação se o jogo gerado tem gap médio "realista"
- [ ] Histórico de acertos por estratégia
- [ ] Exportar cartões para PDF/Excel
- [ ] Notificação quando sair resultado
- [ ] Análise de dezenas por posição (1ª bola, 2ª bola, etc.)
- [ ] Análise de soma total dos números
- [ ] Gráfico de evolução dos números ao longo do tempo

### 🐛 Bugs Conhecidos
- Nenhum bug crítico identificado

---

## 📡 API Utilizada

**URL:** `https://loteriascaixa-api.herokuapp.com/api/megasena`

**Dados retornados:**
- Número do concurso
- Data do sorteio
- Dezenas sorteadas
- Valor acumulado
- Ganhadores

---

## 💾 Formato dos Arquivos JSON

### cartoes_concurso_XXXX.json
```json
{
  "concurso_alvo": 2949,
  "data_criacao": "2025-12-06T23:30:00",
  "cartoes": [
    {
      "numero": 1,
      "id_original": "ESC-1",
      "estrategia": "Escada",
      "dezenas": [3, 15, 22, 38, 45, 57]
    },
    ...
  ]
}
```

---

## 📞 Suporte

Para continuar o desenvolvimento:
1. Abra este arquivo no VS Code
2. Execute `streamlit run megasena_app.py`
3. Consulte esta documentação

**Última atualização:** 6 de dezembro de 2025
