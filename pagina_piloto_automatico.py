"""
================================================================================
🤖 PÁGINA: PILOTO AUTOMÁTICO
================================================================================
Modo automático que roda dentro do Streamlit:
- Auto-refresh periódico (configurável)
- Detecta se há resultado novo e confere automaticamente
- Gera cartões para o próximo concurso se não existirem
- Exibe dashboard em tempo real com ranking e status
================================================================================
"""

import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime, timedelta
from modules import data_manager as dm
from modules import statistics as stats
from modules import game_generator as gen
from modules import notificacoes as notif
from helpers import versao_estrategia

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

    def st_autorefresh(interval=0, limit=None, key="autorefresh"):
        """Fallback simples para auto-refresh quando o pacote externo não está disponível."""
        count_key = f"__fallback_autorefresh_count_{key}"
        count = st.session_state.get(count_key, 0)

        if limit is not None and count >= limit:
            return count

        st.components.v1.html(
            f"""
            <script>
              setTimeout(function() {{
                window.parent.location.reload();
              }}, {int(interval)});
            </script>
            """,
            height=0,
        )

        count += 1
        st.session_state[count_key] = count
        return count


# =============================================================================
# CONFIGURAÇÃO PERSISTENTE EM ARQUIVO
# =============================================================================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piloto_config.json")

def _carregar_config():
    """Carrega configurações salvas do disco. Fallback para st.secrets no Streamlit Cloud."""
    defaults = {
        'ativo': True,
        'intervalo': 60,
        'qtd_numeros': 14,
        'cartoes_por_est': 20,
        'cartoes_ensemble': 40,
        'ensemble_only': False,
        'whatsapp_ativo': False,
        'whatsapp_telefone': '',
        'whatsapp_apikey': ''
    }
    # Fallback: preencher defaults com st.secrets (Streamlit Cloud)
    try:
        wa_secrets = st.secrets.get('whatsapp', {})
        if wa_secrets.get('telefone'):
            defaults['whatsapp_ativo'] = True
            defaults['whatsapp_telefone'] = wa_secrets.get('telefone', '')
            defaults['whatsapp_apikey'] = wa_secrets.get('apikey', '')
    except Exception:
        pass
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Merge com defaults (caso falte alguma chave)
            for k, v in defaults.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        pass
    return defaults

def _salvar_config(config):
    """Salva configurações no disco"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# =============================================================================
# CONSTANTES (mesmas de pagina_simulacao.py)
# =============================================================================

TODAS_ESTRATEGIAS = [
    'escada', 'atrasados', 'quentes',
    'equilibrado', 'misto', 'consenso', 'aleatorio_smart',
    'sequencias', 'wheel',
    'candidatos_ouro', 'momentum', 'vizinhanca',
    'frequencia_desvio', 'pares_frequentes', 'ciclos', 'atraso_recente',
    'ensemble',
]

NOMES_ESTRATEGIAS = {
    'escada': '🔄 Escada Temporal',
    'atrasados': '⏰ Números Atrasados',
    'quentes': '🔥 Números Quentes',
    'equilibrado': '⚖️ Equilibrado',
    'misto': '🎨 Misto',
    'consenso': '🤝 Consenso',
    'aleatorio_smart': '🎲 Aleatório Inteligente',
    'ensemble': '🧠 Ensemble (Votação)',
    'sequencias': '🧬 Sequências (Clusters+Vizinhança)',
    'wheel': '🎯 Wheel (Cobertura)',
    'candidatos_ouro': '🥇 Candidatos Ouro',
    'momentum': '🚀 Momentum',
    'vizinhanca': '📍 Vizinhança',
    'frequencia_desvio': '📊 Frequência+Desvio',
    'pares_frequentes': '👫 Pares Frequentes',
    'ciclos': '🔁 Ciclos',
    'atraso_recente': '🕰️ Atraso Recente',
    'automl': '🤖 AutoML',
    'Manual': '✍️ Manual'
}

def _nome_estrategia(key):
    return NOMES_ESTRATEGIAS.get(key, str(key))


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def pagina_piloto_automatico(df):
    """Página do Piloto Automático"""

    st.title("🤖 Piloto Automático")
    st.markdown("### O sistema roda sozinho: confere resultados e gera novos cartões automaticamente")

    # ----- INICIALIZAR SESSION STATE A PARTIR DO ARQUIVO -----
    if 'piloto_config_loaded' not in st.session_state:
        config = _carregar_config()
        st.session_state['piloto_ativo'] = config['ativo']
        st.session_state['piloto_intervalo'] = config['intervalo']
        st.session_state['piloto_qtd_numeros'] = config['qtd_numeros']
        st.session_state['piloto_cartoes_por_est'] = config['cartoes_por_est']
        st.session_state['piloto_cartoes_ensemble'] = config['cartoes_ensemble']
        st.session_state['piloto_ensemble_only'] = config['ensemble_only']
        st.session_state['piloto_whatsapp_ativo'] = config['whatsapp_ativo']
        st.session_state['piloto_whatsapp_telefone'] = config['whatsapp_telefone']
        st.session_state['piloto_whatsapp_apikey'] = config['whatsapp_apikey']
        # Inicializar chaves dos widgets diretamente para garantir valor correto
        st.session_state['toggle_whatsapp'] = config['whatsapp_ativo']
        st.session_state['input_wa_telefone'] = config['whatsapp_telefone']
        st.session_state['input_wa_apikey'] = config['whatsapp_apikey']
        st.session_state['piloto_ciclo'] = 0
        st.session_state['piloto_config_loaded'] = True

    # ----- CONTROLES -----
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)

    with col_ctrl1:
        ativo = st.toggle(
            "⚡ Piloto Automático ATIVO",
            value=st.session_state['piloto_ativo'],
            key="toggle_piloto",
            help="Ativa/desativa o auto-refresh e execução automática"
        )
        st.session_state['piloto_ativo'] = ativo

    with col_ctrl2:
        intervalo = st.select_slider(
            "⏱️ Intervalo de atualização",
            options=[1, 2, 5, 10, 15, 30, 60],
            value=st.session_state['piloto_intervalo'],
            key="slider_intervalo",
            format_func=lambda x: f"{x} min",
            help="De quanto em quanto tempo o sistema verifica novidades"
        )
        st.session_state['piloto_intervalo'] = intervalo

    with col_ctrl3:
        qtd_numeros = st.select_slider(
            "🔢 Números por cartão",
            options=list(range(6, 21)),
            value=st.session_state['piloto_qtd_numeros'],
            key="slider_qtd_nums",
            help="Quantidade de números em cada cartão gerado"
        )
        st.session_state['piloto_qtd_numeros'] = qtd_numeros

    # ----- MODO ENSEMBLE ONLY -----
    ensemble_only = st.toggle(
        "🧠 Modo Ensemble Only",
        value=st.session_state['piloto_ensemble_only'],
        key="toggle_ensemble_only",
        help="Gera cartões APENAS da estratégia Ensemble adaptativa, que vota usando só as estratégias com melhor desempenho recente."
    )
    st.session_state['piloto_ensemble_only'] = ensemble_only

    if ensemble_only:
        st.info("🧠 **Modo Ensemble Only ativo** — Apenas cartões ensemble serão gerados com base nas estratégias mais fortes do ranking atual.")
        cartoes_ensemble = st.slider(
            "🧠 Cartões Ensemble", 5, 50,
            value=st.session_state['piloto_cartoes_ensemble'],
            key="slider_cartoes_ensemble",
            help="Quantos cartões ensemble gerar. Recomendado: 30-50"
        )
        st.session_state['piloto_cartoes_ensemble'] = cartoes_ensemble
        cartoes_por_estrategia = st.session_state['piloto_cartoes_por_est']
    else:
        col_cart1, col_cart2 = st.columns(2)
        with col_cart1:
            cartoes_por_estrategia = st.slider(
                "📋 Cartões por estratégia", 1, 20,
                value=st.session_state['piloto_cartoes_por_est'],
                key="slider_cartoes_est",
                help="Quantos cartões gerar para cada estratégia"
            )
            st.session_state['piloto_cartoes_por_est'] = cartoes_por_estrategia

        with col_cart2:
            cartoes_ensemble = st.slider(
                "🧠 Cartões Ensemble (extra)", 1, 50,
                value=st.session_state['piloto_cartoes_ensemble'],
                key="slider_cartoes_ensemble",
                help="Ensemble gera mais cartões para ampliar a cobertura da votação entre as estratégias mais fortes. Recomendado: 30-50"
            )
            st.session_state['piloto_cartoes_ensemble'] = cartoes_ensemble

    # ----- NOTIFICAÇÕES WHATSAPP -----
    with st.expander("📲 Notificações WhatsApp", expanded=False):
        st.caption(
            "Receba resultados e acertos no seu WhatsApp via CallMeBot (gratuito). "
            "Para ativar, envie a mensagem *I allow callmebot to send me messages* "
            "para o número **+34 644 59 71 67** no WhatsApp e anote a API key recebida."
        )

        col_wa1, col_wa2 = st.columns(2)

        with col_wa1:
            wa_ativo = st.toggle(
                "Notificar via WhatsApp",
                value=st.session_state['piloto_whatsapp_ativo'],
                key="toggle_whatsapp",
                help="Envia resultado do concurso, acertos e ranking por WhatsApp"
            )
            st.session_state['piloto_whatsapp_ativo'] = wa_ativo

        with col_wa2:
            if wa_ativo:
                if st.button("📨 Testar Notificação", use_container_width=True):
                    tel = st.session_state['piloto_whatsapp_telefone']
                    key = st.session_state['piloto_whatsapp_apikey']
                    if tel and key:
                        res = notif.enviar_whatsapp(tel, key, "✅ Teste do Piloto Automático MegaSena — notificações funcionando!")
                        if res['sucesso']:
                            st.success(res['mensagem'])
                        else:
                            st.error(res['mensagem'])
                    else:
                        st.warning("Preencha telefone e API key primeiro.")

        if wa_ativo:
            wa_telefone = st.text_input(
                "📱 Telefone (com código do país)",
                value=st.session_state['piloto_whatsapp_telefone'],
                key="input_wa_telefone",
                placeholder="5511999999999",
                help="Número completo com código do país, sem + ou espaços"
            )
            st.session_state['piloto_whatsapp_telefone'] = wa_telefone

            wa_apikey = st.text_input(
                "🔑 API Key do CallMeBot",
                value=st.session_state['piloto_whatsapp_apikey'],
                key="input_wa_apikey",
                type="password",
                help="Chave recebida ao registrar no CallMeBot"
            )
            st.session_state['piloto_whatsapp_apikey'] = wa_apikey

    # ----- SALVAR CONFIG NO DISCO (somente quando muda) -----
    nova_config = {
        'ativo': ativo,
        'intervalo': intervalo,
        'qtd_numeros': qtd_numeros,
        'cartoes_por_est': cartoes_por_estrategia,
        'cartoes_ensemble': cartoes_ensemble,
        'ensemble_only': ensemble_only,
        'whatsapp_ativo': st.session_state['piloto_whatsapp_ativo'],
        'whatsapp_telefone': st.session_state['piloto_whatsapp_telefone'],
        'whatsapp_apikey': st.session_state['piloto_whatsapp_apikey']
    }
    if nova_config != st.session_state.get('_piloto_ultima_config'):
        _salvar_config(nova_config)
        st.session_state['_piloto_ultima_config'] = nova_config

    # ----- AUTO-REFRESH -----
    if ativo:
        count = st_autorefresh(
            interval=intervalo * 60 * 1000,  # ms
            limit=None,
            key="piloto_auto_refresh"
        )
        st.session_state['piloto_ciclo'] = count
        if not HAS_AUTOREFRESH:
            st.info("ℹ️ Auto-refresh em modo compatibilidade (fallback interno).")
    else:
        count = 0

    st.markdown("---")

    # Carregar cartoes uma unica vez por rerun e repassar para as funcoes
    todos_cartoes = dm.carregar_cartoes_salvos()

    # ----- STATUS DO SISTEMA -----
    _exibir_status_sistema(df, ativo, intervalo, count, todos_cartoes)

    # ----- COMPOSIÇÃO ATUAL DO ENSEMBLE -----
    _exibir_composicao_ensemble()

    st.markdown("---")

    # ----- EXECUÇÃO AUTOMÁTICA -----
    if ativo:
        # Guard de ciclo: so executa conferencia/geracao uma vez por ciclo de autorefresh
        # (evita rodar a cada interacao de widget do usuario)
        ultimo_ciclo_executado = st.session_state.get('_piloto_ciclo_executado', -1)
        if count != ultimo_ciclo_executado:
            st.session_state['_piloto_ciclo_executado'] = count
            with st.spinner("🔄 Verificando novidades..."):
                resultado_conferencia = _auto_conferir(df, todos_cartoes=todos_cartoes)
                resultado_geracao = _auto_gerar(df, qtd_numeros, cartoes_por_estrategia, cartoes_ensemble=cartoes_ensemble, ensemble_only=ensemble_only, todos_cartoes=todos_cartoes)
            st.session_state['_piloto_ultimo_resultado_conf'] = resultado_conferencia
            st.session_state['_piloto_ultimo_resultado_ger'] = resultado_geracao
        else:
            resultado_conferencia = st.session_state.get('_piloto_ultimo_resultado_conf')
            resultado_geracao = st.session_state.get('_piloto_ultimo_resultado_ger')

        # Enviar WhatsApp se configurado e houve conferência
        if (
            resultado_conferencia
            and resultado_conferencia.get('status') == 'conferido'
            and st.session_state.get('piloto_whatsapp_ativo')
            and st.session_state.get('piloto_whatsapp_telefone')
            and st.session_state.get('piloto_whatsapp_apikey')
        ):
            mensagem = notif.formatar_resultado_concurso(resultado_conferencia)
            res_wa = notif.enviar_whatsapp(
                st.session_state['piloto_whatsapp_telefone'],
                st.session_state['piloto_whatsapp_apikey'],
                mensagem
            )
            if res_wa['sucesso']:
                st.toast("📲 Resultado enviado por WhatsApp!")
            else:
                st.toast(f"⚠️ Falha no WhatsApp: {res_wa['mensagem']}")

        # Mostrar log de ações
        _exibir_log_acoes(resultado_conferencia, resultado_geracao)
    else:
        st.info("⏸️ Piloto automático está **desativado**. Ative o toggle acima para iniciar.")

    st.markdown("---")

    # ----- DASHBOARD -----
    _exibir_dashboard(df, todos_cartoes)

    # ----- BOTÕES MANUAIS -----
    st.markdown("---")
    st.subheader("🔧 Ações Manuais")
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        if st.button("🔍 Conferir Agora", type="primary", use_container_width=True):
            with st.spinner("Conferindo..."):
                resultado = _auto_conferir(df, forcar=True)
                _exibir_log_acoes(resultado, None)

    with col_m2:
        if st.button("🎲 Gerar Agora", type="primary", use_container_width=True):
            with st.spinner("Gerando..."):
                resultado = _auto_gerar(df, qtd_numeros, cartoes_por_estrategia, cartoes_ensemble=cartoes_ensemble, ensemble_only=ensemble_only, forcar=True)
                _exibir_log_acoes(None, resultado)

    with col_m3:
        if st.button("🔄 Atualizar Dashboard", use_container_width=True):
            st.rerun()


# =============================================================================
# STATUS DO SISTEMA
# =============================================================================

def _exibir_status_sistema(df, ativo, intervalo, count, todos_cartoes):
    """Mostra cards com status atual"""

    verificados = [c for c in todos_cartoes if c.get('verificado', False)]
    pendentes = [c for c in todos_cartoes if not c.get('verificado', False)]

    concursos_pendentes = sorted(set(
        c.get('concurso_alvo') for c in pendentes if c.get('concurso_alvo')
    ))

    proximo_concurso = int(df['concurso'].max()) + 1 if 'concurso' in df.columns else "?"
    ultimo_concurso = int(df['concurso'].max()) if 'concurso' in df.columns else "?"

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        status_txt = "🟢 ATIVO" if ativo else "🔴 PARADO"
        st.metric("Status", status_txt)

    with col2:
        st.metric("📊 Total Cartões", len(todos_cartoes))

    with col3:
        st.metric("✅ Verificados", len(verificados))

    with col4:
        st.metric("⏳ Pendentes", len(pendentes))

    with col5:
        st.metric("🎯 Próximo Concurso", proximo_concurso)

    # Info adicional
    if concursos_pendentes:
        st.info(f"⏳ Concursos aguardando resultado: **{', '.join(map(str, concursos_pendentes))}**")

    if ativo:
        agora = datetime.now().strftime("%H:%M:%S")
        proxima = (datetime.now() + timedelta(minutes=intervalo)).strftime("%H:%M:%S")
        st.caption(f"🕐 Última verificação: {agora} | Próxima: ~{proxima} | Ciclo #{count}")


# =============================================================================
# COMPOSIÇÃO DO ENSEMBLE
# =============================================================================

def _exibir_composicao_ensemble():
    """Mostra quais estratégias estão dentro/fora do ensemble agora."""
    composicao = gen.composicao_ensemble_atual()
    if not composicao:
        return

    dentro = [c for c in composicao if c['status'] == 'dentro']
    fora = [c for c in composicao if c['status'] == 'fora']

    with st.expander(f"🧠 Composição do Ensemble — {len(dentro)} dentro / {len(fora)} fora", expanded=False):
        st.caption(
            "O ensemble vota apenas com as estratégias que acertaram terno+ "
            "nos últimos concursos. Quem fica 2 concursos seguidos sem terno+ sai."
        )
        if dentro:
            nomes_in = ' · '.join(NOMES_ESTRATEGIAS.get(c['estrategia'], c['estrategia']) for c in dentro)
            st.success(f"**Dentro:** {nomes_in}")
        if fora:
            linhas_fora = []
            for c in fora:
                nome = NOMES_ESTRATEGIAS.get(c['estrategia'], c['estrategia'])
                linhas_fora.append(f"{nome} (streak {c['streak_sem_terno']})")
            st.error(f"**Fora:** {' · '.join(linhas_fora)}")


# =============================================================================
# AUTO-CONFERIR
# =============================================================================

def _auto_conferir(df, forcar=False, todos_cartoes=None):
    """Confere automaticamente todos os concursos pendentes"""

    if todos_cartoes is None:
        todos_cartoes = dm.carregar_cartoes_salvos()
    pendentes_por_concurso = {}

    for c in todos_cartoes:
        if not c.get('verificado', False) and c.get('concurso_alvo'):
            conc = c['concurso_alvo']
            pendentes_por_concurso.setdefault(conc, []).append(c)

    if not pendentes_por_concurso:
        return {'status': 'sem_pendentes', 'mensagem': 'Nenhum concurso pendente', 'conferidos': []}

    conferidos = []
    alterou = False

    for concurso in sorted(pendentes_por_concurso.keys()):
        # Buscar resultado
        resultado = _buscar_resultado(df, concurso)

        if not resultado:
            continue  # Ainda não sorteado

        # Conferir cada cartão
        jogos_concurso = pendentes_por_concurso[concurso]
        stats_concurso = {}
        detalhes_concurso = dm.buscar_detalhes_concurso(concurso)

        for jogo in jogos_concurso:
            acertos = len(set(jogo['dezenas']) & set(resultado))
            jogo['acertos'] = acertos
            jogo['verificado'] = True
            jogo['resultado_concurso'] = resultado
            jogo['data_verificacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            est = jogo.get('estrategia', 'N/A')
            if est not in stats_concurso:
                stats_concurso[est] = {
                    'total_jogos': 0, 'total_acertos': 0,
                    'senas': 0, 'quinas': 0, 'quadras': 0, 'ternos': 0,
                    'melhor_acerto': 0, 'media_acertos': 0
                }
            s = stats_concurso[est]
            s['total_jogos'] += 1
            s['total_acertos'] += acertos
            s['melhor_acerto'] = max(s['melhor_acerto'], acertos)
            if acertos == 6:
                s['senas'] += 1
            elif acertos == 5:
                s['quinas'] += 1
            elif acertos == 4:
                s['quadras'] += 1
            elif acertos == 3:
                s['ternos'] += 1

        # Calcular médias
        for est in stats_concurso:
            t = stats_concurso[est]['total_jogos']
            stats_concurso[est]['media_acertos'] = round(
                stats_concurso[est]['total_acertos'] / t, 2) if t > 0 else 0

        # Arquivar no histórico
        dm.salvar_historico_analise(
            concurso,
            datetime.now().strftime("%Y-%m-%d"),
            stats_concurso,
            resultado
        )

        melhor = max(j.get('acertos', 0) for j in jogos_concurso)
        conferidos.append({
            'concurso': concurso,
            'resultado': resultado,
            'total_jogos': len(jogos_concurso),
            'melhor_acerto': melhor,
            'stats': stats_concurso,
            'acumulou': detalhes_concurso.get('acumulou'),
            'valor_proximo_concurso': detalhes_concurso.get('valor_proximo_concurso')
        })
        alterou = True

    # Salvar cartões atualizados
    if alterou:
        dm.salvar_cartoes(todos_cartoes)

    return {
        'status': 'conferido' if conferidos else 'sem_resultado',
        'mensagem': f'{len(conferidos)} concurso(s) conferido(s)' if conferidos else 'Nenhum resultado novo disponível',
        'conferidos': conferidos
    }


# =============================================================================
# AUTO-GERAR
# =============================================================================

@st.cache_data(show_spinner=False)
def _calcular_estatisticas_cache(df):
    """Wrapper cacheado de stats.calcular_estatisticas — evita recomputar a cada rerun."""
    return stats.calcular_estatisticas(df)


def _auto_gerar(df, qtd_numeros, cartoes_por_estrategia, cartoes_ensemble=None, ensemble_only=False, forcar=False, todos_cartoes=None):
    """Gera cartões automaticamente para o próximo concurso"""

    proximo = int(df['concurso'].max()) + 1 if 'concurso' in df.columns else None
    if not proximo:
        return {'status': 'erro', 'mensagem': 'Não foi possível determinar próximo concurso', 'gerados': 0}

    if todos_cartoes is None:
        todos_cartoes = dm.carregar_cartoes_salvos()
    ja_existem = [c for c in todos_cartoes if c.get('concurso_alvo') == proximo and not c.get('verificado', False)]

    if ja_existem and not forcar:
        return {
            'status': 'ja_existe',
            'mensagem': f'Já existem {len(ja_existem)} cartões para o concurso {proximo}',
            'gerados': 0,
            'concurso': proximo
        }

    # Gerar cartões
    contagem_total, contagem_recente, df_atrasos = _calcular_estatisticas_cache(df)
    novos_cartoes = []

    estrategias_ativas = ['ensemble'] if ensemble_only else TODAS_ESTRATEGIAS
    for estrategia in estrategias_ativas:
        qtd = cartoes_ensemble if (estrategia == 'ensemble' and cartoes_ensemble) else cartoes_por_estrategia
        for i in range(qtd):
            try:
                # Gerar jogo base (6 números)
                dezenas_base = gen.gerar_jogo(
                    estrategia=estrategia,
                    contagem_total=contagem_total,
                    contagem_recente=contagem_recente,
                    df_atrasos=df_atrasos,
                    df=df
                )

                # Expandir se necessário
                if qtd_numeros > 6:
                    dezenas = gen.expandir_jogo(
                        dezenas_base, qtd_numeros, estrategia,
                        contagem_total, contagem_recente, df_atrasos, df=df
                    )
                else:
                    dezenas = dezenas_base

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                cartao = {
                    'id': f'AUTO-{estrategia.upper()}-{timestamp}-{i+1:02d}',
                    'dezenas': sorted(dezenas),
                    'estrategia': estrategia,
                    'estrategia_versao': versao_estrategia(estrategia),
                    'vai_jogar': True,
                    'verificado': False,
                    'concurso_alvo': proximo,
                    'status': 'aguardando',
                    'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'qtd_numeros': qtd_numeros,
                    'origem': 'piloto_automatico'
                }
                novos_cartoes.append(cartao)
            except Exception as e:
                pass  # Silenciar erros de geração individual

    if novos_cartoes:
        todos_cartoes.extend(novos_cartoes)
        dm.salvar_cartoes(todos_cartoes)

    return {
        'status': 'gerado',
        'mensagem': f'{len(novos_cartoes)} cartões gerados para o concurso {proximo}',
        'gerados': len(novos_cartoes),
        'concurso': proximo
    }


# =============================================================================
# LOG DE AÇÕES
# =============================================================================

def _exibir_log_acoes(resultado_conferencia, resultado_geracao):
    """Mostra o resultado das ações automáticas"""

    st.subheader("📋 Log de Ações")

    if resultado_conferencia:
        status = resultado_conferencia['status']
        if status == 'conferido':
            for conf in resultado_conferencia['conferidos']:
                nums = " - ".join([f"**{n:02d}**" for n in conf['resultado']])
                melhor = conf['melhor_acerto']

                if melhor >= 4:
                    st.success(
                        f"🎉 **Concurso {conf['concurso']}** conferido! "
                        f"Resultado: {nums} | "
                        f"**Melhor acerto: {melhor}!** | "
                        f"{conf['total_jogos']} jogos verificados"
                    )
                else:
                    st.info(
                        f"✅ **Concurso {conf['concurso']}** conferido | "
                        f"Resultado: {nums} | "
                        f"Melhor acerto: {melhor} | "
                        f"{conf['total_jogos']} jogos verificados"
                    )

                # Mini-ranking
                if conf['stats']:
                    ranking_items = sorted(
                        conf['stats'].items(),
                        key=lambda x: x[1]['media_acertos'],
                        reverse=True
                    )
                    top = ranking_items[0]
                    st.caption(
                        f"🏆 Melhor estratégia: {_nome_estrategia(top[0])} "
                        f"(média {top[1]['media_acertos']:.2f} acertos)"
                    )
        elif status == 'sem_pendentes':
            st.caption("✅ Nenhum concurso pendente de conferência")
        elif status == 'sem_resultado':
            st.caption("⏳ Resultado(s) ainda não disponível(is)")

    if resultado_geracao:
        status = resultado_geracao['status']
        if status == 'gerado':
            st.success(f"🎲 {resultado_geracao['mensagem']}")
        elif status == 'ja_existe':
            st.caption(f"📌 {resultado_geracao['mensagem']}")
        elif status == 'erro':
            st.warning(f"⚠️ {resultado_geracao['mensagem']}")


# =============================================================================
# DASHBOARD
# =============================================================================

def _exibir_dashboard(df, todos_cartoes=None):
    """Dashboard com ranking e estatísticas consolidadas"""

    st.subheader("🏆 Dashboard - Ranking de Estratégias")

    if todos_cartoes is None:
        todos_cartoes = dm.carregar_cartoes_salvos()
    verificados = [c for c in todos_cartoes if c.get('verificado', False) and c.get('acertos') is not None]

    if not verificados:
        st.info("📭 Nenhum cartão verificado ainda. O ranking aparecerá após a primeira conferência.")
        return

    # Calcular ranking
    ranking = {}
    for c in verificados:
        est = c.get('estrategia', 'N/A')
        if est not in ranking:
            ranking[est] = {
                'jogos': 0, 'total_acertos': 0,
                'senas': 0, 'quinas': 0, 'quadras': 0, 'ternos': 0,
                'melhor_acerto': 0, 'concursos': set()
            }
        r = ranking[est]
        r['jogos'] += 1
        acertos = c.get('acertos', 0)
        r['total_acertos'] += acertos
        r['melhor_acerto'] = max(r['melhor_acerto'], acertos)
        if acertos == 6:
            r['senas'] += 1
        elif acertos == 5:
            r['quinas'] += 1
        elif acertos == 4:
            r['quadras'] += 1
        elif acertos == 3:
            r['ternos'] += 1
        if c.get('concurso_alvo'):
            r['concursos'].add(c['concurso_alvo'])

    # Montar lista rankeada
    ranking_lista = []
    for est, dados in ranking.items():
        score = dados['senas'] * 10000 + dados['quinas'] * 1000 + dados['quadras'] * 100 + dados['ternos'] * 10 + dados['melhor_acerto']
        ranking_lista.append({
            'Estratégia': _nome_estrategia(est),
            'Jogos': dados['jogos'],
            'Senas': dados['senas'],
            'Quinas': dados['quinas'],
            'Quadras': dados['quadras'],
            'Ternos': dados['ternos'],
            'Melhor': dados['melhor_acerto'],
            'Concursos': len(dados['concursos']),
            'Score': score
        })

    ranking_lista.sort(key=lambda x: x['Score'], reverse=True)

    # Top 3
    for i, item in enumerate(ranking_lista[:3]):
        medalha = ["🥇", "🥈", "🥉"][i]
        cols = st.columns([1, 3, 5])
        cols[0].markdown(f"### {medalha}")
        cols[1].markdown(f"**{item['Estratégia']}**\n\n{item['Jogos']} jogos em {item['Concursos']} concurso(s)")
        premios = []
        if item['Senas']:
            premios.append(f"🏆 {item['Senas']} Sena")
        if item['Quinas']:
            premios.append(f"⭐ {item['Quinas']} Quina")
        if item['Quadras']:
            premios.append(f"🎯 {item['Quadras']} Quadra")
        if item['Ternos']:
            premios.append(f"✅ {item['Ternos']} Terno")
        resumo = " | ".join(premios) if premios else "Nenhum prêmio ainda"
        cols[2].markdown(f"\n\n{resumo}")
        st.markdown("---")

    # Tabela completa
    with st.expander("📊 Tabela completa", expanded=False):
        df_ranking = pd.DataFrame(ranking_lista)
        st.dataframe(df_ranking, use_container_width=True, hide_index=True)

    # Gráfico
    if len(ranking_lista) > 1:
        st.markdown("### 📈 Comparativo Visual")
        df_grafico = pd.DataFrame({
            'Estratégia': [r['Estratégia'] for r in ranking_lista],
            'Ternos': [r['Ternos'] for r in ranking_lista],
            'Quadras': [r['Quadras'] for r in ranking_lista],
            'Quinas': [r['Quinas'] for r in ranking_lista],
            'Senas': [r['Senas'] for r in ranking_lista],
        })
        st.bar_chart(df_grafico.set_index('Estratégia'))

    # Últimos concursos conferidos
    concursos_verificados = sorted(set(
        c.get('concurso_alvo') for c in verificados if c.get('concurso_alvo')
    ), reverse=True)

    if concursos_verificados:
        st.markdown("### 🗓️ Últimos Concursos")
        for concurso in concursos_verificados[:5]:
            jogos_c = [c for c in verificados if c.get('concurso_alvo') == concurso]
            melhor = max(c.get('acertos', 0) for c in jogos_c)
            resultado = jogos_c[0].get('resultado_concurso', [])

            # Contar prêmios do concurso
            n_senas = sum(1 for c in jogos_c if c.get('acertos', 0) == 6)
            n_quinas = sum(1 for c in jogos_c if c.get('acertos', 0) == 5)
            n_quadras = sum(1 for c in jogos_c if c.get('acertos', 0) == 4)
            n_ternos = sum(1 for c in jogos_c if c.get('acertos', 0) == 3)

            icone = "🎉" if melhor >= 4 else "✅"
            nums = " - ".join([f"{n:02d}" for n in sorted(resultado)]) if resultado else "?"

            premios_resumo = []
            if n_senas:
                premios_resumo.append(f"{n_senas} Sena")
            if n_quinas:
                premios_resumo.append(f"{n_quinas} Quina")
            if n_quadras:
                premios_resumo.append(f"{n_quadras} Quadra")
            if n_ternos:
                premios_resumo.append(f"{n_ternos} Terno")
            premios_txt = " | ".join(premios_resumo) if premios_resumo else "Sem prêmio"

            with st.expander(
                f"{icone} Concurso {concurso} | {nums} | "
                f"{len(jogos_c)} jogos | {premios_txt}"
            ):
                por_est = {}
                for c in jogos_c:
                    est = c.get('estrategia', 'N/A')
                    por_est.setdefault(est, []).append(c.get('acertos', 0))

                for est, acertos_list in sorted(por_est.items(), key=lambda x: max(x[1]), reverse=True):
                    mx = max(acertos_list)
                    t = sum(1 for a in acertos_list if a == 3)
                    q = sum(1 for a in acertos_list if a == 4)
                    qi = sum(1 for a in acertos_list if a == 5)
                    s = sum(1 for a in acertos_list if a == 6)
                    partes = []
                    if s:
                        partes.append(f"{s} Sena")
                    if qi:
                        partes.append(f"{qi} Quina")
                    if q:
                        partes.append(f"{q} Quadra")
                    if t:
                        partes.append(f"{t} Terno")
                    det = " | ".join(partes) if partes else f"Melhor: {mx}"
                    st.markdown(
                        f"**{_nome_estrategia(est)}**: {len(acertos_list)} jogos | {det}"
                    )


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _buscar_resultado(df, concurso):
    """Busca resultado de um concurso"""
    max_concurso_df = int(df['concurso'].max()) if 'concurso' in df.columns else 0

    if concurso <= max_concurso_df:
        linha = df[df['concurso'] == concurso]
        if not linha.empty:
            row = linha.iloc[0]
            dezenas = []
            if 'dez1' in df.columns:
                for i in range(1, 7):
                    try:
                        dezenas.append(int(row.get(f'dez{i}')))
                    except (ValueError, TypeError):
                        pass
            if len(dezenas) == 6:
                return sorted(dezenas)

    return dm.buscar_resultado_concurso(concurso)


def _expandir_jogo(dezenas_base, qtd_numeros, estrategia,
                   contagem_total, contagem_recente, df_atrasos, df):
    """Expande um jogo de 6 para N números baseado na estratégia"""
    pool_size = max(40, qtd_numeros + 10)
    if estrategia == 'atrasados':
        candidatos = contagem_total.sort_values().head(pool_size).index.tolist()
    elif estrategia == 'quentes':
        candidatos = contagem_recente.nlargest(pool_size).index.tolist()
    elif estrategia == 'escada':
        _, _, _, _, _, inversoes = stats.calcular_escada_temporal(df)
        candidatos = [inv['numero'] for inv in inversoes[:pool_size]] if inversoes else list(range(1, 61))
    else:
        candidatos = list(range(1, 61))

    candidatos = [n for n in candidatos if n not in dezenas_base]
    random.shuffle(candidatos)
    extras = candidatos[:qtd_numeros - 6]
    return sorted(dezenas_base + extras)
