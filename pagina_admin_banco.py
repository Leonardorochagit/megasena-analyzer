"""
================================================================================
PÁGINA: ADMINISTRAÇÃO DO BANCO DE DADOS
================================================================================
Permite visualizar, exportar e manter o banco megasena.db pelo próprio app.
================================================================================
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

from modules.db import (
    get_connection,
    stats_cartoes_db,
    carregar_cartoes_db,
    carregar_historico_db,
    carregar_backtesting_db,
    carregar_todas_configs_db,
    salvar_config_db,
    deletar_cartao_db,
    DB_PATH,
)


def _tamanho_banco() -> str:
    try:
        tam = os.path.getsize(DB_PATH)
        if tam < 1024:
            return f"{tam} B"
        elif tam < 1024 ** 2:
            return f"{tam / 1024:.1f} KB"
        else:
            return f"{tam / 1024 ** 2:.2f} MB"
    except Exception:
        return "N/D"


def _executar_vacuum():
    try:
        conn = get_connection()
        conn.execute("VACUUM")
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro no VACUUM: {e}")
        return False


def _backup_banco() -> bytes:
    try:
        with open(DB_PATH, 'rb') as f:
            return f.read()
    except Exception:
        return b""


def pagina_admin_banco():
    st.title("🗄️ Administração do Banco de Dados")
    st.caption(f"SQLite — `{DB_PATH}`")

    # ── MÉTRICAS GERAIS ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Visão Geral")

    stats = stats_cartoes_db()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Cartões", stats.get('total', 0))
    with col2:
        st.metric("Pendentes", stats.get('pendentes', 0))
    with col3:
        st.metric("Verificados", stats.get('verificados', 0))
    with col4:
        st.metric("Vou Jogar", stats.get('vai_jogar', 0))
    with col5:
        st.metric("Tamanho do Banco", _tamanho_banco())

    col6, col7 = st.columns(2)
    with col6:
        st.metric("Concursos distintos", stats.get('concursos_distintos', 0))
    with col7:
        st.metric("Estratégias distintas", stats.get('estrategias_distintas', 0))

    # ── TABELAS ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Conteúdo das Tabelas")

    tab_cartoes, tab_hist, tab_bt, tab_cfg = st.tabs([
        "🎲 Cartões", "📈 Histórico", "🔬 Backtesting", "⚙️ Configurações"
    ])

    with tab_cartoes:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_verif = st.selectbox("Verificado", ["Todos", "Sim", "Não"])
        with col_f2:
            filtro_jogar = st.selectbox("Vai Jogar", ["Todos", "Sim", "Não"])
        with col_f3:
            filtro_lim = st.number_input("Limite", 10, 1000, 100, step=50)

        kwargs = {'limit': int(filtro_lim)}
        if filtro_verif == "Sim":
            kwargs['verificado'] = True
        elif filtro_verif == "Não":
            kwargs['verificado'] = False
        if filtro_jogar == "Sim":
            kwargs['vai_jogar'] = True
        elif filtro_jogar == "Não":
            kwargs['vai_jogar'] = False

        cartoes = carregar_cartoes_db(**kwargs)
        if cartoes:
            df_c = pd.DataFrame(cartoes)
            cols_show = [c for c in ['id', 'dezenas', 'estrategia', 'estrategia_versao',
                                      'concurso_alvo', 'vai_jogar', 'verificado',
                                      'acertos', 'data_criacao'] if c in df_c.columns]
            st.dataframe(df_c[cols_show], hide_index=True, use_container_width=True)

            csv = df_c.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Exportar CSV", csv,
                               f"cartoes_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("Nenhum cartão encontrado com esses filtros.")

    with tab_hist:
        historico = carregar_historico_db()
        if historico:
            linhas = []
            for h in historico:
                for est, s in h.get('estatisticas', {}).items():
                    linhas.append({
                        'concurso': h['concurso'],
                        'data_analise': h.get('data_analise'),
                        'estrategia': est,
                        'total_jogos': s.get('total_jogos', 0),
                        'quadras': s.get('quadras', 0),
                        'quinas': s.get('quinas', 0),
                        'senas': s.get('senas', 0),
                        'media_acertos': s.get('media_acertos', 0),
                    })
            df_h = pd.DataFrame(linhas).sort_values(['concurso', 'estrategia'], ascending=False)
            st.dataframe(df_h, hide_index=True, use_container_width=True)
            csv = df_h.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Exportar CSV", csv,
                               f"historico_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("Nenhum histórico encontrado.")

    with tab_bt:
        bt_rows = carregar_backtesting_db(limit=50)
        if bt_rows:
            df_bt = pd.DataFrame(bt_rows)
            st.dataframe(df_bt, hide_index=True, use_container_width=True)
            csv = df_bt.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Exportar CSV", csv,
                               f"backtesting_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("Nenhum resultado de backtesting no banco.")

    with tab_cfg:
        configs = carregar_todas_configs_db()
        if configs:
            df_cfg = pd.DataFrame([
                {'chave': k, 'valor': str(v)} for k, v in configs.items()
            ])
            st.dataframe(df_cfg, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhuma configuração no banco.")

        st.markdown("**Adicionar / atualizar configuração:**")
        col_k, col_v = st.columns(2)
        with col_k:
            nova_chave = st.text_input("Chave")
        with col_v:
            novo_valor = st.text_input("Valor")
        if st.button("Salvar configuração") and nova_chave:
            salvar_config_db(nova_chave, novo_valor)
            st.success(f"Configuração '{nova_chave}' salva.")
            st.rerun()

    # ── MANUTENÇÃO ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔧 Manutenção")

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        if st.button("🧹 VACUUM (compactar banco)", use_container_width=True,
                     help="Remove espaço não utilizado do arquivo .db"):
            if _executar_vacuum():
                st.success(f"VACUUM concluído. Tamanho atual: {_tamanho_banco()}")

    with col_m2:
        backup_bytes = _backup_banco()
        st.download_button(
            "💾 Download backup (.db)",
            data=backup_bytes,
            file_name=f"megasena_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
            mime="application/octet-stream",
            use_container_width=True,
            help="Baixa o arquivo SQLite completo"
        )

    with col_m3:
        st.markdown("**Executar SQL direto:**")

    with st.expander("💻 Console SQL (somente leitura)"):
        sql_query = st.text_area("Query SQL", value="SELECT * FROM cartoes LIMIT 10", height=80)
        if st.button("Executar"):
            try:
                conn = get_connection()
                df_sql = pd.read_sql_query(sql_query, conn)
                conn.close()
                st.dataframe(df_sql, use_container_width=True)
                st.caption(f"{len(df_sql)} linhas retornadas.")
            except Exception as e:
                st.error(f"Erro: {e}")

    # ── MIGRAÇÃO ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔄 Migração de Dados Legados (JSON → SQLite)")
    st.info(
        "Se ainda não rodou a migração, execute no terminal:\n\n"
        "```\ncd c:\\Projetos\\1.Megasena\n"
        "python scripts/migrar_json_para_sqlite.py\n```"
    )

    # ── EXCLUSÃO DE CARTÕES ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🗑️ Excluir Cartões Verificados")
    st.warning(
        "Remove permanentemente do banco os cartões já verificados. "
        "Faça um backup antes."
    )
    if st.button("Excluir todos os cartões verificados", type="primary"):
        cartoes_verif = carregar_cartoes_db(verificado=True)
        if not cartoes_verif:
            st.info("Nenhum cartão verificado para excluir.")
        else:
            for c in cartoes_verif:
                deletar_cartao_db(c['id'])
            st.success(f"{len(cartoes_verif)} cartões verificados excluídos.")
            st.rerun()
