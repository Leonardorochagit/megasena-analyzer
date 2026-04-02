# 📋 Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [3.4.0] - 2026-03-02

### 🎉 Adicionado
- **Menu reorganizado**: Todas as 10 estratégias visíveis no menu principal da sidebar
  - "⏰ Números Atrasados" e "🔥 Números Quentes" movidos do selectbox separado para o menu principal
  - "⏳ Atraso Recente" adicionado ao menu (estratégia existia no gerador mas não tinha acesso na UI)
  - Removido selectbox "Análises Individuais" (desnecessário)
- **Relatório de estratégias redesenhado** (`pagina_verificar_resultados.py`):
  - Ranking por consistência (concursos com 3+ acertos, streaks consecutivos)
  - Evolução temporal por concurso com gráfico de linhas
  - Recomendação para bolão por quantidade de números jogados
  - Métricas absolutas em vez de percentuais abstratos
- **Duques (2ac) e Ternas (3ac)** em todos os rankings e relatórios
- **Quantidade de números usados** registrada nas estatísticas do histórico
- **Relatório Geral** (`pagina_relatorio_geral.py`) atualizado:
  - Colunas de Duques e Ternas nas tabelas
  - Ordenação prioriza consistência (senas → quinas → quadras → ternas → duques)
  - Resumo mostra contagem de duques e ternas

### 🔧 Modificado
- `pagina_verificar_resultados.py`: função `_calcular_stats_estrategias` substituída por `_calcular_stats_estrategias_v2`
- `pagina_verificar_resultados.py`: nova função `_calcular_stats_para_historico` com ternas, duques e qtd_nums_usadas
- `megasena_app.py`: sidebar simplificada — um único radio com todas as opções

## [3.3.0] - 2026-02-26

### 🎉 Adicionado
- **Piloto Automático** (`pagina_piloto_automatico.py`):
  - Dashboard em tempo real com auto-refresh (streamlit-autorefresh)
  - Auto-conferir resultados pendentes automaticamente
  - Auto-gerar cartões para o próximo concurso
  - Log de ações com histórico completo
  - Configurações persistentes via arquivo (`piloto_config.json`)
  - Integrado como primeira opção no menu principal
- **Limites unificados**: até 20 cartões por estratégia em todas as páginas
- **Análise de sequências expandida**: slider de 6-20 números (antes era 6-15)
- **Dependência**: `streamlit-autorefresh>=1.0.0` para auto-refresh do Piloto
- **Dependência**: `seaborn>=0.12.0` para visualizações

### 🔧 Modificado
- GitHub Actions: cron nos dias de sorteio (Ter/Qui/Sáb às 22h Brasília)
- Dados (`meus_cartoes.json`, `historico_analises.json`) agora versionados no git
- README.md atualizado com documentação do Piloto Automático

## [3.2.0] - 2026-02-15

### 🎉 Adicionado
- **Cartões de 6 a 20 números**: Expandido limite máximo de 15 para 20
- **Preços atualizados**: Base R$ 6,00 conforme tabela oficial Mega Sena 2026
- **Tabela de preços completa**: Custos para 16 a 20 números incluídos
- **Script de automação CLI** (`scripts/automacao_dia_jogo.py`):
  - Conferência automática de resultados pendentes
  - Geração de lote de cartões para o próximo concurso
  - Ranking consolidado de performance por estratégia
  - Parâmetros via linha de comando (--qtd-numeros, --apenas-conferir, etc.)
- **GitHub Actions** (`.github/workflows/dia_de_jogo.yml`):
  - Execução automática nos dias de sorteio (terça, quinta, sábado)
  - Confere + gera + commit automático no repositório
  - Também pode ser disparado manualmente
- **Deploy no Streamlit Cloud**: App acessível em https://megasena-analyzer.streamlit.app

### 🔧 Modificado
- Valor padrão de números por cartão alterado para 10
- Pool de expansão dinâmico (pool_size adaptado à quantidade de números)
- README.md reescrito com documentação completa

### 🐛 Corrigido
- Erro `ModuleNotFoundError: sklearn` ao usar Python global em vez do venv
- Correção do path do Python para usar `.venv\Scripts\python.exe`

---

## [3.1.0] - 2026-02-12

### 🎉 Adicionado
- **AutoML Redesenhado - Foco na Quadra**:
  - Treina modelos de ML para **todos os 60 números** automaticamente
  - Calcula probabilidade individual de cada número sair no próximo sorteio
  - Gera cartões otimizados para maximizar chance de acertar **quadra (4+ acertos)**
  - Score combinado: ML + frequência recente + números atrasados
  - Diversificação automática entre cartões para maior cobertura
  - Validação de equilíbrio (par/ímpar, soma, baixos/altos)

- **Aba Ranking de Números**:
  - Ranking completo dos 60 números por probabilidade ML
  - Classificação visual: 🔥 Alto / ⚡ Médio / ❄️ Baixo
  - Gráfico interativo dos Top 30 números
  - Métricas de distribuição de probabilidades

- **Configuração de Geração Avançada**:
  - Suporte a cartões de **6 a 15 números**
  - Custo estimado em R$ exibido na interface
  - Cálculo de vantagem combinatória para quadra
  - Slider de concursos para treino (100-500)

- **Histórico por Concurso**:
  - Cartões AutoML agrupados por concurso alvo
  - Score ML de cada cartão visível
  - Botão para limpar histórico AutoML

### 🔧 Modificado
- **Fluxo Simplificado**: Removida separação entre "Treinar" e "Gerar" — agora é um único botão
- **Sem "Número para Prever"**: Eliminado campo confuso; sistema treina todos automaticamente
- **Barra de Progresso**: Mostra progresso em tempo real (número 1/60, 2/60...)
- **Top 10 Números**: Exibição dos 10 mais prováveis após geração

### 🐛 Corrigido
- Erro `KeyError: 'atraso'` — coluna correta é `'jogos_sem_sair'`
- Erro `TypeError: '<' not supported between NoneType and int` no histórico
- PyCaret não reconhecido após instalação (Streamlit não usava o venv correto)

---

## [2.0.0] - 2025-12-07

### 🎉 Adicionado
- **Sistema de Preview**: Cartões gerados são mostrados antes de adicionar à lista
  - Permite análise detalhada antes da decisão
  - Números especiais destacados visualmente (⭐ inversões, 🏆 ouro, etc.)
  - Botões individuais "➕ Adicionar" por cartão
  
- **Feedback Visual Completo**:
  - Cartões já adicionados mostram "✅ Adicionado"
  - Impossível adicionar duplicatas por engano
  - Mensagens claras de sucesso/erro

- **Sliders de Quantidade Padronizados**:
  - Todos geradores agora suportam 1-10 cartões
  - Interface consistente em todas estratégias
  - Feedback de quantidade gerada

- **Módulo `megasena_utils.py`**:
  - Funções reutilizáveis para geração de cartões
  - Gerenciamento padronizado de session state
  - Componentes de UI consistentes
  - Validações centralizadas

- **Documentação Completa**:
  - README.md com guia de uso detalhado
  - CHANGELOG.md para rastreamento de versões
  - Comentários explicativos no código
  - Docstrings em todas funções do utils

- **Sliders de Peso/Prioridade**:
  - Controle fino sobre influência de números prioritários
  - Range 50-100% configurável
  - Aplicado em AutoML, Probabilidades e Clusters

### 🔧 Modificado
- **Padrão de Geração Unificado**:
  - Todas estratégias seguem mesmo fluxo: gerar → preview → selecionar → adicionar
  - Estrutura de dados consistente: `{'id', 'estrategia', 'dezenas', 'concurso_alvo'}`
  - Session state gerenciado de forma uniforme

- **Inversões Temporais**:
  - Migrado para sistema de preview
  - Destaque visual de números em inversão (⭐)
  - Slider de quantidade (1-10)

- **Candidatos Ouro**:
  - Migrado para sistema de preview
  - Destaque visual de candidatos (🏆)
  - Slider de quantidade (1-10)

- **Quadrantes**:
  - Slider de quantidade adicionado
  - Mantém lógica de 3+ números do quadrante frio
  - Feedback melhorado

- **AutoML (PyCaret)**:
  - Slider de quantidade (1-10)
  - Slider de peso para números previsíveis
  - Preview antes de adicionar (planejado)

- **Probabilidades (Random Forest)**:
  - Slider de quantidade (1-10)
  - Slider de peso para números prováveis
  - Geração mais inteligente

- **Clusters e Sequências**:
  - Sliders de quantidade padronizados
  - Interface consistente com outras estratégias

### 🐛 Corrigido
- **Erro de Sintaxe (linha 2417)**:
  - Removido bloco `else` duplicado
  - Corrigido código órfão de `st.error`
  - App agora compila sem erros

- **Estrutura de Dados Inconsistente**:
  - Todas gerações agora usam estrutura padrão
  - Chave correta: `'cartoes_selecionados'` (não `'meus_cartoes'`)
  - Campo `'concurso_alvo'` sempre presente

- **Session State**:
  - Inicialização verificada antes de uso
  - Evita erros de chave inexistente
  - Gerenciamento thread-safe

- **Duplicatas**:
  - Sistema robusto de detecção
  - Aviso claro ao usuário
  - Previne adição acidental

- **Warnings do PyCaret/LightGBM**:
  - Supressão global de warnings
  - Variáveis de ambiente configuradas
  - Console mais limpo

- **Deprecation Warnings do Streamlit**:
  - Substituído `use_container_width=True` por `width='stretch'`
  - Código atualizado para versões recentes

### 🔄 Refatorado
- **Código Modularizado**:
  - Funções extraídas para `megasena_utils.py`
  - Redução de duplicação de código
  - Mais fácil manter e atualizar

- **Funções de Geração**:
  - `gerar_cartao_aleatorio()`: Geração base com priorização
  - `gerar_multiplos_cartoes()`: Geração em lote
  - Parâmetros consistentes e documentados

- **Funções de UI**:
  - `exibir_cartoes_com_selecao()`: Display padronizado
  - `formatar_dezenas_com_destaque()`: Formatação com emojis
  - `criar_slider_quantidade()`: Slider padrão
  - `criar_slider_peso()`: Slider de peso

- **Funções de Gerenciamento**:
  - `adicionar_cartao_a_lista()`: Adicionar com validação
  - `cartao_existe_na_lista()`: Verificação de duplicata
  - `validar_cartao()`: Validação de estrutura

### 📊 Estatísticas da Versão 2.0.0
- **Linhas de Código**: ~4500 (app) + ~400 (utils)
- **Funções Reutilizáveis**: 15+
- **Estratégias Suportadas**: 10+
- **Teste de Qualidade**: ✅ Compilação sem erros

### 🎯 Próximas Versões (Planejado)

#### [2.1.0] - Planejado
- [ ] Preview em AutoML individual
- [ ] Preview em Probabilidades
- [ ] Preview em Clusters e Sequências
- [ ] Estatísticas dos cartões gerados
- [ ] Comparação entre estratégias

#### [2.2.0] - Planejado
- [ ] Exportação de cartões para CSV/PDF
- [ ] Histórico de cartões jogados
- [ ] Verificação de acertos
- [ ] Dashboard de performance

#### [3.0.0] - Planejado
- [ ] API REST para geração remota
- [ ] Modo escuro
- [ ] Temas personalizáveis
- [ ] Multi-idioma (EN/ES)

---

## [1.0.0] - 2025-12-01

### 🎉 Adicionado
- Release inicial do sistema
- Carregamento de dados da API da Caixa
- Análises estatísticas básicas:
  - Frequências gerais
  - Números quentes e frios
  - Pares e ímpares
  - Distribuição por dezena
  
- Análises avançadas:
  - Inversões temporais
  - Candidatos ouro
  - Mapa de quadrantes
  - Lei da soma

- Machine Learning:
  - AutoML com PyCaret
  - Random Forest para probabilidades
  - K-Means clustering
  - Análise de sequências

- Geração de cartões:
  - Múltiplas estratégias
  - Validação de duplicatas
  - Limite de 20 cartões

- Sistema de impressão:
  - Seleção de cartões
  - Preview de impressão
  - Formatação para papel

### 🐛 Corrigido
- Performance de carregamento inicial
- Erros de importação de bibliotecas
- Problemas de cache do Streamlit

---

## Formato do Changelog

### Tipos de Mudanças
- `🎉 Adicionado` para novas funcionalidades
- `🔧 Modificado` para mudanças em funcionalidades existentes
- `🗑️ Depreciado` para funcionalidades que serão removidas
- `🐛 Corrigido` para correção de bugs
- `🔒 Segurança` para correções de vulnerabilidades
- `🔄 Refatorado` para mudanças de código sem alterar funcionalidade
- `📊 Performance` para melhorias de desempenho

### Links
- [2.0.0]: https://github.com/seu-usuario/megasena-analise/releases/tag/v2.0.0
- [1.0.0]: https://github.com/seu-usuario/megasena-analise/releases/tag/v1.0.0
