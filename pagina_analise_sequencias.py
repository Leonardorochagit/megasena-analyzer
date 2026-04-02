"""
================================================================================
🧬 PÁGINA: ANÁLISE DE SEQUÊNCIAS E PADRÕES
================================================================================
Análise estatística avançada dos sorteios da Mega-Sena:
  - Gerador Inteligente (Clusters + Vizinhança + Filtros)
  - Clusters de Co-ocorrência (K-Means)
  - Vizinhança de Saída (N±1)
  - Matriz de Transição (Cadeia de Markov + Qui-Quadrado)
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # backend não-interativo → evita crash no Streamlit
import matplotlib.pyplot as plt
import seaborn as sns
import random
import warnings
from datetime import datetime
from modules import data_manager as dm

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE ANÁLISE
# ──────────────────────────────────────────────────────────────────────────────

def _preparar_dados(df: pd.DataFrame):
    """Prepara o DataFrame e extrai a lista de sets de dezenas por concurso."""
    cols = ["dez1", "dez2", "dez3", "dez4", "dez5", "dez6"]
    df_calc = df.copy().sort_values("concurso").reset_index(drop=True)

    for c in cols:
        df_calc[c] = pd.to_numeric(df_calc[c], errors="coerce").fillna(0).astype(int)

    sorteios = [set(row) for row in df_calc[cols].values.tolist()]
    return df_calc, sorteios


def _analise_vizinhanca(sorteios: list, k: int = 1) -> pd.DataFrame:
    """Taxa de vizinhança N±k entre sorteios consecutivos."""
    contagem_saiu = np.zeros(61, dtype=int)
    contagem_vizinho = np.zeros(61, dtype=int)

    for t in range(len(sorteios) - 1):
        S_t, S_t1 = sorteios[t], sorteios[t + 1]
        for n in S_t:
            contagem_saiu[n] += 1
            vizinhos = {n + d for d in range(-k, k + 1) if d != 0}
            vizinhos = {v for v in vizinhos if 1 <= v <= 60}
            if vizinhos & S_t1:
                contagem_vizinho[n] += 1

    registros = []
    for d in range(1, 61):
        s = int(contagem_saiu[d])
        v = int(contagem_vizinho[d])
        registros.append({
            "Dezena": d,
            "Vezes Saiu (T)": s,
            "Vizinho Saiu (T+1)": v,
            "Taxa Vizinhança": round(v / s, 4) if s else 0.0,
        })
    return pd.DataFrame(registros).sort_values("Taxa Vizinhança", ascending=False).reset_index(drop=True)


def _calcular_matriz_transicao(sorteios: list):
    """Matriz 60×60 de probabilidade de transição + teste Qui-Quadrado."""
    contagem = np.zeros((61, 61), dtype=int)
    freq_i = np.zeros(61, dtype=int)

    for t in range(len(sorteios) - 1):
        S_t, S_t1 = sorteios[t], sorteios[t + 1]
        for i in S_t:
            freq_i[i] += 1
            for j in S_t1:
                contagem[i][j] += 1

    prob = np.zeros((61, 61))
    for i in range(1, 61):
        if freq_i[i] > 0:
            prob[i, :] = contagem[i, :] / freq_i[i]

    df_mat = pd.DataFrame(prob[1:, 1:], index=range(1, 61), columns=range(1, 61))

    # Qui-Quadrado
    c_df = pd.DataFrame(contagem[1:, 1:], index=range(1, 61), columns=range(1, 61))
    c_df = c_df.loc[(c_df.sum(axis=1) > 0), (c_df.sum(axis=0) > 0)]
    try:
        from scipy.stats import chi2_contingency
        _, p_value, _, _ = chi2_contingency(c_df.values)
        p_value = float(p_value)
    except Exception:
        p_value = 1.0

    return df_mat, p_value


@st.cache_data(ttl=3600, show_spinner="Calculando clusters…")
def _analise_clusters(_df_concursos_hash: str, df_concursos: pd.DataFrame):
    """K-Means sobre a matriz de co-ocorrência das 60 dezenas."""
    co = np.zeros((61, 61), dtype=int)
    cols = ["dez1", "dez2", "dez3", "dez4", "dez5", "dez6"]

    mat = df_concursos[cols].values.astype(int)
    for row in mat:
        for i in range(6):
            for j in range(i + 1, 6):
                co[row[i]][row[j]] += 1
                co[row[j]][row[i]] += 1

    features = co[1:, 1:]
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans

    scaled = StandardScaler().fit_transform(features)
    clusters = KMeans(n_clusters=4, random_state=42, n_init=10).fit_predict(scaled)

    df_cl = pd.DataFrame({"dezena": range(1, 61), "cluster": clusters})
    cluster_dict = {}
    for c in range(4):
        cluster_dict[c] = df_cl[df_cl["cluster"] == c]["dezena"].tolist()

    return cluster_dict, features.tolist(), df_cl


def _get_clusters(df_calc):
    """Wrapper para chamar _analise_clusters com hash estável."""
    chave = str(len(df_calc))
    return _analise_clusters(chave, df_calc)


# ──────────────────────────────────────────────────────────────────────────────
# GERADOR DE CARTÕES
# ──────────────────────────────────────────────────────────────────────────────

def _gerar_cartoes(cluster_dict, ultimo_sorteio, qtd_dezenas, qtd_cartoes):
    """Gera cartões aplicando Clusters + Vizinhança + Filtros de Soma/Amplitude."""
    fator = qtd_dezenas / 6.0
    soma_min = int(143 * fator)
    soma_max = int(223 * fator)
    amp_min = int(30 * (1 + (qtd_dezenas - 6) * 0.05))
    amp_max = 59
    max_seq = 2 if qtd_dezenas == 6 else 3

    cartoes = []
    for _ in range(8000):
        if len(cartoes) >= qtd_cartoes:
            break

        jogo = []
        # 1. Balanceamento de Clusters
        por_cluster = max(1, qtd_dezenas // 4)
        for dezenas in cluster_dict.values():
            jogo.extend(random.sample(dezenas, min(por_cluster, len(dezenas))))

        # 2. Vizinhança do último sorteio
        viz = set()
        for n in ultimo_sorteio:
            if n > 1:
                viz.add(n - 1)
            if n < 60:
                viz.add(n + 1)
        viz = list(viz - set(ultimo_sorteio) - set(jogo))
        if viz:
            jogo.extend(random.sample(viz, min(random.choice([1, 2]), len(viz))))

        # 3. Completar / cortar
        if len(jogo) < qtd_dezenas:
            resto = list(set(range(1, 61)) - set(jogo))
            jogo.extend(random.sample(resto, qtd_dezenas - len(jogo)))
        elif len(jogo) > qtd_dezenas:
            jogo = random.sample(jogo, qtd_dezenas)
        jogo = sorted(jogo)

        # 4. Filtros
        soma = sum(jogo)
        amp  = jogo[-1] - jogo[0]
        saltos = np.diff(jogo)
        if soma_min <= soma <= soma_max and amp_min <= amp <= amp_max and (saltos == 1).sum() <= max_seq:
            if jogo not in cartoes:
                cartoes.append(jogo)

    return cartoes


# ──────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def pagina_analise_sequencias(df: pd.DataFrame):
    """Renderiza a página 🧬 Análise de Sequências no Streamlit."""

    st.title("🧬 Análise de Sequências e Padrões")
    st.markdown(
        "Estatística avançada e Machine Learning (K-Means) aplicados aos sorteios "
        "da Mega-Sena — ignorando superstições e focando em matemática pura."
    )

    if df is None or df.empty:
        st.warning("Nenhum dado disponível para análise.")
        return

    # Preparar dados
    with st.spinner("Preparando dados…"):
        df_calc, sorteios = _preparar_dados(df)

    ultimo = df_calc.iloc[-1]
    ultimo_sorteio = [int(ultimo[f"dez{i}"]) for i in range(1, 7)]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Gerador Inteligente",
        "🧩 Clusters",
        "🔗 Vizinhança (N±1)",
        "🎲 Matriz de Transição",
    ])

    # ─────────────────────────────────────────────────────────────────────
    # TAB 1 — GERADOR INTELIGENTE
    # ─────────────────────────────────────────────────────────────────────
    with tab1:
        st.header("Gerador Baseado em Padrões Estatísticos")
        st.markdown(f"**Último Concurso ({ultimo['concurso']}):** `{ultimo_sorteio}`")

        c1, c2 = st.columns([1, 2])
        with c1:
            qtd_dez = st.slider("Dezenas por cartão", 6, 20, 10)
            qtd_cart = st.number_input("Qtd. de cartões", 1, 20, 5)
            gerar = st.button("🎲 Gerar Cartões Inteligentes", type="primary")

        with c2:
            st.info(
                "**Como funciona?**\n"
                "1. **Clusters:** dezenas de famílias diferentes (co-ocorrência).\n"
                "2. **Vizinhança:** inclui 1-2 vizinhos (N±1) do último sorteio.\n"
                "3. **Filtro de Soma:** dentro da curva normal histórica.\n"
                "4. **Filtro de Amplitude:** evita jogos espremidos."
            )

        if gerar:
            with st.spinner("Gerando cartões…"):
                cluster_dict, _, _ = _get_clusters(df_calc)
                st.session_state["cartoes_seq"] = _gerar_cartoes(
                    cluster_dict, ultimo_sorteio, qtd_dez, qtd_cart
                )
                # Limpar flag de salvamento ao gerar novos cartões
                st.session_state.pop("cartoes_seq_salvos", None)

        if "cartoes_seq" in st.session_state and st.session_state["cartoes_seq"]:
            st.subheader("Cartões Sugeridos")

            # Concurso alvo para salvar
            proximo_concurso = int(ultimo["concurso"]) + 1
            concurso_alvo = st.number_input(
                "Concurso alvo para estes cartões",
                min_value=1,
                value=proximo_concurso,
                key="concurso_alvo_seq"
            )

            for i, cartao in enumerate(st.session_state["cartoes_seq"]):
                viz_incl = [n for n in cartao if (n - 1 in ultimo_sorteio or n + 1 in ultimo_sorteio)]
                st.success(f"**Cartão {i + 1}:** `{cartao}`")
                st.caption(f"Soma: {sum(cartao)} · Amplitude: {cartao[-1]-cartao[0]} · Vizinhos: {viz_incl}")

            # Botão salvar
            st.markdown("---")
            col_salvar, col_info = st.columns([1, 2])
            with col_salvar:
                salvar = st.button("💾 Salvar Cartões para Conferência", type="primary", key="salvar_seq")
            with col_info:
                st.caption(
                    f"Os {len(st.session_state['cartoes_seq'])} cartões serão salvos "
                    f"para o concurso **{concurso_alvo}** e ficarão disponíveis na "
                    f"aba **Simulação & Conferência**."
                )

            if salvar:
                cartoes_existentes = dm.carregar_cartoes_salvos()
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                novos = []
                for idx, dezenas in enumerate(st.session_state["cartoes_seq"]):
                    novos.append({
                        "id": f"SEQ-{timestamp}-{idx+1:02d}",
                        "dezenas": sorted(dezenas),
                        "estrategia": "Análise de Sequências",
                        "vai_jogar": True,
                        "verificado": False,
                        "concurso_alvo": int(concurso_alvo),
                        "status": "aguardando",
                        "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "qtd_numeros": len(dezenas),
                    })
                cartoes_existentes.extend(novos)
                if dm.salvar_cartoes(cartoes_existentes):
                    st.session_state["cartoes_seq_salvos"] = True
                    st.success(f"✅ {len(novos)} cartões salvos para o concurso {concurso_alvo}!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao salvar cartões.")

            if st.session_state.get("cartoes_seq_salvos"):
                st.info("✅ Cartões já salvos! Confira na aba **🎯 Simulação & Conferência**.")

    # ─────────────────────────────────────────────────────────────────────
    # TAB 2 — CLUSTERS
    # ─────────────────────────────────────────────────────────────────────
    with tab2:
        st.header("Clusters de Co-ocorrência (K-Means)")
        st.markdown(
            "As 60 dezenas agrupadas em 4 'famílias' pela frequência com que saem juntas."
        )

        cluster_dict, features_list, df_cl = _get_clusters(df_calc)
        features = np.array(features_list)

        cols_ui = st.columns(4)
        cores = ["🔴", "🔵", "🟢", "🟡"]
        for c in range(4):
            with cols_ui[c]:
                st.markdown(f"### {cores[c]} Cluster {c}")
                st.info(f"{len(cluster_dict[c])} dezenas")
                st.write(", ".join(map(str, cluster_dict[c])))

        st.markdown("---")
        st.subheader("Heatmap de Co-ocorrência (ordenado por cluster)")
        ordem = np.array(df_cl.sort_values("cluster")["dezena"].values, dtype=int) - 1
        mat_ord = features[ordem][:, ordem]
        fig, ax = plt.subplots(figsize=(10, 8))
        labels = [str(x + 1) for x in ordem]
        sns.heatmap(mat_ord, cmap="viridis", xticklabels=labels, yticklabels=labels, ax=ax)
        ax.set_title("Matriz de Co-ocorrência Ordenada por Cluster")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 3 — VIZINHANÇA
    # ─────────────────────────────────────────────────────────────────────
    with tab3:
        st.header("Vizinhança de Saída (N±1)")
        st.markdown(
            "Quando o número **N** sai no sorteio T, qual a chance de **N-1** ou **N+1** "
            "sair no sorteio T+1?"
        )

        with st.spinner("Calculando vizinhança…"):
            df_viz = _analise_vizinhanca(sorteios, k=1)

        media_viz = df_viz["Taxa Vizinhança"].mean()
        st.metric("Taxa Média de Vizinhança", f"{media_viz * 100:.1f}%")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 10 — Maiores taxas")
            st.dataframe(df_viz.head(10))
        with c2:
            st.subheader("Top 10 — Menores taxas")
            st.dataframe(df_viz.tail(10).sort_values("Taxa Vizinhança"))

        fig, ax = plt.subplots(figsize=(14, 4))
        dp = df_viz.sort_values("Dezena")
        cmap = plt.get_cmap("RdYlGn")
        cores_bar = cmap(dp["Taxa Vizinhança"] / dp["Taxa Vizinhança"].max())
        ax.bar(dp["Dezena"], dp["Taxa Vizinhança"], color=cores_bar, edgecolor="grey", linewidth=0.3)
        ax.axhline(media_viz, color="red", ls="--", lw=1.2, label=f"Média ({media_viz*100:.1f}%)")
        ax.set_xlabel("Dezena")
        ax.set_ylabel("Taxa de Vizinhança")
        ax.set_title("Taxa de Vizinhança por Dezena (k=1)")
        ax.set_xticks(range(1, 61))
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 4 — MATRIZ DE TRANSIÇÃO
    # ─────────────────────────────────────────────────────────────────────
    with tab4:
        st.header("Matriz de Transição (Cadeia de Markov)")
        st.markdown(
            "Existe correlação estatística entre o sorteio **T** e o **T+1**? "
            "O teste Qui-Quadrado de independência responde."
        )

        with st.spinner("Calculando matriz de transição…"):
            df_mat, p_value = _calcular_matriz_transicao(sorteios)

        if p_value < 0.05:
            st.error(
                f"⚠️ **HÁ EVIDÊNCIA DE DEPENDÊNCIA** (p = {p_value:.4e}). "
                "Os sorteios podem não ser independentes!"
            )
        else:
            st.success(
                f"✅ **NÃO HÁ EVIDÊNCIA DE DEPENDÊNCIA** (p = {p_value:.4e}). "
                "Os sorteios são estatisticamente independentes."
            )

        st.subheader("Heatmap — Top 15 dezenas com maiores transições")
        top_l = df_mat.sum(axis=1).nlargest(15).index
        top_c = df_mat.sum(axis=0).nlargest(15).index
        sub = df_mat.loc[top_l, top_c]

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(sub, cmap="YlOrRd", annot=True, fmt=".3f", ax=ax,
                    cbar_kws={"label": "P(j em T+1 | i em T)"})
        ax.set_title("Sub-Matriz de Transição (Top 15)")
        ax.set_xlabel("Dezena em T+1")
        ax.set_ylabel("Dezena em T")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("Heatmap de Desvio da Média")
        media_mat = df_mat.values.mean()
        desvio = df_mat - media_mat
        fig2, ax2 = plt.subplots(figsize=(12, 10))
        sns.heatmap(desvio, cmap="coolwarm", center=0, ax=ax2,
                    cbar_kws={"label": "Desvio da probabilidade média"})
        ax2.set_title("Desvio da Média — Transições Acima/Abaixo do Esperado")
        ax2.set_xlabel("Dezena em T+1")
        ax2.set_ylabel("Dezena em T")
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)
