# 📦 Estrutura Modular do Mega Sena Analyzer

## 🎯 Visão Geral

O código foi refatorado e dividido em módulos menores e mais organizados, facilitando manutenção, testes e expansão futura.

## 📂 Estrutura de Arquivos

```
megasena-analyzer/
├── modules/                          # 📁 Pasta com todos os módulos
│   ├── __init__.py                  # Inicialização dos módulos
│   ├── auth.py                      # 🔐 Autenticação e login
│   ├── data_manager.py              # 📊 Gerenciamento de dados
│   ├── statistics.py                # 📈 Cálculos estatísticos
│   ├── game_generator.py            # 🎲 Geração de jogos
│   ├── visualizations.py            # 📉 Gráficos e visualizações
│   └── ui_components.py             # 🎨 Componentes de interface
│
├── megasena_app.py                  # 🎰 Aplicação original (7.300+ linhas)
├── megasena_app_simple.py           # ✨ Nova aplicação modular (~400 linhas)
├── megasena_utils.py                # 🔧 Utilitários (existente)
├── README_MODULAR.md                # 📖 Esta documentação
└── requirements.txt                 # 📦 Dependências
```

## 🧩 Descrição dos Módulos

### 1️⃣ **auth.py** - Autenticação
**Responsabilidade:** Gerenciar login, logout e controle de usuários

**Funções principais:**
- `carregar_usuarios()` - Carrega usuários do arquivo/secrets
- `verificar_login(usuario, senha)` - Valida credenciais
- `pagina_login()` - Exibe página de login
- `logout()` - Efetua logout
- `verificar_autenticacao()` - Verifica se está autenticado
- `obter_usuario_atual()` - Retorna dados do usuário

**Uso:**
```python
from modules import auth

if not auth.verificar_autenticacao():
    auth.pagina_login()
    return
```

---

### 2️⃣ **data_manager.py** - Gerenciamento de Dados
**Responsabilidade:** Carregar, salvar e verificar dados e cartões

**Funções principais:**
- `carregar_dados()` - Carrega dados da API (com cache)
- `salvar_cartoes(cartoes, concurso_alvo)` - Salva cartões em JSON
- `carregar_cartoes_salvos()` - Carrega cartões do arquivo
- `verificar_acertos(dezenas_cartao, dezenas_resultado)` - Verifica acertos
- `buscar_resultado_concurso(numero_concurso)` - Busca resultado na API
- `verificar_resultados_automatico(cartoes, df)` - Verifica múltiplos cartões
- `limpar_cache()` - Limpa cache do Streamlit

**Uso:**
```python
from modules import data_manager as dm

df = dm.carregar_dados()
cartoes = dm.carregar_cartoes_salvos()
dm.salvar_cartoes(novos_cartoes)
```

---

### 3️⃣ **statistics.py** - Estatísticas
**Responsabilidade:** Cálculos estatísticos e análises avançadas

**Funções principais:**
- `calcular_estatisticas(df)` - Estatísticas básicas
- `calcular_escada_temporal(df, janela_recente)` - Análise temporal
- `calcular_candidatos_ouro(contagem_total, df_atrasos)` - Candidatos prioritários
- `calcular_quadrantes(df, n_ultimos)` - Análise por quadrantes
- `calcular_soma_gaussiana(df)` - Distribuição de somas
- `validar_soma_jogo(dezenas, stats_soma)` - Valida soma do jogo
- `calcular_linhas_colunas(df, n_ultimos)` - Análise de linhas/colunas

**Uso:**
```python
from modules import statistics as stats

contagem_total, contagem_recente, df_atrasos = stats.calcular_estatisticas(df)
candidatos = stats.calcular_candidatos_ouro(contagem_total, df_atrasos)
```

---

### 4️⃣ **game_generator.py** - Geração de Jogos
**Responsabilidade:** Gerar jogos com diferentes estratégias

**Funções principais:**
- `gerar_jogo(estrategia, contagem_total, contagem_recente, df_atrasos)` - Gera um jogo
- `gerar_jogo_avancado(...)` - Jogo com análises avançadas
- `gerar_cartoes(n_cartoes, ...)` - Gera múltiplos cartões
- `validar_jogo(jogo)` - Valida jogo gerado

**Estratégias disponíveis:**
- `atrasados` - Números menos frequentes
- `quentes` - Números mais recentes
- `equilibrado` - Mix de pares/ímpares
- `misto` - Combinação de estratégias
- `escada` - Baseado em escada temporal
- `consenso` - Números em múltiplas análises
- `atraso_recente` - Maior atraso atual
- `aleatorio_smart` - Aleatório com validações

**Uso:**
```python
from modules import game_generator as gen

jogo = gen.gerar_jogo('atrasados', contagem_total, contagem_recente, df_atrasos)
cartoes = gen.gerar_cartoes(5, contagem_total, contagem_recente, df_atrasos)
```

---

### 5️⃣ **visualizations.py** - Visualizações
**Responsabilidade:** Criar gráficos e visualizações com Plotly

**Funções principais:**
- `criar_grafico_frequencia(contagem_total)` - Gráfico de barras
- `criar_grafico_atrasos(df_atrasos)` - Gráfico de atrasos
- `criar_grafico_comparacao(freq_total, freq_recente, variacao)` - Comparativo
- `criar_heatmap_quadrantes(stats_quadrantes)` - Heatmap
- `criar_grafico_soma_gaussiana(somas, stats_soma)` - Histograma
- `criar_grafico_linhas_colunas(...)` - Linhas e colunas
- `exibir_cartao(dezenas, estrategia, numero)` - Exibe cartão visual
- `criar_tabela_estrategias(analise)` - Tabela formatada

**Uso:**
```python
from modules import visualizations as viz

fig = viz.criar_grafico_frequencia(contagem_total)
st.plotly_chart(fig)
viz.exibir_cartao(dezenas=[5, 12, 23, 34, 45, 56], estrategia="Misto")
```

---

### 6️⃣ **ui_components.py** - Componentes de Interface
**Responsabilidade:** Componentes reutilizáveis do Streamlit

**Funções principais:**
- `exibir_header(titulo, icone)` - Cabeçalho estilizado
- `exibir_metricas(metricas_dict)` - Métricas em colunas
- `criar_card(titulo, conteudo, cor_fundo)` - Card visual
- `exibir_numero(numero, tamanho, cor)` - Número formatado
- `exibir_numeros_linha(numeros, titulo)` - Linha de números
- `criar_tag_estrategia(estrategia)` - Tag colorida
- `exibir_tabela_cartoes(cartoes)` - Tabela de cartões
- `criar_sidebar_filtros()` - Filtros na sidebar
- `exibir_info_box(titulo, conteudo, tipo)` - Caixa de informação
- `criar_botao_download(dados, nome_arquivo)` - Botão de download
- `exibir_legenda_cores()` - Legenda de cores
- `criar_progresso(valor, maximo)` - Barra de progresso

**Uso:**
```python
from modules import ui_components as ui

ui.exibir_header("Bem-vindo", "🎰")
ui.criar_card("Total", "100")
ui.exibir_numeros_linha([5, 12, 23, 34, 45, 56])
```

---

## 🚀 Como Usar

### Opção 1: Usar o novo app modular (RECOMENDADO)

```bash
streamlit run megasena_app_simple.py
```

**Vantagens:**
- ✅ Código limpo e organizado (~400 linhas)
- ✅ Fácil manutenção
- ✅ Módulos reutilizáveis
- ✅ Melhor performance

### Opção 2: Usar o app original

```bash
streamlit run megasena_app.py
```

**Características:**
- 📄 Arquivo único com 7.300+ linhas
- 🔧 Todas as funcionalidades em um só lugar
- ⚠️ Mais difícil de manter

---

## 🔧 Migração do Código Antigo

Se você tem funcionalidades no `megasena_app.py` que não estão no `megasena_app_simple.py`, siga este guia:

### 1. Identifique a função que deseja migrar

```python
# No megasena_app.py
def minha_funcao_especial(param1, param2):
    # código...
    return resultado
```

### 2. Determine em qual módulo ela se encaixa

- **Autenticação?** → `modules/auth.py`
- **Manipulação de dados?** → `modules/data_manager.py`
- **Cálculos estatísticos?** → `modules/statistics.py`
- **Geração de jogos?** → `modules/game_generator.py`
- **Gráficos?** → `modules/visualizations.py`
- **Interface?** → `modules/ui_components.py`

### 3. Adicione a função ao módulo apropriado

```python
# Em modules/statistics.py (exemplo)

def minha_funcao_especial(param1, param2):
    """
    Descrição da função
    
    Args:
        param1: Descrição
        param2: Descrição
        
    Returns:
        tipo: Descrição do retorno
    """
    # código...
    return resultado
```

### 4. Use a função no app

```python
# Em megasena_app_simple.py
from modules import statistics as stats

resultado = stats.minha_funcao_especial(valor1, valor2)
```

---

## 📊 Comparação de Tamanho

| Arquivo | Linhas | Descrição |
|---------|--------|-----------|
| **megasena_app.py** | ~7.300 | Aplicação original monolítica |
| **megasena_app_simple.py** | ~400 | Nova aplicação modular |
| **modules/auth.py** | ~130 | Módulo de autenticação |
| **modules/data_manager.py** | ~200 | Gerenciamento de dados |
| **modules/statistics.py** | ~350 | Cálculos estatísticos |
| **modules/game_generator.py** | ~200 | Geração de jogos |
| **modules/visualizations.py** | ~250 | Visualizações |
| **modules/ui_components.py** | ~300 | Componentes UI |
| **TOTAL MODULAR** | ~1.830 | Soma de todos os módulos + app |

**Redução:** 75% menos complexidade no arquivo principal!

---

## 🎯 Benefícios da Modularização

### ✅ **Manutenibilidade**
- Código organizado em responsabilidades claras
- Fácil localizar e corrigir bugs
- Mudanças isoladas não afetam todo o sistema

### ✅ **Reutilização**
- Módulos podem ser importados em outros projetos
- Funções bem documentadas e testáveis
- Componentes padronizados

### ✅ **Escalabilidade**
- Adicionar novas funcionalidades é simples
- Fácil criar novos módulos
- Estrutura preparada para crescimento

### ✅ **Testabilidade**
- Cada módulo pode ser testado isoladamente
- Facilita criação de testes unitários
- Melhor cobertura de testes

### ✅ **Colaboração**
- Múltiplos desenvolvedores podem trabalhar em módulos diferentes
- Menos conflitos de merge
- Código review mais eficiente

---

## 🛠️ Próximos Passos

1. **Testar** o novo app modular
2. **Migrar** funcionalidades faltantes (se houver)
3. **Adicionar testes** unitários para cada módulo
4. **Documentar** funções complexas
5. **Otimizar** performance onde necessário

---

## 📝 Notas Importantes

- ⚠️ O arquivo original `megasena_app.py` **não foi modificado** - está preservado como backup
- ✅ Todos os módulos estão na pasta `modules/`
- 🔄 Para atualizar, basta modificar o módulo específico
- 📦 As dependências continuam as mesmas (`requirements.txt`)

---

## 🆘 Suporte

Se encontrar problemas ou tiver dúvidas:
1. Verifique se todos os módulos estão na pasta `modules/`
2. Certifique-se de que `__init__.py` existe em `modules/`
3. Verifique as importações no início de cada arquivo
4. Consulte a documentação inline nas funções

---

**Desenvolvido por Leonardo**  
**Versão 2.1.0 - Estrutura Modular**  
**Data: Dezembro 2025**
