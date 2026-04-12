# Análise Técnica de Metodologias e Melhorias — Mega Sena Analyzer

Documento de referência técnica para avaliação, priorização e rastreamento de
implementação das técnicas e metodologias do sistema.

---

## 1. Hierarquia de valor das técnicas

| Técnica | Valor | Motivo | Status |
|---|---|---|---|
| Filtro de soma (P10–P90 histórico) | **Alto** | Base matemática — TLC, distribuição empírica | ✅ Implementado `v1.0` |
| Filtro de paridade (2–4 pares) | **Alto** | Distribuição binomial conhecida | ✅ Implementado `v1.0` |
| Filtro de amplitude (≥30) | **Alto** | Elimina combinações geometricamente improváveis | ✅ Implementado `v1.0` |
| Filtro de consecutivos (≤2 seguidos) | **Alto** | Sequências longas são raras historicamente | ✅ Implementado `v1.0` |
| Teste Qui-Quadrado (Markov) | **Alto** | Único que detecta viés real nos sorteios | ✅ Implementado `v1.0` |
| Teste Binomial por par | **Alto** | Detecta pares sobre/sub-representados com p-valor por par | ✅ Implementado `v1.1` |
| Backtesting com IC 95% | **Alto** | Valida se estratégia tem edge sobre o aleatório | ✅ Implementado `v1.0` |
| Calibração de probabilidade (RF) | **Alto** | RF não calibrado comprime probabilidades — sem sentido probabilístico real | ✅ Implementado `v2.0` |
| Persistência de modelos (joblib) | **Médio-Alto** | Evita re-treino de 60 modelos a cada chamada | ✅ Implementado `v2.0` |
| Features de combinação no ML | **Médio-Alto** | Features de número isolado têm baixo poder preditivo | ✅ Implementado `v1.1` |
| Balanceamento por clusters/quadrantes | **Médio** | Boa cobertura espacial — premissa fraca mas defensável | ✅ Implementado `v1.0` |
| Wheel / Cobertura combinatória | **Médio** | Maximiza cobertura de subconjuntos dentro de um pool | ✅ Implementado `v1.0` |
| Vizinhança N±1 | **Baixo como gerador / Médio como diagnóstico** | Vizinhança numérica ≠ vizinhança física nas bolinhas | ✅ Implementado `v1.0` |
| Números frios/atrasados | **Baixo** | Falácia do jogador — sem base matemática | ✅ Implementado `v1.0` (mantido como baseline) |
| Números quentes | **Baixo** | Falácia do jogador — sem base matemática | ✅ Implementado `v1.0` (mantido como baseline) |
| AutoML com features de atraso apenas | **Baixo** | Aprende frequência histórica, não tendência | Substituído por `v2.0` com features de combinação |

---

## 2. Análise Detalhada das Metodologias

### 2.1 Cadeia de Markov + Teste Qui-Quadrado

**O que faz:** Monta uma matriz 60×60 de transição: `P(j aparece no sorteio T+1 | i apareceu no T)`.
Testa independência com qui-quadrado.

**Implementação atual:** `pagina_analise_sequencias.py → _calcular_matriz_transicao()` — versão `1.0`

**O que é valioso:**
O teste qui-quadrado é a única análise do projeto que pode revelar se há **dependência serial real** nos sorteios. Se p-valor < 0.05, existe evidência estatística de que o sorteio não é completamente independente — o que indicaria viés mecânico nas urnas.

**Exibição:** Resultado exibido com `st.error` (se dependente) ou `st.success` (se independente) no topo da aba — destaque adequado.

**Limitação conhecida:** A Cadeia de Markov implementada é de **primeira ordem** (T→T+1). Poderia ser estendida para ordem 2 (T-1, T → T+1) como próximo passo.

---

### 2.2 K-Means sobre Matriz de Co-ocorrência

**O que faz:** Constrói matriz 60×60 de co-ocorrências (quantas vezes `i` e `j` saíram juntos), depois agrupa com K-Means em 4 clusters.

**Implementação atual:** `pagina_analise_sequencias.py → _analise_clusters()` e `game_generator.py → _gerar_jogo_sequencias()` — versão `1.0`

**O que tem valor real:** O gerador que sorteia `qtd_numeros // 4` dezenas de cada cluster. Isso garante **cobertura espacial no volante** — não porque prevê padrões, mas porque **maximiza diversificação**.

**Limitação conhecida:** `StandardScaler` é aplicado antes do KMeans (correto), mas o número de clusters (4) é arbitrário — sem análise de silhouette/elbow para validar.

**Próximo passo sugerido:** Usar silhouette score para escolher K ótimo entre 3 e 8.

---

### 2.3 Vizinhança N±1

**O que faz:** Calcula com que frequência, quando o número N saiu no sorteio T, seus vizinhos (N-1 ou N+1) saíram no sorteio T+1.

**Implementação atual:** `pagina_analise_sequencias.py → _analise_vizinhanca()` — versão `1.0`

**Avaliação:** Outro teste de dependência serial. Vizinhança numérica **não tem relação com vizinhança física nas bolinhas** — o número 14 não está "perto" do 13 dentro da máquina. Valor como **diagnóstico** (mede taxa observada vs baseline ~10%); valor reduzido como **gerador**.

**Status atual:** Usado tanto como diagnóstico (aba Vizinhança) quanto como input de geração (`_gerar_jogo_sequencias`). Mantido pois é defensável como diversificação.

---

### 2.4 Filtros Geométricos do Gerador Avançado

Implementados em `game_generator.py → _aplicar_filtros_basicos()` e `pagina_analise_sequencias.py → _gerar_cartoes()` — versão `1.0`.

| Filtro | Base matemática | Status |
|---|---|---|
| Soma dentro de P10–P90 histórico | TLC — elimina combinações improváveis | ✅ |
| Amplitude mínima ≥ 30 | Combinações concentradas são raras | ✅ |
| Máximo de consecutivos ≤ 2 | Sequências (1,2,3) têm baixa frequência histórica | ✅ |
| Paridade 2–4 pares | Distribuição binomial — extremos são raros | ✅ |

---

### 2.5 Teste Binomial por Par

**O que faz:** Para cada um dos 1770 pares possíveis, testa se a frequência observada desvia da esperada sob independência usando o **teste binomial exato**.

- Frequência esperada: `C(6,2) / C(60,2) × N ≈ 0.848%` por sorteio
- p-valor por par via `scipy.stats.binom_test`

**Implementação atual:** `pagina_analise_sequencias.py → _analise_pares_binomial()` — versão `1.1`

**Aviso importante:** Com 1770 testes simultâneos, o **problema de comparações múltiplas** (Family-Wise Error Rate) é significativo. Um α = 0.05 implica ~88 falsos positivos esperados mesmo se os dados forem completamente aleatórios. Interpretar com cautela — pares com p < 0.001 são mais confiáveis.

**Próximo passo sugerido:** Aplicar correção de Bonferroni (`α / 1770 ≈ 0.000028`) ou correção de Benjamini-Hochberg (FDR) para reduzir falsos positivos.

---

### 2.6 Backtesting Estatístico com IC 95%

**O que faz:** Para cada concurso nos últimos N sorteios, gera cartões com cada estratégia usando **apenas dados anteriores** (sem data leakage) e conta acertos. Compara distribuições com IC 95% e teste de Mann-Whitney.

**Implementação atual:** `pagina_backtesting.py` — versão `1.0`

**Como interpretar:**
- Se IC de duas estratégias se **sobrepõem** → estatisticamente equivalentes → nenhuma tem edge
- Se IC **não se sobrepõem** → pode haver diferença real — confirmar com Mann-Whitney
- Mann-Whitney p < 0.05 → diferença significativa → uma estratégia tem edge

**O que esperar:** Com sorteios verdadeiramente aleatórios, todas as estratégias deverão convergir para ~0.6 acertos em média (= 6 × 6/60). Estratégias com média sistematicamente acima de 0.6 merecem investigação.

---

### 2.7 AutoML com Calibração e Features de Combinação

**Implementação atual:** `pagina_automl.py` — versão `2.0`

#### Evolução das features (`modules/statistics.py → preparar_dados_pycaret`):

| Feature | v1.0 | v1.1 (atual) |
|---|---|---|
| `contagem_numero_10` | ✅ | ✅ |
| `atraso` | ✅ | ✅ |
| `soma_media` | ❌ | ✅ |
| `soma_std` | ❌ | ✅ |
| `pares_media` | ❌ | ✅ |
| `amplitude_media` | ❌ | ✅ |
| `amplitude_std` | ❌ | ✅ |
| `max_seq_media` | ❌ | ✅ |
| `quadrante` | ❌ | ✅ |

#### Melhorias no modelo (`pagina_automl.py`):

| Aspecto | v1.x (anterior) | v2.0 (atual) |
|---|---|---|
| Algoritmo | Decision Tree (PyCaret) ou RF básico | Random Forest scikit-learn direto |
| Balanceamento | Sem tratamento | `class_weight='balanced'` |
| Calibração | Nenhuma | `CalibratedClassifierCV(method='isotonic')` |
| Validação cruzada | `KFold` aleatório | `TimeSeriesSplit` (respeita ordem temporal) |
| Persistência | Re-treina a cada chamada | `joblib` em disco — cache por hash do dataset |
| PyCaret | Obrigatório | Opcional (fallback para sklearn direto) |

#### Limitações que permanecem:
- 60 modelos independentes — não captura correlação entre números
- Janela de features ainda pequena (10 concursos)
- Probabilidades calibradas mas não validadas em hold-out temporal explícito

---

### 2.8 Wheel / Cobertura Combinatória

**O que faz:** Dado um pool de N números candidatos, gera o menor conjunto de cartões que cobre todas as combinações de K números do pool (greedy covering design).

**Implementação atual:** `game_generator.py → gerar_wheel()` e `_gerar_jogo_wheel()` — versão `1.0`

**Valor real:** Para bolão, o wheel garante que se K números específicos do pool saírem, pelo menos um cartão os contém. Com pool de 18 e K=3 (cobertura de ternas), é uma estratégia matematicamente defensável para bolões.

---

## 3. Estratégias e Versões Atuais

Rastreado em `helpers.py → VERSOES_ESTRATEGIAS`.

| Estratégia | Versão | O que mudou |
|---|---|---|
| `escada` | `1.1` | Usa inversões reais da escada temporal (antes era fallback para atrasados) |
| `atrasados` | `1.0` | Top-20 menos frequentes historicamente |
| `quentes` | `1.0` | Top-20 mais frequentes recentes |
| `equilibrado` | `1.0` | 3 pares + 3 ímpares exatos |
| `misto` | `1.0` | 2 atrasados + 2 quentes + 2 atraso_recente |
| `consenso` | `1.0` | Interseção de 3 análises (≥2 votos) |
| `aleatorio_smart` | `1.0` | Aleatório com filtro soma (140–210) e paridade (2–4) |
| `ensemble` | `1.0` | Votação de 7 estratégias base |
| `sequencias` | `1.1` | KMeans 4 clusters + vizinhança N±1 + filtros geométricos |
| `wheel` | `1.0` | Greedy covering design K=3, pool 18 por consenso |
| `automl` | `2.0` | RF calibrado (isotônico) + `class_weight='balanced'` + cache joblib + features de combinação |
| `Manual` | `-` | Cartão manual do usuário |

---

## 4. O que ainda pode ser implementado (backlog)

### Prioridade Alta

| Item | Descrição | Complexidade |
|---|---|---|
| Correção de Bonferroni/BH no teste de pares | Reduz falsos positivos nos 1770 testes simultâneos | Baixa |
| Markov de ordem 2 | Testa dependência (T-1, T) → T+1 | Média |
| Silhouette score para K ótimo no KMeans | Validar se 4 clusters é o melhor K | Baixa |

### Prioridade Média

| Item | Descrição | Complexidade |
|---|---|---|
| Modelo joint (60 saídas simultâneas) | Em vez de 60 classificadores independentes, uma rede com 60 saídas e constraint soma=6 | Alta |
| Features de correlação entre pares | Usar co-ocorrências como features de ML | Média |
| Gatilho automático por prêmio > R$100M | Verificar valor acumulado via API da Caixa e notificar | Média |
| Análise de grafo de co-ocorrências | PageRank ou Node2Vec sobre grafo de pares | Alta |

### Prioridade Baixa

| Item | Descrição | Complexidade |
|---|---|---|
| LSTM/GRU sobre sequência histórica | Aprender padrões de série temporal entre sorteios | Alta |
| Criptografia da API key do WhatsApp | Hoje salva em texto plano no piloto_config.json | Baixa |
| Unificar score weights (1000/100/10 vs 10000/1000/100) | Inconsistência entre simulacao.py e piloto_automatico.py | Baixa |

---

## 5. Referências técnicas

- **TLC aplicado à soma de sorteios:** a soma de 6 uniformes em [1,60] converge para normal com μ ≈ 183.5, σ ≈ 28. Os filtros P10–P90 (≈143–223) correspondem a ≈±1.43σ.
- **Probabilidade de um par específico:** `C(6,2) / C(60,2) = 15/1770 ≈ 0.848%` por sorteio.
- **Baseline de acertos esperados:** `6 × 6/60 = 0.6` acertos por jogo de 6 números — qualquer estratégia com média consistentemente acima disso no backtesting merece investigação.
- **Falácia do jogador:** números frios/quentes não têm base matemática em sorteios independentes. Mantidos no sistema apenas como baseline comparativo.
- **Calibração isotônica vs Platt:** isotônica é não-paramétrica e mais flexível para Random Forest; Platt scaling pressupõe saída sigmoide (mais adequado para SVM).
