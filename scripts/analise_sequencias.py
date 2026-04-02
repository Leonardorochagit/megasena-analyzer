"""
================================================================================
🔬 ANÁLISE DE SEQUÊNCIAS INTER-SORTEIOS DA MEGA-SENA
================================================================================
Script standalone para três abordagens de análise sequencial:
  1. Vizinhança de Saída (Proximidade N±1)
  2. Matriz de Transição (Cadeia de Markov)
  3. Salto de Dezenas (Step Analysis)

Autor : Copilot + Leonardo
Data  : 2026-02-19
================================================================================
"""

import sys
import os
import json
import time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chisquare, chi2_contingency
from sklearn.cluster import KMeans
from pathlib import Path
from itertools import combinations
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES GLOBAIS
# ──────────────────────────────────────────────────────────────────────────────
DEZENAS_MEGASENA = range(1, 61)       # 01 a 60
NUM_DEZENAS = 60
DEZENAS_POR_SORTEIO = 6
PASTA_SAIDA = Path("resultados_analise")

# APIs
API_HISTORICO = "https://loteriascaixa-api.herokuapp.com/api/megasena"
API_OFICIAL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"


# ──────────────────────────────────────────────────────────────────────────────
# 0. COLETA E PREPARAÇÃO DOS DADOS
# ──────────────────────────────────────────────────────────────────────────────
def carregar_historico(cache_path: str = "data/historico_megasena.json") -> pd.DataFrame:
    """
    Carrega o histórico completo da Mega-Sena.
    Tenta usar cache local; se não existir, busca na API.

    Returns
    -------
    pd.DataFrame
        Colunas: concurso (int), data (str), d1..d6 (int)
        Ordenado por concurso crescente.
    """
    cache = Path(cache_path)

    # Tentar cache local (menos de 12 h)
    if cache.exists():
        idade_h = (time.time() - cache.stat().st_mtime) / 3600
        if idade_h < 12:
            print(f"📂 Usando cache local ({cache_path}) — {idade_h:.1f}h atrás")
            with open(cache, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _json_para_dataframe(data)

    # Buscar da API
    print("🌐 Baixando histórico completo da API…")
    try:
        resp = requests.get(API_HISTORICO, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            data = [data]
    except Exception as e:
        print(f"❌ Falha na API alternativa: {e}")
        return pd.DataFrame()

    # Tentar complementar com último concurso da API oficial
    try:
        resp_of = requests.get(API_OFICIAL, timeout=15)
        resp_of.raise_for_status()
        oficial = resp_of.json()
        ultimo_api = max(d.get("concurso", 0) for d in data)
        num_of = oficial.get("numero", 0)
        if num_of > ultimo_api:
            data.append({
                "concurso": num_of,
                "data": oficial.get("dataApuracao", ""),
                "dezenas": oficial.get("listaDezenas", []),
            })
            print(f"  ✨ Concurso {num_of} adicionado via API oficial")
    except Exception:
        pass

    # Salvar cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  💾 Cache salvo em {cache_path}")

    return _json_para_dataframe(data)


def _json_para_dataframe(data: list) -> pd.DataFrame:
    """Converte o JSON bruto da API num DataFrame limpo."""
    registros = []
    for item in data:
        conc = item.get("concurso", 0)
        dt = item.get("data", "")
        dezenas_raw = item.get("dezenas", [])

        # Normalizar dezenas (pode vir como lista de str ou int)
        dezenas = []
        for d in dezenas_raw:
            try:
                dezenas.append(int(str(d).strip().strip("'\"[] ")))
            except (ValueError, TypeError):
                continue

        if len(dezenas) == 6:
            dezenas.sort()
            registros.append({
                "concurso": int(conc),
                "data": dt,
                "d1": dezenas[0], "d2": dezenas[1], "d3": dezenas[2],
                "d4": dezenas[3], "d5": dezenas[4], "d6": dezenas[5],
            })

    df = pd.DataFrame(registros)
    df.sort_values("concurso", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"✅ {len(df)} concursos carregados (de {df['concurso'].min()} a {df['concurso'].max()})")
    return df


def extrair_dezenas(df: pd.DataFrame) -> list[set[int]]:
    """
    Retorna lista ordenada de sets — um set por concurso.
    Índice 0 = concurso mais antigo.
    """
    cols = ["d1", "d2", "d3", "d4", "d5", "d6"]
    return [set(row) for row in df[cols].values.tolist()]


# ──────────────────────────────────────────────────────────────────────────────
# 1. VIZINHANÇA DE SAÍDA (PROXIMIDADE N ± k)
# ──────────────────────────────────────────────────────────────────────────────
def analise_vizinhanca(sorteios: list[set[int]], k: int = 1) -> pd.DataFrame:
    """
    Para cada par consecutivo (T, T+1), verifica se números vizinhos (N±k)
    de números sorteados em T aparecem em T+1.

    Parâmetros
    ----------
    sorteios : list[set[int]]
        Lista de sets de dezenas por concurso.
    k : int
        Raio de vizinhança (padrão 1 → N-1 e N+1).

    Retorna
    -------
    pd.DataFrame
        Colunas: dezena, vezes_saiu, vizinhos_saiu_t1, taxa_vizinhanca
    """
    print(f"\n{'='*70}")
    print(f"  1. VIZINHANÇA DE SAÍDA — raio k={k}")
    print(f"{'='*70}")

    contagem_saiu = np.zeros(NUM_DEZENAS + 1, dtype=int)       # idx 1..60
    contagem_vizinho = np.zeros(NUM_DEZENAS + 1, dtype=int)

    for t in range(len(sorteios) - 1):
        S_t = sorteios[t]
        S_t1 = sorteios[t + 1]

        for n in S_t:
            contagem_saiu[n] += 1
            vizinhos = {n + delta for delta in range(-k, k + 1) if delta != 0}
            vizinhos = {v for v in vizinhos if 1 <= v <= 60}
            if vizinhos & S_t1:
                contagem_vizinho[n] += 1

    registros = []
    for d in DEZENAS_MEGASENA:
        saiu = int(contagem_saiu[d])
        viz = int(contagem_vizinho[d])
        taxa = viz / saiu if saiu > 0 else 0.0
        registros.append({
            "dezena": d,
            "vezes_saiu_em_T": saiu,
            "vizinho_saiu_em_T1": viz,
            "taxa_vizinhanca": round(taxa, 4),
        })

    df_viz = pd.DataFrame(registros)
    df_viz.sort_values("taxa_vizinhanca", ascending=False, inplace=True)
    df_viz.reset_index(drop=True, inplace=True)

    # Estatísticas gerais
    media = df_viz["taxa_vizinhanca"].mean()
    mediana = df_viz["taxa_vizinhanca"].median()
    print(f"  Taxa média de vizinhança: {media:.4f} ({media*100:.2f}%)")
    print(f"  Taxa mediana:             {mediana:.4f}")
    print(f"\n  Top-10 dezenas com MAIOR taxa de vizinhança:")
    print(df_viz.head(10).to_string(index=False))

    return df_viz


def plot_vizinhanca(df_viz: pd.DataFrame, k: int = 1):
    """Gráfico de barras da taxa de vizinhança por dezena."""
    df_plot = df_viz.sort_values("dezena")

    fig, ax = plt.subplots(figsize=(16, 5))
    cores = plt.cm.RdYlGn(df_plot["taxa_vizinhanca"] / df_plot["taxa_vizinhanca"].max())
    ax.bar(df_plot["dezena"], df_plot["taxa_vizinhanca"], color=cores, edgecolor="grey", linewidth=0.3)
    ax.axhline(df_plot["taxa_vizinhanca"].mean(), color="red", ls="--", lw=1.2, label="Média")
    ax.set_xlabel("Dezena")
    ax.set_ylabel(f"Taxa de Vizinhança (k={k})")
    ax.set_title(f"Vizinhança de Saída — Probabilidade de N±{k} sair em T+1")
    ax.set_xticks(range(1, 61))
    ax.legend()
    plt.tight_layout()
    _salvar_figura(fig, f"vizinhanca_k{k}.png")


# ──────────────────────────────────────────────────────────────────────────────
# 2. MATRIZ DE TRANSIÇÃO (CADEIA DE MARKOV)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_matriz_transicao(sorteios: list[set[int]]) -> pd.DataFrame:
    """
    Calcula a matriz de transição 60×60.
    M[i][j] = P(j sai em T+1 | i saiu em T)

    Cada célula conta quantas vezes j apareceu em T+1 dado que i apareceu em T,
    normalizado pelo número de vezes que i apareceu em T.

    Retorna
    -------
    pd.DataFrame  (60 × 60) com índices/colunas 1..60
    """
    print(f"\n{'='*70}")
    print(f"  2. MATRIZ DE TRANSIÇÃO (CADEIA DE MARKOV)")
    print(f"{'='*70}")

    contagem = np.zeros((NUM_DEZENAS + 1, NUM_DEZENAS + 1), dtype=int)
    freq_i = np.zeros(NUM_DEZENAS + 1, dtype=int)

    for t in range(len(sorteios) - 1):
        S_t = sorteios[t]
        S_t1 = sorteios[t + 1]
        for i in S_t:
            freq_i[i] += 1
            for j in S_t1:
                contagem[i][j] += 1

    # Normalizar → probabilidades
    prob = np.zeros((NUM_DEZENAS + 1, NUM_DEZENAS + 1), dtype=float)
    for i in DEZENAS_MEGASENA:
        if freq_i[i] > 0:
            prob[i, :] = contagem[i, :] / freq_i[i]

    # Recortar 1..60
    df_mat = pd.DataFrame(
        prob[1:, 1:],
        index=range(1, 61),
        columns=range(1, 61),
    )
    df_mat.index.name = "saiu_em_T"
    df_mat.columns.name = "saiu_em_T+1"

    # Estatísticas
    media_global = df_mat.values.mean()
    max_val = df_mat.values.max()
    max_pos = np.unravel_index(df_mat.values.argmax(), df_mat.shape)
    i_max, j_max = max_pos[0] + 1, max_pos[1] + 1
    print(f"  Probabilidade média por célula: {media_global:.5f}")
    print(f"  Maior transição: P({j_max} em T+1 | {i_max} em T) = {max_val:.4f}")

    # Teste Qui-Quadrado de Independência
    print(f"\n  📊 Teste Qui-Quadrado de Independência (Matriz de Transição):")
    # Usamos a matriz de contagem (frequências absolutas) para o teste
    contagem_df = pd.DataFrame(contagem[1:, 1:], index=range(1, 61), columns=range(1, 61))
    
    # Remover linhas/colunas com soma zero para evitar erros no teste
    contagem_df = contagem_df.loc[(contagem_df.sum(axis=1) > 0), (contagem_df.sum(axis=0) > 0)]
    
    try:
        chi2, p_value, dof, expected = chi2_contingency(contagem_df.values)
        print(f"  Estatística Chi2: {chi2:.2f}")
        print(f"  Graus de liberdade: {dof}")
        print(f"  Valor-p: {p_value:.4e}")
        
        if p_value < 0.05:
            print("  ⚠️ CONCLUSÃO: Rejeitamos a hipótese nula. HÁ evidência de dependência entre sorteios consecutivos (p < 0.05).")
        else:
            print("  ✅ CONCLUSÃO: Não rejeitamos a hipótese nula. NÃO HÁ evidência de dependência entre sorteios consecutivos (p >= 0.05). Os sorteios parecem independentes.")
    except Exception as e:
        print(f"  ❌ Erro ao calcular Qui-Quadrado: {e}")

    # Top-20 pares com maior transição
    pares = []
    for i in DEZENAS_MEGASENA:
        for j in DEZENAS_MEGASENA:
            pares.append((i, j, df_mat.loc[i, j]))
    pares.sort(key=lambda x: x[2], reverse=True)
    print(f"\n  Top-20 transições mais fortes:")
    print(f"  {'De':>4} → {'Para':>4}   P(transição)")
    print(f"  {'-'*30}")
    for de, para, p in pares[:20]:
        print(f"  {de:4d} → {para:4d}   {p:.4f}")

    return df_mat


def plot_heatmap_transicao(df_mat: pd.DataFrame, compacto: bool = False):
    """Heatmap da matriz de transição."""

    if compacto:
        # Versão compacta: só top-15 linhas e colunas com maiores somas
        top_linhas = df_mat.sum(axis=1).nlargest(15).index
        top_colunas = df_mat.sum(axis=0).nlargest(15).index
        sub = df_mat.loc[top_linhas, top_colunas]
        titulo = "Matriz de Transição — Top 15 Dezenas (sub-matriz)"
        nome = "matriz_transicao_top15.png"
    else:
        sub = df_mat
        titulo = "Matriz de Transição Completa (60 × 60)"
        nome = "matriz_transicao_completa.png"

    fig, ax = plt.subplots(figsize=(18, 15) if not compacto else (12, 10))
    sns.heatmap(
        sub,
        cmap="YlOrRd",
        linewidths=0.1 if compacto else 0,
        linecolor="white",
        annot=compacto,
        fmt=".3f" if compacto else "",
        ax=ax,
        cbar_kws={"label": "P(j em T+1 | i em T)"},
    )
    ax.set_title(titulo, fontsize=14)
    ax.set_xlabel("Dezena em T+1")
    ax.set_ylabel("Dezena em T")
    plt.tight_layout()
    _salvar_figura(fig, nome)


def plot_heatmap_desvio(df_mat: pd.DataFrame):
    """Heatmap de desvio da média — destaca transições acima/abaixo do esperado."""
    media = df_mat.values.mean()
    desvio = df_mat - media

    fig, ax = plt.subplots(figsize=(18, 15))
    sns.heatmap(
        desvio,
        cmap="coolwarm",
        center=0,
        linewidths=0,
        ax=ax,
        cbar_kws={"label": "Desvio da média"},
    )
    ax.set_title("Desvio da Probabilidade Média de Transição", fontsize=14)
    ax.set_xlabel("Dezena em T+1")
    ax.set_ylabel("Dezena em T")
    plt.tight_layout()
    _salvar_figura(fig, "matriz_desvio_media.png")


# ──────────────────────────────────────────────────────────────────────────────
# 3. SALTO DE DEZENAS (STEP ANALYSIS)
# ──────────────────────────────────────────────────────────────────────────────
def analise_saltos(sorteios: list[set[int]], df_concursos: pd.DataFrame) -> dict:
    """
    Analisa os "saltos" entre dezenas de concursos consecutivos:
      - Salto absoluto: |d_T+1 - d_T| para cada posição ordenada
      - Salto do centro de massa: diferença entre a média das dezenas em T e T+1
      - Amplitude: diferença entre maior e menor dezena do sorteio
      - Dispersão: desvio-padrão intra-sorteio

    Retorna dict com DataFrames de resultados.
    """
    print(f"\n{'='*70}")
    print(f"  3. SALTO DE DEZENAS (STEP ANALYSIS)")
    print(f"{'='*70}")

    # 3a. Salto posicional (dezenas ordenadas posição a posição)
    cols = ["d1", "d2", "d3", "d4", "d5", "d6"]
    mat = df_concursos[cols].values.astype(int)  # (N, 6)

    saltos_pos = np.abs(np.diff(mat, axis=0))  # (N-1, 6)
    df_saltos = pd.DataFrame(
        saltos_pos,
        columns=[f"salto_pos{i+1}" for i in range(6)],
    )
    df_saltos.insert(0, "concurso_T1", df_concursos["concurso"].iloc[1:].values)

    print(f"\n  📊 Saltos Posicionais (|d_pos_T+1 - d_pos_T|):")
    print(f"  {'Posição':<12} {'Média':>8} {'Mediana':>8} {'DP':>8} {'Max':>6}")
    print(f"  {'-'*46}")
    for i in range(6):
        col = f"salto_pos{i+1}"
        m = df_saltos[col].mean()
        md = df_saltos[col].median()
        dp = df_saltos[col].std()
        mx = df_saltos[col].max()
        print(f"  Posição {i+1:<3}  {m:8.2f} {md:8.1f} {dp:8.2f} {mx:6d}")

    # 3b. Salto do centro de massa
    centros = mat.mean(axis=1)  # média das 6 dezenas por sorteio
    salto_centro = np.abs(np.diff(centros))
    print(f"\n  📊 Salto do Centro de Massa:")
    print(f"  Média do salto: {salto_centro.mean():.2f}")
    print(f"  Mediana:        {np.median(salto_centro):.2f}")
    print(f"  DP:             {salto_centro.std():.2f}")

    # 3c. Amplitude e dispersão intra-sorteio
    amplitude = mat.max(axis=1) - mat.min(axis=1)
    dispersao = mat.std(axis=1)

    print(f"\n  📊 Amplitude (max - min) do sorteio:")
    print(f"  Média:      {amplitude.mean():.2f}")
    print(f"  Mediana:    {np.median(amplitude):.1f}")

    print(f"\n  📊 Dispersão (DP intra-sorteio):")
    print(f"  Média:      {dispersao.mean():.2f}")
    print(f"  Mediana:    {np.median(dispersao):.2f}")

    # 3d. Distribuição de saltos individuais (todas as dezenas juntas)
    todos_saltos = saltos_pos.flatten()
    print(f"\n  📊 Distribuição geral dos saltos individuais:")
    print(f"  Total de saltos: {len(todos_saltos)}")
    print(f"  Média:           {todos_saltos.mean():.2f}")
    print(f"  Mediana:         {np.median(todos_saltos):.1f}")
    print(f"  Percentil 25%:   {np.percentile(todos_saltos, 25):.1f}")
    print(f"  Percentil 75%:   {np.percentile(todos_saltos, 75):.1f}")
    print(f"  Percentil 95%:   {np.percentile(todos_saltos, 95):.1f}")

    return {
        "df_saltos_posicionais": df_saltos,
        "salto_centro_massa": salto_centro,
        "amplitude": amplitude,
        "dispersao": dispersao,
        "todos_saltos": todos_saltos,
    }


def plot_saltos(resultado_saltos: dict):
    """Gera múltiplos gráficos para a análise de saltos."""
    todos = resultado_saltos["todos_saltos"]
    centros = resultado_saltos["salto_centro_massa"]
    amplitude = resultado_saltos["amplitude"]
    df_sp = resultado_saltos["df_saltos_posicionais"]

    # ── Histograma geral de saltos ──
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    ax = axes[0, 0]
    ax.hist(todos, bins=range(0, 61), color="steelblue", edgecolor="white", alpha=0.85)
    ax.axvline(todos.mean(), color="red", ls="--", lw=1.5, label=f"Média={todos.mean():.1f}")
    ax.set_title("Distribuição dos Saltos Posicionais")
    ax.set_xlabel("Salto (|d_T+1 - d_T|)")
    ax.set_ylabel("Frequência")
    ax.legend()

    # ── Salto do centro de massa ──
    ax = axes[0, 1]
    ax.hist(centros, bins=40, color="coral", edgecolor="white", alpha=0.85)
    ax.axvline(centros.mean(), color="red", ls="--", lw=1.5, label=f"Média={centros.mean():.1f}")
    ax.set_title("Distribuição do Salto do Centro de Massa")
    ax.set_xlabel("Salto do Centro de Massa")
    ax.set_ylabel("Frequência")
    ax.legend()

    # ── Boxplot por posição ──
    ax = axes[1, 0]
    pos_cols = [c for c in df_sp.columns if c.startswith("salto_pos")]
    df_sp[pos_cols].boxplot(ax=ax, grid=False, patch_artist=True,
                            boxprops=dict(facecolor="lightblue"))
    ax.set_title("Boxplot de Saltos por Posição Ordenada")
    ax.set_xlabel("Posição")
    ax.set_ylabel("Salto")
    ax.set_xticklabels([f"Pos {i+1}" for i in range(6)])

    # ── Amplitude ao longo do tempo ──
    ax = axes[1, 1]
    ax.plot(amplitude, color="teal", alpha=0.4, linewidth=0.5)
    # Média móvel
    window = 50
    if len(amplitude) > window:
        media_movel = pd.Series(amplitude).rolling(window).mean()
        ax.plot(media_movel, color="red", linewidth=1.5, label=f"Média móvel ({window})")
    ax.set_title("Amplitude do Sorteio ao Longo do Tempo")
    ax.set_xlabel("Concurso (índice)")
    ax.set_ylabel("Amplitude (max - min)")
    ax.legend()

    plt.tight_layout()
    _salvar_figura(fig, "saltos_analise.png")


# ──────────────────────────────────────────────────────────────────────────────
# 4. ANÁLISES COMPLEMENTARES
# ──────────────────────────────────────────────────────────────────────────────
def analise_repeticoes(sorteios: list[set[int]]):
    """Quantas dezenas se repetem entre sorteios consecutivos."""
    print(f"\n{'='*70}")
    print(f"  4. REPETIÇÕES ENTRE SORTEIOS CONSECUTIVOS")
    print(f"{'='*70}")

    repeticoes = []
    for t in range(len(sorteios) - 1):
        r = len(sorteios[t] & sorteios[t + 1])
        repeticoes.append(r)

    repeticoes = np.array(repeticoes)
    print(f"  Média de dezenas repetidas: {repeticoes.mean():.3f}")
    print(f"  Distribuição:")
    for v in range(7):
        cnt = (repeticoes == v).sum()
        pct = cnt / len(repeticoes) * 100
        barra = "█" * int(pct / 2)
        print(f"    {v} repetições: {cnt:5d} ({pct:5.2f}%) {barra}")

    # Gráfico
    fig, ax = plt.subplots(figsize=(8, 5))
    valores, contagens = np.unique(repeticoes, return_counts=True)
    ax.bar(valores, contagens, color="mediumpurple", edgecolor="white")
    for v, c in zip(valores, contagens):
        ax.text(v, c + 5, str(c), ha="center", fontsize=10)
    ax.set_xlabel("Nº de Dezenas Repetidas")
    ax.set_ylabel("Frequência")
    ax.set_title("Repetições entre Sorteios Consecutivos")
    ax.set_xticks(range(7))
    plt.tight_layout()
    _salvar_figura(fig, "repeticoes_consecutivas.png")

    return repeticoes


def analise_soma_dezenas(df_concursos: pd.DataFrame):
    """Soma das 6 dezenas e sua evolução."""
    print(f"\n{'='*70}")
    print(f"  5. SOMA DAS DEZENAS POR SORTEIO")
    print(f"{'='*70}")

    cols = ["d1", "d2", "d3", "d4", "d5", "d6"]
    soma = df_concursos[cols].astype(int).sum(axis=1)

    print(f"  Média: {soma.mean():.1f}")
    print(f"  DP:    {soma.std():.1f}")
    print(f"  Min:   {soma.min()} | Max: {soma.max()}")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.hist(soma, bins=50, color="goldenrod", edgecolor="white", alpha=0.85)
    ax.axvline(soma.mean(), color="red", ls="--", lw=1.5, label=f"Média={soma.mean():.0f}")
    ax.set_title("Distribuição da Soma das Dezenas")
    ax.set_xlabel("Soma")
    ax.set_ylabel("Frequência")
    ax.legend()
    plt.tight_layout()
    _salvar_figura(fig, "soma_dezenas.png")

    return soma


def analise_clusters_dezenas(df_concursos: pd.DataFrame):
    """
    Agrupa as dezenas em clusters baseados na frequência de saída conjunta.
    """
    print(f"\n{'='*70}")
    print(f"  6. ANÁLISE DE CLUSTERS (K-MEANS)")
    print(f"{'='*70}")

    # Criar matriz de co-ocorrência (quantas vezes i e j saíram no mesmo sorteio)
    co_ocorrencia = np.zeros((NUM_DEZENAS + 1, NUM_DEZENAS + 1), dtype=int)
    
    cols = ["d1", "d2", "d3", "d4", "d5", "d6"]
    for _, row in df_concursos[cols].iterrows():
        dezenas = row.values.astype(int)
        for i in range(len(dezenas)):
            for j in range(i + 1, len(dezenas)):
                d1, d2 = dezenas[i], dezenas[j]
                co_ocorrencia[d1][d2] += 1
                co_ocorrencia[d2][d1] += 1

    # Usar a matriz de co-ocorrência como features para o KMeans
    # (cada dezena é representada por suas co-ocorrências com as outras 59)
    features = co_ocorrencia[1:, 1:]
    
    # Normalizar (opcional, mas ajuda o KMeans)
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Aplicar KMeans (vamos tentar 4 grupos)
    n_clusters = 4
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(features_scaled)

    # Organizar resultados
    df_clusters = pd.DataFrame({
        "dezena": range(1, 61),
        "cluster": clusters
    })

    print(f"  Dezenas agrupadas em {n_clusters} clusters baseados em co-ocorrência:")
    for c in range(n_clusters):
        dezenas_cluster = df_clusters[df_clusters["cluster"] == c]["dezena"].tolist()
        print(f"  Cluster {c}: {len(dezenas_cluster)} dezenas")
        print(f"    {dezenas_cluster}")

    # Plotar a matriz de co-ocorrência reordenada por cluster
    df_clusters_sorted = df_clusters.sort_values("cluster")
    ordem = df_clusters_sorted["dezena"].values - 1 # índices 0-59
    
    matriz_ordenada = features[ordem][:, ordem]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(matriz_ordenada, cmap="viridis", xticklabels=ordem+1, yticklabels=ordem+1, ax=ax)
    ax.set_title("Matriz de Co-ocorrência (Ordenada por Clusters)")
    plt.tight_layout()
    _salvar_figura(fig, "clusters_co_ocorrencia.png")

    return df_clusters


# ──────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ──────────────────────────────────────────────────────────────────────────────
def _salvar_figura(fig, nome: str):
    """Salva a figura na pasta de saída."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / nome
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📈 Gráfico salvo: {caminho}")


def exportar_csv(df: pd.DataFrame, nome: str):
    """Exporta DataFrame para CSV."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / nome
    df.to_csv(caminho, index=True)
    print(f"  📄 CSV salvo: {caminho}")


def gerar_relatorio_texto(
    df_viz: pd.DataFrame,
    df_mat: pd.DataFrame,
    resultado_saltos: dict,
    repeticoes: np.ndarray,
):
    """Gera um relatório resumido em texto."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / "relatorio_sequencias.txt"

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  RELATÓRIO DE ANÁLISE DE SEQUÊNCIAS — MEGA-SENA\n")
        f.write(f"  Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        # Vizinhança
        f.write("1. VIZINHANÇA DE SAÍDA (k=1)\n")
        f.write("-" * 40 + "\n")
        media_viz = df_viz["taxa_vizinhanca"].mean()
        f.write(f"   Taxa média: {media_viz:.4f} ({media_viz*100:.2f}%)\n")
        f.write(f"   Top-5 dezenas:\n")
        for _, row in df_viz.head(5).iterrows():
            f.write(f"     Dezena {int(row['dezena']):02d}: {row['taxa_vizinhanca']:.4f}\n")

        # Transição
        f.write(f"\n2. MATRIZ DE TRANSIÇÃO\n")
        f.write("-" * 40 + "\n")
        media_mat = df_mat.values.mean()
        f.write(f"   P média por célula: {media_mat:.5f}\n")
        max_val = df_mat.values.max()
        max_pos = np.unravel_index(df_mat.values.argmax(), df_mat.shape)
        f.write(f"   Maior transição: {max_pos[0]+1} → {max_pos[1]+1} = {max_val:.4f}\n")

        # Saltos
        f.write(f"\n3. SALTOS DE DEZENAS\n")
        f.write("-" * 40 + "\n")
        todos = resultado_saltos["todos_saltos"]
        f.write(f"   Salto médio: {todos.mean():.2f}\n")
        f.write(f"   Mediana:     {np.median(todos):.1f}\n")
        centro = resultado_saltos["salto_centro_massa"]
        f.write(f"   Salto centro de massa médio: {centro.mean():.2f}\n")

        # Repetições
        f.write(f"\n4. REPETIÇÕES CONSECUTIVAS\n")
        f.write("-" * 40 + "\n")
        f.write(f"   Média: {repeticoes.mean():.3f} dezenas repetidas\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("  Gráficos e CSVs exportados em: resultados_analise/\n")
        f.write("=" * 70 + "\n")

    print(f"\n📝 Relatório salvo: {caminho}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "█" * 70)
    print("  🔬 ANÁLISE DE SEQUÊNCIAS INTER-SORTEIOS — MEGA-SENA")
    print("█" * 70)

    # ── Carregar dados ──
    df = carregar_historico()
    if df.empty:
        print("❌ Nenhum dado carregado. Verifique sua conexão.")
        sys.exit(1)

    sorteios = extrair_dezenas(df)

    # ── 1. Vizinhança ──
    df_viz = analise_vizinhanca(sorteios, k=1)
    plot_vizinhanca(df_viz, k=1)
    exportar_csv(df_viz, "vizinhanca_k1.csv")

    # Vizinhança k=2 (bônus)
    df_viz2 = analise_vizinhanca(sorteios, k=2)
    plot_vizinhanca(df_viz2, k=2)
    exportar_csv(df_viz2, "vizinhanca_k2.csv")

    # ── 2. Matriz de Transição ──
    df_mat = calcular_matriz_transicao(sorteios)
    plot_heatmap_transicao(df_mat, compacto=False)
    plot_heatmap_transicao(df_mat, compacto=True)
    plot_heatmap_desvio(df_mat)
    exportar_csv(df_mat, "matriz_transicao.csv")

    # ── 3. Saltos ──
    resultado_saltos = analise_saltos(sorteios, df)
    plot_saltos(resultado_saltos)
    exportar_csv(resultado_saltos["df_saltos_posicionais"], "saltos_posicionais.csv")

    # ── 4. Repetições ──
    repeticoes = analise_repeticoes(sorteios)

    # ── 5. Soma ──
    analise_soma_dezenas(df)

    # ── 6. Clusters ──
    df_clusters = analise_clusters_dezenas(df)
    exportar_csv(df_clusters, "clusters_dezenas.csv")

    # ── Relatório final ──
    gerar_relatorio_texto(df_viz, df_mat, resultado_saltos, repeticoes)

    print("\n" + "█" * 70)
    print(f"  ✅ ANÁLISE CONCLUÍDA — resultados em: {PASTA_SAIDA}/")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
