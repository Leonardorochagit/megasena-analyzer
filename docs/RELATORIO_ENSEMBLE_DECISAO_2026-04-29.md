# Relatorio Ensemble Decisao - 2026-04-29

## Objetivo

Melhorar o poder de decisao na hora de jogar, reduzindo a ilusao de muitos ternos gerados por cartoes repetidos e tornando o ensemble mais util para escolher nucleos de 9 a 13 numeros.

## Mudancas no codigo

- `modules/game_generator.py`
  - O ensemble passou a ranquear estrategias por score de decisao.
  - O score considera media, quadra+ por jogo, quadra+ por concurso, quina+ por concurso, melhor cartao por concurso, senas, quinas e quadras.
  - O score penaliza repeticao/concentracao usando intersecao media entre cartoes e frequencia maxima de dezenas.
  - O streak recente deixou de ser o unico criterio; agora remove apenas estrategias explicitamente frias.

- `scripts/conferir_e_notificar.py`
  - Geracao automatica passou para 15 numeros no experimento atual.
  - Lista automatica expandida para 17 estrategias.
  - Inclusao de filtro de diversidade para evitar cartoes muito parecidos.
  - Correcao da expansao de jogos quando o pool da estrategia era curto.

- `scripts/backtesting.py`
  - Backtest passou a medir intersecao media, intersecao maxima e concentracao por numero.
  - Lista padrao de estrategias foi ampliada com `atraso_recente`.
  - `wheel` foi mantida fora do padrao longo porque a rodada 400 x 10 estourou o tempo.

- `helpers.py`
  - Ensemble atualizado para versao 3.1.

## Teste longo principal

Configuracao:

- 400 concursos
- Concursos 2596 a 2995
- 16 estrategias
- 10 cartoes por estrategia
- 15 numeros por cartao
- 64.000 jogos simulados
- Seed 42

Benchmark aleatorio para 15 numeros:

- Media esperada: 1.500
- Terno+: 15.88%
- Quadra+: 2.98%

Totais do backtest:

| Premio | Total |
|---|---:|
| Senas | 7 |
| Quinas | 154 |
| Quadras | 1.774 |
| Ternos | 8.065 |
| Quadra ou mais | 1.935 |
| Quina ou mais | 161 |

Melhores leituras:

| Estrategia | Senas | Quinas | Quadras | Media | Quadra+ jogo | Quadra+ concurso | Intersecao |
|---|---:|---:|---:|---:|---:|---:|---:|
| aleatorio_smart | 0 | 13 | 115 | 1.5145 | 3.20% | 28.75% | 3.74 |
| atraso_recente | 1 | 9 | 111 | 1.5123 | 3.02% | 25.50% | 4.62 |
| sequencias | 0 | 14 | 129 | 1.5120 | 3.57% | 27.25% | 4.59 |
| ensemble antigo | 1 | 12 | 111 | 1.5048 | 3.10% | 26.50% | 3.96 |
| momentum | 2 | 11 | 116 | 1.4510 | 3.23% | 19.50% | 6.12 |
| consenso | 2 | 7 | 108 | 1.5005 | 2.93% | 16.25% | 7.47 |

Leitura: nenhuma estrategia venceu o aleatorio de forma estatisticamente forte na media, mas algumas estrategias mostraram utilidade pratica para decisao por combinarem quinas/quadras e menor repeticao.

## Teste isolado do ensemble 3.1

Configuracao:

- 400 concursos
- 10 cartoes por concurso
- 15 numeros por cartao
- 4.000 jogos simulados
- Votantes escolhidos pelo novo ranking de decisao

Votantes escolhidos:

1. aleatorio_smart
2. sequencias
3. candidatos_ouro
4. momentum
5. ciclos

Resultado:

| Metrica | Valor |
|---|---:|
| Media por cartao | 1.4875 |
| Ternos | 483 |
| Quadras | 123 |
| Quinas | 11 |
| Senas | 0 |
| Quadra+ por jogo | 3.35% |
| Quadra+ por concurso | 29.50% |
| Quina+ por concurso | 2.75% |
| Melhor cartao medio por concurso | 3.125 |
| Intersecao media | 3.81 |
| Intersecao maxima media | 7.13 |

Comparacao com ensemble anterior no backtest principal:

| Versao | Senas | Quinas | Quadras | Media | Quadra+ concurso | Intersecao |
|---|---:|---:|---:|---:|---:|---:|
| Ensemble anterior | 1 | 12 | 111 | 1.5048 | 26.50% | 3.96 |
| Ensemble decisao 3.1 | 0 | 11 | 123 | 1.4875 | 29.50% | 3.81 |

Leitura: o ensemble 3.1 perdeu um pouco em media e nao repetiu sena no teste isolado, mas melhorou a frequencia de quadra+ por concurso e reduziu levemente a repeticao. Isso combina melhor com o objetivo de escolher nucleos mais uteis para bolao.

## Teste do wheel

`wheel` foi testada isoladamente em 400 concursos x 10 cartoes x 15 numeros, mas estourou o limite de 20 minutos. Ela precisa de otimizacao ou de um backtest separado com menos concursos antes de entrar no comparativo longo.

## Ensembles gerados para o concurso 3002

Foram adicionados 10 cartoes manuais:

- Concurso: 3002
- Estrategia: ensemble
- Origem: `ensemble_decisao_manual`
- Quantidade: 10
- Numeros por cartao: 15

Cartoes:

| ID | Dezenas |
|---|---|
| AUTO-ENSEMBLE-DECISAO-20260429202716-01 | 03 07 11 14 23 24 28 30 32 39 40 42 43 49 59 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-02 | 01 02 03 08 11 26 31 32 33 36 37 39 43 47 55 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-03 | 01 08 15 22 26 28 31 36 38 41 42 46 53 54 58 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-04 | 02 03 04 05 12 15 18 19 27 30 35 36 46 52 57 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-05 | 05 09 10 12 14 15 22 26 34 36 42 43 49 57 58 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-06 | 15 16 17 19 21 31 32 34 40 41 42 45 46 47 54 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-07 | 01 08 11 23 28 31 32 35 43 47 50 51 52 56 60 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-08 | 02 04 09 12 17 20 23 27 28 39 41 52 53 55 56 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-09 | 02 10 19 20 21 22 27 32 37 43 45 52 55 57 58 |
| AUTO-ENSEMBLE-DECISAO-20260429202716-10 | 06 08 12 15 16 19 28 32 34 39 42 43 51 54 59 |

Validacao dos cartoes:

- IDs unicos: sim
- Todos com 15 numeros: sim
- Intersecao media entre os 10 novos: 3.82
- Intersecao maxima entre os 10 novos: 7

## Proxima decisao recomendada

Para os proximos testes, comparar:

1. Ensemble 3.1
2. Sequencias
3. Aleatorio smart
4. Candidatos ouro
5. Momentum

Depois reduzir de 15 para 13, e em seguida para 10 ou 9 numeros, mantendo a penalidade de repeticao.
