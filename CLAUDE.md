# Mega Sena Analyzer

Aplicação Streamlit para acompanhar e analisar estratégias de apostas na Mega-Sena.
Deploy no Streamlit Cloud; automação via GitHub Actions.

## Como rodar

```bash
streamlit run megasena_app.py
```

## Estrutura de páginas (menu lateral)

| Item de menu | Arquivo | Finalidade |
|---|---|---|
| 🤖 Piloto Automático | `pagina_piloto_automatico.py` | Confere resultado, gera cartões e salva automaticamente |
| 📋 Conferência Semanal | `pagina_simulacao.py` → `pagina_conferencia()` | Histórico de conferências + conferir concurso + ranking |
| 🏆 Ensemble Top 10 | `pagina_ensemble_14.py` | Gera jogos com ensemble de 14 números |
| ✅ Verificar Resultados | `pagina_verificar_resultados.py` | Gerenciar cartões salvos e verificar acertos |
| 🏆 Resultados Validação | `pagina_validacao_visual.py` | Visualiza backtesting salvo — guia a direção das estratégias |
| 🧪 Validacao Ensemble | `pagina_validacao_ensemble.py` | Testa variações do ensemble |
| 📊 Backtesting Estatístico | `pagina_backtesting.py` | Testa estratégias em N concursos históricos sem data leakage |
| 🔬 Simulador Combinações | `pagina_simulador_combinacoes.py` | Analisa custo/cobertura por tamanho de cartão |
| 🎲 Simulação de Jogos | `pagina_simulacao.py` → `pagina_simulacao()` | Gera jogos para testar metodologias — **não é uso semanal** |
| 🔄 Análise Escada | `pagina_escada_temporal.py` | Análise de inversões da escada temporal |
| 🧬 Análise de Sequências | `pagina_analise_sequencias.py` | Clusters de co-ocorrência |
| 📊 Relatório Geral | `pagina_relatorio_geral.py` | Resumo geral dos cartões salvos |
| Estratégias 01–17 | `pagina_analise_estrategia.py` | Análise individual de cada estratégia |
| 🤖 AutoML PyCaret | `pagina_automl.py` | Modelo de ML para seleção de números |
| 🗄️ Admin Banco | `pagina_admin_banco.py` | Gerenciar SQLite/JSON |

## Módulos (`modules/`)

| Arquivo | Responsabilidade |
|---|---|
| `data_manager.py` | Carregar/salvar cartões (JSON↔SQLite), buscar resultados da API |
| `game_generator.py` | `gerar_jogo()` e `expandir_jogo()` — todas as estratégias |
| `statistics.py` | Cálculo de estatísticas, escada temporal, análises |
| `auth.py` | Sessão sem login obrigatório |
| `temas.py` | Seletor de tema visual |
| `notificacoes.py` | Envio de notificações WhatsApp |

## Constantes compartilhadas (`helpers.py`)

- `CUSTOS_CARTAO` — preços oficiais CEF por qtd de números (6–20)
- `FILTROS_JOGO` — soma 140–210, 2–4 pares, amplitude ≥ 30
- `JANELAS_ANALISE` — janelas padrão (recente=50, momentum=20/100, etc.)
- `VERSOES_ESTRATEGIAS` — versão de cada estratégia; bumpar ao alterar lógica
- `versao_estrategia(key)` — retorna versão de uma estratégia

## Persistência de dados

| Arquivo | Conteúdo |
|---|---|
| `meus_cartoes.json` | Todos os cartões salvos (jogados + verificados) |
| `historico_analises.json` | Histórico arquivado de conferências passadas |
| `data/megasena_historico.csv` | Histórico de sorteios da Mega-Sena |
| `piloto_config.json` | Configuração do piloto automático (gerado por CI) |

**Streamlit Cloud não persiste SQLite entre deploys.** Por isso, na inicialização do app `dm.sincronizar_json_para_db()` recria o banco a partir do JSON. Toda escrita vai para o JSON primeiro.

## Automação (GitHub Actions)

`.github/workflows/conferir_megasena.yml` roda terça, quinta e sábado às 21:30, 22:30 e 23:30 BRT:
1. Executa `scripts/conferir_e_notificar.py`
2. Commita `meus_cartoes.json` e `historico_analises.json` de volta no repo
3. Envia notificação WhatsApp via secrets `WHATSAPP_TELEFONE` / `WHATSAPP_APIKEY`

## Estratégias disponíveis

`escada`, `atrasados`, `quentes`, `equilibrado`, `misto`, `consenso`, `aleatorio_smart`, `sequencias`, `wheel`, `ensemble`, `candidatos_ouro`, `momentum`, `vizinhanca`, `frequencia_desvio`, `pares_frequentes`, `ciclos`, `atraso_recente`

Todas implementadas em `modules/game_generator.py`. Para adicionar uma nova estratégia:
1. Implementar em `game_generator.py`
2. Adicionar em `VERSOES_ESTRATEGIAS` no `helpers.py`
3. Adicionar em `TODAS_ESTRATEGIAS` no `pagina_simulacao.py`
4. Adicionar `elif` no dispatcher de `megasena_app.py`

## Decisões de design importantes

- **Separação Conferência vs Simulação**: `pagina_conferencia()` é o uso semanal (histórico sempre visível no topo). `pagina_simulacao()` é para testes de metodologia em concursos passados — fica embaixo no menu.
- **Validação guia a direção**: As páginas de Backtesting e Resultados Validação ficam no topo da seção ANÁLISE pois são o critério de decisão sobre qual estratégia seguir.
- **Histórico de conferências**: O seletor de concurso na Conferência Semanal mostra **todos** os concursos (verificados ✅ e pendentes ⏳), não só pendentes.
- **Tamanho ideal do ensemble**: Estudo indicou tamanho 10–11 como ótimo (ver memory). Ainda não implementado em `gerar_jogo_ensemble`.
