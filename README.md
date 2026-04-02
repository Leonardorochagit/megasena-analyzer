# 🎰 Mega Sena Analyzer - Análise e Geração Inteligente de Cartões

[![Versão](https://img.shields.io/badge/vers%C3%A3o-3.4.0-blue.svg)](https://github.com/Leonardorochagit/megasena-analyzer)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-orange.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/deploy-Streamlit%20Cloud-FF4B4B.svg)](https://megasena-analyzer.streamlit.app)

## 🌐 Acesso Online

**O app está rodando em produção no Streamlit Cloud:**

👉 **https://megasena-analyzer.streamlit.app**

Não precisa instalar nada — basta acessar pelo navegador.

## 📋 Índice

- [Sobre](#sobre)
- [Acesso Online](#-acesso-online)
- [Funcionalidades](#funcionalidades)
- [Piloto Automático](#-piloto-automático)
- [Automação - Dia de Jogo](#-automação---dia-de-jogo)
- [Estratégias Disponíveis](#estratégias-disponíveis)
- [Instalação Local](#-instalação-local)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Licença](#licença)

## 🎯 Sobre

Sistema completo de análise estatística e geração inteligente de cartões para Mega Sena. Utiliza múltiplas estratégias de análise (Escada Temporal, Frequências, Consenso, Machine Learning) para gerar cartões de **6 a 20 números** e acompanhar qual metodologia tem dado mais resultados ao longo do tempo.

### 💡 Objetivo

A ideia central é **simular cartões com diversas análises**, gerar sempre para o **próximo concurso**, e depois de cada sorteio **validar qual metodologia acertou mais**. Assim sabemos qual estratégia seguir para jogar oficialmente.

### ⚠️ Aviso Importante

Este sistema é uma ferramenta de **análise estatística e educacional**. Não há garantia de acertos, pois a Mega Sena é um jogo aleatório. Use com responsabilidade.

## ✨ Funcionalidades

### 🎯 Simulação & Conferência (Hub Central)
- **Geração automática** de cartões em TODAS as estratégias de uma vez
- **Cartões de 6 a 20 números** (mais números = mais combinações = mais chance)
- **Preços atualizados** da Mega Sena (base R$ 6,00)
- Conferência automática de resultados via API da Caixa
- **Ranking de estratégias** — descubra qual metodologia acerta mais

### 🤖 Piloto Automático (Dashboard)
- **Painel em tempo real** com status de todos os cartões e estratégias
- **Auto-refresh** — atualiza a página automaticamente (intervalo configurável)
- **Auto-conferir** — confere resultados pendentes automaticamente
- **Auto-gerar** — gera novos cartões para o próximo concurso
- **Dashboard** com resumo: total de cartões, verificados, pendentes, acertos
- **Configurações persistentes** — preferências salvas entre sessões
- **Log de ações** — histórico de tudo que o piloto executou

### 🤖 Automação - Dia de Jogo (CLI + GitHub Actions)
- **Script automático** que confere pendentes + gera lote para o próximo concurso
- Roda via linha de comando, ideal para agendar (cron/task scheduler)
- **GitHub Actions** — execução automática nos dias de sorteio (Ter/Qui/Sáb)
- Ranking consolidado de performance de todas as estratégias

### 📊 8 Estratégias de Análise
| Estratégia | Descrição |
|---|---|
| 🔄 Escada Temporal | Detecta inversões de tendência (números frios ficando quentes) |
| ⏰ Números Atrasados | Prioriza números que não saem há mais tempo (frequência geral) |
| 🔥 Números Quentes | Foca nos mais frequentes recentemente |
| ⏳ Atraso Recente | Números que estão há mais concursos seguidos sem sair |
| ⚖️ Equilibrado | Balanceia pares/ímpares |
| 🎨 Misto | Combina atrasados + quentes + atraso recente |
| 🤝 Consenso | Números que aparecem em 2+ estratégias |
| 🎲 Aleatório Inteligente | Aleatório com filtros (soma, paridade) |

### 🤖 AutoML (PyCaret)
- Treina modelos de ML para os 60 números
- Score combinado: ML + frequência + atraso
- Geração otimizada para maximizar quadras (4+ acertos)

### 📈 Fluxo Recomendado
1. Ative o **Piloto Automático** para acompanhamento contínuo
2. Ou acesse **Simulação & Conferência** para controle manual
3. Escolha a quantidade de números (recomendado: **10 a 12**)
4. Gere uma simulação automática para o próximo concurso
5. Quando sair o resultado, **confira** na mesma página (ou deixe o Piloto conferir)
6. Veja no **Ranking** qual estratégia foi melhor
7. Repita e acompanhe a evolução!

## 🤖 Piloto Automático

O **Piloto Automático** é o painel de controle central do sistema. Com ele, você liga o "modo automático" e o app faz tudo sozinho:

### Como funciona
1. Acesse a primeira opção do menu: **🤖 Piloto Automático**
2. Ative o toggle **"Ativar Piloto Automático"**
3. Configure:
   - **Intervalo de atualização** (1 a 60 minutos)
   - **Números por cartão** (6 a 20)
   - **Cartões por estratégia** (1 a 20)
4. O piloto vai:
   - ✅ Conferir resultados de concursos já sorteados
   - ✅ Gerar novos cartões para o próximo concurso
   - ✅ Atualizar o dashboard em tempo real
   - ✅ Registrar tudo no log de ações

### Dashboard
- **Total de cartões** gerados
- **Verificados** vs **Pendentes**
- **Máximo de acertos** por estratégia
- **Status do sistema** (hora de consulta, próximo concurso, etc.)

> **Nota**: O auto-refresh funciona enquanto a página está aberta no navegador. Para automação em background (sem navegador), use o **GitHub Actions**.

## 🔧 Requisitos

- Python 3.8+
- Streamlit 1.28+
- Pandas, NumPy, Plotly, Scikit-learn, Requests
- PyCaret 3.0+ (opcional, para AutoML)

## 📥 Instalação Local

```bash
# Clone o repositório
git clone https://github.com/Leonardorochagit/megasena-analyzer.git
cd megasena-analyzer

# Crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instale as dependências
pip install -r requirements.txt

# Execute
streamlit run megasena_app.py
```

O app abrirá em `http://localhost:8501`

### 🤖 Automação via Linha de Comando

```bash
# Conferir resultados pendentes + gerar lote para o próximo concurso (10 números, 3 por estratégia)
python scripts/automacao_dia_jogo.py

# Customizar
python scripts/automacao_dia_jogo.py --qtd-numeros 12 --cartoes-por-estrategia 5

# Apenas conferir resultados
python scripts/automacao_dia_jogo.py --apenas-conferir

# Apenas gerar novos cartões
python scripts/automacao_dia_jogo.py --apenas-gerar

# Forçar geração mesmo se já existirem cartões
python scripts/automacao_dia_jogo.py --forcar
```

## 🎮 Como Usar

### Via Web (Recomendado)
Acesse **https://megasena-analyzer.streamlit.app** e use diretamente no navegador.

### Via Interface Local
1. Execute `streamlit run megasena_app.py`
2. No menu lateral, escolha a página desejada
3. Em **Simulação & Conferência**, gere cartões para o próximo concurso
4. Após o sorteio, confira os resultados na mesma página
5. Acompanhe o ranking de estratégias

### Via Script de Automação
Execute `python scripts/automacao_dia_jogo.py` nos dias de sorteio (terça, quinta, sábado).
O script automaticamente:
- Confere resultados de concursos já sorteados
- Gera cartões para o próximo concurso
- Exibe ranking consolidado de estratégias

## 🎯 Estratégias Disponíveis

### 🔄 Inversões Temporais
Identifica números que estavam frios e começaram a sair mais recentemente.
- **Como funciona**: Compara tendência recente vs histórico
- **Ideal para**: Detectar mudanças de ciclo
- **Números destacados**: ⭐ Números em inversão

### 🏆 Candidatos Ouro
Números que são frios no geral mas quentes recentemente (dupla pressão).
- **Como funciona**: Cruzamento de análises de prazo
- **Ideal para**: Números com "pressão de saída"
- **Números destacados**: 🏆 Candidatos identificados

### 🗺️ Quadrantes
Divide o volante em 4 regiões e identifica a mais fria.
- **Como funciona**: Heatmap de frequência por região
- **Ideal para**: Distribuição espacial balanceada
- **Números destacados**: 🔵 Números do quadrante frio

### 🤖 AutoML (PyCaret)
Testa automaticamente 10+ algoritmos de ML.
- **Como funciona**: Treinamento e comparação de modelos
- **Ideal para**: Análise preditiva avançada
- **Modelos testados**: Random Forest, XGBoost, CatBoost, etc.

### 📊 Probabilidades (Random Forest)
Calcula probabilidade individual de cada número.
- **Como funciona**: Features temporais + ensemble learning
- **Ideal para**: Previsão baseada em padrões
- **Controle de peso**: Ajuste a influência dos top números

### 🔢 Clusters (K-Means)
Agrupa números com comportamento similar.
- **Como funciona**: Clustering baseado em frequência
- **Ideal para**: Encontrar grupos consistentes
- **Configurável**: Escolha número de clusters

### 🔗 Sequências
Analisa padrões de números consecutivos.
- **Como funciona**: Identifica tendência de sequências
- **Ideal para**: Incluir ou evitar números seguidos
- **Configurável**: Prioriza ou evita sequências

## 📁 Estrutura do Projeto

```
megasena-analyzer/
├── megasena_app.py               # 🎯 App principal Streamlit
├── pagina_piloto_automatico.py   # 🤖 Piloto Automático (dashboard + auto-refresh)
├── pagina_simulacao.py           # 🎲 Simulação & Conferência (hub central)
├── pagina_escada_temporal.py     # 🔄 Análise Escada Temporal
├── pagina_analise_estrategia.py  # 📊 Template genérico de estratégias
├── pagina_analise_sequencias.py  # 🧬 Análise de Sequências
├── pagina_automl.py              # 🤖 AutoML com PyCaret
├── pagina_relatorio_geral.py     # 📊 Relatório consolidado
├── pagina_verificar_resultados.py# 🎯 Verificar resultados
├── meus_cartoes.json             # 💾 Cartões salvos
├── historico_analises.json       # 📚 Histórico de conferências
├── piloto_config.json            # ⚙️ Config do Piloto Automático
├── requirements.txt              # Dependências
│
├── modules/                      # Lógica de negócio
│   ├── data_manager.py           # Gerenciamento de dados e API
│   ├── game_generator.py         # Geração de jogos
│   ├── statistics.py             # Estatísticas e cálculos
│   ├── ui_components.py          # Componentes de interface
│   ├── visualizations.py         # Gráficos e visualizações
│   └── auth.py                   # Autenticação
│
├── scripts/                      # Scripts de automação
│   └── automacao_dia_jogo.py     # 🤖 Automação dia de sorteio
│
├── .github/workflows/            # CI/CD
│   └── dia_de_jogo.yml           # ⏰ GitHub Actions (Ter/Qui/Sáb)
│
├── data/                         # Dados e cache
└── docs/                         # Documentação adicional
```

## 💰 Tabela de Preços (Mega Sena - 2026)

| Números | Combinações | Custo |
|---------|-------------|-------|
| 6 | 1 | R$ 6,00 |
| 7 | 7 | R$ 42,00 |
| 8 | 28 | R$ 168,00 |
| 9 | 84 | R$ 504,00 |
| 10 | 210 | R$ 1.260,00 |
| 11 | 462 | R$ 2.772,00 |
| 12 | 924 | R$ 5.544,00 |
| 13 | 1.716 | R$ 10.296,00 |
| 14 | 3.003 | R$ 18.018,00 |
| 15 | 5.005 | R$ 30.030,00 |
| 16 | 8.008 | R$ 48.048,00 |
| 17 | 12.376 | R$ 74.256,00 |
| 18 | 18.564 | R$ 111.384,00 |
| 19 | 27.132 | R$ 162.792,00 |
| 20 | 38.760 | R$ 232.560,00 |

## 🤖 Automação via GitHub Actions

O projeto inclui um workflow que roda automaticamente nos dias de sorteio:

- **Quando**: Terça, Quinta e Sábado à noite (após sorteio das 20h)
- **O que faz**: Confere resultados pendentes → Gera cartões para o próximo concurso → Commit automático
- **Disparo manual**: Também pode ser acionado manualmente pela aba Actions do GitHub

Para funcionar, basta ter o repositório no GitHub — o workflow já está configurado em `.github/workflows/dia_de_jogo.yml`.

## 🔄 Versionamento

Ver [CHANGELOG.md](CHANGELOG.md) para histórico completo de versões.

### Versão 3.4.0 (Atual)
- **Menu reorganizado** — todas as 10 estratégias visíveis no menu principal
- **Atraso Recente** — nova estratégia acessível pela UI
- **Relatório de consistência** — ranking por acertos absolutos em vez de percentuais
- **Duques e Ternas** — contagem de 2 e 3 acertos em todos os relatórios
- **Recomendação para bolão** — sugestão de estratégia por tamanho de aposta
- **Evolução temporal** — gráfico de desempenho por concurso

### Versão 3.3.0
- **Piloto Automático** — dashboard com auto-refresh, auto-conferir, auto-gerar
- Configurações persistentes (salvas entre sessões)
- Log de ações do piloto
- Limites unificados (até 20 números, até 20 cartões por estratégia)
- Análise de sequências expandida (6-20 números)

### Versão 3.2.0
- Cartões de 6 a 20 números
- Preços atualizados para R$ 6,00 (base)
- Script de automação CLI (`scripts/automacao_dia_jogo.py`)
- GitHub Actions para execução automática nos dias de sorteio
- Deploy no Streamlit Cloud

### Versão 3.1.0
- Hub de Simulação & Conferência
- 7 estratégias de análise integradas
- Ranking de performance por estratégia
- Arquitetura modular

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

**Leonardo** — 2025/2026

## 🙏 Agradecimentos

- [API da Caixa Econômica Federal](https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena)
- [Streamlit](https://streamlit.io) — framework web
- [Scikit-learn](https://scikit-learn.org) / [PyCaret](https://pycaret.org) — Machine Learning

---

**⚠️ Lembre-se**: Este é um projeto educacional. Jogue com responsabilidade! 🎲
