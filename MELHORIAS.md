# Plano de Melhorias - Mega Sena Analyzer

**Data:** 2026-04-11
**Total:** 22 melhorias organizadas em 4 fases

---

## Fase 1 - Correções Críticas nas Estratégias (Impacto Alto)

### 1.1 Corrigir estratégia `escada`
- **Problema:** A implementação atual em `game_generator.py:76` faz `contagem_total.sort_values().head(15)` — idêntico à estratégia `atrasados`. Não usa as inversões da escada temporal.
- **Solução:** Usar `calcular_escada_temporal()` para obter inversões reais (números esquentando) como pool de candidatos.
- **Evidência:** `escada` tem média 0.55 acertos (a pior) vs `equilibrado` com 1.45 em cartões de 14 números.

### 1.2 Incluir estratégia "Análise de Sequências" no piloto automático
- **Problema:** A estratégia mais sofisticada (clusters + vizinhança + filtros de soma/amplitude) só existe na página Streamlit, não no `TODAS_ESTRATEGIAS` do gerador automático.
- **Solução:** Adicionar ao `conferir_e_notificar.py` e `pagina_piloto_automatico.py`.
- **Evidência:** Média 1.28 acertos — a mais alta do dataset geral.

### 1.3 Melhorar expansão 6→14 números
- **Problema:** `_expandir_jogo()` sorteia os 8 extras com `random.shuffle(candidatos)` — dilui a lógica da estratégia base.
- **Solução:** Expandir mantendo a coerência:
  - `equilibrado`: manter proporção par/ímpar (7+7)
  - `quentes`: extras também dos quentes
  - `escada`: extras das inversões
  - Todos: aplicar filtro de soma proporcional ao qtd_numeros

### 1.4 Padronizar `qtd_numeros` para comparação justa
- **Problema:** Cartões gerados com 6, 10, 11, 12, 14 números — impossível comparar estratégias.
- **Solução:** Fixar `qtd_numeros` no `piloto_config.json` e garantir que o GitHub Actions sempre use o mesmo valor.

---

## Fase 2 - Filtros Universais (Impacto Médio-Alto)

### 2.1 Filtro de soma gaussiana em todas as estratégias
- **Problema:** Apenas `aleatorio_smart` e `sequências` validam a soma. Outras estratégias podem gerar jogos com soma fora da faixa estatística.
- **Solução:** Toda geração de jogo passa por validação de soma. Se falhar, reSorteia (até N tentativas).
- **Base matemática:** Teorema do Limite Central — somas fora de [p10, p90] são sub-representadas.

### 2.2 Filtro de paridade em todas as estratégias
- **Problema:** Exceto `equilibrado` e `aleatorio_smart`, nenhuma estratégia garante distribuição par/ímpar.
- **Solução:** Rejeitar jogos com < 2 ou > 4 pares (para 6 números). Para 14 números: 5-9 pares.
- **Base matemática:** Distribuição binomial — extremos têm probabilidade muito baixa.

### 2.3 Filtro de amplitude mínima
- **Problema:** Nenhuma estratégia valida amplitude (max - min).
- **Solução:** Amplitude mínima de 30 para 6 números, escalando para jogos maiores.
- **Base matemática:** Combinações concentradas em faixa estreita são raras historicamente.

### 2.4 Estratégia wheel/cobertura garantida
- **Problema:** Nenhuma estratégia atual oferece garantia combinatória.
- **Solução:** Implementar sistema de rodízio que garanta: "se K dos 6 sorteados estiverem no pool de N, pelo menos 1 cartão acerta quadra".
- **Valor:** Única abordagem com garantia matemática (não probabilística).

---

## Fase 3 - Análise e Inteligência (Impacto Alto para decisão)

### 3.1 Backtesting histórico (500 concursos)
- **Problema:** Apenas 14 concursos verificados — dados insuficientes para conclusão.
- **Solução:** Script que retroativamente aplica cada estratégia nos últimos 500 concursos e compara com resultado real.
- **Valor:** Resposta imediata sem esperar meses.

### 3.2 Teste estatístico no ranking (IC + significância)
- **Problema:** O ranking atual mostra média bruta sem intervalo de confiança.
- **Solução:** Exibir IC95% e p-valor de comparação entre pares de estratégias.
- **Valor:** Saber quando uma diferença é real vs. sorte.

### 3.3 Redesign do AutoML
- **Problema:** Features atuais (atraso, contagem_10) são baseadas na falácia do jogador. Média 0.80 (abaixo de aleatório).
- **Solução:** Treinar modelo sobre propriedades da COMBINAÇÃO: soma, paridade, amplitude, distribuição por quadrante, consecutivos.
- **Abordagem:** Classificação binária "esta combinação acerta ≥ 4?" em vez de "este número vai sair?".

---

## Fase 4 - Infraestrutura e Código

### 4.1 Eliminar `dia_de_jogo.yml`
- **Problema:** Dois workflows fazendo a mesma coisa em horários próximos — risco de race condition e commits conflitantes.
- **Solução:** Consolidar toda a lógica no `conferir_megasena.yml` (que já tem `git pull --rebase`).

### 4.2 Arquivar cartões verificados
- **Problema:** `meus_cartoes.json` tem 1549 cartões (850KB) e cresce ~140 por concurso. Git guarda todas as versões.
- **Solução:** Após conferência, mover verificados para `data/cartoes_YYYY.json`. Manter em `meus_cartoes.json` apenas pendentes.

### 4.3 Corrigir bug cartões sem `concurso_alvo`
- **Problema:** TypeError ao ordenar concursos pendentes (NoneType vs int).
- **Solução:** Filtrar cartões com `concurso_alvo is None` na carga.

### 4.4 Extrair função `_parse_dezenas()`
- **Problema:** Lógica de parsing duplicada em `buscar_ultimo_resultado()`, `buscar_resultado_concurso()` e `data_manager.py`.
- **Solução:** Criar função utilitária única.

### 4.5 Remover import `Counter` não usado
- **Arquivo:** `scripts/conferir_e_notificar.py`

### 4.6 Não commitar `piloto_config.json`
- **Problema:** `conferir_megasena.yml` commita o arquivo, mas `dia_de_jogo.yml` o sobrescreve. Config runtime não deveria estar no git.
- **Solução:** Usar variáveis de ambiente; adicionar ao `.gitignore` (ou manter apenas defaults).

### 4.7 Retry no WhatsApp
- **Problema:** Se CallMeBot falhar (timeout/instabilidade), notificação perdida.
- **Solução:** 1 retry após 5 segundos em caso de falha.

### 4.8 Usar dados locais para gerar cartões
- **Problema:** `gerar_cartoes_proximo_concurso()` faz GET de TODA a API para calcular estatísticas.
- **Solução:** Usar dados em `data/` como cache primário, API só para atualizar último concurso.

### 4.9 Padronizar Python 3.12
- **Problema:** `dia_de_jogo.yml` usa 3.11, `conferir_megasena.yml` usa 3.12.
- **Solução:** Ambos em 3.12 (ou eliminar `dia_de_jogo.yml` — item 4.1).

### 4.10 Unificar `CUSTOS_CARTAO`
- **Problema:** Tabela duplicada em 3 arquivos com valores diferentes (R$5.00 vs R$6.00 para 6 números).
- **Solução:** Manter apenas em `modules/notificacoes.py` (ou criar `modules/constants.py`) e importar.

### 4.11 Git pull --rebase no `dia_de_jogo.yml`
- **Problema:** Sem pull antes do push — pode falhar se o outro workflow commitou primeiro.
- **Solução:** Já implementado no `conferir_megasena.yml`; replicar ou eliminar workflow (item 4.1).

---

## Ordem de implementação recomendada

```
Fase 1 (impacto imediato na qualidade dos cartões):
  1.1 → 1.3 → 1.2 → 1.4

Fase 2 (filtros que melhoram TODAS as estratégias):
  2.1 → 2.2 → 2.3 → 2.4

Fase 3 (inteligência para tomar decisão):
  3.1 → 3.2 → 3.3

Fase 4 (saúde do projeto):
  4.1 → 4.2 → 4.3 → 4.10 → 4.4 → 4.7 → 4.8 → resto
```

---

## Métricas de sucesso

| Métrica | Antes | Meta |
|---|---|---|
| Média acertos (14 nums, melhor estratégia) | 1.45 | > 1.8 |
| Estratégia `escada` | 0.55 | > 1.0 |
| Concursos para conclusão estatística | 30+ (estimado) | 20 (com backtesting) |
| Tamanho `meus_cartoes.json` | 850KB crescente | < 200KB estável |
| Workflows conflitantes | 2 | 1 |
